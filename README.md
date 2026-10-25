# Vibe Editing System

*By Ideabro Studio. Adapted from "Let Claude Edit Your Videos" by @pauloshimas, The Creator Stack (2026).*

Film yourself talking, drop the file in a project folder, describe the style, and Claude Code edits it:
transcribes every word (Whisper), looks at your frames (FFmpeg), builds captions, zooms, pop-ups, sound
effects and 3D motion as HyperFrames compositions, and renders a validated MP4. No timeline, no editing app.

```
01 import  →  02 transcribe  →  03 look & analyze  →  04 beat sheet (you approve)  →  05 build compositions
   →  06 check + preview  →  07 render  →  08 ffprobe validate  →  09 save  →  10 commit & push
```

## Quick start

```bash
python3 scripts/check_setup.py                       # Node 22+, FFmpeg, Python, Whisper, HyperFrames
python3 scripts/new_project.py my-reel --format 9:16 # 9:16 Reels · 16:9 YouTube · 1:1 square
cp ~/Videos/take.mp4 projects/my-reel/input/         # your raw video (never modified, never committed)
$EDITOR projects/my-reel/instructions.md             # describe the style and effects in plain words
claude                                               # open Claude Code in the repo, then paste:
```
> New project "my-reel". My raw video is projects/my-reel/input/take.mp4 and my brief is in projects/my-reel/instructions.md. Follow projects/my-reel/CLAUDE.md: transcribe, look at the frames, analyze the video, write the beat sheet and wait for my OK.

More prompts: [`prompts/PROMPTS.md`](prompts/PROMPTS.md). Effect recipes: [`templates/edit.examples.md`](templates/edit.examples.md).

## What each project folder holds

`projects/<slug>/`: `input/` raw media (git-ignored) · `assets/ refs/ sfx/ music/` · `work/` transcript, analysis, beat sheet, cut list (tracked) ·
`hyperframes/` generated compositions + local GSAP · `previews/` drafts · `exports/` final MP4s (tracked if ≤ 25 MB) ·
`instructions.md` your brief · `edit.json` the edit spec · `CLAUDE.md` project rules · `names.txt` spellings.

## Commands

| Do this | Run |
|---|---|
| New project | `python3 scripts/new_project.py <name> --format 9:16` |
| Transcribe (word timestamps) | `python3 scripts/transcribe.py projects/<slug>/input/take.mp4 --language en` |
| Frames + analysis | `python3 scripts/extract_frames.py …/take.mp4` · `python3 scripts/analyze_video.py …/take.mp4` |
| Beat sheet | `python3 scripts/beat_sheet.py projects/<slug>/work/take.words.json` |
| Cut pauses | `python3 scripts/cut_dead_air.py …/take.mp4 …/take.words.json` |
| Draft preview | `bash scripts/produce.sh projects/<slug>` |
| Final render | `bash scripts/produce.sh projects/<slug> --final` |
| Validate any MP4 | `python3 scripts/validate_video.py out.mp4 --project projects/<slug>/hyperframes` |
| Save + push | `bash scripts/commit_project.sh <slug> "message" --push` |
| Markdown → explainer video | `bash scripts/build_video.sh guide.md <slug> --format 16:9` |
| Self-test everything | `bash scripts/selftest.sh` |

## Cloud / blocked-network note

HyperFrames templates load GSAP from `cdn.jsdelivr.net`, which cloud sandboxes block (`ERR_TUNNEL_CONNECTION_FAILED`,
`Cannot read properties of null (reading 'timeline')`). `scripts/vendor_gsap.sh` replaces it with a local copy; `new_project.py`
and `produce.sh` run it automatically. Whisper's model comes from huggingface.co: if blocked, transcribe on your own computer
(or pass `--model <folder>`) and commit `work/<take>.words.json`.

## Included projects

- `projects/guide-explainer/`: the Ideabro guide (this repo's source brief, `input/brief.md`) turned into a 101 s, 1920×1080 explainer. Final: `exports/guide-explainer.mp4`.
- `projects/sample-talk/`: **synthetic** sample (generated colour-bar footage, hand-written word timings) used to test every effect: `bash scripts/make_sample_project.sh`.

See [`CLAUDE.md`](CLAUDE.md) for how Claude operates this repo and the known limits.
