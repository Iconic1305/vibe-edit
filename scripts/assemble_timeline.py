"""Assemble several takes into one master A-roll with Hinglish captions aligned to real speech.

Usage:
    python3 scripts/assemble_timeline.py projects/<slug>

Reads   <project>/timeline.json   ordered clips: {id, media, words, ...}
        <project>/work/hinglish.json   per clip, reviewed caption text (see below)
Writes  work/master.mp4            dead-air-free, loudness-normalised concatenation of the kept speech
        work/master.words.json     caption words on the master timeline (roman text, layer back|front)
        work/master.clips.json     where each clip starts/ends on the master timeline
        work/master.cuts.json      every jump-cut point on the master timeline
        work/captions_review.md    every caption line next to what was heard, for the owner to check

hinglish.json (per clip id):
    {"roman": {"<index>": "Aaj", ...},   # reviewed Roman-Hinglish for each Whisper word index
     "drop":  [20, 21],                  # words to remove (stutters, retakes, noise)
     "back":  [2, 6]}                    # words rendered BEHIND the speaker (cut-out layer)
Why chunks: Whisper smears words across pauses. Speech chunks come from the audio energy itself;
each word is assigned to the chunk it overlaps most, and unreliable chunks are re-spaced by word length.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refine_words import HOP, envelope  # noqa: E402

PAD = 0.06          # air kept before/after each chunk
MERGE_GAP = 0.28    # pauses shorter than this stay in; longer ones are cut
MIN_CHUNK = 0.12


def voiced_chunks(db, total):
    peak = np.percentile(db, 95)
    thr = max(np.percentile(db, 15) + 8, peak - 26)
    v = db > thr
    chunks, i, n = [], 0, len(v)
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]:
                j += 1
            chunks.append([i * HOP, j * HOP])
            i = j
        else:
            i += 1
    merged = []
    for c in chunks:
        if merged and c[0] - merged[-1][1] < MERGE_GAP:
            merged[-1][1] = c[1]
        else:
            merged.append(c)
    return [c for c in merged if c[1] - c[0] >= MIN_CHUNK], thr


def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def cut_spans(words, drop):
    """Time spans of dropped words (contiguous runs merged), shrunk a hair so neighbouring words are not clipped."""
    spans, run = [], []
    for i in sorted(drop):
        if run and i == run[-1] + 1:
            run.append(i)
        else:
            if run:
                spans.append(run)
            run = [i]
    if run:
        spans.append(run)
    out = []
    for r in spans:
        a, b = words[r[0]]["start"] + 0.02, words[r[-1]]["end"] - 0.02
        if b > a:
            out.append((a, b))
    return out


def subtract(segs, spans, min_len=0.08):
    out = []
    for a, b in segs:
        pieces = [(a, b)]
        for c0, c1 in spans:
            nxt = []
            for x, y in pieces:
                if c1 <= x or c0 >= y:
                    nxt.append((x, y))
                else:
                    if c0 > x:
                        nxt.append((x, c0))
                    if c1 < y:
                        nxt.append((c1, y))
            pieces = nxt
        out += [(x, y) for x, y in pieces if y - x >= min_len]
    return out


def plan_clip(clip, hl, total_dur, db):
    words = json.loads(Path(clip["words"]).read_text())["words"]
    drop = set(hl.get("drop", []))
    back = set(hl.get("back", []))
    roman = hl.get("roman", {})
    kept = []
    for i, w in enumerate(words):
        if i in drop:
            continue
        txt = roman.get(str(i), w["word"]).strip()
        if not txt:
            continue
        kept.append({"i": i, "text": txt, "orig": w["word"], "start": w["start"], "end": w["end"],
                     "prob": w.get("prob", 1.0), "layer": "back" if i in back else "front"})
    chunks, thr = voiced_chunks(db, total_dur)
    # assign each kept word to the chunk it overlaps most (monotonic)
    last = 0
    for w in kept:
        scores = [overlap(w["start"], w["end"], c[0], c[1]) for c in chunks]
        k = int(np.argmax(scores)) if scores and max(scores) > 0 else last
        w["chunk"] = max(k, last)
        last = w["chunk"]
    used = sorted({w["chunk"] for w in kept})
    segs, words_out = [], []
    for ci in used:
        c0, c1 = chunks[ci]
        ws = [w for w in kept if w["chunk"] == ci]
        s0 = max(0.0, c0 - PAD)
        s1 = min(total_dur, c1 + PAD)
        if segs and s0 < segs[-1][1]:
            s0 = segs[-1][1]
        # keep Whisper's own timings, clamped to the real speech; re-space the chunk only when a word is clearly wrong
        for w in ws:
            w["start"], w["end"] = max(w["start"], c0), min(w["end"], c1)
        bad = any((w["end"] - w["start"]) > 1.0 or (w["end"] - w["start"]) < 0.05 for w in ws)
        if bad:
            weights = np.array([max(len(w["text"]), 2) for w in ws], dtype=float)
            edges = c0 + (c1 - c0) * np.concatenate([[0], np.cumsum(weights) / weights.sum()])
            for w, a, b in zip(ws, edges[:-1], edges[1:]):
                w["start"], w["end"] = float(a), float(b)
                w["realigned"] = True
        segs.append((s0, s1))
        words_out += ws
    # dropped words (repeats, stutters, noise) are cut from the audio/video too, not only from the captions
    segs = subtract(segs, cut_spans(words, drop))
    return segs, words_out


def build_master(clips_plan, out_path, work):
    inputs, parts, vlabels, alabels = [], [], [], []
    n = 0
    for media, segs in clips_plan:
        for a, b in segs:
            inputs += ["-i", str(media)]
            d = b - a
            parts.append(f"[{n}:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps=30,format=yuv420p[v{n}]")
            parts.append(f"[{n}:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                         f"afade=t=in:d=0.015,afade=t=out:st={max(d - 0.015, 0):.3f}:d=0.015[a{n}]")
            vlabels.append(f"[v{n}]")
            alabels.append(f"[a{n}]")
            n += 1
    parts.append("".join(f"{v}{a}" for v, a in zip(vlabels, alabels)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    parts.append("[ac]highpass=f=70,afftdn=nf=-28,loudnorm=I=-15:TP=-1.5:LRA=9[aout]")
    script = work / "master.filter.txt"
    script.write_text(";\n".join(parts), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex_script", str(script),
           "-map", "[vc]", "-map", "[aout]", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-g", "30", "-keyint_min", "30",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", str(out_path)]
    subprocess.run(cmd, check=True)
    script.unlink()


def main():
    proj = Path(sys.argv[1]).resolve()
    work = proj / "work"
    tl = json.loads((proj / "timeline.json").read_text())
    hl_all = json.loads((work / "hinglish.json").read_text())
    plans, master_words, clip_spans, cuts, review = [], [], [], [], ["# Caption review (what was heard -> what is shown)\n"]
    t = 0.0
    for clip in tl["clips"]:
        media = proj / clip["media"]
        clip = {**clip, "words": str(proj / clip["words"])}
        db = envelope(media)
        dur = len(db) * HOP
        segs, words = plan_clip(clip, hl_all[clip["id"]], dur, db)
        plans.append((media, segs))
        start_t = t
        offset = t
        review.append(f"\n## {clip['id']}  ({clip['media']})\n")
        for k, (a, b) in enumerate(segs):
            if k > 0:
                cuts.append(round(offset, 3))
            for w in words:
                if a - 1e-6 <= w["start"] and w["start"] < b + 1e-6:
                    ns = max(w["start"], a) - a + offset
                    ne = min(w["end"], b) - a + offset
                    master_words.append({"word": w["text"], "start": round(ns, 3), "end": round(max(ne, ns + 0.06), 3),
                                         "layer": w["layer"], "clip": clip["id"], "orig": w["orig"], "prob": w["prob"],
                                         "realigned": bool(w.get("realigned"))})
            offset += b - a
        line = " ".join(f"{w['text']}" for w in words)
        heard = " ".join(w["orig"] for w in words)
        low = [w["text"] for w in words if w["prob"] < 0.4]
        review.append(f"- shown: **{line}**\n- heard: {heard}\n" + (f"- low-confidence words: {', '.join(low)}\n" if low else ""))
        clip_spans.append({"id": clip["id"], "start": round(start_t, 3), "end": round(offset, 3)})
        if clip_spans[-1]["start"] > 0:
            cuts.append(round(start_t, 3))
        t = offset
    out = work / "master.mp4"
    build_master(plans, out, work)
    (work / "master.words.json").write_text(json.dumps({"words": master_words, "duration": round(t, 3)}, indent=2, ensure_ascii=False) + "\n")
    (work / "master.clips.json").write_text(json.dumps(clip_spans, indent=2) + "\n")
    (work / "master.cuts.json").write_text(json.dumps(sorted(set(cuts)), indent=2) + "\n")
    (work / "captions_review.md").write_text("\n".join(review) + "\n", encoding="utf-8")
    print(f"master {t:.1f}s from {len(tl['clips'])} clips · {len(master_words)} caption words · {len(set(cuts))} cuts")
    for c in clip_spans:
        print(f"  {c['id']:8} {c['start']:6.2f} -> {c['end']:6.2f}")


if __name__ == "__main__":
    main()
