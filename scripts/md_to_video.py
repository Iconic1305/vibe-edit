"""Markdown -> HyperFrames project generator (stdlib only).

Usage:
    python3 scripts/md_to_video.py <brief.md> <project-dir> [--lang en]

Reads a guide-style Markdown file and writes, inside an existing HyperFrames project:
    source/brief.md       copy of the brief
    source/scenes.json    the parsed scenes (edit + rerun with --from-json to hand-tune)
    index.html            root composition, one host per scene
    compositions/*.html   one sub-composition per scene

Mapping:
    # H1                       -> title scene headline
    first line before any ##   -> byline
    first un-numbered ##       -> title scene tagline (+ its first line as the sub-line)
    ## NN · Name               -> one scene (kicker "NN · NAME")
      first ###                -> scene headline, its first sentences -> lede
      other ###                -> rows on the right (leading "NN · " and "Prompt · " removed, max 7)
      ### Source credit        -> small footer on the scene
      no rows                  -> centred "statement" layout

Everything is silent and text-driven: no voiceover or music is invented.
"""
import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

W, H, FPS = 1920, 1080, 30
BG, INK, ACCENT, MUTED = "#0d0f14", "#f5f5f0", "#FFD400", "#8b93a3"
MAX_ROWS = 7
SKIP_H3 = re.compile(r"^(what's inside|source credit)\b", re.I)
NUMBERED = re.compile(r"^(\d{2})\s*·\s*(.+)$")


# ---------- parsing ----------
def clean(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)       # [text](url) -> text
    s = re.sub(r"[`*_]{1,3}", "", s)
    return re.sub(r"\s+", " ", s).strip()


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text.strip())


