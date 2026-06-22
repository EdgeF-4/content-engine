# Content Engine desktop

A thin desktop shell over the pipeline. Pick a script and a voiceover, choose a
couple of options, and press make. Progress streams live and the finished video
plays in the window.

The shell adds no logic of its own. It runs `python -m content_engine run` in
the repository root and shows the output.

## Run

```bash
cd electron
npm install
npm start
```

The shell expects the Python side to be set up (`pip install -r ../requirements.txt`)
and `ffmpeg` on the path. The renderer's Node dependencies must be installed too
(`cd ../remotion && npm install`).

## Options

- **Quick preview** renders at small dimensions for a fast result.
- **Offline** uses placeholder visuals and skips the network.
- **Built in planner only** forces the heuristic planner and quality check.

## Build a Windows installer

```bash
npm run dist:win
```

This produces an NSIS installer under `dist/`. Building the Windows target is
usually done on Windows or in a Windows CI runner.

## Headless check

```bash
npm run smoke
```

Boots the app, confirms the window and renderer load, then exits. Useful in CI
where there is no display (run it under `xvfb-run` on Linux).
