"""Build the HyperFrames edit for a project from edit.json + word timings.

Usage:
    python3 scripts/build_edit.py projects/<slug>

Reads   project.json, edit.json, the words file (word-level timestamps) and the source video.
Writes  hyperframes/index.html, hyperframes/compositions/{captions,overlays,title}.html,
        hyperframes/assets/<video>, hyperframes/assets/sfx/*, work/build_report.json

Features (all driven by edit.json; see templates/edit.template.json):
  captions (pop | box | minimal, N words per group, active-word highlight)
  title card, lower third, punch-in zooms (manual by word/time + auto per sentence),
  jump-cut punch (alternating scale at each cut), flash transitions,
  pop-ups (image or text, bounce), 3D logo (CSS 3D spin + throw at camera),
  sound effects on every effect, background music, formats 9:16 / 16:9 / 1:1.
All timing comes from the transcript; a word that can't be found is reported, never guessed.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
STOP = set("the a an and or but if then so to of in on at for with from by is are was were be been it this that these those "
           "you your i me my we our they them their he she his her as not no yes just very really can will would could should "
           "have has had do does did there here what when where which who how why about into over under than too also".split())


def e(s):
    return html.escape(str(s), quote=True)


def norm(w):
    return re.sub(r"[^\w']+", "", w.lower())


def probe(path, entry="format=duration"):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entry, "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out.splitlines()[0]) if out else 0.0


class Ctx:
    def __init__(self, proj):
        self.proj = Path(proj).resolve()
        self.meta = json.loads((self.proj / "project.json").read_text())
        self.spec = json.loads((self.proj / "edit.json").read_text())
        self.fmt = self.spec.get("format", self.meta.get("format", "9:16"))
        if self.fmt not in FORMATS:
            sys.exit(f"edit.json format must be one of {list(FORMATS)}")
        self.W, self.H = FORMATS[self.fmt]
        st = self.spec["style"]
        self.accent, self.ink, self.font, self.bg = st["accent"], st["text"], st["font"], st["background"]
        self.warnings = []
        self.sfx_events = []   # (time, sound name)
        self.hf = self.proj / "hyperframes"

    def warn(self, msg):
        self.warnings.append(msg)
        print("  WARN", msg)


# ---------- transcript helpers ----------
def load_words(ctx):
    src = ctx.spec["source"]
    p = ctx.proj / src["words"]
    if not p.exists():
        ctx.warn(f"words file {src['words']} not found: building without captions/word-timed effects")
        return []
    return json.loads(p.read_text())["words"]


def find(words, key, nth=1):
    """Start/end of a word or phrase (case/punctuation-insensitive). Returns (start, end) or None."""
    toks = [norm(t) for t in str(key).split() if norm(t)]
    if not toks:
        return None
    seen = 0
    for i in range(len(words) - len(toks) + 1):
        if all(norm(words[i + k]["word"]) == toks[k] for k in range(len(toks))):
            seen += 1
            if seen == nth:
                return words[i]["start"], words[i + len(toks) - 1]["end"]
    return None


def when(ctx, words, item, t0, label):
    """Absolute time for an effect: item['at'] (seconds in the video) or item['when'] (a spoken word/phrase)."""
    if item.get("at") is not None:
        return float(item["at"]) + t0
    if item.get("when"):
        hit = find(words, item["when"], int(item.get("nth", 1)))
        if hit:
            return hit[0] + t0 + float(item.get("offset", 0))
        ctx.warn(f"{label}: word '{item['when']}' not found in transcript, effect skipped")
    else:
        ctx.warn(f"{label}: needs 'at' (seconds) or 'when' (spoken word), effect skipped")
    return None


# ---------- captions ----------
def caption_groups(words, n):
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or w["word"].endswith((".", "!", "?", "…")) or (len(cur) > 1 and w["word"].endswith((",", ";"))):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def build_captions(ctx, words, t0, total):
    c = ctx.spec["captions"]
    if not c.get("enabled") or not words:
        return None
    W, H = ctx.W, ctx.H
    size = c.get("size") or {"9:16": 84, "16:9": 64, "1:1": 72}[ctx.fmt]
    y = min(float(c.get("y", 0.65)), 0.70 if ctx.fmt == "9:16" else 0.80)   # keep out of the bottom 20% for Reels
    width = {"9:16": 0.74, "16:9": 0.70, "1:1": 0.78}[ctx.fmt]               # extra right margin on vertical for app buttons
    left = (1 - width) / 2 * 100 - (3 if ctx.fmt == "9:16" else 0)
    style = c.get("style", "pop")
    groups = caption_groups(words, int(c.get("words_per_group", 3)))
    css_word = {
        "pop": f"text-shadow:0 4px 0 rgba(0,0,0,.55),0 0 18px rgba(0,0,0,.6); -webkit-text-stroke:{max(size // 14, 4)}px rgba(0,0,0,.85); paint-order:stroke fill;",
        "box": f"",
        "minimal": "text-shadow:0 2px 12px rgba(0,0,0,.75);",
    }[style]
    box = "background:rgba(10,12,18,.82);padding:.18em .5em;border-radius:.3em;" if style == "box" else ""
    parts, js = [], ["const tl = gsap.timeline({ paused: true });"]
    for gi, g in enumerate(groups):
        gs = g[0]["start"] + t0
        nxt = groups[gi + 1][0]["start"] + t0 if gi + 1 < len(groups) else None
        ge = min(g[-1]["end"] + t0 + 0.35, nxt) if nxt else min(g[-1]["end"] + t0 + 0.5, total)
        ge = max(ge, gs + 0.2)
        spans = "".join(
            f'<span id="cw{gi}_{k}" class="cw">{e(w["word"].upper() if c.get("uppercase") else w["word"])}</span>'
            for k, w in enumerate(g))
        parts.append(f'<div id="cg{gi}" class="clip cg" data-start="{gs:.3f}" data-duration="{ge - gs:.3f}"><div id="cgi{gi}" class="cgi">{spans}</div></div>')
        js.append(f'tl.fromTo("#cgi{gi}",{{opacity:0,scale:.82,y:18}},{{opacity:1,scale:1,y:0,duration:.14,ease:"back.out(2)"}},{gs:.3f});')
        for k, w in enumerate(g):
            ws, we = w["start"] + t0, min(w["end"] + t0, ge)
            js.append(f'tl.fromTo("#cw{gi}_{k}",{{color:"{ctx.ink}"}},{{color:"{ctx.accent}",duration:.04}},{ws:.3f});')
            js.append(f'tl.fromTo("#cw{gi}_{k}",{{color:"{ctx.accent}"}},{{color:"{ctx.ink}",duration:.04,immediateRender:false}},{max(we, ws + .05):.3f});')
    js.append('window.__timelines["caps"] = tl;')
    scene = f"""<template>
