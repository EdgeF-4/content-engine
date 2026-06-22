import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TitleCardSpec } from "../types";

const FONT = "Helvetica, Arial, sans-serif";

/**
 * Opening title card. Lives over the first scene rather than on its own black
 * frame, so the video starts on a visual. Text springs up and fades out near
 * the end of its window.
 */
export const TitleCard: React.FC<{
  spec: TitleCardSpec;
  accentColor: string;
}> = ({ spec, accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18, stiffness: 90 } });
  const fadeOut = interpolate(
    frame,
    [spec.durationFrames - fps * 0.5, spec.durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const y = interpolate(enter, [0, 1], [40, 0]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: Math.min(enter, fadeOut),
      }}
    >
      <div
        style={{
          transform: `translateY(${y}px)`,
          textAlign: "center",
          padding: "0 8%",
          maxWidth: "92%",
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 800,
            fontSize: "8vw",
            lineHeight: 1.05,
            color: "white",
            textShadow: "0 8px 30px rgba(0,0,0,0.6)",
          }}
        >
          {spec.text}
        </div>
        {spec.subtitle ? (
          <div
            style={{
              marginTop: "0.5em",
              fontFamily: FONT,
              fontWeight: 600,
              fontSize: "3.6vw",
              color: accentColor,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            {spec.subtitle}
          </div>
        ) : null}
        <div
          style={{
            margin: "0.7em auto 0",
            width: interpolate(enter, [0, 1], [0, 120]),
            height: "0.7vw",
            background: accentColor,
            borderRadius: 999,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
