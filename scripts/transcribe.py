"""Ears: transcribe a video with faster-whisper, one timestamp per word.

Usage:
    python scripts/transcribe.py footage/take.mp4 [--model small] [--language en]

Writes work/<name>.words.json and work/<name>.transcript.txt.
Names in names.txt are passed to Whisper as hints and "wrong => right" lines
are fixed in the output.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from common import fmt_time, load_names, project_root, save_json, work_dir

CLEAN = "highpass=f=80,afftdn=nf=-28,dynaudnorm=f=150:g=15,loudnorm=I=-16:TP=-1.5"


def load_audio(path, clean=False):
    """Decode any media file to 16 kHz mono float32 with FFmpeg (independent of PyAV versions)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", *(["-af", CLEAN] if clean else []), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True)
    if raw.returncode != 0 or not raw.stdout:
        sys.exit(f"No decodable audio in {path}: {raw.stderr.decode()[:200]}")
    return np.frombuffer(raw.stdout, dtype=np.float32)


PUNCT = re.compile(r"^(\W*)(.*?)(\W*)$")


def fix_word(text, fixes):
    lead, core, trail = PUNCT.match(text).groups()
    right = fixes.get(core.lower())
    return f"{lead}{right}{trail}" if right else text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--model", default="small", help="tiny, base, small, medium, large-v3, or a local model folder (default: small)")
    ap.add_argument("--language", default=None, help="e.g. en, es, pt (default: auto-detect)")
    ap.add_argument("--device", default="auto", help="auto, cpu or cuda")
    ap.add_argument("--prompt", default=None, help="extra initial prompt, e.g. a Roman-script Hinglish sentence to bias the output script")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--clean", action="store_true", help="denoise + normalise loudness before transcribing (quiet or noisy takes)")
    args = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. Run: python -m pip install faster-whisper")

    video = Path(args.video)
    if not video.exists():
        sys.exit(f"Not found: {video}")

    WORK = work_dir(video)
    names, fixes = load_names(project_root(video) / "names.txt")
    hint = " ".join(x for x in [args.prompt, ("Names: " + ", ".join(names) + ".") if names else None] if x) or None

    print(f"Loading Whisper '{args.model}' (downloads on first use)…")
    try:
        model = WhisperModel(args.model, device=args.device, compute_type="int8" if args.device in ("auto", "cpu") else "auto")
    except Exception as exc:  # no network, blocked host, bad path
        sys.exit(
            f"Could not load Whisper model '{args.model}': {type(exc).__name__}: {exc}\n"
            "The model downloads from huggingface.co on first use. If that host is blocked, either\n"
            "  * run this step on a machine with internet access, then commit work/<take>.words.json, or\n"
            "  * download the model once and pass its folder:  --model /path/to/faster-whisper-small"
        )
    segments, info = model.transcribe(
        load_audio(video, args.clean),
        beam_size=args.beam,
        condition_on_previous_text=False,
        temperature=[0.0, 0.2, 0.4],
        language=args.language,
        word_timestamps=True,
        initial_prompt=hint,
        vad_filter=False,  # keep pauses visible so cut_dead_air.py can find them
    )

    words, segs = [], []
    for seg in segments:
        seg_words = []
        for w in seg.words or []:
            item = {
                "word": fix_word(w.word.strip(), fixes),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "prob": round(w.probability, 3),
            }
            words.append(item)
            seg_words.append(item["word"])
        segs.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": " ".join(seg_words)})
        print(f"  {fmt_time(seg.start)}  {segs[-1]['text']}")

    out = WORK / f"{video.stem}.words.json"
    save_json({
        "source": str(video),
        "language": info.language,
        "duration": round(info.duration, 3),
        "words": words,
        "segments": segs,
    }, out)

    txt = WORK / f"{video.stem}.transcript.txt"
    txt.write_text(
        "\n".join(f"{w['start']:7.2f}s -> {w['end']:7.2f}s  {w['word']}" for w in words) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(words)} words · language {info.language} · {info.duration:.1f}s")
    print(f"Saved {out.relative_to(WORK.parent)} and {txt.relative_to(WORK.parent)}")


if __name__ == "__main__":
    main()
