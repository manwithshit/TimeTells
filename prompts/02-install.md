# Prompt 2 — install generated faces

Paste this whole file to a coding agent that can see this repository. The 16 images should already exist.

---

Install a user-generated Time Tells face set.

## Inputs

Exactly these 16 files, already generated:

`age-000.webp`, `age-005.webp`, `age-010.webp`, `age-015.webp`, `age-020.webp`, `age-025.webp`, `age-030.webp`, `age-035.webp`, `age-040.webp`, `age-045.webp`, `age-050.webp`, `age-055.webp`, `age-060.webp`, `age-065.webp`, `age-070.webp`, `age-080.webp`

Put them in:

```
content/anchors/natural/
```

Overwrite the demo anchors. Do not rename. Do not add night / second-track folders.

## Process

Works on macOS, Windows, and Linux. Prefer Python 3.10 or 3.11.

```bash
python3 -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install -r pipeline/requirements.txt
python pipeline/process.py --check
python pipeline/process.py
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r pipeline/requirements.txt
python pipeline/process.py --check
python pipeline/process.py
```

`--check` must report all 16 anchors present before processing.

`pipeline/process.py` aligns eyes, hard-crops the head, evens skin, and writes ages 0–80 to `web/assets/frames/`. Do not replace those frames by copying raw generated images. The script exists so the slider stays locked.

## Preview

```bash
cd web
python3 -m http.server 4175 --bind 127.0.0.1
```

Open http://127.0.0.1:4175/ and hard-refresh. Drag from Baby to 80.

## Optional GitHub Pages

Commit the new anchors and frames, then push `main`. Pages is configured from the `web/` folder.

If MediaPipe cannot find a face, or a frame ghosts between ages, stop and report the failing filename. Do not invent missing ages by duplicating a neighbor.
