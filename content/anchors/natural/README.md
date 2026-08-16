# Natural-track anchors

The processor expects **exactly these 16 files**:

```
age-000.webp
age-005.webp
age-010.webp
age-015.webp
age-020.webp
age-025.webp
age-030.webp
age-035.webp
age-040.webp
age-045.webp
age-050.webp
age-055.webp
age-060.webp
age-065.webp
age-070.webp
age-080.webp
```

The demo repository ships the author's existing 10 source images. Ages 15, 25, 35, 45, 55 and 65 are not included on purpose. The live demo uses already-processed frames in `web/assets/frames/`.

To use your own face, generate all 16 with `prompts/01-generate.md`, put them here, then run `prompts/02-install.md`.
