export type AssetKind = "image" | "clip";

export interface SceneAsset {
  kind: AssetKind;
  path: string; // relative to public/
}

export interface TransitionSpec {
  type: string; // cut | crossfade | dip-to-black | slide | whip
  durationFrames: number;
}

export interface MotionSpec {
  type: string; // static | ken-burns | pan | counter | text-reveal
  params: Record<string, unknown>;
}

export interface LowerThirdSpec {
  text: string;
  subtitle: string;
  startFrame: number; // relative to scene start
  durationFrames: number;
}

export interface SceneSpec {
  index: number;
  startFrame: number; // absolute
  durationFrames: number;
  asset: SceneAsset;
  transition: TransitionSpec;
  motion: MotionSpec;
  lowerThird: LowerThirdSpec | null;
  query: string;
}

export interface TitleCardSpec {
  text: string;
  subtitle: string;
  startFrame: number;
  durationFrames: number;
}

export type RenderProps = {
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  voiceover: string | null;
  music: string | null;
  transitionSfx: string | null;
  musicVolume: number;
  accentColor: string;
  titleCard: TitleCardSpec;
  scenes: SceneSpec[];
};
