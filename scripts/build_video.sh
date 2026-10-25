#!/usr/bin/env bash
# Markdown brief -> animated explainer MP4 (text-driven scenes, silent). One command.
# Usage: scripts/build_video.sh <brief.md> <slug> [--format 16:9|9:16|1:1]
#   Creates projects/<slug>/ if needed, generates one scene per "## NN · Section" of the Markdown
#   (scripts/md_to_video.py), bundles GSAP, checks, renders and validates -> projects/<slug>/exports/<slug>.mp4
# (For a raw talking-head video use scripts/produce.sh instead; see README.md.)
set -euo pipefail
md="${1:?usage: build_video.sh <brief.md> <slug> [--format 16:9]}"; slug="${2:?project slug required}"; shift 2
fmt="16:9"; [ "${1:-}" = "--format" ] && fmt="${2:?format}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
proj="$root/projects/$slug"
[ -f "$md" ] || { echo "Markdown not found: $md" >&2; exit 1; }
[ -d "$proj" ] || python3 "$root/scripts/new_project.py" "$slug" --format "$fmt"
[ -f "$proj/hyperframes/hyperframes.json" ] || { echo "$proj/hyperframes missing" >&2; exit 1; }
python3 "$root/scripts/md_to_video.py" "$md" "$proj/hyperframes"
cp -f "$md" "$proj/input/brief.md"
bash "$root/scripts/produce.sh" "$proj" --no-build --final
