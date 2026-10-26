# Edit notes: Bulandshahr AI website video (D' Closet)

Final (v2): `exports/bulandshahr-ai-website_web.mp4` (share, 27 MB, in git) and `exports/bulandshahr-ai-website.mp4` (full-quality master, local only)
9:16 · 1080×1920 · 30 fps · 37 s · Hinglish captions · no music (none supplied). v1 is kept as `exports/bulandshahr-ai-website_v1_web.mp4`.

## v2 changes (after feedback: repeated lines + faded picture)

- **Repeats removed from captions AND audio/video** (dropped words are now cut from the audio too):
  "ChatGPT" said 3x in one sentence (kept 1st and last, cut the middle), the "jo bhi output ... vo amazing / dekhne layak hoga" line said twice
  (kept the IMG_6119 version), the "follow" ask said twice (kept IMG_6072; IMG_6132 now only has the "like" ask), and
  "Bulandshahr ke andar" repeating the hook (cut). Length 45 s -> 37 s.
- **Faded picture fixed**: the iPhone footage is HDR (HLG). The v1 conversion to SDR was too washed out. v2 tone-maps in linear light
  before the gamut conversion with a 0.8 saturation grade (`scripts/make_proxies.sh`), giving natural skin and a blue wall.

## Footage inventory (all 16 originals are in `input/`, untouched; `input/` is git-ignored)

| Original | What it is | Used? |
|---|---|---|
| IMG_6058.MOV | Hook: "60 second ke andar ... website bana ke dikhaunga" | yes (clip 1) |
| IMG_6060.MOV | D' Closet intro, founder named | yes (clip 2) |
| IMG_6061.MOV | "Poora tutorial aage hai..." | yes (clip 3) |
| IMG_6067.MOV | Step 1: give business details to ChatGPT | yes (clip 4); stutter "with logo, with logo" cut |
| IMG_6119.MOV | Step 2: paste the ChatGPT prompt into Claude | yes (clip 5) |
| IMG_6134.MOV | "Here is our output, have a look." | yes (clip 6) |
| IMG_6132.MOV | Output reaction + like/follow ask | yes (clip 7) |
| IMG_6072.MOV | "AI se related aur bhi content... follow" | yes (clip 8, outro) |
| IMG_6105.MOV | Retake of IMG_6067, audio unintelligible to Whisper | no |
| IMG_6073.MOV | 2.2 s, speech unintelligible | no |
| IMG_6128.MOV | 7.8 s, no intelligible speech detected | no |
| Screen Recording ... 2.05.45 AM.mov | ChatGPT + Notes with business details | B-roll (STEP 1) |
| Screen Recording ... 3.38.07 AM.mov | Pasting the prompt into Claude | B-roll (STEP 2) |
| Screen Recording ... 3.41.36 AM.mov | Claude Design output (D' Closet site preview) | B-roll (OUTPUT) |
| Screen Recording ... 2.13.13 AM.mov | Opening Claude Design | not used |
| ScreenRecording_10-06-2026 15-17-17_1.mp4 | The live site on a phone (dcloset.checkstore.in) | B-roll (LIVE) |

## Names used (all from your footage; nothing invented)

- Store: **D' Closet** (on the website and in your Notes); site: **dcloset.checkstore.in** (visible in the phone recording)
- Tools: **ChatGPT** and **Claude Design** (claude.ai/design, visible on screen)
- **Priyanshi Di** (founder) is spelled as Whisper heard it. **Please confirm the spelling.**
- Speaker name/handle: not provided, so no lower third was added.

## Please check

1. `work/captions_review.md`: every caption line next to what Whisper heard, with low-confidence words listed.
2. IMG_6060: "aur usko host karti hain, uski founder hain Priyanshi Di" is the least certain line (the audio there is unclear).
3. Hindi words were converted to Roman Hinglish by hand from Whisper's output. Fix any word in `work/hinglish.json` and rebuild (below).

## Rebuild / change

```bash
python3 scripts/assemble_timeline.py projects/bulandshahr-ai-website     # after editing work/hinglish.json or timeline.json
# (if the master changed, redo the cut-out: npx hyperframes remove-background work/master.mp4 -o work/master.cutout.webm)
bash scripts/produce.sh projects/bulandshahr-ai-website --final          # build -> check -> render -> ffprobe validation
```

## Technical notes

- iPhone clips are HDR (HLG / Dolby Vision). Editing uses SDR BT.709 proxies made with `scripts/make_proxies.sh` (tone-mapped); the tone-mapped wall looks brighter than the iPhone's own SDR rendering.
- Speaker cut-out (for words behind him) is `work/master.cutout.webm` (u2net, CPU). It is git-ignored (large); regenerate it with the command above.
- Music: none was supplied. Put a file you have the rights to in `music/` and set `"music": {"file": "music/<file>"}` in `edit.json`.
