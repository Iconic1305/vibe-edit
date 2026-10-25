# Vibe Editing System

By Ideabro Studio

## Let Claude Edit Your Videos

Claude Code + HyperFrames · Whisper · FFmpeg · No editing app

Film yourself talking, drop the file in a folder and tell Claude what you want on screen. It listens to every word, looks at your frames and builds the edit for you. This guide covers the setup, the method and the prompts to copy.

## 00 · Start Here

### No timeline. You just ask.

Claude does not open Premiere or CapCut. It writes your edit as code with HyperFrames, a free tool that turns a web page into a video, and renders it as an MP4. You never have to read that code. You talk, Claude builds, you watch and give notes.

Out of the box, Claude can't hear or watch a video. Whisper gives it ears and FFmpeg gives it eyes. Once they are installed, every edit follows the same five steps.

### 01 · You film

One take on your phone or camera. Ask for effects out loud while you film, or type them in the chat later.

### 02 · Claude listens

Whisper writes down every word you say, with its exact start and end time.

### 03 · Claude looks

FFmpeg pulls still frames, so Claude sees where you are, where your hands are and what is behind you.

### 04 · Claude builds

It plans the edit, cuts the pauses and adds captions, zooms and effects, each one synced to a word.

### 05 · You review, Claude renders

You watch the preview in your browser, give notes, and get the final MP4.

### What's inside

- 01 · What Claude needs
- 02 · Install it once
- 03 · Eyes and ears
- 04 · Film it right
- 05 · The edit loop
- 06 · Everyday edits
- 07 · Show-off edits
- 08 · Any style you want
- 09 · Best use cases
- 10 · Fix it fast

The toolkit: Claude Code · HyperFrames · Whisper · FFmpeg · Python · Node.js.

## 01 · What Claude Needs

### Six tools. Five are free.

This is the whole kit, and you install it once. Claude Code is the only part you pay for. The other five are free and open source.

### The editor · Claude Code

Claude working on your computer: it reads your files, runs commands and writes the edit. Needs Claude Pro ($20 a month, or $17 a month billed yearly) or higher. The free plan does not include it.

https://claude.com/product/claude-code

### The engine · HyperFrames

A free, open-source video framework by HeyGen, made for AI agents. Claude writes the edit as a web page, HyperFrames plays it in your browser and renders the MP4.

https://github.com/heygen-com/hyperframes

### The ears · Whisper

OpenAI's free speech-to-text model. It turns your voice into text, with a time for every word. faster-whisper runs the same model up to 4x faster.

https://github.com/openai/whisper

https://github.com/SYSTRAN/faster-whisper

### The eyes and the scissors · FFmpeg

The tool behind almost every video app. Claude uses it to pull frames, cut clips, clean up audio and convert files. HyperFrames needs it too.

https://github.com/FFmpeg/FFmpeg

### The helper · Python 3

Runs Whisper and the small scripts Claude writes along the way. Version 3.13 is a safe pick.

https://python.org/downloads

### The motor · Node.js 22+

Runs HyperFrames. Install the LTS version from the site and forget about it.

https://nodejs.org

