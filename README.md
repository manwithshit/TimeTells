# Time Tells

A single-screen age slider. Drag from Baby to 80. The page only switches local frames. It never calls an image model.

This public product is one life track: ordinary time passing. There is no second path in the UI.

## Try the demo

After GitHub Pages is enabled:

`https://<you>.github.io/TimeTells/`

On your machine:

```bash
cd web
python3 -m http.server 4175 --bind 127.0.0.1
```

Open http://127.0.0.1:4175/

## Use your own face

You need 16 generated portraits and one local Python run. macOS, Windows, and Linux all work. Viewing the demo does not need Python.

1. Paste [`prompts/01-generate.md`](prompts/01-generate.md) into an image-capable agent. Give it a front-facing photo of you, alone. It will ask for nothing except that photo, then make these 16 files:

   `0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80`

2. Paste [`prompts/02-install.md`](prompts/02-install.md) into a coding agent, or run it yourself. Put the 16 files in `content/anchors/natural/` and run `pipeline/process.py`. That script aligns the face, crops the head, and writes ages 0–80 into `web/assets/frames/`.

Do not drop raw ChatGPT images straight onto the website. Alignment is the difference between a locked portrait and a drifting head.

Python 3.10 or 3.11 is the safe choice. On Windows, install the [Visual C++ redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if OpenCV or MediaPipe fails to import.

## License

- Code, prompts, and page: [MIT](LICENSE)
- The default face in this repo: shareable, **not for commercial use**. See [NOTICE.md](NOTICE.md)

This is a visual experiment, not a medical prediction.
