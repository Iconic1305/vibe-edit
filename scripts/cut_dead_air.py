"""Rough cut: remove pauses and breaths using the word timings.

Usage:
    python scripts/cut_dead_air.py footage/take.mp4 work/take.words.json
        [--max-pause 0.3] [--pad 0.08] [--beat 0.25] [--dry-run]

Rules (from the guide):
  * cut every gap between words longer than --max-pause
  * never cut inside a word (each word keeps --pad seconds of air on both sides)
  * keep a short beat (--beat) after sentence endings, before the next line lands

Writes:
  work/<name>.cuts.json        the segments kept, in source time
  work/<name>.cut.mp4          the rough cut (unless --dry-run)
  work/<name>.cut.words.json   word timings remapped to the rough cut
"""
import argparse
import subprocess
import sys
from pathlib import Path

from common import fmt_time, load_words, probe_duration, require, save_json, work_dir

WORK = None

SENTENCE_END = (".", "!", "?", "…")


def plan_segments(words, duration, max_pause, pad, beat):
    if not words:
        return [(0.0, duration)]
    segments = []
    start = max(0.0, words[0]["start"] - pad)
    for prev, nxt in zip(words, words[1:]):
        gap = nxt["start"] - prev["end"]
        if gap > max_pause:
            # Close the segment after prev, reopen just before nxt.
            tail = beat if prev["word"].endswith(SENTENCE_END) else pad
            end = prev["end"] + min(tail, gap - pad)
            segments.append((start, end))
            start = nxt["start"] - pad
    segments.append((start, min(duration, words[-1]["end"] + pad)))
    return [(round(a, 3), round(b, 3)) for a, b in segments if b - a > 0.02]


def remap(words, segments):
    """Move each word onto the new, shorter timeline."""
    out, offset, i = [], 0.0, 0
    for a, b in segments:
        while i < len(words) and words[i]["start"] < b:
            w = words[i]
            if w["end"] > a:
                out.append({**w, "start": round(max(w["start"], a) - a + offset, 3),
                            "end": round(min(w["end"], b) - a + offset, 3)})
            i += 1
        offset += b - a
    return out


def render(video, segments, out_path):
    require("ffmpeg")
    expr = "+".join(f"between(t,{a},{b})" for a, b in segments)
    graph = (f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];"
             f"[0:a]aselect='{expr}',asetpts=N/SR/TB[a]")
    script = WORK / f"{Path(video).stem}.cut.filter.txt"
    script.write_text(graph, encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
           "-filter_complex_script", str(script), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-g", "30", "-keyint_min", "30", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k",
           str(out_path)]
    subprocess.run(cmd, check=True)
    script.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("words")
    ap.add_argument("--max-pause", type=float, default=0.3)
    ap.add_argument("--pad", type=float, default=0.08)
    ap.add_argument("--beat", type=float, default=0.25)
    ap.add_argument("--dry-run", action="store_true", help="plan only, don't render")
    args = ap.parse_args()

    global WORK
    video = Path(args.video)
    if not video.exists():
        sys.exit(f"Not found: {video}")
    WORK = work_dir(video)
    data = load_words(args.words)
    words = data["words"]
    duration = probe_duration(video)

    segments = plan_segments(words, duration, args.max_pause, args.pad, args.beat)
    new_len = sum(b - a for a, b in segments)
    stem = video.stem

    save_json({"source": str(video), "segments": [{"start": a, "end": b} for a, b in segments]},
              WORK / f"{stem}.cuts.json")
    save_json({**data, "source": str(WORK / f"{stem}.cut.mp4"), "duration": round(new_len, 3),
               "words": remap(words, segments)}, WORK / f"{stem}.cut.words.json")

    print(f"Kept {len(segments)} segments · {fmt_time(duration)} -> {fmt_time(new_len)} "
          f"({duration - new_len:.1f}s of dead air removed)")
    if args.dry_run:
        return
    out = WORK / f"{stem}.cut.mp4"
    print("Rendering rough cut…")
    render(video, segments, out)
    print(f"Saved {out.relative_to(WORK.parent)} · new length {fmt_time(probe_duration(out))}")


if __name__ == "__main__":
    main()
