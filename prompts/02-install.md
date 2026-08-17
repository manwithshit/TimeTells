# Prompt 2 — install generated faces

Paste this whole file to a coding agent that can see this repository. The 16 images should already exist.

---

Install a user-generated Time Tells face set.

## Before anything else: find the repository

Every path below is relative to the Time Tells repository root — the one folder that contains **both** `pipeline/process.py` and `web/index.html`.

1. If you have not downloaded the repository yet, clone it and enter it:

   ```bash
   git clone https://github.com/manwithshit/TimeTells.git
   cd TimeTells
   ```

   If the user downloaded a ZIP from the web instead, the unpacked folder is named `TimeTells-main`. Enter that one.

2. If you already have it, change into that directory first.

3. Confirm you are in the right place before running anything else:

   ```bash
   ls pipeline/process.py web/index.html
   ```

   Both files must exist. **Do not create `content/`, `pipeline/`, or `web/` yourself.** If they are missing, you are in the wrong directory — stop and ask the user where the repository is. Never write a replacement `process.py`.

Stay in this directory for every command in this file.

## Inputs

Exactly these 16 files, already generated:

`age-000.webp`, `age-005.webp`, `age-010.webp`, `age-015.webp`, `age-020.webp`, `age-025.webp`, `age-030.webp`, `age-035.webp`, `age-040.webp`, `age-045.webp`, `age-050.webp`, `age-055.webp`, `age-060.webp`, `age-065.webp`, `age-070.webp`, `age-080.webp`

Put them in:

```
content/anchors/natural/
```

Overwrite the demo anchors. Do not rename. Do not add night / second-track folders.

The demo anchors and frames are tracked in git, so the user can always get them back with:

```bash
git checkout -- content/anchors/natural web/assets/frames
```

## Process

Works on macOS, Windows, and Linux. Requires Python 3.10–3.12; MediaPipe has no wheels for 3.13 yet.

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r pipeline/requirements.txt
.venv/bin/python pipeline/process.py --check
.venv/bin/python pipeline/process.py
```

Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r pipeline\requirements.txt
.venv\Scripts\python.exe pipeline\process.py --check
.venv\Scripts\python.exe pipeline\process.py
```

Call the interpreter inside `.venv` directly, as shown. Do not rely on `activate` — it silently stops applying if the working directory changes.

`--check` must report all 16 anchors present before processing.

If `--check` reports files as missing, look in `content/anchors/natural/` for files with the same names but a `.png` extension. Rename them to `.webp` and run `--check` again. The images themselves are fine; only the extension matters.

`pipeline/process.py` aligns eyes, hard-crops the head, evens skin, and writes ages 0–80 to `web/assets/frames/`. Do not replace those frames by copying raw generated images. The script exists so the slider stays locked.

## Preview

The page is plain static HTML with relative paths, so the simplest way is to just open `web/index.html` in a browser — no server, no Python.

If you prefer a local server, run it without leaving the repository root:

```bash
python3 -m http.server 4175 --bind 127.0.0.1 --directory web
```

Open http://127.0.0.1:4175/ and hard-refresh. Drag from Baby to 80.

## Optional GitHub Pages

Committing and pushing will publish these images. **The 16 anchors and 81 frames are photographs of the user's face — pushing them to a public repository puts that face on the open internet.** Confirm with the user before doing this. If they only want a local copy, stop here.

If they do want to publish, commit the new anchors and frames and push `main`. Deployment runs through the Actions workflow in `.github/workflows/pages.yml`; in the repository settings, Pages → Source must be set to **GitHub Actions**. There is no "deploy from `/web` folder" option — do not look for one.

If MediaPipe cannot find a face, or a frame ghosts between ages, stop and report the failing filename. Do not invent missing ages by duplicating a neighbor.
