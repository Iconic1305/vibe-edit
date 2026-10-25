#!/usr/bin/env bash
# End-to-end regression test on the synthetic sample project (draft render + ffprobe validation).
# Usage: scripts/selftest.sh     Exit code 0 only if the sample renders and validates.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$root/scripts/check_setup.py" || true
bash "$root/scripts/make_sample_project.sh" sample-talk
bash "$root/scripts/produce.sh" "$root/projects/sample-talk"
echo "SELFTEST PASSED"
