"""Eyes: pull still frames from a video so Claude can see the shot.

Usage:
    python scripts/extract_frames.py footage/take.mp4 [--fps 1] [--width 640]
    python scripts/extract_frames.py footage/take.mp4 --at 7.0 12.5   # specific moments

Writes work/<name>_frames/ with files named by timestamp (t0007.00.jpg)
plus a contact_sheet.jpg that shows everything in one image.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

from common import probe_duration, require, work_dir

WORK = None


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=1.0, help="frames per second (default 1)")
    ap.add_argument("--width", type=int, default=640, help="frame width in px (default 640)")
    ap.add_argument("--at", type=float, nargs="+", help="grab only these timestamps (seconds)")
    ap.add_argument("--no-sheet", action="store_true", help="skip the contact sheet")
    args = ap.parse_args()

    require("ffmpeg")
    video = Path(args.video)
    if not video.exists():
        sys.exit(f"Not found: {video}")

    global WORK
    WORK = work_dir(video)
    out = WORK / f"{video.stem}_frames"
    out.mkdir(parents=True, exist_ok=True)
    scale = f"scale={args.width}:-2"

    if args.at:
        times = args.at
    else:
        duration = probe_duration(video)
        step = 1 / args.fps
        times = [round(i * step, 2) for i in range(int(math.floor(duration / step)) + 1) if i * step < duration]

    files = []
    for t in times:
        f = out / f"t{t:07.2f}.jpg"
        run(["ffmpeg", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", scale, "-q:v", "3", str(f)])
        if f.exists():
            files.append(f)
    print(f"Saved {len(files)} frames to {out.relative_to(WORK.parent)}/")

    if not args.no_sheet and len(files) > 1:
        sheet = make_contact_sheet(files, out)
        if sheet:
            print(f"Contact sheet: {sheet.relative_to(WORK.parent)}")


def make_contact_sheet(files, out):
    """Tile all frames into one image, each labelled with its timestamp."""
    thumbs = out / "_thumbs"
    thumbs.mkdir(exist_ok=True)
    for i, f in enumerate(files):
        label = f"{float(f.stem[1:]):.1f}"
        thumb = thumbs / f"{i:05d}.jpg"
        base = ["ffmpeg", "-y", "-i", str(f)]
        try:
            run(base + ["-vf", f"scale=320:-2,drawtext=text='{label}s':x=6:y=6:fontsize=20"
                               ":fontcolor=white:box=1:boxcolor=black@0.6", str(thumb)])
        except subprocess.CalledProcessError:
            run(base + ["-vf", "scale=320:-2", str(thumb)])  # build without drawtext
    cols = min(6, len(files))
    rows = math.ceil(len(files) / cols)
    sheet = out / "contact_sheet.jpg"
    run(["ffmpeg", "-y", "-i", str(thumbs / "%05d.jpg"), "-vf", f"tile={cols}x{rows}",
         "-frames:v", "1", "-q:v", "3", str(sheet)])
    for t in thumbs.iterdir():
        t.unlink()
    thumbs.rmdir()
    return sheet if sheet.exists() else None


if __name__ == "__main__":
    main()