<style>
#root {{ position:absolute; inset:0; font-family:'{ctx.font}',sans-serif; }}
.cg {{ position:absolute; left:{left:.1f}%; width:{width * 100:.1f}%; top:{y * 100:.1f}%; display:flex; justify-content:center; }}
.cgi {{ display:flex; flex-wrap:wrap; justify-content:center; gap:.18em .3em; font-size:{size}px; font-weight:900; line-height:1.1; text-align:center; {box} }}
.cw {{ color:{ctx.ink}; display:inline-block; {css_word} }}
</style>
<div id="root" data-composition-id="caps" data-width="{W}" data-height="{H}">
{chr(10).join(parts)}
</div>
<script>
{chr(10).join(js)}
</script>
</template>
"""
    (ctx.hf / "compositions" / "captions.html").write_text(scene, encoding="utf-8")
    return len(groups)


# ---------- title card ----------
def build_title(ctx, dur):
    t = ctx.spec["title_card"]
    W, H = ctx.W, ctx.H
    size = {"9:16": 120, "16:9": 130, "1:1": 110}[ctx.fmt]
    scene = f"""<template>
<style>
#root {{ position:absolute; inset:0; background:{ctx.bg}; font-family:'{ctx.font}',sans-serif; color:{ctx.ink}; }}
#t-wrap {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:36px; padding:0 {int(W * .12)}px; text-align:center; }}
#t-text {{ font-size:{size}px; font-weight:900; letter-spacing:-.03em; line-height:1.04; }}
#t-sub {{ font-size:{size // 3}px; font-weight:700; color:{ctx.accent}; letter-spacing:.06em; }}
</style>
<div id="root" data-composition-id="title" data-width="{W}" data-height="{H}">
<div id="t-wrap" class="clip" data-start="0" data-duration="{dur:.3f}">
<div id="t-text">{e(t['text'])}</div>{f'<div id="t-sub">{e(t["subtitle"])}</div>' if t.get('subtitle') else ''}
</div></div>
<script>
const tl = gsap.timeline({{ paused: true }});
tl.fromTo("#t-text",{{opacity:0,y:50,scale:.94}},{{opacity:1,y:0,scale:1,duration:.5,ease:"power4.out"}},0.1);
{'tl.fromTo("#t-sub",{opacity:0,y:20},{opacity:1,y:0,duration:.4,ease:"power3.out"},0.5);' if t.get('subtitle') else ''}
tl.fromTo("#t-wrap",{{opacity:1}},{{opacity:0,duration:.18,ease:"power1.in"}},{max(dur - .2, .3):.3f});
window.__timelines["title"] = tl;
</script>
</template>
"""
    (ctx.hf / "compositions" / "title.html").write_text(scene, encoding="utf-8")


# ---------- overlays (lower third, pop-ups, 3D logo, flashes) ----------
POS = {  # (css left/right, top as % of height); chosen to stay off a centred face and out of the bottom 20%
    "left": "left:6%;top:24%;", "right": "right:12%;top:24%;", "top": "left:50%;margin-left:-{hw}px;top:8%;",
    "center": "left:50%;margin-left:-{hw}px;top:30%;",
}


def asset(ctx, rel, label):
    """Copy a project asset into hyperframes/assets and return its root-relative path, or None."""
    src = ctx.proj / rel
    if not src.exists():
        ctx.warn(f"{label}: file {rel} not found, effect skipped")
        return None
    dst = ctx.hf / "assets" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return f"assets/{src.name}"


def build_overlays(ctx, words, t0, total, cuts):
    s, W, H = ctx.spec, ctx.W, ctx.H
    parts, js, n = [], ["const tl = gsap.timeline({ paused: true });"], 0
    sfx = s["sfx"]

    def add_sfx(t, key):
        if sfx.get("enabled") and sfx.get(key):
            ctx.sfx_events.append((t, sfx[key]))

    lt = s.get("lower_third") or {}
    if lt.get("name"):
        ts = when(ctx, words, {"at": lt.get("at"), "when": lt.get("when")} if (lt.get("at") is not None or lt.get("when")) else
                  {"at": (words[0]["start"] if words else 0)}, t0, "lower_third")
        if ts is not None:
            d = float(lt.get("duration", 4))
            fs = {"9:16": 54, "16:9": 44, "1:1": 48}[ctx.fmt]
            handle = f'<div id="lt-handle">{e(lt["handle"])}</div>' if lt.get("handle") else ""
            parts.append(
                f'<div id="lt" class="clip" data-start="{ts:.3f}" data-duration="{d:.3f}"><div id="lt-in"><div id="lt-bar"></div>'
                f'<div id="lt-txt"><div id="lt-name">{e(lt["name"])}</div>{handle}</div></div></div>')
            js.append(f'tl.fromTo("#lt-in",{{opacity:0,x:-80}},{{opacity:1,x:0,duration:.45,ease:"power3.out"}},{ts:.3f});')
            js.append(f'tl.fromTo("#lt-in",{{opacity:1,x:0}},{{opacity:0,x:-60,duration:.3,ease:"power2.in",immediateRender:false}},{ts + d - .35:.3f});')
            add_sfx(ts, "on_lower_third")
            lt_css = fs
    else:
        lt_css = 48

    for i, p in enumerate(s.get("popups", [])):
        ts = when(ctx, words, p, t0, f"popups[{i}]")
        if ts is None:
            continue
        d = float(p.get("duration", 2))
        hw = int(W * float(p.get("size", 0.28)) / 2)
        pos = POS.get(p.get("position", "right"), POS["right"]).format(hw=hw)
        if p.get("image"):
            a = asset(ctx, p["image"], f"popups[{i}]")
            if not a:
                continue
            inner = f'<img id="pu{i}-img" src="{a}" style="width:{hw * 2}px;height:auto;display:block;" />'
        else:
            inner = f'<div id="pu{i}-img" class="putxt">{e(p.get("text", ""))}</div>'
        parts.append(f'<div id="pu{i}" class="clip pu" data-start="{ts:.3f}" data-duration="{d:.3f}" style="{pos}"><div id="pu{i}-in">{inner}</div></div>')
        bounce = "back.out(2.4)" if p.get("bounce", True) else "power3.out"
        js.append(f'tl.fromTo("#pu{i}-in",{{opacity:0,scale:.2,rotation:-8}},{{opacity:1,scale:1,rotation:0,duration:.4,ease:"{bounce}"}},{ts:.3f});')
        js.append(f'tl.fromTo("#pu{i}-in",{{opacity:1}},{{opacity:0,duration:.2,immediateRender:false}},{ts + d - .22:.3f});')
        add_sfx(ts, "on_popup")

    l3 = s.get("logo3d")
    if l3 and l3.get("image"):
        ts = when(ctx, words, l3, t0, "logo3d")
        a = asset(ctx, l3["image"], "logo3d") if ts is not None else None
        if a:
            hold = float(l3.get("hold", 2.4))
            throw = when(ctx, words, {"when": l3["throw_when"]}, t0, "logo3d.throw_when") if l3.get("throw_when") else ts + hold
            throw = throw if throw and throw > ts else ts + hold
            hw = int(W * float(l3.get("size", 0.34)) / 2)
            pos = POS.get(l3.get("position", "center"), POS["center"]).format(hw=hw)
            parts.append(
                f'<div id="l3" class="clip" data-start="{ts:.3f}" data-duration="{throw + .6 - ts:.3f}" style="{pos}">'
                f'<div id="l3-stage"><img id="l3-card" src="{a}" style="width:{hw * 2}px;height:auto;display:block;filter:drop-shadow(0 30px 40px rgba(0,0,0,.55));" /></div></div>'
                f'<div id="flash" class="clip" data-start="{throw:.3f}" data-duration=".5"><div id="flash-in"></div></div>')
            js.append(f'tl.fromTo("#l3-card",{{opacity:0,scale:.3,rotationY:-180,transformPerspective:900}},{{opacity:1,scale:1,rotationY:0,duration:.6,ease:"back.out(1.6)",transformPerspective:900}},{ts:.3f});')
            js.append(f'tl.fromTo("#l3-card",{{rotationY:0,rotationX:0,y:0}},{{rotationY:360,rotationX:12,y:-14,duration:{max(throw - ts - .7, .3):.3f},ease:"sine.inOut",immediateRender:false}},{ts + .65:.3f});')
            js.append(f'tl.fromTo("#l3-card",{{scale:1,z:0,opacity:1}},{{scale:7,z:600,opacity:0,rotationX:25,duration:.28,ease:"power4.in",immediateRender:false}},{throw:.3f});')
            js.append(f'tl.fromTo("#flash-in",{{opacity:0}},{{opacity:.95,duration:.06,immediateRender:false}},{throw + .2:.3f});')
            js.append(f'tl.fromTo("#flash-in",{{opacity:.95}},{{opacity:0,duration:.35,ease:"power2.out",immediateRender:false}},{throw + .26:.3f});')
            add_sfx(ts, "on_popup")
            add_sfx(throw + .2, "on_throw")

    flashes = [float(x) + t0 for x in s["transitions"].get("flash_at", [])]
    if s["transitions"].get("flash_on_cuts"):
        flashes += [c + t0 for c in cuts]
    for k, ft in enumerate(sorted(set(round(x, 3) for x in flashes))):
        parts.append(f'<div id="fl{k}" class="clip" data-start="{ft:.3f}" data-duration=".25"><div id="fl{k}-in" class="flin"></div></div>')
        js.append(f'tl.fromTo("#fl{k}-in",{{opacity:.7}},{{opacity:0,duration:.22,ease:"power2.out"}},{ft:.3f});')
        add_sfx(ft, "on_flash")

    if not parts:
        return False
    js.append('window.__timelines["fx"] = tl;')
    ps = {"9:16": 56, "16:9": 46, "1:1": 50}[ctx.fmt]
    scene = f"""<template>
