#!/usr/bin/env bash
# Commit (and optionally push) one project's source + small outputs safely.
# Usage: scripts/commit_project.sh <slug> "commit message" [--push]
# Guards: refuses files > 25 MB, raw media in input/, and anything that looks like a secret.
set -euo pipefail
slug="${1:?usage: commit_project.sh <slug> \"message\" [--push]}"; msg="${2:?commit message required}"; push="${3:-}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$root"
proj="projects/$slug"; [ -d "$proj" ] || { echo "no such project: $proj" >&2; exit 1; }
MAX=$((25*1024*1024))

git add -A -- "$proj" scripts templates prompts sfx README.md CLAUDE.md .gitignore requirements.txt 2>/dev/null || git add -A -- "$proj"
bad=0
while IFS= read -r f; do
  [ -f "$f" ] || continue
  size=$(stat -c %s "$f")
  if [ "$size" -gt "$MAX" ]; then echo "TOO LARGE (>25MB), unstaging: $f"; git reset -q -- "$f"; bad=1; continue; fi
  case "$f" in */input/*.mp4|*/input/*.mov|*/input/*.mkv|*/input/*.wav|*/input/*.m4a) echo "RAW MEDIA, unstaging: $f"; git reset -q -- "$f"; bad=1; continue;; esac
  if grep -IEq '(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)' "$f" 2>/dev/null; then
    echo "POSSIBLE SECRET, unstaging: $f"; git reset -q -- "$f"; bad=1
  fi
done < <(git diff --cached --name-only)

if git diff --cached --quiet; then echo "Nothing to commit."; exit 0; fi
git commit -q -m "$msg"
echo "Committed: $(git log --oneline -1)"
[ "$bad" = 0 ] || echo "(some files were left out, see above)"
if [ "$push" = "--push" ]; then git push -u origin HEAD; fi
