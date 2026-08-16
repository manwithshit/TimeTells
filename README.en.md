<p align="right">
  <a href="./README.md">中文</a> · <strong>English</strong>
</p>

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Time Tells: drag one real face from baby to 80. The page only switches local frames.">
</p>

One front-facing photo becomes 16 age stills. A local script aligns and crops them into a Baby → 80 ruler. Dragging never calls an image model.

The public product is a single track: ordinary time passing.

## Desktop

<p align="center">
  <img src="./assets/readme/desktop-040.webp" width="100%" alt="Desktop at age 40: Time Tells wordmark, cropped portrait, and age ruler">
</p>

<p align="center">
  <img src="./assets/readme/desktop-pair.webp" width="100%" alt="Desktop side by side: Baby on the left, age 80 on the right">
</p>

<p align="center">
  <img src="./assets/readme/desktop-020.webp" width="49%" alt="Desktop at age 20">
  <img src="./assets/readme/desktop-060.webp" width="49%" alt="Desktop at age 60">
</p>

<p align="center">
  <img src="./assets/readme/age-strip.webp" width="100%" alt="The same face at ages 0, 10, 20, 40, 60, and 80">
</p>

## Phone

390×844 is a typical phone width. 375×667 is the product minimum.

<p align="center">
  <img src="./assets/readme/mobile-trio.webp" width="100%" alt="Three phones at ages 10, 50, and 70">
</p>

<p align="center">
  <img src="./assets/readme/mobile-five.webp" width="100%" alt="Five phones from Baby through 10, 40, 50, and 80">
</p>

## How it works

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="A photo becomes 16 age stills, process.py writes 81 frames, and the page only handles dragging">
</p>

1. Paste [`prompts/01-generate.md`](prompts/01-generate.md) into an image-capable agent. Give it a front-facing photo of you, alone, and generate these **16 ages one at a time**:

   `0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80`

2. Paste [`prompts/02-install.md`](prompts/02-install.md) into a coding agent, or run the script yourself. Put the files in `content/anchors/natural/`, then:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -r pipeline/requirements.txt
python pipeline/process.py --check
python pipeline/process.py
```

The script locks the eyes, hard-crops the head, fills in every year from 0–80, and writes `web/assets/frames/`. Do not drop raw ChatGPT images onto the website.

## Try the demo

This repository already includes a processed demo face. On your machine:

```bash
cd web
python3 -m http.server 4175 --bind 127.0.0.1
```

Open http://127.0.0.1:4175/

The processor runs on macOS, Windows, and Linux. Viewing the demo does not need anything beyond Python for the static server. Use Python 3.10 or 3.11. On Windows, install the [Visual C++ redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if OpenCV or MediaPipe fails to import.

The GitHub Pages workflow is in `.github/workflows/pages.yml`. A free private repo cannot enable Pages; after the repo is public, set Settings → Pages to GitHub Actions.

## What other people change

```
content/anchors/natural/   ← replace only these 16 stills
pipeline/process.py        ← align, crop, interpolate
web/                       ← one page + 81 frames
prompts/                   ← the two agent briefs
```

## License

- Code, page, and prompts: [MIT](LICENSE)
- The demo face in this repo may be shared, **not used for advertising**. See [NOTICE.md](NOTICE.md)

This is a visual experiment, not a medical or lifespan prediction.
