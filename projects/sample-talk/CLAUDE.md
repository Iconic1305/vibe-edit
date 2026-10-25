# sample-talk: video project instructions for Claude

Project folder: `projects/sample-talk/` · Format: **9:16** · Editor: HyperFrames (HTML to MP4).
You edit this video by talking to the user: they describe it, you build it, they review. The user never
reads code. Repo-wide rules are in the root `CLAUDE.md`; this file is the project-specific part.

## Files (never delete or overwrite the user's media in `input/`)

| Path | What |
|---|---|
| `input/` | raw video and clean plates. **Read-only: never edit, rename or delete.** |
| `instructions.md` | the user's editing brief: the source of truth for style and effects |
| `edit.json` | machine-readable edit spec you fill in from the brief (`templates/edit.examples.md`) |
| `names.txt` | names Whisper must spell right |
| `assets/ refs/ sfx/ music/` | logos and images, style references, sound effects, music |
| `work/` | transcript, frames, analysis, beat sheet, cut list, build report |
| `hyperframes/` | generated HyperFrames project (regenerate with `build_edit.py`, don't hand-edit) |
| `previews/` `exports/` | draft renders and final MP4s (keep finals) |

## Workflow (from the repo root)

1. **Ears**: `python3 scripts/transcribe.py projects/sample-talk/input/take.mp4 --language en`
   → `work/take.words.json` (every word with start/end). If Whisper can't download its model (blocked
   network), say so and ask the user to run this step elsewhere and commit the JSON. Never invent a transcript.
2. **Eyes**: `python3 scripts/extract_frames.py projects/sample-talk/input/take.mp4 --fps 1` then *look* at
   `work/take_frames/contact_sheet.jpg`: where are the face and hands, what is behind, what is empty?
   `python3 scripts/analyze_video.py …/take.mp4` flags dark footage, quiet audio, silences, scene cuts.
3. **Plan**: `python3 scripts/beat_sheet.py projects/sample-talk/work/take.words.json`; fill in the table
   (what appears, where, which sound) and **wait for the user's OK**.
4. **Rough cut** (if asked): `python3 scripts/cut_dead_air.py …/take.mp4 …/work/take.words.json`
   then point `edit.json` `source` at `work/take.cut.mp4`, `work/take.cut.words.json`, `work/take.cuts.json`.
5. **Spec**: translate `instructions.md` into `edit.json`. Every effect is tied to a spoken word (`when`) or a time (`at`).
6. **Build**: `bash scripts/produce.sh projects/sample-talk` generates the compositions, bundles GSAP locally
   (`scripts/vendor_gsap.sh`), runs `hyperframes check`, snapshots, renders a preview and validates it.
7. **Review**: show frames (`npx hyperframes snapshot`) and check them yourself before telling the user it's done.
   Give the user the preview path; take notes one per line with a time ("at 0:07 …").
8. **Render final**: `bash scripts/produce.sh projects/sample-talk --final` → `exports/sample-talk.mp4`, validated with ffprobe.
9. **Save**: `bash scripts/commit_project.sh sample-talk "message"`; run `scripts/version.py save` before risky changes.

## Style rules (edit these for this project)

- Accent `#FFD400`, white text, font Inter (bundled; any other font needs `@font-face` in `hyperframes/assets/fonts/`).
- Captions 2–3 words, key word highlighted, ~65% of frame height. Nothing in the bottom 20% or near the
  right edge for vertical video. Zooms ≤ 1 per 5 s, 1.2×, hold ~2 s.
- Give every effect a twist (the logo is thrown, the speaker vanishes) and a sound.
- One change per round of notes; save a version before each round.

## Hard rules

- No network at render time: GSAP is vendored (`hyperframes/vendor/gsap.min.js`). Never reintroduce CDN `<script>`/fonts/images.
- Never claim a render succeeded without `scripts/validate_video.py` passing on the MP4.
- Never commit raw video, secrets or files over 25 MB (`commit_project.sh` enforces it).
