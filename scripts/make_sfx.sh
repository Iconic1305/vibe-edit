#!/usr/bin/env bash
# Synthesize royalty-free default sound effects with FFmpeg into sfx/*.wav.
# Usage: scripts/make_sfx.sh [output-dir]   (default: <repo>/sfx)
# These are simple synthetic sounds (no samples, no licensing issues). Swap in your own files any time.
set -euo pipefail
out="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/sfx}"
mkdir -p "$out"
ff() { ffmpeg -y -loglevel error "$@"; }

# whoosh: band-passed noise swept up and faded in/out
ff -f lavfi -i "anoisesrc=d=0.7:c=pink:r=44100:a=0.8" \
   -af "highpass=f=300,lowpass=f=6000,afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.4,volume=0.8" "$out/whoosh.wav"
# pop: short falling sine blip
ff -f lavfi -i "aevalsrc='0.9*sin(2*PI*(900-3500*t)*t)*exp(-28*t)':d=0.18:s=44100" "$out/pop.wav"
# click: tiny noise tick
ff -f lavfi -i "anoisesrc=d=0.05:c=white:r=44100:a=0.9" -af "highpass=f=2000,afade=t=out:st=0.01:d=0.04" "$out/click.wav"
# boom / impact: low sine thud with noise tail
ff -f lavfi -i "aevalsrc='0.95*sin(2*PI*(70-40*t)*t)*exp(-6*t)':d=1.0:s=44100" "$out/boom.wav"
# ding: bright two-partial bell
ff -f lavfi -i "aevalsrc='0.5*(sin(2*PI*1320*t)+0.5*sin(2*PI*1980*t))*exp(-5*t)':d=0.9:s=44100" "$out/ding.wav"
# shutter: two quick noise clicks (camera)
ff -f lavfi -i "anoisesrc=d=0.25:c=white:r=44100:a=0.9" \
   -af "highpass=f=1500,volume='if(lt(t,0.03)+between(t,0.09,0.12),1,0.02)':eval=frame,afade=t=out:st=0.15:d=0.1" "$out/shutter.wav"
ls -la "$out"/*.wav
