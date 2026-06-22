# Content Engine

Turn a script and a voiceover into a finished, edited video. Give it a text
script and an audio file and it plans the scenes, sources the visuals, runs a
quality check, and renders an MP4 with transitions, title cards, lower thirds,
motion graphics, sound effects, and music.

It runs from the command line and ships with a desktop app.

## What it does

```
script.txt + voiceover.wav  ->  scene plan  ->  sourced assets  ->  quality check  ->  rendered .mp4
```

- **Scene planner** breaks the script into beats, times them to the voiceover,
  and decides per beat whether to show a clip or a still, what to search for,
  which transition to use, what the title card and lower thirds say, and what
  motion graphics to add.
- **Asset sourcing** pulls images and clips from stock providers (Pexels or
  Pixabay) and music and sound effects from a local library. With no keys it
  synthesizes placeholders so a render always completes.
- **Quality check** scores every visual against a guidelines document, accepts
  or rejects it, and flags weak but important images for upscaling.
- **Render** stitches everything with Remotion and writes the final MP4, length
  matched to the voiceover.

## Requirements

- Python 3.10+ and `ffmpeg` on the path
- Node.js 18+ (for the renderer)

## Setup

```bash
# python side
pip install -r requirements.txt

# renderer
cd remotion && npm install && cd ..

# configuration and keys
cp config.example.json config.json
chmod 600 config.json
# edit config.json to add API keys (optional; the pipeline runs without them)
```

Keys live in `config.json` only. Leave them blank to run fully offline with
placeholder visuals and the built in planner.

## Usage

Render a video in one command:

```bash
python -m content_engine run \
  --script examples/sample_script.txt \
  --voiceover examples/sample_vo.wav \
  --out out/video.mp4
```

Useful flags:

- `--test` renders at small dimensions for a quick preview
- `--offline` skips the network and uses placeholder visuals
- `--no-llm` forces the built in heuristic planner and quality check
- `--concurrency N` sets renderer parallelism

Run a single stage against a shared work directory:

```bash
python -m content_engine plan   --script s.txt --voiceover vo.wav --work-dir work/job1
python -m content_engine source --work-dir work/job1
python -m content_engine qc     --work-dir work/job1
python -m content_engine render --work-dir work/job1 --voiceover vo.wav --out out.mp4
```

Each stage writes a JSON artifact (`scene_plan.json`, `sourced_plan.json`,
`qc_plan.json`, `render_props.json`) you can open and inspect.

## Desktop app

The `electron/` folder holds a desktop shell. Drop in a script and a voiceover,
press go, and watch the stages run.

```bash
cd electron && npm install && npm start
```

## Configuration

`config.json` controls three things:

1. **LLM providers and roles.** The planner and quality check call a model
   through one interface. Each role names a primary and a fallback provider.
   A role with no usable key falls back to the built in logic, so nothing
   breaks when a key is missing.
2. **Sourcing.** Which image and video provider to use, and their keys.
3. **Render.** Output and test dimensions and frame rate.

## Tests

```bash
python -m pytest
```

The suite runs offline with no keys. The heavy end to end render is opt in:

```bash
CE_RENDER_TEST=1 python -m pytest tests/test_render_e2e.py
```

## Layout

```
content_engine/   pipeline core: config, llm, planner, sourcing, qc, render, cli
remotion/         the renderer (composition and components)
electron/         desktop shell
assets/           local library: music, sfx, transitions, backgrounds
examples/         sample script and voiceover
tests/            pytest suite
```

See `ARCHITECTURE.md` for the full design.
