"""Shared helpers for the Vibe Editing System scripts."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repository root


def project_root(hint=None):
    """The project folder (the nearest ancestor holding project.json) for a file or folder.

    Falls back to the current directory so the scripts still work on a loose file.
    """
    start = Path(hint).resolve() if hint else Path.cwd()
    for p in [start, *start.parents]:
        if (p / "project.json").exists():
            return p
    return Path.cwd()


def work_dir(hint=None):
    return project_root(hint) / "work"


def require(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' not found. Run: python scripts/check_setup.py")


def probe_duration(video):
    require("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def load_words(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def fmt_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:05.2f}"


def load_names(path=None):
    """Returns (hint names, {wrong: right} corrections) from the project's names.txt."""
    names, fixes = [], {}
    path = path or project_root() / "names.txt"
    if not Path(path).exists():
        return names, fixes
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" in line:
            wrong, right = (p.strip() for p in line.split("=>", 1))
            fixes[wrong.lower()] = right
            names.append(right)
        else:
            names.append(line)
    return list(dict.fromkeys(names)), fixes
