"""Validate a rendered MP4 with ffprobe + a full decode.

Usage:
    python3 scripts/validate_video.py out.mp4 --project project/<name>
    python3 scripts/validate_video.py out.mp4 --duration 70.2 --size 1920x1080 --fps 30

Checks: file exists and is non-empty, has an H.264 video stream, resolution, frame rate,
duration within tolerance of the composition's data-duration, frame count, a clean full
decode (no errors), and that frames are not all identical (a blank render fails).
Exit code 0 only if every check passes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd, binary=False):
    return subprocess.run(cmd, capture_output=True, text=not binary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--project")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--tolerance", type=float, default=0.5)
    a = ap.parse_args()

    v = Path(a.video)
    expected = a.duration
    if a.project and expected is None:
        m = re.search(r'data-composition-id="main"[^>]*data-duration="([\d.]+)"',
                      (Path(a.project) / "index.html").read_text(encoding="utf-8"))
        expected = float(m.group(1)) if m else None

    results = []

    def check(name, ok, detail):
        results.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<18} {detail}")

    print(f"Validating {v}")
    if not v.exists() or v.stat().st_size == 0:
        check("file exists", False, "missing or empty")
        sys.exit(1)
    check("file exists", True, f"{v.stat().st_size / 1e6:.2f} MB")

    p = sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames,pix_fmt",
            "-show_entries", "format=duration", "-of", "json", str(v)])
    if p.returncode != 0:
        check("ffprobe", False, p.stderr.strip()[:200])
        sys.exit(1)
    info = json.loads(p.stdout)
    s, dur = info["streams"][0], float(info["format"]["duration"])
    check("ffprobe", True, "readable")
    check("video codec", s["codec_name"] == "h264", f"{s['codec_name']} {s.get('pix_fmt')}")
    w, h = map(int, a.size.split("x"))
    check("resolution", (s["width"], s["height"]) == (w, h), f"{s['width']}x{s['height']} (want {a.size})")
    num, den = map(int, s["r_frame_rate"].split("/"))
    check("frame rate", abs(num / den - a.fps) < 0.01, f"{num / den:g} fps")
    if expected is not None:
        check("duration", abs(dur - expected) <= a.tolerance, f"{dur:.2f}s (composition {expected:.2f}s)")
        frames = int(s["nb_read_frames"])
        check("frame count", abs(frames - expected * a.fps) <= a.fps * a.tolerance, f"{frames} frames")
    else:
        print(f"  INFO  duration           {dur:.2f}s (no expected value given)")

    d = sh(["ffmpeg", "-v", "error", "-i", str(v), "-f", "null", "-"])
    check("full decode", d.returncode == 0 and not d.stderr.strip(), d.stderr.strip()[:200] or "no errors")

    # Sample frames across the video; a blank/frozen render has identical hashes.
    hashes = set()
    n = 8
    for k in range(n):
        t = dur * (k + 0.5) / n
        f = sh(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "bmp", "-"], binary=True)
        hashes.add(hashlib.md5(f.stdout).hexdigest())
    check("content varies", len(hashes) >= n - 1, f"{len(hashes)}/{n} distinct sampled frames")

    print("RESULT:", "ALL CHECKS PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
