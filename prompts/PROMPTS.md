# Prompt library

Copy, swap the `[brackets]` for your own words, send **one at a time**.
Paths are relative to your project folder (`projects/<slug>/`). Claude Code reads that folder's `CLAUDE.md` and the repo's `scripts/`, so it uses them automatically.
Start a project with `python3 scripts/new_project.py <name> --format 9:16`, then open Claude Code in the repo root.

---

## 0 · Setup (once)

```text
I want you to edit my videos with HyperFrames. Run python scripts/check_setup.py and install anything that is missing (Node.js 22+, FFmpeg, Python 3, Whisper — faster-whisper on Windows, whisper-cpp on Mac). Ask me before each install. Then run claude plugin marketplace add heygen-com/hyperframes and claude plugin install hyperframes@hyperframes, and run npx hyperframes doctor. Fix whatever it flags and finish with a list of what is installed, with versions.
```

## 1 · Test your shot

Film 5 seconds, save it as `input/test.mp4`.

```text
Here is a 5-second test clip, input/test.mp4. Pull a few frames and check the shot before I record the real take: is my face well lit, is the background far enough to cut me out cleanly, and is anything important too close to the edges? Tell me exactly what to fix.
```

## 2 · Eyes and ears (your first prompt on every video)

```text
My video is input/take.mp4. Transcribe it with Whisper, with a timestamp for every word, and save it to work/take.words.json. Then pull one frame per second and look at the frames. Tell me what I say, when I say it and what is in the shot at each moment. These names must be spelled right: [your name, brand, product].
```

## 3 · Plan first

```text
Before you build anything, write a beat sheet for this edit as a table: start and end time, my exact words, what appears on screen, where the text sits, and the sound. Format: vertical 9:16 for Reels. Keep all text out of the bottom 20% of the screen and away from the right edge, where the app buttons are. Wait for my OK before you build.
```

## 4 · Notes that work

One change per line, always with the time.

```text
At 0:07 the logo covers my face. Move it next to my hand and make it 20% smaller.
From 0:12 to 0:14 the captions go too fast. Show two words at a time.
The zoom at 0:21 lands late. Start it on the word "now".
```

---

## Everyday edits

**Captions** — start here.
```text
Add captions word by word, synced to the transcript. Two or three words on screen at a time, bold and white, with the key word of each sentence in [color]. Place them at about 65% of the screen height.
```

**Cut the dead air**
```text
Cut every pause longer than 0.3 seconds and every breath, using the word timings. Never cut inside a word, and keep a short beat before each punchline. Tell me the new length.
```

**Punch-in zooms** — keep them rare.
```text
Punch in 1.2x on the key word of each sentence, hold for two seconds, then ease back out. No more than one zoom every five seconds.
```

**Title card + name tag**
```text
Open with a title card in big bold type: "[your hook]". Hold it for two seconds, then cut to me. Add a lower third with my name and [@handle] the first time I speak.
```

**Pop-ups** — image in `assets/`.
```text
When I say "[word]", pop up assets/[image.png] next to me for two seconds with a small bounce. It must never cover my face.
```

**Music + sound effects**
```text
Add music/[music.mp3] under my voice at a low volume, and lower it further while I talk. Put a whoosh on every zoom and a pop on every pop-up, using the files in the sfx folder. Never the same sound twice in a row.
```

**Reframe for Reels**
```text
Reframe this 16:9 video to 9:16 for Reels and keep my face centered the whole time.
```

---

## Show-off edits

Say the quoted lines **on camera**; Claude finds them in the transcript.

| Effect | Say on camera | You need |
|---|---|---|
| Logo on your hand, thrown at the lens | "Zoom in on my hand and put the [brand] logo right here, in 3D." → "Now throw it straight at the camera!" | Logo in `assets/`. Hold your open hand still 1s. |
| Split the scene into layers | "Now split the scene into layers: the wall, me, and the text." → "Now hide my layer." → "Okay, bring me back." | 2s clean plate of the empty room. Distance from the wall. |
| Split-screen explainer | "Put me in a frame on the right, and on the left, show how [topic]." | 2–3 short points said right after. |
| Reels floating in 3D | "Back to full screen. Now float my best reels behind me, in 3D." | Videos in `reels/`. |
| Object comes to life | "Grab the [object] from my shelf and open it up." → "Now put it back… and take my picture!" | A second clean plate without the object, and a pose. |

Then tell Claude:
```text
I asked for effects on camera in this take. Find every request in the transcript, list them with their times, and propose how you'll build each one, with a twist. Wait for my OK.
```

---

## Any style you want

**From your references** (`refs/` folder):
```text
In the refs folder there are screenshots and a short clip of a motion graphics style I like. Pull frames from the clip and study the layout, the fonts, the colors, how things move and the pacing. Describe the style back to me in five bullet points and wait for my OK. Then build something similar for my video, based on what I say and in my brand colors. Similar, not a copy.
```

**Just name it:**
```text
Edit this video like a cinematic movie trailer.
Turn this video into a Vox-style documentary explainer.
Make it an Apple-style product reveal.
Make it look like a breaking news broadcast.
Give it a retro 80s VHS tape look.
```

Mix both: *"movie trailer style, with titles like the ones in refs/titles.png".*

---

## Batch

```text
Make three versions of this edit with the same timing and style: captions in English, in Spanish and in Portuguese. Translate the captions only, keep my voice, and render all three.
```

---

## Fix it fast

| Problem | Say |
|---|---|
| Names spelled wrong | Add them to `names.txt`, then "re-transcribe and fix the captions". |
| Text hidden by app buttons | "Nothing in the bottom 20% of the screen or near the right edge." |
| Effect lands late | "Start the [effect] on the word '[word]'." |
| Claude says done, looks wrong | "Snapshot the frame at 0:07 and check it yourself." |
| Preview or render fails | Run `npx hyperframes doctor`, paste the error. |
| A change broke something | "Save a version before each round" → `python scripts/version.py restore v2`. |
| An effect works great | "Save this effect as a template." |

---

## Whole-system prompts

**New video from a raw take** (the usual start):
```text
New project "[name]", format [9:16]. My raw video is projects/[slug]/input/take.mp4 and my brief is in projects/[slug]/instructions.md. Follow projects/[slug]/CLAUDE.md: transcribe, look at the frames, analyze the video, write the beat sheet and wait for my OK.
```

**Build it** (after you approve the beat sheet):
```text
Fill in edit.json from my brief, run scripts/produce.sh for a draft, look at the snapshot frames yourself, fix anything that looks wrong, and show me the preview path. Do not say it is done until validate_video.py passes.
```

**Final + save:**
```text
Render the final with produce.sh --final, validate it with ffprobe, then run scripts/commit_project.sh [slug] "[message]" --push.
```

**Markdown guide to explainer video:**
```text
Turn [file].md into an explainer video: scripts/build_video.sh [file].md [slug] --format 16:9
```
