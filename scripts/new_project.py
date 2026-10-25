"""Create a persistent video project: projects/<slug>/ with its own folders, HyperFrames
project (GSAP bundled locally), CLAUDE.md, edit.json and names.txt.

Usage:
    python3 scripts/new_project.py my-reel [--format 9:16|16:9|1:1] [--no-hyperframes]

Layout created:
    projects/<slug>/
      project.json      marks the folder as a project (scripts find it by walking up)
      CLAUDE.md         project-specific instructions for Claude (from templates/)
      instructions.md   your editing brief: style, effects, tone  <- you write this
      edit.json         the machine-readable edit spec Claude fills in
      names.txt         names Whisper must spell right
      input/            raw video + clean plates (large media is git-ignored)
      assets/ refs/ sfx/ music/   logos, style references, sounds
      work/             transcripts, beat sheets, cut lists, analysis (JSON/MD tracked)
      hyperframes/      the HyperFrames project (generated compositions)
      previews/ exports/ versions/
Never overwrites an existing project.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
HF = ["npx", "--yes", "hyperframes@0.8.199"]
DIRS = ["input", "assets", "refs", "sfx", "music", "work", "previews", "exports", "versions"]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--format", default="9:16", choices=FORMATS)
    ap.add_argument("--no-hyperframes", action="store_true", help="skip `hyperframes init` (offline)")
    a = ap.parse_args()

    slug = slugify(a.name)
    if not slug:
        sys.exit("Project name must contain letters or digits")
    proj = ROOT / "projects" / slug
    if proj.exists():
        sys.exit(f"{proj} already exists. Pick another name; existing projects are never overwritten.")

    proj.mkdir(parents=True)
    for d in DIRS:
        (proj / d).mkdir()
        (proj / d / ".gitkeep").touch()
    # default sound effects (synthetic, royalty-free) so SFX work out of the box
    for f in (ROOT / "sfx").glob("*.wav"):
        shutil.copy2(f, proj / "sfx" / f.name)

    w, h = FORMATS[a.format]
    (proj / "project.json").write_text(json.dumps({
        "name": a.name, "slug": slug, "format": a.format, "width": w, "height": h, "fps": 30,
        "created": date.today().isoformat(),
    }, indent=2) + "\n")

    spec = json.loads((ROOT / "templates" / "edit.template.json").read_text())
    spec["format"] = a.format
    (proj / "edit.json").write_text(json.dumps(spec, indent=2) + "\n")
    (proj / "names.txt").write_text(
        "# Names Whisper must spell right. One per line; use 'wrong => right' to force a fix.\n")
    (proj / "instructions.md").write_text((ROOT / "templates" / "instructions.template.md").read_text())
    claude = (ROOT / "templates" / "PROJECT_CLAUDE.template.md").read_text()
    (proj / "CLAUDE.md").write_text(claude.replace("{{NAME}}", a.name).replace("{{SLUG}}", slug).replace("{{FORMAT}}", a.format))

    if not a.no_hyperframes:
        r = subprocess.run(HF + ["init", str(proj / "hyperframes"), "--example", "blank", "--non-interactive"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("hyperframes init failed:\n" + (r.stderr or r.stdout)[-600:], file=sys.stderr)
            sys.exit(1)
        # bundled GSAP instead of the blocked CDN (existing fix, run on every new project)
        subprocess.run(["bash", str(ROOT / "scripts" / "vendor_gsap.sh"), str(proj / "hyperframes")], check=True)

    print(f"\nCreated projects/{slug}  ({a.format}, {w}x{h})")
    print(f"Next: drop your raw video in projects/{slug}/input/ and write projects/{slug}/instructions.md")


if __name__ == "__main__":
    main()
