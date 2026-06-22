import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

const FONT = "Helvetica, Arial, sans-serif";

function parseTarget(raw: unknown): number {
  if (typeof raw !== "string") return 0;
  const digits = raw.replace(/[^\d]/g, "");
  return digits ? parseInt(digits, 10) : 0;
}

/**
 * An animated counter that ticks up to a number pulled from the beat. Used as
 * the motion graphic for scenes that state a statistic.
 */
export const Counter: React.FC<{ value: unknown; accentColor: string }> = ({
  value,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const target = parseTarget(value);
  const span = Math.round(fps * 1.4);
  const current = Math.round(
    interpolate(frame, [0, span], [0, target], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const display = current.toLocaleString("en-US");

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: "16%",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <span
        style={{
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: "12vw",
          color: "white",
          textShadow: "0 6px 24px rgba(0,0,0,0.55)",
          borderBottom: `0.8vw solid ${accentColor}`,
          padding: "0 0.4em 0.1em",
        }}
      >
        {display}
      </span>
    </div>
  );
};
