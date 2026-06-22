# Visual quality guidelines

These are the rules the quality check applies to every sourced visual before
it reaches the timeline. The heuristic check enforces the measurable ones from
metadata. When a vision model is configured it judges the subjective ones from
the image itself, using this same document as its rubric.

## Resolution

A visual should cover the output frame without upscaling.

- Accept when the asset area is at least 90 percent of the target frame area.
- Acceptable when it sits between 45 and 90 percent. Keep it, but note the
  softness.
- Below 45 percent is too small. Re-source it, unless it is script critical
  (see below), in which case flag it for upscale rather than dropping it.

## Orientation and framing

The asset orientation should match the output. Portrait output wants portrait
assets; landscape wants landscape. A mismatch is not a rejection on its own,
since the renderer can crop to fill, but it is recorded so a reviewer can swap
it if the crop loses the subject.

## Relevance

The visual should clearly relate to what the narration says over it. A generic
or off topic asset weakens the scene. When relevance scores poorly the asset is
re-sourced, again unless it is script critical, where it is flagged for upscale
or manual swap instead of being silently dropped.

## Script critical visuals

A visual is script critical when the beat names a specific entity, a number, or
a claim the viewer is meant to register (a place, a statistic, a product). These
carry meaning, so they are never silently dropped. If a critical visual is only
low resolution it is flagged for upscale. If it is irrelevant it is flagged for
manual review.

## Safety and tone

Reject anything with visible watermarks, on screen text that competes with the
title cards and lower thirds, or content that clashes with the tone of the
script. Placeholder assets generated for an offline run are exempt, since they
are built to fit the frame and carry no third party content.

## Verdicts

Every visual ends with one verdict:

- `accept` keep as is.
- `flag-upscale` keep but raise the resolution before the final render.
- `reject` re-source with the same search terms.
