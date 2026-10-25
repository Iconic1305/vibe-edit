"""Versions: snapshot the edit before each round of notes, so you can go back.

Usage:
    python scripts/version.py save "logo moved next to hand"
    python scripts/version.py list
    python scripts/version.py restore v2

Run from inside a project folder (or any subfolder). Snapshots everything except
input/, exports/, previews/, node_modules and versions/ itself.
"""
import argparse
import shutil
import sys
from datetime import datetime

from common import project_root

ROOT = project_root()
VERSIONS = ROOT / "versions"
SKIP = {"versions", "input", "exports", "previews", "node_modules", ".git", "__pycache__"}


def existing():
    return sorted((p for p in VERSIONS.glob("v*") if p.is_dir() and p.name[1:].isdigit()),
                  key=lambda p: int(p.name[1:]))


def ignore(dir_, names):
    return [n for n in names if (dir_ == str(ROOT) and n in SKIP) or n in ("node_modules", "__pycache__")]


def save(note):
    n = (int(existing()[-1].name[1:]) + 1) if existing() else 1
    dest = VERSIONS / f"v{n}"
    shutil.copytree(ROOT, dest, ignore=ignore)
    (dest / "VERSION.txt").write_text(f"v{n} · {datetime.now():%Y-%m-%d %H:%M} · {note}\n", encoding="utf-8")
    print(f"Saved v{n}: {note}")


def list_versions():
    vs = existing()
    if not vs:
        print("No versions yet.")
    for v in vs:
        info = v / "VERSION.txt"
        print(info.read_text(encoding="utf-8").strip() if info.exists() else v.name)


def restore(name):
    src = VERSIONS / name
    if not src.is_dir():
        sys.exit(f"No version called {name}")
    save(f"auto-backup before restoring {name}")
    for item in src.iterdir():
        if item.name == "VERSION.txt":
            continue
        dest = ROOT / item.name
        if item.is_dir():
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print(f"Restored {name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("note", nargs="?", default="")
    sub.add_parser("list")
    r = sub.add_parser("restore")
    r.add_argument("name")
    args = ap.parse_args()
    VERSIONS.mkdir(exist_ok=True)
    {"save": lambda: save(args.note), "list": list_versions, "restore": lambda: restore(args.name)}[args.cmd]()


if __name__ == "__main__":
    main()