<style>
#root {{ position:absolute; inset:0; font-family:'{ctx.font}',sans-serif; color:{ctx.ink}; }}
#lt {{ position:absolute; left:{int(W * .08)}px; top:{int(H * (.70 if ctx.fmt == '9:16' else .74))}px; }}
#lt-in {{ display:flex; gap:20px; align-items:stretch; }}
#lt-bar {{ width:8px; background:{ctx.accent}; border-radius:4px; }}
#lt-txt {{ background:rgba(10,12,18,.82); padding:14px 26px; border-radius:6px; }}
#lt-name {{ font-size:{lt_css}px; font-weight:900; letter-spacing:-.01em; }}
#lt-handle {{ font-size:{int(lt_css * .62)}px; font-weight:700; color:{ctx.accent}; margin-top:4px; }}
.pu {{ position:absolute; }}
.putxt {{ font-size:{ps}px; font-weight:900; background:{ctx.accent}; color:#111; padding:.3em .6em; border-radius:.3em; text-align:center; }}
#l3 {{ position:absolute; perspective:900px; }}
#flash, .clip.flc {{ position:absolute; inset:0; }}
#flash-in, .flin {{ position:absolute; inset:0; background:#fff; opacity:0; }}
[id^=fl][id$="-in"] {{ position:absolute; inset:0; }}
</style>
<div id="root" data-composition-id="fx" data-width="{W}" data-height="{H}">
{chr(10).join(parts)}
</div>
<script>
{chr(10).join(js)}
</script>
</template>
"""
    (ctx.hf / "compositions" / "overlays.html").write_text(scene, encoding="utf-8")
    return True


# ---------- zooms ----------
def plan_zooms(ctx, words, t0, total):
    z = ctx.spec["zooms"]
    plan = []
    for i, m in enumerate(z.get("manual", [])):
        ts = when(ctx, words, m, t0, f"zooms.manual[{i}]")
        if ts is not None:
            plan.append({"t": ts, "scale": float(m.get("scale", 1.2)), "hold": float(m.get("hold", 2.0)),
                         "origin": m.get("origin", "50% 40%")})
    a = z.get("auto", {})
    if a.get("enabled") and words:
        kws = {norm(k) for k in a.get("keywords", [])}
        sent, cand = [], []
        for w in words:
            sent.append(w)
            if w["word"].endswith((".", "!", "?")):
                cand.append(sent)
                sent = []
        if sent:
            cand.append(sent)
        for sn in cand:
            pick = next((w for w in sn if norm(w["word"]) in kws), None) or max(
                (w for w in sn if len(norm(w["word"])) >= 5 and norm(w["word"]) not in STOP),
                key=lambda w: len(norm(w["word"])), default=None)
            if pick:
                plan.append({"t": pick["start"] + t0, "scale": float(a.get("scale", 1.2)), "hold": float(a.get("hold", 2.0)),
                             "origin": a.get("origin", "50% 40%")})
    plan.sort(key=lambda x: x["t"])
    gap = float(a.get("min_gap", 5.0))
    out = []
    for p in plan:
        if not out or p["t"] - out[-1]["t"] >= max(gap, out[-1]["hold"] + 1.0):
            out.append(p)
    return [p for p in out if p["t"] + p["hold"] + 0.6 < total + 1]


# ---------- index.html ----------
def build_index(ctx, words, cuts):
    s, W, H = ctx.spec, ctx.W, ctx.H
    src = s["source"]
    vsrc = ctx.proj / src["video"]
    if not vsrc.exists():
        sys.exit(f"Source video not found: {vsrc}\nPut your raw video in input/ and set source.video in edit.json.")
    vdur = probe(vsrc)
    title = s.get("title_card") or {}
    t0 = float(title.get("duration", 2.0)) if title.get("text") else 0.0
    total = round(t0 + vdur, 3)

    (ctx.hf / "assets").mkdir(parents=True, exist_ok=True)
    (ctx.hf / "compositions").mkdir(exist_ok=True)
    vdst = ctx.hf / "assets" / vsrc.name
    if not vdst.exists() or vdst.stat().st_size != vsrc.stat().st_size:
        try:
            if vdst.exists():
                vdst.unlink()
            os.link(vsrc, vdst)
        except OSError:
            shutil.copyfile(vsrc, vdst)

    ncap = build_captions(ctx, words, t0, total)
    if t0:
        build_title(ctx, t0)
    has_fx = build_overlays(ctx, words, t0, total, cuts)
    zooms = plan_zooms(ctx, words, t0, total)

    tl = ["const tl = gsap.timeline({ paused: true });"]
    for zi, zm in enumerate(zooms):
        o, sc = zm["origin"], zm["scale"]
        tl.append(f'tl.fromTo("#zoomwrap",{{scale:1,transformOrigin:"{o}"}},{{scale:{sc},transformOrigin:"{o}",duration:.35,ease:"power3.out"}},{zm["t"]:.3f});')
        tl.append(f'tl.fromTo("#zoomwrap",{{scale:{sc},transformOrigin:"{o}"}},{{scale:1,transformOrigin:"{o}",duration:.5,ease:"power2.inOut",immediateRender:false}},{zm["t"] + zm["hold"]:.3f});')
        if s["sfx"].get("enabled") and s["sfx"].get("on_zoom"):
            ctx.sfx_events.append((zm["t"], s["sfx"]["on_zoom"]))
    jp = s.get("jump_cut_punch", {})
    if jp.get("enabled") and cuts:
        edges = [0.0] + list(cuts) + [vdur]
        for k in range(len(edges) - 1):
            sc = float(jp.get("scale", 1.08)) if k % 2 else 1.0
            tl.append(f'tl.set("#punchwrap",{{scale:{sc},transformOrigin:"50% 40%"}},{edges[k] + t0:.3f});')
    if t0 and s["sfx"].get("enabled") and s["sfx"].get("on_title"):
        ctx.sfx_events.append((0.1, s["sfx"]["on_title"]))
    tl += ['window.__timelines["main"] = tl;', "tl.seek(0);"]

    hosts, z = [], 1
    if t0:
        hosts.append(f'<div id="title" data-composition-id="title" data-composition-src="compositions/title.html" data-start="0" data-duration="{t0:.3f}" data-track-index="5" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:50"></div>')
    if ncap:
        hosts.append(f'<div id="caps" data-composition-id="caps" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total:.3f}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:30"></div>')
    if has_fx:
        hosts.append(f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/overlays.html" data-start="0" data-duration="{total:.3f}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:40"></div>')

    # audio: video's own track plays via the <video>; sfx + music are separate <audio> clips
    audios, lib = [], ctx.hf / "assets" / "sfx"
    for k, (t, name) in enumerate(sorted(ctx.sfx_events)):
        f = ctx.proj / "sfx" / f"{name}.wav"
        if not f.exists():
            f = Path(__file__).resolve().parent.parent / "sfx" / f"{name}.wav"
        if not f.exists():
            ctx.warn(f"sound effect '{name}' not found in sfx/, skipped")
            continue
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, lib / f.name)
        d = min(probe(f), total - t)
        if d >= 0.04:
            audios.append(f'<audio id="sfx{k}" src="assets/sfx/{f.name}" data-start="{t:.3f}" data-duration="{d:.3f}" data-volume="{s["sfx"].get("volume", .7)}"></audio>')
    mu = s.get("music", {})
    if mu.get("file"):
        mf = ctx.proj / mu["file"]
        if mf.exists():
            (ctx.hf / "assets" / "music").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(mf, ctx.hf / "assets" / "music" / mf.name)
            audios.append(f'<audio id="music" src="assets/music/{mf.name}" data-start="0" data-duration="{total:.3f}" data-volume="{mu.get("volume", .12)}" data-fade-in="0.5" data-fade-out="1.0"></audio>')
        else:
            ctx.warn(f"music file {mu['file']} not found, skipped")

    fx = float(src.get("focus_x", 0.5)) * 100
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(ctx.meta['name'])}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {ctx.bg}; }}
      #zoomwrap, #punchwrap {{ position: absolute; inset: 0; }}
      #zoomwrap {{ overflow: hidden; }}
      #take {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; object-position: {fx:.0f}% 50%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}">
      <div id="zoomwrap"><div id="punchwrap" data-layout-allow-overflow>
        <video id="take" class="clip" src="assets/{vsrc.name}" data-start="{t0:.3f}" data-duration="{vdur:.3f}" data-track-index="0" playsinline {'muted' if src.get('muted') else 'data-has-audio="true"'}></video>
      </div></div>
      {chr(10).join('      ' + h for h in hosts)}
      {chr(10).join('      ' + a for a in audios)}
    </div>
    <script>
      {chr(10).join('      ' + l for l in tl).strip()}
    </script>
  </body>
</html>
"""
    (ctx.hf / "index.html").write_text(page, encoding="utf-8")
    return {"total": total, "title": t0, "video_duration": vdur, "caption_groups": ncap or 0, "zooms": len(zooms),
            "overlays": has_fx, "sfx": len(audios), "format": ctx.fmt, "size": f"{W}x{H}"}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ctx = Ctx(sys.argv[1])
    if not (ctx.hf / "hyperframes.json").exists():
        sys.exit(f"{ctx.hf} is not a HyperFrames project. Run scripts/new_project.py or: npx hyperframes init {ctx.hf}")
    words = load_words(ctx)
    cuts = []
    cj = ctx.spec["source"].get("cuts")
    if cj and (ctx.proj / cj).exists():
        segs = json.loads((ctx.proj / cj).read_text())["segments"]
        acc = 0.0
        for sg in segs[:-1]:
            acc += sg["end"] - sg["start"]
            cuts.append(round(acc, 3))
    print(f"Building {ctx.meta['name']} ({ctx.fmt} {ctx.W}x{ctx.H}) · {len(words)} words · {len(cuts)} cuts")
    report = build_index(ctx, words, cuts)
    report["warnings"] = ctx.warnings
    (ctx.proj / "work").mkdir(exist_ok=True)
    (ctx.proj / "work" / "build_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "warnings"}))
    print(f"{len(ctx.warnings)} warning(s)")


if __name__ == "__main__":
    main()
