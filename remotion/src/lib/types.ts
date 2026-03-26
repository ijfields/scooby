/** Composition JSON spec — passed from the Python backend to Remotion for rendering. */

export interface CompositionProps {
  episodeId: string;
  title: string;
  fps: number;
  width: number;
  height: number;
  totalDurationFrames: number;
  musicBed?: MusicBed;
  scenes: SceneProps[];
}

export interface MusicBed {
  url: string;
  volume: number;
  fadeInFrames: number;
  fadeOutFrames: number;
}

export interface SceneProps {
  sceneId: string;
  beatLabel: string;
  startFrame: number;
  durationFrames: number;
  image: SceneImage;
  voiceover?: SceneVoiceover;
  captions: Caption[];
  transition?: SceneTransition;
}

export interface SceneImage {
  url: string;
  animation: KenBurnsAnimation;
}

export interface KenBurnsAnimation {
  type: "ken_burns";
  startScale: number;
  endScale: number;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

export interface SceneVoiceover {
  url: string;
  startOffsetFrames: number;
  volume: number;
}

export interface Caption {
  text: string;
  startFrame: number;
  endFrame: number;
  style: string;
}

export interface SceneTransition {
  type: "crossfade";
  durationFrames: number;
}
