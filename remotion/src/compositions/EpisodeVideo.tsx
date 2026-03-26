import { AbsoluteFill } from "remotion";
import type { CompositionProps } from "../lib/types";

export const EpisodeVideo: React.FC<CompositionProps> = ({ title }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#111",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <h1 style={{ color: "white", fontSize: 48, fontFamily: "sans-serif" }}>
        {title}
      </h1>
    </AbsoluteFill>
  );
};
