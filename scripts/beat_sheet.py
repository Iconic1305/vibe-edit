"""Plan: turn a words file into a beat-sheet skeleton (one row per sentence).

Usage:
    python scripts/beat_sheet.py work/take.words.json [--format 9:16]

Writes work/<name>.beats.md. Claude fills in the On screen / Position / Sound
columns, then waits for the user's OK before building.
"""
import argparse
from pathlib import Path

from common import fmt_time, load_words, work_dir

BREAKS = (".", "!", "?", "…")


def sentences(words, max_len=14):
    cur = []
    for w in words:
        cur.append(w)
        if w["word"].endswith(BREAKS) or len(cur) >= max_len:
            yield cur
            cur = []
    if cur:
        yield cur


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words")
    ap.add_argument("--format", default="9:16")
    args = ap.parse_args()

    WORK = work_dir(args.words)
    data = load_words(args.words)
    name = Path(args.words).name.replace(".words.json", "")
    rows = [
        f"# Beat sheet · {name}",
        "",
        f"Format: **{args.format}** · Safe zone: nothing in the bottom 20% or near the right edge.",
        "",
        "| # | Start | End | Words | On screen | Position | Sound |",
        "|---|-------|-----|-------|-----------|----------|-------|",
    ]
    for i, s in enumerate(sentences(data["words"]), 1):
        text = " ".join(w["word"] for w in s).replace("|", "/")
        rows.append(f"| {i} | {fmt_time(s[0]['start'])} | {fmt_time(s[-1]['end'])} | {text} |  |  |  |")
    rows += ["", "**Status:** waiting for OK before building."]

    out = WORK / f"{name}.beats.md"
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Saved {out.relative_to(WORK.parent)} ({len(rows) - 8} beats)")


if __name__ == "__main__":
    main()
