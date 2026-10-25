# Vibe Editing System: repo instructions for Claude

This repo is a permanent AI video editor (no Premiere / CapCut). The user films one take, drops it in a
project folder and describes the style. You transcribe it (Whisper), look at it (FFmpeg), plan it, build
it as HyperFrames compositions and render a validated MP4. The user never reads code.

**First, read the project's own `projects/<slug>/CLAUDE.md`** (it has that project's workflow and style rules).
Start a new project: `python3 scripts/new_project.py <name> --format 9:16|16:9|1:1`.

## Layout

```
scripts/      the tools (below)            templates/   edit.template.json, edit.examples.md, brief + CLAUDE templates
prompts/      prompt library for the user  sfx/         synthetic default sound effects (scripts/make_sfx.sh)
projects/<slug>/   ONE PERSISTENT FOLDER PER VIDEO: input/ assets/ refs/ sfx/ music/ work/ hyperframes/
                   previews/ exports/ versions/ + project.json, instructions.md, edit.json, names.txt, CLAUDE.md
```

## Tools

| Script | Job |
|---|---|
| `new_project.py` | create `projects/<slug>/`, init HyperFrames, bundle GSAP |
| `transcribe.py` | Whisper (faster-whisper) → `work/<take>.words.json`, word-level timestamps, names fixed from `names.txt` |
| `extract_frames.py` / `analyze_video.py` | FFmpeg stills + contact sheet **you must look at**; brightness, motion, silences, loudness, scene cuts, flags |
| `beat_sheet.py` | timestamped beat sheet table → wait for the user's OK |
| `cut_dead_air.py` | cut pauses > 0.3 s without cutting inside a word; remaps word times |
| `build_edit.py` | `edit.json` + words → HyperFrames: captions (pop/box/minimal), title card, lower third, zooms, jump-cut punch, flashes, pop-ups, 3D logo (CSS 3D), SFX, music; 9:16 / 16:9 / 1:1 |
| `vendor_gsap.sh` | replaces the blocked jsdelivr GSAP `<script>` with a local copy (**do not modify; runs on every project**) |
| `produce.sh` | build → vendor GSAP → check → snapshot → render → validate (`--final` for exports/, `--no-build` for hand-written compositions) |
| `validate_video.py` | ffprobe: codec, resolution, fps, duration vs composition, frame count, full decode, non-blank |
| `md_to_video.py` / `build_video.sh` | Markdown guide → animated explainer MP4 (one scene per `## NN · Section`) |
| `commit_project.sh` | stage + commit (+ `--push`) with guards: 25 MB limit, no raw media in `input/`, secret scan |
| `version.py` | `save` / `list` / `restore` project snapshots |
| `selftest.sh` | end-to-end regression on the synthetic sample project |
| `fetch_icloud_album.py` | download the videos of a PUBLIC iCloud shared-album link into `input/` (never overwrites), ffprobe each |
| `make_proxies.sh` | SDR BT.709 30 fps editing proxies; **tone-maps HDR (iPhone HLG/Dolby Vision)**. Always edit from proxies, never from HDR originals |
| `refine_words.py` / `assemble_timeline.py` | multi-take A-roll: align captions to real voiced chunks, apply reviewed Hinglish (`work/hinglish.json`), cut dead air, write `master.mp4` + `master.words.json` + `captions_review.md` |
| `build_reel.py` | layered Reels builder (`"builder": "reel"` in edit.json): captions BEHIND (cut-out) and IN FRONT of the speaker, B-roll cutaways with step chips, zooms, flashes, SFX |

## Rules

- **Never delete or modify anything in a project's `input/`**, nor a user's existing project or final export. New work goes in new files/projects.
- **Never invent a transcript, footage or assets.** If Whisper can't run, or a file is missing, say exactly which file the user must provide.
- **Never claim a render worked** until `scripts/validate_video.py` passes on the MP4 *and* you've looked at snapshot frames.
- **No CDN at render time.** Cloud sessions block `cdn.jsdelivr.net` and `huggingface.co`. GSAP is vendored per project; `produce.sh` fails if any `http(s)://` asset reference remains. Fonts: only the bundled families, or `@font-face` to a local file.
- Plan before building; one change per round; effects tied to a spoken word (`when`) or a time (`at`).
- Don't commit raw video, secrets or files over 25 MB. Final exports ≤ 25 MB are tracked.
- Silent output unless the user supplies music/voice: no voiceover or music is invented (SFX are synthetic and optional).

## Hinglish workflow (Hindi speech -> Roman captions)

Whisper `--language hi --model medium --clean --prompt "<names>"` writes Devanagari. Convert to Roman Hinglish by hand in
`work/hinglish.json` (one reviewed string per Whisper word index, `drop` for stutters, `back` for words behind the speaker), then
`assemble_timeline.py`. Show the owner `work/captions_review.md` (heard vs shown, low-confidence words) and flag anything uncertain.
Never invent names: use only names visible on screen in the footage or spoken by the host; otherwise say what is missing.

## Known limits (be upfront with the user)

- iPhone footage is HDR: edit from `make_proxies.sh` SDR proxies. Rendering HDR-tagged sources makes HyperFrames use a very slow `rgb48le` path (30+ min for 45 s) and looks washed out when not tone-mapped.
- The speaker cut-out (`npx hyperframes remove-background`, u2net on CPU) costs ~0.45 s/frame (about 10 min for 45 s). Redo it whenever the master video changes (colors must match the footage).

- Whisper's model downloads from huggingface.co on first use; blocked in the cloud sandbox. Run `transcribe.py` where it is reachable, or pass `--model <local folder>`, then commit `work/*.words.json`.
- `analyze_video.py` measures (light, motion, audio, cuts); judging faces, hands and empty space is done by *you* viewing the contact sheet. There is no face tracking: wide→vertical reframing uses `source.focus_x`.
- "3D" is CSS 3D (spinning/thrown card with perspective), not a WebGL scene. Cut-outs of the speaker (background removal) need `npx hyperframes remove-background` and a clean plate; not wired into `build_edit.py` yet.
- Music ducking under the voice is a constant low volume, not automatic.
- HyperFrames renders in software at roughly 1.5× real time (100 s of video ≈ 2m45s).
