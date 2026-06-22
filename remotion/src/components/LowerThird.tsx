import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { LowerThirdSpec } from "../types";

const FONT = "Helvetica, Arial, sans-serif";

/**
 * A lower third that slides in from the left, holds, then slides out. Frame is
 * local to its own Sequence, so timing comes from durationFrames.
 */
export const LowerThird: React.FC<{
  spec: LowerThirdSpec;
  accentColor: string;
}> = ({ spec, accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 20, stiffness: 120 } });
  const exit = interpolate(
    frame,
    [spec.durationFrames - fps * 0.4, spec.durationFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const x = interpolate(enter, [0, 1], [-120, 0]) - exit * 120;
  const opacity = Math.min(enter, 1 - exit);

  return (
    <div
      style={{
        position: "absolute",
        left: "5%",
        bottom: "10%",
        transform: `translateX(${x}px)`,
        opacity,
        display: "flex",
        alignItems: "stretch",
        maxWidth: "80%",
      }}
    >
      <div style={{ width: "0.9vw", background: accentColor, borderRadius: 4 }} />
      <div
        style={{
          background: "rgba(8,12,20,0.78)",
          padding: "0.5em 1em",
          marginLeft: "0.6vw",
          borderRadius: 6,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 700,
            fontSize: "3.4vw",
            color: "white",
            lineHeight: 1.1,
          }}
        >
          {spec.text}
        </div>
        {spec.subtitle ? (
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 500,
              fontSize: "2.2vw",
              color: "rgba(255,255,255,0.8)",
              marginTop: "0.15em",
            }}
          >
            {spec.subtitle}
          </div>
        ) : null}
      </div>
    </div>
  );
};
