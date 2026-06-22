import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { RenderProps } from "./types";
import { SceneView } from "./components/SceneView";
import { TitleCard } from "./components/TitleCard";

/**
 * The full video: a stack of scenes, the title card over the opening, the
 * voiceover, a ducked and looped music bed, and a transition whoosh at each
 * soft scene change. Scenes never overlap, so the total length equals the
 * voiceover length and audio stays in sync.
 */
export const Main: React.FC<RenderProps> = (props) => {
  const {
    scenes,
    titleCard,
    voiceover,
    music,
    transitionSfx,
    musicVolume,
    accentColor,
    fps,
  } = props;

  const sfxLead = Math.round(fps * 0.1);
  const sfxLen = Math.round(fps * 0.6);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((scene) => (
        <SceneView key={scene.index} scene={scene} accentColor={accentColor} />
      ))}

      <Sequence
        from={titleCard.startFrame}
        durationInFrames={titleCard.durationFrames}
        name="title-card"
      >
        <TitleCard spec={titleCard} accentColor={accentColor} />
      </Sequence>

      {voiceover ? <Audio src={staticFile(voiceover)} /> : null}

      {music ? (
        <Audio src={staticFile(music)} volume={musicVolume} loop />
      ) : null}

      {transitionSfx
        ? scenes
            .filter((s) => s.index > 0 && s.transition.type !== "cut")
            .map((s) => (
              <Sequence
                key={`sfx-${s.index}`}
                from={Math.max(0, s.startFrame - sfxLead)}
                durationInFrames={sfxLen}
                name={`sfx-${s.index}`}
              >
                <Audio src={staticFile(transitionSfx)} volume={0.5} />
              </Sequence>
            ))
        : null}
    </AbsoluteFill>
  );
};
