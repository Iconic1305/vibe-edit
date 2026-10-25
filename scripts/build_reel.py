"""Build a layered Reels edit: speaker + cut-out + captions BEHIND and IN FRONT of the speaker + B-roll cutaways.

Usage:
    python3 scripts/build_reel.py projects/<slug>        (selected by edit.json: "builder": "reel")

Extends scripts/build_edit.py (same edit.json: zooms, jump-cut punch, flashes, pop-ups, lower third, SFX, music)
with:
  source.cutout      transparent WebM of the speaker (npx hyperframes remove-background)
  caption words      {"word", "start", "end", "layer": "back"|"front"}  (work/master.words.json)
                     back words are drawn GIANT between the footage and the cut-out, so the speaker's head
                     overlaps them; front words are normal captions in front of everything
  broll              [{"at"|"when", "duration", "video", "media_start", "speed", "crop", "layout", "chip"}]
                     full cutaways of screen recordings in a card, speaker audio continues
Layer order (bottom -> top): footage < back words < cut-out < B-roll < pop-ups/flash < front captions < title.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_edit as B  # noqa: E402
from build_edit import e, norm, probe  # noqa: E402


def groups_of(words, n):
    """Caption groups of up to n words; break on punctuation, a long gap, or a new clip."""
    out, cur = [], []
    for w in words:
        if cur and (w.get("clip") != cur[-1].get("clip") or w["start"] - cur[-1]["end"] > 0.45):
            out.append(cur)
            cur = []
        cur.append(w)
        if len(cur) >= n or w["word"].endswith((".", "!", "?", "…", ",")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def back_size(text, W):
    n = max(len(text), 1)
    return int(min(320, (W * 1.25) / n))


def build_front_and_back(ctx, words, total, windows):
    """Return (front captions scene html or None, list of inline back-caption blocks, tl_js for back)."""
    c = ctx.spec["captions"]
    W, H = ctx.W, ctx.H
    size = c.get("size") or 84
    y = min(float(c.get("y", 0.66)), 0.70)
    width, left = 0.80, 10.0
    in_b = lambda t: any(a <= t < b for a, b in windows)
    front_parts, front_js = [], ["const tl = gsap.timeline({ paused: true });"]
    back_parts, back_js, backs = [], [], []
    gs_list = groups_of(words, int(c.get("words_per_group", 3)))
    for gi, g in enumerate(gs_list):
        gs = g[0]["start"]
        nxt = gs_list[gi + 1][0]["start"] if gi + 1 < len(gs_list) else None
        ge = min(g[-1]["end"] + 0.25, nxt) if nxt else min(g[-1]["end"] + 0.5, total)
        ge = max(ge, gs + 0.25)
        cand = [w for w in g if w.get("layer") == "back" and not in_b(w["start"])]
        use_back = [max(cand, key=lambda w: len(w["word"]))] if cand else []
        if len(cand) > 1 and cand[0]["word"].strip(",.!?").lower() in ("d'", "claude") and len(cand) == 2:
            use_back = cand                       # a two-word name ("D' Closet") stays together
        front = [w for w in g if w not in use_back]
        if front:
            spans = "".join(f'<span id="cw{gi}_{k}" class="cw{" hl" if w.get("layer") == "back" else ""}">{e(w["word"])}</span>'
                            for k, w in enumerate(front))
            front_parts.append(f'<div id="cg{gi}" class="clip cg" data-start="{gs:.3f}" data-duration="{ge - gs:.3f}">'
                               f'<div id="cgi{gi}" class="cgi">{spans}</div></div>')
            front_js.append(f'tl.fromTo("#cgi{gi}",{{opacity:0,scale:.8,y:22}},{{opacity:1,scale:1,y:0,duration:.14,ease:"back.out(2.2)"}},{gs:.3f});')
            for k, w in enumerate(front):
                ws, we = w["start"], min(w["end"], ge)
                front_js.append(f'tl.fromTo("#cw{gi}_{k}",{{color:"{ctx.ink}"}},{{color:"{ctx.accent}",duration:.04}},{ws:.3f});')
                if w.get("layer") != "back":
                    front_js.append(f'tl.fromTo("#cw{gi}_{k}",{{color:"{ctx.accent}"}},{{color:"{ctx.ink}",duration:.04,immediateRender:false}},{max(we, ws + .05):.3f});')
        if use_back:
            text = " ".join(w["word"].strip(",.!?") for w in use_back).upper()
            backs.append({"gi": gi, "bt": use_back[0]["start"], "pref": max(ge, use_back[0]["start"] + 1.0), "text": text})
    for n_, bk in enumerate(backs):
        gi, bt, text = bk["gi"], bk["bt"], bk["text"]
        be = bk["pref"]
        if n_ + 1 < len(backs):
            be = min(be, backs[n_ + 1]["bt"] - 0.05)
        be = max(be, bt + 0.4)
        bs = back_size(text, W)
        bottom_y = int(H * 0.225)
        back_parts.append(
            f'<div id="bk{gi}" class="clip bk" data-start="{bt:.3f}" data-duration="{be - bt:.3f}" style="top:{bottom_y - bs}px;font-size:{bs}px">'
            f'<div id="bki{gi}" class="bki" data-layout-allow-occlusion data-layout-allow-overflow>{e(text)}</div></div>')
        back_js.append(f'tl.fromTo("#bki{gi}",{{opacity:0,scale:1.35,y:30}},{{opacity:1,scale:1,y:0,duration:.22,ease:"power4.out"}},{bt:.3f});')
        back_js.append(f'tl.fromTo("#bki{gi}",{{opacity:1}},{{opacity:0,duration:.14,immediateRender:false}},{be - .16:.3f});')
    scene = None
    if front_parts:
        front_js.append('window.__timelines["caps"] = tl;')
        scene = f"""<template>
