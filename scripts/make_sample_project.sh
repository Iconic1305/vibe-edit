#!/usr/bin/env bash
# Create (or refresh) a clearly-labelled SYNTHETIC sample project to test the whole pipeline end to end.
# Usage: scripts/make_sample_project.sh [slug]      (default: sample-talk)
# The footage is generated test video (colour bars + tone bursts); word timings are hand-written in
# templates/sample/take.words.json, not a real transcription. Existing input/ files are never overwritten.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
slug="${1:-sample-talk}"; P="$root/projects/$slug"
[ -d "$P" ] || python3 "$root/scripts/new_project.py" "$slug" --format 9:16
if [ ! -f "$P/input/take.mp4" ]; then
  ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=1280x720:r=30:d=12" -f lavfi -i "sine=f=300:r=48000:d=12" \
    -af "volume='if(between(t,0.5,1.4)+between(t,2.6,3.7)+between(t,5.0,5.9)+between(t,7.2,8.6)+between(t,10.0,11.0),0.5,0)':eval=frame" \
    -vf "drawtext=text='SAMPLE FOOTAGE (synthetic)':x=(w-tw)/2:y=40:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.6" \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$P/input/take.mp4"
fi
[ -f "$P/assets/logo.png" ] || ffmpeg -y -loglevel error -f lavfi -i "color=c=0xFFD400:s=400x400,format=rgba,drawtext=text='LOGO':x=(w-tw)/2:y=(h-th)/2:fontsize=110:fontcolor=black" -frames:v 1 "$P/assets/logo.png"
cp -n "$root/templates/sample/take.words.json" "$P/work/take.words.json" || true
cd "$P"
python3 "$root/scripts/analyze_video.py" input/take.mp4
python3 "$root/scripts/extract_frames.py" input/take.mp4 --fps 1
python3 "$root/scripts/beat_sheet.py" work/take.words.json
python3 "$root/scripts/cut_dead_air.py" input/take.mp4 work/take.words.json
cp "$root/templates/sample/edit.json" edit.json
echo "Sample ready: projects/$slug  ->  bash scripts/produce.sh projects/$slug"
