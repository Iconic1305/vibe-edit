"""Check that the whole kit is installed: Node.js 22+, FFmpeg, Python 3, Whisper.

Usage:
    python scripts/check_setup.py

Then run `npx hyperframes doctor` for the HyperFrames side.
"""
import importlib.util
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

OS = platform.system()
INSTALL = {
    "node": {"Windows": "winget install OpenJS.NodeJS.LTS", "Darwin": "brew install node"},
    "ffmpeg": {"Windows": "winget install Gyan.FFmpeg", "Darwin": "brew install ffmpeg"},
    "whisper": {"Windows": "python -m pip install faster-whisper",
                "Darwin": "brew install whisper-cpp   (or: python3 -m pip install faster-whisper)"},
}


def version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return None


def hint(tool):
    return INSTALL[tool].get(OS, "see README.md")


def main():
    ok = True

    def row(name, good, detail):
        nonlocal ok
        ok &= good
        print(f"  {'✔' if good else '✘'} {name:<12} {detail}")

    print("Vibe Editing System · setup check\n")

    node = version(["node", "-v"]) if shutil.which("node") else None
    major = int(re.findall(r"\d+", node)[0]) if node else 0
    row("Node.js", major >= 22, node + ("" if major >= 22 else "  (need 22+)") if node else f"missing → {hint('node')}")

    ff = version(["ffmpeg", "-version"]) if shutil.which("ffmpeg") else None
    row("FFmpeg", bool(ff), ff.split(" Copyright")[0] if ff else f"missing → {hint('ffmpeg')}")

    py_ok = sys.version_info >= (3, 9)
    row("Python", py_ok, platform.python_version())

    fw = importlib.util.find_spec("faster_whisper") is not None
    wcpp = shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    row("Whisper", fw or bool(wcpp),
        "faster-whisper" if fw else ("whisper-cpp (HyperFrames will use it)" if wcpp else f"missing → {hint('whisper')}"))

    hf = version(["npx", "--yes", "hyperframes@0.8.199", "--version"]) if shutil.which("npx") else None
    row("HyperFrames", bool(hf), hf or "npx hyperframes unavailable (needs Node 22+ and npm registry access)")
    probe = shutil.which("ffprobe")
    row("ffprobe", bool(probe), version(["ffprobe", "-version"]).split(" Copyright")[0] if probe else "missing (ships with FFmpeg)")
    chrome = Path.home() / ".cache" / "hyperframes" / "chrome"
    print(f"  {'✔' if chrome.exists() else '•'} {'Chrome':<12} {'cached for rendering' if chrome.exists() else 'not cached yet: run npx hyperframes browser ensure'}")

    claude = shutil.which("claude")
    print(f"  {'✔' if claude else '•'} {'Claude Code':<12} {'found' if claude else 'not on PATH (fine if you use the desktop app)'}")

    print()
    if ok:
        print("All set. Next: claude plugin marketplace add heygen-com/hyperframes")
        print("            claude plugin install hyperframes@hyperframes")
        print("            npx hyperframes doctor")
    else:
        print("Install what's missing, open a NEW terminal, and run this again.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
