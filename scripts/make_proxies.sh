#!/usr/bin/env bash
# Make editing proxies (SDR BT.709, 30 fps, 1 keyframe/s) from raw clips. Originals are never touched.
# Usage: scripts/make_proxies.sh <input-dir> <output-dir> [clip-name ...]   (default: every video in input-dir)
#
# Why: iPhone video is usually HDR (HLG / Dolby Vision, BT.2020). Used as-is it looks flat and washed out in
# SDR players and pushes HyperFrames into its very slow HDR render path. HDR sources are tone-mapped to SDR
# (zscale + mobius); SDR sources are only rescaled. Portrait 4K -> 1080x1920, landscape -> 1920 wide.
set -euo pipefail
in="${1:?usage: make_proxies.sh <input-dir> <output-dir> [names...]}"; out="${2:?output dir}"; shift 2
mkdir -p "$out"
TM="zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:desat=0.3,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
if [ "$#" -gt 0 ]; then files=(); for n in "$@"; do files+=("$in/$n"); done
else mapfile -t files < <(find "$in" -maxdepth 1 -type f \( -iname '*.mov' -o -iname '*.mp4' -o -iname '*.m4v' \) | sort); fi
for f in "${files[@]}"; do
  base="$(basename "$f")"; name="$(echo "${base%.*}" | tr ' ' '_' | tr -cd 'A-Za-z0-9_.-')"
  IFS=, read -r w h trc < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,color_transfer -of csv=p=0 "$f")
  vf="fps=30"
  if [ "${trc:-}" = "arib-std-b67" ] || [ "${trc:-}" = "smpte2084" ]; then vf="$TM,$vf"; echo "HDR ($trc) -> tone-mapping $base"; fi
  if [ "$h" -gt "$w" ]; then [ "$w" -gt 1080 ] && vf="$vf,scale=1080:1920" || vf="$vf,scale=720:-2"; else vf="$vf,scale=1920:-2"; fi
  ffmpeg -y -loglevel error -i "$f" -vf "$vf" -c:v libx264 -preset veryfast -crf 18 -g 30 -keyint_min 30 -pix_fmt yuv420p \
    -colorspace bt709 -color_primaries bt709 -color_trc bt709 -movflags +faststart -c:a aac -b:a 160k -ar 48000 "$out/$name.mp4"
  echo "ok $out/$name.mp4"
done
