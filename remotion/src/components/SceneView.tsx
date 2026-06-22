import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { SceneSpec } from "../types";
import { Reveal } from "./Reveal";
import { Visual } from "./Visual";
import { Counter } from "./Counter";
import { LowerThird } from "./LowerThird";

/**
 * One scene on the timeline: the visual with its entrance transition, an
 * optional counter motion graphic, a soft bottom gradient for legibility, and
 * an optional lower third on its own sub timeline.
 */
export const SceneView: React.FC<{ scene: SceneSpec; accentColor: string }> = ({
  scene,
  accentColor,
}) => {
  return (
    <Sequence
      from={scene.startFrame}
      durationInFrames={scene.durationFrames}
      name={`scene-${scene.index}`}
    >
      <Reveal transition={scene.transition}>
        <Visual scene={scene} durationFrames={scene.durationFrames} />
      </Reveal>

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.5), rgba(0,0,0,0) 32%)",
          pointerEvents: "none",
        }}
      />

      {scene.motion.type === "counter" ? (
        <Counter value={scene.motion.params.value} accentColor={accentColor} />
      ) : null}

      {scene.lowerThird ? (
        <Sequence
          from={scene.lowerThird.startFrame}
          durationInFrames={scene.lowerThird.durationFrames}
          name={`lower-third-${scene.index}`}
        >
          <LowerThird spec={scene.lowerThird} accentColor={accentColor} />
        </Sequence>
      ) : null}
    </Sequence>
  );
};
