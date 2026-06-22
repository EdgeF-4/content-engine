import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { TransitionSpec } from "../types";

/**
 * Entrance animation for a scene, driven by the planned transition type.
 * Frame is local to the enclosing Sequence, so the effect plays as the scene
 * appears. The composition background is black, so a fade reads as a dip.
 */
export const Reveal: React.FC<{
  transition: TransitionSpec;
  children: React.ReactNode;
}> = ({ transition, children }) => {
  const frame = useCurrentFrame();
  const d = Math.max(1, transition.durationFrames);
  const p = interpolate(frame, [0, d], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  let style: React.CSSProperties = {};
  switch (transition.type) {
    case "crossfade":
    case "dip-to-black":
      style = { opacity: p };
      break;
    case "slide":
      style = { transform: `translateX(${(1 - p) * 100}%)` };
      break;
    case "whip":
      style = {
        transform: `translateX(${(1 - p) * 60}%)`,
        opacity: p,
        filter: `blur(${(1 - p) * 8}px)`,
      };
      break;
    case "cut":
    default:
      style = {};
  }
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};
