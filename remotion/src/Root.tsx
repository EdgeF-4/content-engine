import React from "react";
import { Composition } from "remotion";
import { Main } from "./Video";
import { RenderProps } from "./types";
import defaultProps from "./defaultProps";

/**
 * Duration, fps, and dimensions all come from the props the bridge passes, via
 * calculateMetadata, so the video length tracks the voiceover exactly.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Main}
      durationInFrames={defaultProps.durationInFrames}
      fps={defaultProps.fps}
      width={defaultProps.width}
      height={defaultProps.height}
      defaultProps={defaultProps}
      calculateMetadata={({ props }: { props: RenderProps }) => ({
        durationInFrames: props.durationInFrames,
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
  );
};
