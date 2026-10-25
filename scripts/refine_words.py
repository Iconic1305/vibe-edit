"""Snap Whisper word timings to the real speech energy.

Whisper often smears a word across a following pause (e.g. one word "lasting" 3 s). That breaks dead-air
cutting and caption timing. This trims each word's start/end to where the audio is actually above the
noise floor.

Usage:
    python3 scripts/refine_words.py projects/<slug>/work/<clip>.words.json <media> [--out refined.json]
Writes <clip>.words.refined.json next to the input unless --out is given.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HOP = 0.01  # seconds per energy frame
CLEAN = "highpass=f=80,afftdn=nf=-28"


def envelope(media):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-af", CLEAN, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True)
    if raw.returncode != 0 or not raw.stdout:
        sys.exit(f"cannot decode audio from {media}")
    x = np.frombuffer(raw.stdout, dtype=np.float32)
    n = int(16000 * HOP)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def refine(words, db):
    floor = np.percentile(db, 15)
    peak = np.percentile(db, 95)
    thr = max(floor + 8, peak - 26)   # speech sits within ~26 dB of its 95th-percentile level; pauses are far below
    out, prev_end = [], 0.0
    for w in words:
        a = max(0, int((w["start"] - 0.08) / HOP))
        b = min(len(db), int((w["end"] + 0.08) / HOP) + 1)
        idx = np.where(db[a:b] > thr)[0]
        if len(idx) == 0:
            s, e = w["start"], w["end"]
        else:
            s, e = (a + idx[0]) * HOP, (a + idx[-1] + 1) * HOP
        s = max(s, prev_end)
        e = max(e, s + 0.06)
        out.append({**w, "start": round(s, 3), "end": round(e, 3), "orig_start": w["start"], "orig_end": w["end"]})
        prev_end = e
    return out, float(thr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words")
    ap.add_argument("media")
    ap.add_argument("--out")
    a = ap.parse_args()
    data = json.loads(Path(a.words).read_text())
    db = envelope(a.media)
    words, thr = refine(data["words"], db)
    out = Path(a.out) if a.out else Path(a.words).with_name(Path(a.words).name.replace(".words.json", ".words.refined.json"))
    out.write_text(json.dumps({**data, "words": words, "energy_threshold_db": round(thr, 1)}, indent=2, ensure_ascii=False) + "\n")
    moved = sum(1 for w in words if abs(w["end"] - w["orig_end"]) > 0.15)
    print(f"{out.name}: {len(words)} words, threshold {thr:.1f} dB, {moved} word(s) re-timed by > 0.15 s")


if __name__ == "__main__":
    main()