def lede(lines, limit):
    """First prose line, trimmed to whole sentences that fit within `limit` characters."""
    for ln in lines:
        if ln.startswith(("-", "|", "http", "*", "`", "!")) or len(ln.split()) < 4:
            continue
        out = ""
        for s in sentences(clean(ln)):
            if len(out) + len(s) + 1 <= limit:
                out = f"{out} {s}".strip()
            else:
                break
        if out:
            return out
        first = clean(ln)
        return first[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return ""


def parse(md):
    h1, pre, sections, cur, sub, in_code = "", [], [], None, None, False
    for raw in md.splitlines():
        ln = raw.rstrip()
        if ln.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if ln.startswith("# "):
            h1 = clean(ln[2:])
        elif ln.startswith("## "):
            cur = {"title": clean(ln[3:]), "intro": [], "subs": []}
            sections.append(cur)
            sub = None
        elif ln.startswith("### ") and cur is not None:
            sub = {"title": clean(ln[4:]), "body": []}
            cur["subs"].append(sub)
        elif ln.strip():
            if cur is None:
                pre.append(clean(ln))
            else:
                (sub["body"] if sub else cur["intro"]).append(ln.strip())

    scenes = []
    tagline = next((s for s in sections if not NUMBERED.match(s["title"])), None)
    scenes.append({
        "kind": "title", "id": "s00", "headline": h1,
        "byline": pre[0] if pre else "",
        "tagline": tagline["title"] if tagline else "",
        "sub": clean(tagline["intro"][0]) if tagline and tagline["intro"] else "",
    })
    numbered = [s for s in sections if NUMBERED.match(s["title"])]
    for i, s in enumerate(numbered, 1):
        num, name = NUMBERED.match(s["title"]).groups()
        subs = s["subs"]
        head = subs[0] if subs else {"title": name, "body": []}
        rows = []
        for r in subs[1:]:
            if SKIP_H3.match(r["title"]):
                continue
            t = re.sub(r"^(\d{2}\s*·\s*|Prompt\s*·\s*)", "", r["title"]).strip()
            rows.append(t)
        credit = next((lede(r["body"], 200) for r in subs if r["title"].lower().startswith("source credit")), "")
        statement = not rows
        scenes.append({
            "kind": "statement" if statement else "split", "id": f"s{i:02d}",
            "index": i, "total": len(numbered),
            "kicker": f"{num} · {name}".upper(),
            "headline": head["title"],
            "lede": lede(head["body"] or s["intro"], 230 if statement else 160),
            "rows": rows[:MAX_ROWS], "credit": credit,
        })
    return scenes


def duration(sc):
    if sc["kind"] == "title":
        return 5.0
    words = len(sc.get("lede", "").split())
    return round(max(4.5, 3.2 + 0.5 * len(sc.get("rows", [])) + 0.1 * words), 1)


# ---------- html ----------
def e(s):
    return html.escape(s, quote=False)


def head_size(text, big, small):
    return small if len(text) > 28 else big


def css(sc):
    p = f"#{sc['id']}"
    c = f"""
    #root {{ position:absolute; inset:0; background:{BG}; font-family:'Inter',sans-serif; color:{INK}; overflow:hidden; }}
    {p}-wrap {{ position:absolute; inset:0; }}
    {p}-bg {{ position:absolute; inset:0; background:radial-gradient(1200px 700px at 85% 10%, #1b2230 0%, {BG} 70%); }}
    {p}-kicker {{ font-size:28px; font-weight:700; letter-spacing:.14em; color:{ACCENT}; }}
    {p}-head {{ font-weight:900; letter-spacing:-.03em; line-height:1.03; }}
    {p}-lede {{ font-size:30px; line-height:1.4; color:#c8ccd6; font-weight:400; }}
    {p}-prog {{ position:absolute; left:192px; right:192px; top:1000px; display:flex; gap:8px; }}
    {p}-prog i {{ flex:1; height:6px; background:#222836; border-radius:3px; position:relative; overflow:hidden; display:block; }}
    {p}-prog i b {{ position:absolute; inset:0; background:{ACCENT}; transform-origin:left center; display:block; }}
    """
    if sc["kind"] == "split":
        c += f"""
    {p}-left {{ position:absolute; left:192px; top:150px; width:700px; display:flex; flex-direction:column; gap:30px; }}
    {p}-head {{ font-size:{head_size(sc['headline'], 84, 68)}px; }}
    {p}-list {{ position:absolute; left:1000px; width:728px; top:130px; bottom:130px; list-style:none; display:flex; flex-direction:column; justify-content:center; gap:14px; }}
    {p}-list li {{ display:flex; align-items:center; gap:22px; min-height:78px; padding:14px 26px; background:#161b26; border-left:6px solid {ACCENT}; border-radius:4px; }}
    {p}-list .n {{ font-size:26px; font-weight:900; color:{ACCENT}; min-width:44px; }}
    {p}-list .t {{ font-size:34px; font-weight:700; line-height:1.2; }}
    """
    else:
        c += f"""
    {p}-center {{ position:absolute; left:192px; right:192px; top:0; bottom:0; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; gap:34px; }}
    {p}-head {{ font-size:{'104' if sc['kind']=='statement' else '128'}px; }}
    {p}-lede {{ max-width:1100px; }}
    {p}-sub {{ font-size:32px; color:#c8ccd6; font-weight:400; }}
    {p}-by {{ font-size:30px; font-weight:700; letter-spacing:.12em; color:{ACCENT}; text-transform:uppercase; }}
    {p}-credit {{ position:absolute; left:192px; right:192px; top:930px; text-align:center; font-size:22px; color:{MUTED}; }}
    """
    return c


def markup(sc, dur):
    i = sc["id"]
    out = [f'<div id="{i}-wrap" class="clip" data-start="0" data-duration="{dur}">', f'<div id="{i}-bg"></div>']
    if sc["kind"] == "title":
        out += [f'<div id="{i}-center">',
                f'<div id="{i}-by">{e(sc["byline"])}</div>',
                f'<h1 id="{i}-head">{e(sc["headline"])}</h1>',
                f'<div id="{i}-kicker">{e(sc["tagline"].upper())}</div>',
                f'<p id="{i}-sub">{e(sc["sub"])}</p></div>']
        return "\n".join(out + ["</div>"])
    if sc["kind"] == "split":
        out += [f'<div id="{i}-left"><div id="{i}-kicker">{e(sc["kicker"])}</div>',
                f'<h2 id="{i}-head">{e(sc["headline"])}</h2>',
                f'<p id="{i}-lede">{e(sc["lede"])}</p></div>', f'<ol id="{i}-list">']
        for n, r in enumerate(sc["rows"], 1):
            out.append(f'<li id="{i}-r{n}"><span class="n">{n:02d}</span><span class="t">{e(r)}</span></li>')
        out.append("</ol>")
    else:
        out += [f'<div id="{i}-center"><div id="{i}-kicker">{e(sc["kicker"])}</div>',
                f'<h2 id="{i}-head">{e(sc["headline"])}</h2>',
                f'<p id="{i}-lede">{e(sc["lede"])}</p></div>']
        if sc.get("credit"):
            out.append(f'<div id="{i}-credit">{e(sc["credit"])}</div>')
    segs = "".join(f'<i><b id="{i}-p{k}"></b></i>' for k in range(1, sc["total"] + 1))
    out.append(f'<div id="{i}-prog">{segs}</div>')
    return "\n".join(out + ["</div>"])


def script(sc, dur):
    i = sc["id"]
    t = ["const tl = gsap.timeline({ paused: true });"]
    fx = lambda sel, frm, to, at: t.append(f'tl.fromTo("{sel}", {frm}, {to}, {at});')
    if sc["kind"] == "title":
        fx(f"#{i}-by", "{opacity:0,y:-20}", "{opacity:1,y:0,duration:.5,ease:'power3.out'}", 0.2)
        fx(f"#{i}-head", "{opacity:0,y:60}", "{opacity:1,y:0,duration:.7,ease:'power4.out'}", 0.5)
        fx(f"#{i}-kicker", "{opacity:0,y:30}", "{opacity:1,y:0,duration:.5,ease:'power3.out'}", 1.3)
        fx(f"#{i}-sub", "{opacity:0}", "{opacity:1,duration:.6,ease:'power2.out'}", 1.9)
    else:
        fx(f"#{i}-kicker", "{opacity:0,x:-30}", "{opacity:1,x:0,duration:.5,ease:'power3.out'}", 0.1)
        fx(f"#{i}-head", "{opacity:0,y:50}", "{opacity:1,y:0,duration:.6,ease:'power4.out'}", 0.25)
        fx(f"#{i}-lede", "{opacity:0,y:20}", "{opacity:1,y:0,duration:.6,ease:'power2.out'}", 0.8)
        for n in range(1, len(sc.get("rows", [])) + 1):
            fx(f"#{i}-r{n}", "{opacity:0,x:70}", "{opacity:1,x:0,duration:.45,ease:'power3.out'}", round(1.1 + 0.5 * (n - 1), 2))
        if sc.get("credit"):
            fx(f"#{i}-credit", "{opacity:0}", "{opacity:1,duration:.6}", round(dur - 2.2, 2))
        for k in range(1, sc["total"] + 1):
            if k < sc["index"]:
                t.append(f'tl.set("#{i}-p{k}", {{scaleX:1}}, 0);')
            elif k == sc["index"]:
                fx(f"#{i}-p{k}", "{scaleX:0}", f"{{scaleX:1,duration:{max(dur - 1.0, 1):.1f},ease:'none'}}", 0.2)
            else:
                t.append(f'tl.set("#{i}-p{k}", {{scaleX:0}}, 0);')
    fx(f"#{i}-wrap", "{opacity:1}", "{opacity:0,duration:.25,ease:'power1.in'}", round(dur - 0.3, 2))
    t.append(f'window.__timelines["{i}"] = tl;')
    return "\n".join(t)


def scene_file(sc, dur):
    return (f"<template>\n<style>{css(sc)}</style>\n"
            f'<div id="root" data-composition-id="{sc["id"]}" data-width="{W}" data-height="{H}">\n{markup(sc, dur)}\n</div>\n'
            f"<script>\n{script(sc, dur)}\n</script>\n</template>\n")


def index_file(scenes, durs, title):
    hosts, t = [], 0.0
    for sc, d in zip(scenes, durs):
        hosts.append(f'      <div id="{sc["id"]}" data-composition-id="{sc["id"]}" data-composition-src="compositions/{sc["id"]}.html" '
                     f'data-start="{t:.1f}" data-duration="{d}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}"></div>')
        t += d
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(title)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {BG}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{t:.1f}" data-width="{W}" data-height="{H}">
{chr(10).join(hosts)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown")
    ap.add_argument("project")
    ap.add_argument("--from-json", action="store_true", help="skip parsing; rebuild from project/source/scenes.json")
    a = ap.parse_args()

    proj = Path(a.project)
    if not (proj / "hyperframes.json").exists():
        sys.exit(f"{proj} is not a HyperFrames project (run: npx hyperframes init {proj} --example blank)")
    (proj / "source").mkdir(exist_ok=True)
    (proj / "compositions").mkdir(exist_ok=True)

    sj = proj / "source" / "scenes.json"
    if a.from_json:
        scenes = json.loads(sj.read_text(encoding="utf-8"))
    else:
        md = Path(a.markdown)
        if md.resolve() != (proj / "source" / "brief.md").resolve():
            shutil.copyfile(md, proj / "source" / "brief.md")
        scenes = parse(md.read_text(encoding="utf-8"))
        sj.write_text(json.dumps(scenes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for old in (proj / "compositions").glob("s[0-9][0-9].html"):
        old.unlink()
    durs = [duration(s) for s in scenes]
    for sc, d in zip(scenes, durs):
        (proj / "compositions" / f"{sc['id']}.html").write_text(scene_file(sc, d), encoding="utf-8")
    (proj / "index.html").write_text(index_file(scenes, durs, scenes[0]["headline"]), encoding="utf-8")
    print(f"{len(scenes)} scenes · {sum(durs):.1f}s · {W}x{H}@{FPS}")
    for sc, d in zip(scenes, durs):
        print(f"  {sc['id']} {d:>4}s  {sc['kind']:<9} {sc['headline']}")


if __name__ == "__main__":
    main()
