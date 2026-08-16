# Prompt 1 — generate 16 faces

Paste this whole file to an image-capable agent (ChatGPT, Codex, or similar). Do not skip ages. Do not invent extra tracks.

---

You are generating a **Time Tells** age set for one real person.

Ask the user for one clear, front-facing photo of themselves, alone, even light, no sunglasses, no other people. Use that photo as the identity reference for every image.

Generate **exactly 16** still photographs. One age per image. One image at a time. After each image is approved or saved, do the next age. Do not batch all 16 in one shot.

## Output files

Save as square 1024×1024 WebP (PNG is acceptable if WebP is unavailable):

| File | Age |
|---|---|
| `age-000.webp` | about 1 year, baby |
| `age-005.webp` | about 5 |
| `age-010.webp` | about 10 |
| `age-015.webp` | about 15 |
| `age-020.webp` | about 20 |
| `age-025.webp` | about 25 |
| `age-030.webp` | about 30 |
| `age-035.webp` | about 35 |
| `age-040.webp` | about 40 |
| `age-045.webp` | about 45 |
| `age-050.webp` | about 50 |
| `age-055.webp` | about 55 |
| `age-060.webp` | about 60 |
| `age-065.webp` | about 65 |
| `age-070.webp` | about 70 |
| `age-080.webp` | about 80 |

## Look

This is the **顺其自然** track: ordinary time passing, gentle and even. Not exhausted, not athletic-ideal, not stylized.

Treat every frame as the same ID-photo session continued over a lifetime.

- Photoreal. No illustration, no beauty filter, no anime.
- Same person. Same slight smile. Same head size and camera height as much as possible.
- Head-on. Full hair, both ears, full face, rounded chin and jaw.
- No shoulders, clothes, text, watermark, or long neck.
- Pure white background.
- Complete teeth. No missing midline, no yellow blotch on the front incisors. One pair of ears, not doubled.

If an image breaks identity, pose, crop, or teeth, regenerate that age only.

When all 16 files exist, tell the user to paste `prompts/02-install.md` into an agent to install them.
