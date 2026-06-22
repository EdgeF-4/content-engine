import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { SceneSpec } from "../types";

/**
 * The full frame visual for a scene: a still image with a slow Ken Burns zoom,
 * or a stock clip. Both cover the frame. Clip audio is dropped so only the
 * voiceover and music are heard.
 */
export const Visual: React.FC<{ scene: SceneSpec; durationFrames: number }> = ({
  scene,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const src = staticFile(scene.asset.path);

  if (scene.asset.kind === "clip") {
    return (
      <AbsoluteFill style={{ backgroundColor: "black" }}>
        <OffthreadVideo
          src={src}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
    );
  }

  // Still image: Ken Burns zoom unless the motion is explicitly static.
  const zoom =
    typeof scene.motion.params.zoom === "number"
      ? (scene.motion.params.zoom as number)
      : 1.12;
  const dir = scene.motion.params.direction === "out" ? "out" : "in";
  const useZoom = scene.motion.type === "ken-burns";
  const scale = !useZoom
    ? 1
    : dir === "in"
      ? interpolate(frame, [0, durationFrames], [1, zoom], {
          extrapolateRight: "clamp",
        })
      : interpolate(frame, [0, durationFrames], [zoom, 1], {
          extrapolateRight: "clamp",
        });

  return (
    <AbsoluteFill style={{ backgroundColor: "black", overflow: "hidden" }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};
