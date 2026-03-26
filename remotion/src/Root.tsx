import { Composition } from "remotion";
import { EpisodeVideo } from "./compositions/EpisodeVideo";
import type { CompositionProps } from "./lib/types";

export const Root: React.FC = () => {
  return (
    <Composition
      id="EpisodeVideo"
      component={EpisodeVideo}
      durationInFrames={30 * 90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={
        {
          episodeId: "preview",
          title: "Preview",
          fps: 30,
          width: 1080,
          height: 1920,
          totalDurationFrames: 30 * 90,
          scenes: [],
        } satisfies CompositionProps
      }
    />
  );
};
