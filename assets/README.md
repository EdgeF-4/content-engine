# Local asset library

The renderer pulls transitions, sound effects, music, and animated backgrounds
from here. Everything shipped in this folder was synthesized locally, so it is
free of third party licensing. Drop your own assets in alongside them and the
sourcing stage will pick them up by folder.

| Folder | What goes here | Shipped |
|--------|----------------|---------|
| `music/` | Background music beds (`.wav`, `.mp3`). The lowest gain bed under the voiceover. | `ambient_bed.wav` (12s, synthesized) |
| `sfx/` | Transition and accent sound effects. | `whoosh.wav`, `pop.wav` |
| `transitions/` | Optional overlay clips (light leaks, film burns). Core transitions (crossfade, slide, whip, dip to black) are drawn by the renderer in code, so this can stay empty. | none |
| `backgrounds/` | Optional looping background clips for title cards and image gaps. Gradients are drawn in code when this is empty. | none |

To add a track, copy a file into the matching folder. Keep music beds longer
than your typical video so they never run short; the renderer loops and ducks
them automatically.