<style>
#root {{ position:absolute; inset:0; font-family:'{ctx.font}',sans-serif; }}
.cg {{ position:absolute; left:{left:.1f}%; width:{width * 100:.1f}%; top:{y * 100:.1f}%; display:flex; justify-content:center; }}
.cgi {{ display:flex; flex-wrap:wrap; justify-content:center; gap:.12em .28em; font-size:{size}px; font-weight:900; line-height:1.08; text-align:center; }}
.cw {{ color:{ctx.ink}; display:inline-block; text-shadow:0 4px 0 rgba(0,0,0,.55),0 0 22px rgba(0,0,0,.65); -webkit-text-stroke:{max(size // 15, 4)}px rgba(0,0,0,.88); paint-order:stroke fill; }}
</style>
<div id="root" data-composition-id="caps" data-width="{W}" data-height="{H}">
{chr(10).join(front_parts)}
</div>
<script>
{chr(10).join(front_js)}
</script>
</template>
"""
        (ctx.hf / "compositions" / "captions.html").write_text(scene, encoding="utf-8")
    return bool(front_parts), back_parts, back_js


def build_broll(ctx, items, words, total):
    """Inline B-roll cutaway blocks. Returns (html parts, tl js, windows)."""
    W, H = ctx.W, ctx.H
    parts, js, windows = [], [], []
    (ctx.hf / "assets" / "broll").mkdir(parents=True, exist_ok=True)
    for k, it in enumerate(items):
        ts = B.when(ctx, words, it, 0.0, f"broll[{k}]")
        if ts is None:
            continue
        d = float(it["duration"])
        src = ctx.proj / it["video"]
        if not src.exists():
            ctx.warn(f"broll[{k}]: {it['video']} not found, skipped")
            continue
        dst = ctx.hf / "assets" / "broll" / src.name
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copyfile(src, dst)
        sw, sh = it["src_size"]
        crop = it.get("crop") or {"x": 0, "y": 0, "w": sw, "h": sh}
        layout = it.get("layout", "mac")
        if layout == "phone":
            ch = int(H * 0.50)
            cw = int(ch * crop["w"] / crop["h"])
            cx, cy = (W - cw) // 2, int(H * 0.15)
            radius = 54
        else:
            cw = int(W * 0.92)
            ch = int(cw * crop["h"] / crop["w"])
            cx, cy = (W - cw) // 2, int(H * 0.20)
            radius = 26
        scale = cw / crop["w"]
        vw, vh = int(sw * scale), int(sh * scale)
        vl, vt = -int(crop["x"] * scale), -int(crop["y"] * scale)
        speed = float(it.get("speed", 1.0))
        chip = it.get("chip") or {}
        chip_html = ""
        if chip:
            chip_html = (f'<div id="br{k}chip" class="brchip"><span class="k">{e(chip.get("kicker", ""))}</span>'
                         f'<span class="t">{e(chip.get("text", ""))}</span></div>')
        bezel = f"border:10px solid #111;" if layout == "phone" else "border:2px solid rgba(255,255,255,.12);"
        parts.append(
            f'<div id="br{k}" class="brw" style="z-index:10"><div class="brbg"></div>{chip_html}'
            f'<div id="br{k}card" class="brcard" style="left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px;border-radius:{radius}px;{bezel}">'
            f'<div id="br{k}in" class="brin" data-layout-allow-overflow><video id="br{k}v" class="clip" src="assets/broll/{src.name}" muted playsinline '
            f'data-start="{ts:.3f}" data-duration="{d:.3f}" data-media-start="{float(it.get("media_start", 0)):.3f}" '
            f'data-playback-rate="{speed}" data-track-index="6" style="position:absolute;left:{vl}px;top:{vt}px;width:{vw}px;height:{vh}px"></video>'
            f'</div></div></div>')
        js.append(f'tl.fromTo("#br{k}",{{opacity:0}},{{opacity:1,duration:.22,ease:"power2.out"}},{ts:.3f});')
        js.append(f'tl.fromTo("#br{k}card",{{scale:.88,y:60}},{{scale:1,y:0,duration:.45,ease:"back.out(1.5)"}},{ts:.3f});')
        js.append(f'tl.fromTo("#br{k}in",{{scale:1}},{{scale:{float(it.get("zoom", 1.08))},duration:{d:.3f},ease:"none"}},{ts:.3f});')
        if chip:
            js.append(f'tl.fromTo("#br{k}chip",{{opacity:0,x:-80}},{{opacity:1,x:0,duration:.4,ease:"power3.out"}},{ts + .15:.3f});')
        js.append(f'tl.fromTo("#br{k}",{{opacity:1}},{{opacity:0,duration:.2,ease:"power1.in",immediateRender:false}},{ts + d - .2:.3f});')
        windows.append((ts, ts + d))
        if ctx.spec["sfx"].get("enabled"):
            ctx.sfx_events.append((ts, ctx.spec["sfx"].get("on_broll", "whoosh")))
            if chip:
                ctx.sfx_events.append((ts + .15, ctx.spec["sfx"].get("on_chip", "pop")))
    return parts, js, windows


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ctx = B.Ctx(sys.argv[1])
    s, W, H = ctx.spec, ctx.W, ctx.H
    if not (ctx.hf / "hyperframes.json").exists():
        sys.exit(f"{ctx.hf} is not a HyperFrames project")
    src = s["source"]
    words = B.load_words(ctx)
    vsrc = ctx.proj / src["video"]
    if not vsrc.exists():
        sys.exit(f"Source video not found: {vsrc}")
    vdur = probe(vsrc)
    total = round(vdur, 3)
    (ctx.hf / "assets").mkdir(parents=True, exist_ok=True)
    (ctx.hf / "compositions").mkdir(exist_ok=True)
    for f in ctx.hf.joinpath("assets").glob("master*"):
        f.unlink()
    shutil.copyfile(vsrc, ctx.hf / "assets" / vsrc.name)
    cut = None
    if src.get("cutout") and (ctx.proj / src["cutout"]).exists():
        cut = ctx.proj / src["cutout"]
        shutil.copyfile(cut, ctx.hf / "assets" / cut.name)
    elif src.get("cutout"):
        ctx.warn(f"cut-out {src['cutout']} not found: back-layer words will sit in front instead")

    cuts = json.loads((ctx.proj / src["cuts"]).read_text()) if src.get("cuts") and (ctx.proj / src["cuts"]).exists() else []
    clips = json.loads((ctx.proj / src["clips"]).read_text()) if src.get("clips") and (ctx.proj / src["clips"]).exists() else []
    boundaries = [c["start"] for c in clips if c["start"] > 0]
    if s["transitions"].get("flash_on_clip_boundaries"):
        s["transitions"]["flash_at"] = list(s["transitions"].get("flash_at", [])) + boundaries
        for bt in boundaries:
            if s["sfx"].get("enabled"):
                ctx.sfx_events.append((bt, s["sfx"].get("on_boundary", "whoosh")))

    br_parts, br_js, windows = build_broll(ctx, s.get("broll", []), words, total)
    if not cut:
        for w in words:
            if w.get("layer") == "back":
                w["layer"] = "front"
    has_front, back_parts, back_js = build_front_and_back(ctx, words, total, windows)

    has_fx = B.build_overlays(ctx, words, 0.0, total, [])   # lower third, pop-ups, 3D logo, flashes
    zooms = B.plan_zooms(ctx, words, 0.0, total)

    # root timeline: zoom on all three subject layers together, jump-cut punch, B-roll + back captions
    tl = ["const tl = gsap.timeline({ paused: true });"]
    targets = '["#zA","#zB","#zC"]'
    tl.append(f'tl.set({targets},{{scale:1,transformOrigin:"50% 40%"}},0);')
    for zm in zooms:
        o, sc = zm["origin"], zm["scale"]
        tl.append(f'tl.fromTo({targets},{{scale:1,transformOrigin:"{o}"}},{{scale:{sc},transformOrigin:"{o}",duration:.35,ease:"power3.out"}},{zm["t"]:.3f});')
        tl.append(f'tl.fromTo({targets},{{scale:{sc},transformOrigin:"{o}"}},{{scale:1,transformOrigin:"{o}",duration:.5,ease:"power2.inOut",immediateRender:false}},{zm["t"] + zm["hold"]:.3f});')
        if s["sfx"].get("enabled") and s["sfx"].get("on_zoom"):
            ctx.sfx_events.append((zm["t"], s["sfx"]["on_zoom"]))
    jp = s.get("jump_cut_punch", {})
    if jp.get("enabled") and cuts:
        edges = [0.0] + list(cuts) + [total]
        for i in range(len(edges) - 1):
            sc = float(jp.get("scale", 1.06)) if i % 2 else 1.0
            tl.append(f'tl.set(["#pA","#pB","#pC"],{{scale:{sc},transformOrigin:"50% 40%"}},{edges[i]:.3f});')
    tl += back_js + br_js
    tl += ['window.__timelines["main"] = tl;', "tl.seek(0);"]

    hosts = []
    if has_front:
        hosts.append(f'<div id="caps" data-composition-id="caps" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total:.3f}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:30"></div>')
    if has_fx:
        hosts.append(f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/overlays.html" data-start="0" data-duration="{total:.3f}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:40"></div>')

    audios, lib = [], ctx.hf / "assets" / "sfx"
    seen = set()
    for k, (t, name) in enumerate(sorted(ctx.sfx_events)):
        key = (name, round(t, 2))
        if key in seen:
            continue
        seen.add(key)
        f = ctx.proj / "sfx" / f"{name}.wav"
        if not f.exists():
            f = Path(__file__).resolve().parent.parent / "sfx" / f"{name}.wav"
        if not f.exists():
            ctx.warn(f"sound effect '{name}' not found, skipped")
            continue
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, lib / f.name)
        d = min(probe(f), total - t)
        if d >= 0.04:
            audios.append(f'<audio id="sfx{k}" src="assets/sfx/{f.name}" data-start="{t:.3f}" data-duration="{d:.3f}" data-volume="{s["sfx"].get("volume", .6)}"></audio>')
    mu = s.get("music", {})
    if mu.get("file") and (ctx.proj / mu["file"]).exists():
        mf = ctx.proj / mu["file"]
        (ctx.hf / "assets" / "music").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mf, ctx.hf / "assets" / "music" / mf.name)
        audios.append(f'<audio id="music" src="assets/music/{mf.name}" data-start="0" data-duration="{total:.3f}" data-volume="{mu.get("volume", .12)}" data-fade-in="0.5" data-fade-out="1.0"></audio>')
    elif mu.get("file"):
        ctx.warn(f"music file {mu['file']} not found: rendering without music")

    fx = float(src.get("focus_x", 0.5)) * 100
    vid = (f'<video id="take" class="clip" src="assets/{vsrc.name}" data-start="0" data-duration="{vdur:.3f}" data-track-index="0" playsinline data-has-audio="true"></video>')
    cutv = (f'<video id="cut" class="clip" src="assets/{cut.name}" data-start="0" data-duration="{vdur:.3f}" data-track-index="1" muted playsinline></video>' if cut else "")
    layers = f"""      <div id="zA" class="zl" style="z-index:1"><div id="pA" class="zl" data-layout-allow-overflow>{vid}</div></div>
      <div id="zC" class="zl" style="z-index:2"><div id="pC" class="zl" data-layout-allow-overflow>
        {chr(10).join(back_parts)}
      </div></div>
      <div id="zB" class="zl" style="z-index:3"><div id="pB" class="zl" data-layout-allow-overflow>{cutv}</div></div>"""
    acc = ctx.accent
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(ctx.meta['name'])}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {ctx.bg}; font-family: '{ctx.font}', sans-serif; }}
      .zl {{ position: absolute; inset: 0; }}
      #zA, #zB, #zC {{ overflow: hidden; }}
      #take, #cut {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; object-position: {fx:.0f}% 50%; }}
      .bk {{ position: absolute; left: 0; width: {W}px; text-align: center; line-height: 1; }}
      .bki {{ display: inline-block; font-weight: 900; letter-spacing: -.02em; color: {acc}; white-space: nowrap;
              -webkit-text-stroke: 6px rgba(0,0,0,.55); paint-order: stroke fill; text-shadow: 0 10px 40px rgba(0,0,0,.35); }}
      .brw {{ position: absolute; inset: 0; opacity: 0; }}
      .brbg {{ position: absolute; inset: 0; background: radial-gradient(900px 700px at 20% 15%, #232a3d 0%, #0d0f14 65%); }}
      .brcard {{ position: absolute; overflow: hidden; background: #fff; box-shadow: 0 40px 90px rgba(0,0,0,.6); }}
      .brin {{ position: absolute; inset: 0; transform-origin: 50% 40%; }}
      .brchip {{ position: absolute; left: {int(W * .08)}px; top: {int(H * .075)}px; display: flex; align-items: center; gap: 18px; }}
      .brchip .k {{ font-size: 34px; font-weight: 900; letter-spacing: .12em; color: #111; background: {acc}; padding: 8px 20px; border-radius: 10px; }}
      .brchip .t {{ font-size: 54px; font-weight: 900; color: #fff; letter-spacing: -.01em; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}">
{layers}
      {chr(10).join('      ' + p for p in br_parts)}
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
    report = {"total": total, "caption_words": len(words), "back_words": sum(1 for w in words if w.get("layer") == "back"),
              "cutout": bool(cut), "broll": len(windows), "zooms": len(zooms), "sfx": len(audios), "format": ctx.fmt,
              "size": f"{W}x{H}", "warnings": ctx.warnings}
    (ctx.proj / "work").mkdir(exist_ok=True)
    (ctx.proj / "work" / "build_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "warnings"}))
    print(f"{len(ctx.warnings)} warning(s)")


if __name__ == "__main__":
    main()