**Already included:** HyperFrames downloads its own Chrome to render your video. On Windows, Git for Windows (https://git-scm.com) is optional.

**You bring:** your video, your logo, and any music or sound effects you have the rights to use.

## 02 · Install It Once

### Fifteen minutes, one time.

Install Claude Code first. Then paste the prompt below and let Claude install the rest (it asks before each step), or run the commands yourself.

### 01 · Install Claude Code

Easiest: the Claude desktop app (https://claude.com/download), in the Code tab. Or in a terminal, then log in with your Claude account.

Windows:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Mac:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

### 02 · Install Node.js, FFmpeg and Python

Windows:

```powershell
winget install OpenJS.NodeJS.LTS
winget install Gyan.FFmpeg
winget install Python.Python.3.13
```

Mac, with Homebrew (https://brew.sh):

```bash
brew install node ffmpeg python
```

### 03 · Install Whisper

Windows:

```bash
python -m pip install faster-whisper
```

Mac: HyperFrames transcribes on its own after this installation. The model downloads the first time you use it.

```bash
brew install whisper-cpp
```

### 04 · Add HyperFrames to Claude

The plugin teaches Claude how to build and render videos.

```bash
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```

### 05 · Check everything

This checks Node.js, FFmpeg and Chrome and tells you what is missing.

```bash
npx hyperframes doctor
```

### Prompt · Let Claude install the rest

Paste it in a new session, in any folder.

```text
I want you to edit my videos with HyperFrames. Check if this computer has Node.js 22 or newer, FFmpeg, Python 3 and Whisper (faster-whisper on Windows, whisper-cpp on Mac). Install anything that is missing, and ask me before each install. Then run claude plugin marketplace add heygen-com/hyperframes and claude plugin install hyperframes@hyperframes, and run npx hyperframes doctor. Fix whatever it flags and finish with a list of what is installed, with versions.
```

**Note:** open a new terminal, or start a new Claude session, after installing, so your computer finds the new tools. If a command fails, paste the error to Claude and ask it to fix it.

## 03 · Eyes and Ears

### Give Claude eyes and ears.

Claude reads text and looks at images, but it cannot play a video file. So you give it two things: a transcript with the time of every word, and still frames from the video. Now it knows what you say, when you say it and what the shot looks like at that moment.

### Ears · Whisper

Whisper turns your audio into text and marks when each word starts and ends, like `zoom 5.32s to 5.74s`.

That is how a zoom lands on the exact word, and how captions stay in sync. It is also how Claude finds the pauses and breaths to cut.

### Eyes · FFmpeg

FFmpeg pulls still images from your video, for example one per second. Claude looks at them to find your face, your hands and the empty spots, so effects land in the right place.

While it edits, it snapshots its own work (`npx hyperframes snapshot`) and checks the frames before you see them.

### Word timings from a real take

```text
4.68s -> 5.12s  First,
5.32s -> 5.74s  zoom
5.74s -> 5.92s  in
5.92s -> 6.00s  on
6.00s -> 6.10s  my
6.10s -> 6.40s  hand
```

### Prompt · Your first prompt

`take.mp4` = your video, in the folder.

```text
My video is take.mp4 in this folder. Transcribe it with Whisper, with a timestamp for every word, and save the words and times to take.words.json. Then use FFmpeg to pull one frame per second and look at the frames. Tell me what I say, when I say it and what is in the shot at each moment. These names must be spelled right: [your name, brand, product].
```

**Names:** Whisper spells names the way they sound. In a test in the source guide, it wrote "Claude" as "Klav". Give Claude the names and it fixes the transcript and the captions.

**Why it matters:** this one step is what makes the edit feel hand-made. Every effect after it is timed to a word, not guessed.

## 04 · Film It Right

### Record a take Claude can edit.

Claude can only edit what the camera caught. Five minutes of prep here decides how clean your cutouts, captions and effects look. A phone is enough.

### Camera and light · Set up the shot

- Phone or camera on a tripod. The shot never moves, so effects stay locked to you.
- Horizontal (16:9) gives Claude room to reframe. Shoot vertical (9:16) if it only goes to Reels.
- Light on your face, and some distance from the wall. A clean edge gives a clean cutout.
- A quiet room and the mic close to you. Whisper hears better, and so do people.
- Before you stop, step out and film 2 seconds of the empty room. This clean plate lets Claude hide you later.
- If an object will come to life, film 2 more seconds without it.

### While you talk · Talk to your editor

- One request per sentence: "Zoom in on my hand." Claude finds it in the transcript.
- A short pause after each request gives the effect room. Claude trims it later.
- Hold still for a second where an effect lands, like an open hand for a logo.
- Look where the effect will appear, and react to it. That is what sells it.
- Say your call to action slowly and clearly. It is the line that matters most.

### Prompt · Test your shot first

Film 5 seconds, drop it in the folder.

```text
Here is a 5-second test clip, test.mp4. Pull a few frames and check the shot before I record the real take: is my face well lit, is the background far enough to cut me out cleanly, and is anything important too close to the edges? Tell me exactly what to fix.
```

**Two ways to ask:** say your requests on camera while you film, so viewers hear you ask and see it happen, or talk normally and type the requests in the chat afterwards. Both work, because Claude has the transcript.

## 05 · The Edit Loop

### Plan, build, watch, repeat.

Every edit runs through the same loop. Two habits make it fast: plan before Claude builds anything, and give notes like a director. Say what, where and when, never how.

### 01 · Plan it first

Ask for a beat sheet: one row per moment, with the time, your words, what appears and the sound. Changes on paper are free.

### 02 · Cut the dead air

Claude trims pauses and breaths with the word timings, without cutting into a word. Rough cut first, effects after.

### 03 · Build

Claude writes the edit in HyperFrames and syncs every effect to its word.

### 04 · Preview and give notes

Run `npx hyperframes preview` to watch it in your browser. Send one note per line, with the time. Claude fixes it and checks its own frames.

### 05 · Render

Say "render it", or run `npx hyperframes render -o final.mp4`.

### Prompt · Plan first

After your first prompt in section 03.

```text
Before you build anything, write a beat sheet for this edit as a table: start and end time, my exact words, what appears on screen, where the text sits, and the sound. Format: vertical 9:16 for Reels. Keep all text out of the bottom 20% of the screen and away from the right edge, where the app buttons are. Wait for my OK before you build.
```

### Prompt · Notes that work

One change per line, always with the time.

```text
At 0:07 the logo covers my face. Move it next to my hand and make it 20% smaller.
From 0:12 to 0:14 the captions go too fast. Show two words at a time.
The zoom at 0:21 lands late. Start it on the word "now".
```

## 06 · Everyday Edits

### The basics, ready to paste.

Start here. These are the edits every talking video needs, and they tend to work on the first try. Swap the words in [brackets] for yours and send one at a time.

### Prompt · Captions

The one to start with.

```text
Add captions word by word, synced to the transcript. Two or three words on screen at a time, bold and white, with the key word of each sentence in [color]. Place them at about 65% of the screen height.
```

### Prompt · Cut the dead air

After the transcript.

```text
Cut every pause longer than 0.3 seconds and every breath, using the word timings. Never cut inside a word, and keep a short beat before each punchline. Tell me the new length.
```

### Prompt · Punch-in zooms

Keep them rare.

```text
Punch in 1.2x on the key word of each sentence, hold for two seconds, then ease back out. No more than one zoom every five seconds.
```

### Prompt · Title card + name tag

Your hook and your handle.

```text
Open with a title card in big bold type: "[your hook]". Hold it for two seconds, then cut to me. Add a lower third with my name and [@handle] the first time I speak.
```

### Prompt · Pop-ups

Your image in the folder.

```text
When I say "[word]", pop up [image.png] next to me for two seconds with a small bounce. It must never cover my face.
```

### Prompt · Music + sound effects

Your files in the folder.

```text
Add [music.mp3] under my voice at a low volume, and lower it further while I talk. Put a whoosh on every zoom and a pop on every pop-up, using the files in the sfx folder. Never the same sound twice in a row.
```

### Prompt · Reframe for Reels

For horizontal takes.

```text
Reframe this 16:9 video to 9:16 for Reels and keep my face centered the whole time.
```

## 07 · Show-Off Edits

### Edits that make people rewatch.

These take more prep, and they are the ones people share. Each line in quotes is something you can say on camera, word for word. Claude finds it in the transcript and builds it on that exact word.

### Logo on your hand, then at the camera

"Zoom in on my hand and put the Claude logo right here, in 3D." Then: "Now throw it straight at the camera!"

**Claude builds:** a punch-in on your hand, the logo as a real 3D object resting on your palm, then flying at the lens with a glass crack.

**You need:** the logo file (SVG or PNG) in the folder. Hold your open hand still for one second.

### Split the scene into layers

"Now split the scene into layers: the wall, me, and the text." Then: "Now hide my layer." Then: "Okay, bring me back."

**Claude builds:** a cutout of you (`npx hyperframes remove-background`) pulled away from the empty room, with the text in between. Hide your layer and the empty room keeps talking in your voice.

**You need:** the 2-second clean plate of the empty room, and some distance between you and the wall.

### A split-screen explainer

"Put me in a frame on the right, and on the left, show how a reel goes viral."

**Claude builds:** you shrink into a frame while an animated explainer builds on the left: titles, icons and a chart, timed to what you say next.

**You need:** a clear topic, plus 2 or 3 short points you say right after.

### Your reels floating in 3D

"Back to full screen. Now float my best reels behind me, in 3D."

**Claude builds:** your cutout in front, your videos playing on 3D screens floating behind you.

**You need:** the videos in a folder. Claude picks the most visual 3 or 4 seconds of each.

### An object comes to life

"Last one: grab the camera from my shelf and open it up." Then: "Now put it back... and take my picture!"

**Claude builds:** the real object cut out of the shot, flying off the shelf, rebuilt in 3D and opened into its parts. Then a flash, and a photo made from a real frame of you.

**You need:** a second clean plate without the object, and a pose on "picture".

**Why they work:** each effect lands on the exact word, and each one has a twist: the logo gets thrown, you vanish, the camera takes your picture. Ask Claude for a twist on every effect you add.

## 08 · Any Style You Want

### Show it, or just name it.

Want a specific motion graphic or editing style? Show Claude an example and ask for something similar, built around what you say. Famous styles don't even need an example: Claude already knows what a movie trailer or a Vox-style explainer looks like.

### Your own references · Show it an example

- Save screenshots, a GIF or a short clip of the style you like in a folder called `refs`.
- Claude can't play the clip, so it pulls frames and studies them: layout, fonts, colors, motion and pacing.
- Ask it to describe the style back to you first. If the description is right, the edit will be too.
- Ask for similar, not a copy: your words, your colors, your brand.

### Famous styles · Just name it

No references needed. Claude knows these and fills in the details: the fonts, the transitions, the pacing.

- Cinematic movie trailer
- Vox-style documentary explainer
- Apple-style product reveal
- Breaking news broadcast
- Retro 80s VHS tape

### Prompt · Show it an example

Your references in the `refs` folder.

```text
In the refs folder there are screenshots and a short clip of a motion graphics style I like. Pull frames from the clip and study the layout, the fonts, the colors, how things move and the pacing. Describe the style back to me in five bullet points and wait for my OK. Then build something similar for my video, based on what I say and in my brand colors. Similar, not a copy.
```

### Prompt · Just name it

One line is enough.

```text
Edit this video like a cinematic movie trailer.
Turn this video into a Vox-style documentary explainer.
```

**Tip:** mix both. Name the style, then point to one reference for the detail you care about most, like "movie trailer style, with titles like the ones in refs/titles.png".

## 09 · Best Use Cases

### Where Claude really shines.

Claude edits best when the video is built on words: someone talking, a list, a process, numbers. Here is where it pays off most, and where another tool does the job better.

### Use it for · Where it shines

- Talking-head reels: captions, zooms, pop-ups and motion graphics on every beat.
- Explainers: diagrams, lists and steps that build as you talk.
- Tutorials and screen recordings: zoom on the click, arrows and callouts.
- Product demos and launches: product shots, 3D, titles and prices.
- Podcast and interview clips: 16:9 to 9:16, captions and speaker names.
- Data videos: numbers and charts that animate straight from your spreadsheet.
- Intros, outros and templates: build it once, reuse it on every video.
- Batches: the same edit on ten videos, or in three languages.

### Skip it for · Where it struggles

- New footage. Claude edits what you give it. For new scenes or new people, use an AI video generator.
- Fast, messy motion. Cutouts of quick hands or loose hair get soft edges.
- An hour-long video in one go. Work section by section instead.
- Fine color grading. It can apply a look, but a colorist's eye is still yours.
- Taste. Claude follows direction very well. You are still the director.

### Prompt · Try a batch

One edit, three languages.

```text
Make three versions of this edit with the same timing and style: captions in English, in Spanish and in Portuguese. Translate the captions only, keep my voice, and render all three.
```

**Rule of thumb:** if you can describe it in one sentence and point to the word where it happens, Claude can build it.

## 10 · Fix It Fast

### When something looks off.

Most problems have a one-line fix. Describe what you see and when, or paste the error, and let Claude work. These are the ones you will run into first.

### 01 · Names spelled wrong

Give Claude your names and brands in the first prompt. It fixes the transcript and the captions.

### 02 · Text hidden by the app buttons

Tell Claude the safe zone: nothing in the bottom 20% of the screen or near the right edge.

### 03 · The effect lands late

Name the word it should start on. Claude has the exact time of every word.

### 04 · Claude says it's done, but it looks wrong

Ask: "snapshot the frame at 0:07 and check it yourself". Then it sees what you see.

### 05 · The preview or the render fails

Run `npx hyperframes doctor`, then paste the error to Claude.

### 06 · A change broke something

Ask Claude to save a version before each round (v1, v2...), so you can always go back.

### Habits · Work like a director

- One change per message.
- Always give the time: "at 0:07".
- Say what you want to see, not how to code it.
- Approve the plan before the build.

### Shortcuts · Save time on every video

- Rough cut first, effects after.
- Preview short sections before a full render.
- Keep your style rules (fonts, colors, safe zone) in a `CLAUDE.md` file in the folder. Claude reads it every time.
- When an effect works, ask Claude to save it as a template.

## 11 · The Takeaway

### You talk. Claude edits.

Install once, film one take and start with captions and cut pauses. When that feels easy, ask for your first 3D effect on camera and watch Claude build it on the exact word.

Vibe Editing System · By Ideabro Studio

### Source credit

Adapted and redesigned by Ideabro Studio from "Let Claude Edit Your Videos" by @pauloshimas, The Creator Stack (2026). The supplied guide states: "Feel free to adapt, remix and make this workflow yours."
