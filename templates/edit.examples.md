# edit.json recipes

Times are seconds in the *video* (the title card offset is added automatically). `when` is a spoken
word or phrase found in the transcript; `nth` picks the 2nd, 3rd… occurrence; `offset` shifts it.

```jsonc
// Punch in on the word "hand" for 2 seconds
"zooms": { "manual": [ { "when": "hand", "scale": 1.3, "hold": 2, "origin": "50% 60%" } ] }

// A zoom on the key word of every sentence, at most one per 5 s
"zooms": { "auto": { "enabled": true, "scale": 1.2, "hold": 2, "min_gap": 5 } }

// Pop-up image when you say "logo", text pop-up at 12.5 s
"popups": [
  { "when": "logo", "image": "assets/logo.png", "duration": 2, "position": "right", "size": 0.28 },
  { "at": 12.5, "text": "Free!", "position": "top", "duration": 1.5 }
]

// 3D logo (CSS 3D) that spins, then is thrown at the camera on the word "camera"
"logo3d": { "when": "logo", "throw_when": "camera", "image": "assets/logo.png", "size": 0.34, "position": "center" }

// Title card + lower third
"title_card": { "text": "Let Claude edit your videos", "subtitle": "@yourhandle", "duration": 2 },
"lower_third": { "name": "Your Name", "handle": "@yourhandle", "when": "hi", "duration": 4 }

// Alternating punch at every jump cut + white flash on each cut (needs source.cuts)
"source": { "video": "work/take.cut.mp4", "words": "work/take.cut.words.json", "cuts": "work/take.cuts.json" },
"jump_cut_punch": { "enabled": true, "scale": 1.08 },
"transitions": { "flash_on_cuts": true }

// Caption styles: "pop" (outlined, accent active word), "box" (dark pill), "minimal" (soft shadow)
"captions": { "style": "box", "words_per_group": 2, "uppercase": true, "y": 0.62 }

// Other formats: "9:16" (Reels/Shorts/TikTok), "16:9" (YouTube), "1:1" (feed). Wide source -> vertical:
// object-fit cover; point it at the speaker with source.focus_x (0 = left edge, 1 = right edge)
```
