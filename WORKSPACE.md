# vibe-edit workspace

| Folder     | Purpose                                                         |
|------------|-----------------------------------------------------------------|
| `input/`   | Original takes. Read-only: never edit, rename or overwrite.     |
| `assets/`  | Logos, images, music, sound effects                             |
| `refs/`    | Style references (screenshots, GIFs, short clips)               |
| `project/` | HyperFrames compositions, transcripts, beat sheets, cut lists   |
| `previews/`| Low-res draft renders                                           |
| `exports/` | Final MP4s                                                      |

Sandbox note: `cdn.jsdelivr.net` and `huggingface.co` are blocked in cloud sessions.
Vendor GSAP locally (`npm pack gsap@3.14.2`, copy `dist/gsap.min.js` into the composition)
instead of loading it from the CDN.
