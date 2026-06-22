# Content Engine: Architecture

A pipeline that turns a script plus a voiceover file into a fully edited, rendered video. It plans scenes, sources visuals, runs a quality check, and renders an MP4. It runs from the command line and ships with a desktop shell.

## Goals

1. Input is a plain text script and an audio voiceover. Output is a finished MP4 with visuals, transitions, title cards, lower thirds, motion graphics, sound effects, and music.
2. Every stage runs from the CLI and is independently testable.
3. The whole thing reproduces offline with placeholder assets, so a contributor can render a video without any API keys.
4. The LLM layer is provider agnostic and config driven. Keys live in `config.json` (chmod 600), never in source or environment.

## Pipeline

```
script.txt + voiceover.(wav|mp3)
        |
        v
[1] scene planner  ->  scene_plan.json     (beats, timing, search terms, copy, transitions, motion specs)
        |
        v
[2] asset sourcing ->  sourced_plan.json    (image/video/local asset bound to each visual)
        |
        v
[3] quality check  ->  qc_plan.json         (accept / reject / flag-for-upscale per visual, against guidelines)
        |
        v
[4] render bridge  ->  render_props.json    (timeline the renderer consumes)
        |
        v
[5] Remotion render -> output.mp4
```

Each arrow is a CLI subcommand and writes a JSON artifact to the job's work directory, so any stage can be inspected, re-run, or replaced in isolation. `run` chains all five.

## Modules

| Module | Path | Responsibility |
|--------|------|----------------|
| config | `content_engine/config.py` | Load `config.json`, resolve role to provider, expose sourcing and render settings. |
| llm | `content_engine/llm/` | Provider agnostic chat completion. Providers: NVIDIA NIM (OpenAI compatible), Anthropic, Google Gemini. Role based routing with fallback. |
| planner | `content_engine/planner/` | Script to structured scene plan. Deterministic heuristic core, optional LLM enrichment. |
| sourcing | `content_engine/sourcing/` | Bind each visual to a real asset: Pexels or Pixabay image, stock video, or a local library asset. Offline mode synthesizes placeholders. |
| qc | `content_engine/qc/` | Score each sourced visual against `qc/guidelines.md`. Accept, reject, or flag script critical low quality images for upscale. |
| render | `content_engine/render/` | Translate the QC plan into renderer props and invoke Remotion. |
| cli | `content_engine/cli.py` | Subcommands: `plan`, `source`, `qc`, `render`, `run`. |

## LLM layer

The planner and the QC stage call an LLM through one interface, `complete(role, system, user, image=None) -> str`. A role (`scene_planning`, `qc`) maps to a primary provider and a fallback in `config.json`. Resolution order per role:

1. Primary provider, if its key is present.
2. Fallback provider, if its key is present.
3. No provider. The stage uses its built in heuristic.

This keeps two promises at once. Real runs use the strong models you pay for (Anthropic for planning, Gemini for QC). Development and the test suite use free models or no model at all, so no paid credits are spent and the suite never touches the network. Every stage produces a valid result with zero providers configured, which is what makes the whole pipeline reproducible offline.

Providers are thin clients over each vendor's HTTP API. Adding one means implementing a single `complete` method.

## Planner

The planner is deterministic first. It splits the script into beats, estimates per beat duration by distributing the voiceover length across beats weighted by word count, and decides for each beat:

- whether the visual is a clip or a still image (motion and action language leans clip, concept and definition language leans image),
- search and selection terms (keyword extraction over the beat),
- title card and lower third copy,
- the transition into the beat and its placement,
- a motion graphics spec (for example a slow zoom on a still, or an animated counter).

When an LLM is configured it refines the search terms and the on screen copy and may adjust the clip to image ratio. The heuristic output and the LLM output share one schema (`planner/schema.py`), so the rest of the pipeline does not care which produced the plan.

## Sourcing

For each visual the sourcer picks a provider based on the plan (clip vs image) and the config, queries it with the plan's search terms, and records the chosen asset plus its metadata (resolution, source, license note). Transitions, sound effects, music, and animated backgrounds are pulled from the local `assets/` library. In offline mode the sourcer synthesizes labeled placeholder images and clips with ffmpeg so a render can complete with no keys and no network. The provider clients respect each API's documented rate and attribution terms.

## Quality check

QC reads `qc/guidelines.md` and scores each sourced visual on resolution, aspect fit, and (when a vision model is configured) relevance to the beat. A visual is accepted, rejected (and re-sourced), or, when it is script critical and merely low resolution, flagged for upscale. The heuristic alone runs on metadata, so QC has a deterministic offline path too.

## Render

The render bridge flattens the QC approved plan into a single props document: an ordered list of scenes, each with its asset path, in and out timing, transition, title card, lower third, and motion spec, plus the global audio track and music bed. It stages the assets into the Remotion project's `public/` folder and calls `npx remotion render` with those props. The composition duration is derived from the voiceover length, so video and audio always match.

Renders are local and CPU bound. Tests and development use short clips at low resolution. A full length high resolution render is a heavy job meant for the end user's machine.

## Desktop shell

An Electron app wraps the same CLI. The user drops in a script and a voiceover, presses go, and watches stage by stage progress while the pipeline runs as a child process. The shell adds no logic of its own; it is a thin front end over `run`.

## Testing

Every module has unit tests. The planner, sourcing (offline), QC, and the render bridge are covered without network or keys. An end to end test runs the full chain on a short generated voiceover and asserts a non empty MP4 comes out. `pytest` is the suite; it must stay green.

## Repository layout

```
content-engine/
  config.example.json     template; copy to config.json (chmod 600)
  ARCHITECTURE.md
  content_engine/         python pipeline core
  remotion/               renderer (composition + components)
  electron/               desktop shell
  assets/                 local library: transitions, sfx, music, backgrounds
  tests/                  pytest suite
  examples/               sample script and generated voiceover
  work/                   per job artifacts (gitignored)
```
