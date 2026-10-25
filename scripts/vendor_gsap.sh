#!/usr/bin/env bash
# Replace CDN script tags in a HyperFrames composition with local copies from npm.
# Usage: scripts/vendor_gsap.sh project/my-video [gsap-version]
# Needed in cloud sessions, where cdn.jsdelivr.net is blocked but the npm registry is not.
set -euo pipefail
dir="${1:?usage: vendor_gsap.sh <composition-dir> [version]}"
ver="${2:-3.14.2}"
mkdir -p "$dir/vendor"
if [ ! -f "$dir/vendor/gsap.min.js" ]; then
  tmp="$(mktemp -d)"
  (cd "$tmp" && npm pack "gsap@$ver" --silent >/dev/null && tar xzf gsap-*.tgz package/dist/gsap.min.js)
  cp "$tmp/package/dist/gsap.min.js" "$dir/vendor/gsap.min.js"
  rm -rf "$tmp"
fi
grep -rlE "cdn\.jsdelivr\.net/npm/gsap@[0-9.]+/dist/gsap\.min\.js" "$dir" --include=*.html 2>/dev/null \
  | xargs -r sed -i -E 's#https://cdn\.jsdelivr\.net/npm/gsap@[0-9.]+/dist/gsap\.min\.js#vendor/gsap.min.js#g'
echo "GSAP $ver vendored into $dir/vendor/gsap.min.js"
grep -rn "cdn\." "$dir" --include=*.html | grep -v node_modules || echo "No other CDN references in $dir"
