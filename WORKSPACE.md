# Workspace notes

The workspace is now `projects/<slug>/` (one persistent folder per video); see README.md.
Cloud sandbox: `cdn.jsdelivr.net` and `huggingface.co` are blocked. GSAP is vendored by `scripts/vendor_gsap.sh`
(run automatically by `new_project.py` and `produce.sh`). To fix an old composition by hand:
`bash scripts/vendor_gsap.sh projects/<slug>/hyperframes`.
