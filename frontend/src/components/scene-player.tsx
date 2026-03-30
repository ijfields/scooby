"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AssetInfo {
  id: string;
  asset_type: string;
  mime_type: string | null;
  url: string;
}

export interface SceneWithAssets {
  id: string;
  scene_order: number;
  beat_label: string;
  visual_description: string;
  narration_text: string | null;
  duration_sec: number | null;
  assets: AssetInfo[];
}

const BEAT_COLORS: Record<string, string> = {
  hook: "bg-red-500/80",
  setup: "bg-blue-500/80",
  escalation_1: "bg-amber-500/80",
  escalation_2: "bg-orange-500/80",
  escalation_3: "bg-rose-500/80",
  climax: "bg-purple-500/80",
  button: "bg-green-500/80",
};

interface ScenePlayerProps {
  scenes: SceneWithAssets[];
  title?: string | null;
}

export function ScenePlayer({ scenes, title }: ScenePlayerProps) {
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [showNarration, setShowNarration] = useState(true);
  const audioRef = useRef<HTMLAudioElement>(null);
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current);
    };
  }, []);

  const scene = scenes[currentScene];
  const imageAsset = scene?.assets?.find((a) => a.asset_type === "image");
  const audioAsset = scene?.assets?.find((a) => a.asset_type === "voiceover");

  const goToScene = useCallback(
    (index: number) => {
      if (index < 0 || index >= scenes.length) return;
      if (autoAdvanceTimer.current) {
        clearTimeout(autoAdvanceTimer.current);
        autoAdvanceTimer.current = null;
      }
      setCurrentScene(index);
      setAudioProgress(0);
      setAudioDuration(0);
    },
    [scenes.length],
  );

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audioAsset) {
      audio.src = `${API_BASE}${audioAsset.url}`;
      audio.load();
      if (isPlaying) {
        audio.play().catch(() => {});
      }
    } else {
      audio.pause();
      audio.src = "";
      if (isPlaying && scene) {
        const dur = (scene.duration_sec || 5) * 1000;
        autoAdvanceTimer.current = setTimeout(() => {
          if (currentScene < scenes.length - 1) {
            goToScene(currentScene + 1);
          } else {
            setIsPlaying(false);
          }
        }, dur);
      }
    }
  }, [currentScene, audioAsset, isPlaying, scene, scenes.length, goToScene]);

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (audio) {
      setAudioProgress(audio.currentTime);
      setAudioDuration(audio.duration || 0);
    }
  };

  const handleAudioEnded = () => {
    if (isPlaying && currentScene < scenes.length - 1) {
      autoAdvanceTimer.current = setTimeout(() => {
        goToScene(currentScene + 1);
      }, 800);
    } else {
      setIsPlaying(false);
    }
  };

  const togglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      audioRef.current?.pause();
      if (autoAdvanceTimer.current) {
        clearTimeout(autoAdvanceTimer.current);
        autoAdvanceTimer.current = null;
      }
    } else {
      setIsPlaying(true);
      if (audioAsset && audioRef.current) {
        audioRef.current.play().catch(() => {});
      }
    }
  };

  if (!scene) return null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      {/* Phone Frame */}
      <div className="flex flex-col items-center">
        <div className="relative w-full max-w-[340px] overflow-hidden rounded-3xl border-2 border-border bg-black shadow-2xl">
          <div className="relative aspect-[9/16] w-full">
            {imageAsset ? (
              <img
                src={`${API_BASE}${imageAsset.url}`}
                alt={`Scene ${scene.scene_order}: ${scene.beat_label}`}
                className="h-full w-full object-cover transition-opacity duration-500"
                key={scene.id}
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-gradient-to-b from-gray-800 to-gray-900">
                <div className="text-center px-6">
                  <p className="text-5xl">
                    {scene.beat_label === "hook" ? "!" : scene.beat_label === "climax" ? "!!!" : "~"}
                  </p>
                  <p className="mt-3 text-sm text-gray-400">
                    {scene.visual_description}
                  </p>
                </div>
              </div>
            )}

            <div className="absolute top-4 left-4">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold text-white backdrop-blur-sm ${BEAT_COLORS[scene.beat_label] || "bg-gray-500/80"}`}
              >
                {scene.beat_label.replace(/_/g, " ")}
              </span>
            </div>

            <div className="absolute top-4 right-4">
              <span className="rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                {currentScene + 1} / {scenes.length}
              </span>
            </div>

            {showNarration && scene.narration_text && (
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/60 to-transparent p-5 pt-12">
                <p className="text-sm leading-relaxed text-white/95">
                  {scene.narration_text}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="mt-4 flex w-full max-w-[340px] flex-col gap-3">
          {audioAsset && audioDuration > 0 && (
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${(audioProgress / audioDuration) * 100}%` }}
              />
            </div>
          )}

          <div className="flex items-center justify-center gap-1.5">
            {scenes.map((_, i) => (
              <button
                key={i}
                onClick={() => goToScene(i)}
                className={`h-2 rounded-full transition-all duration-300 ${
                  i === currentScene
                    ? "w-6 bg-primary"
                    : i < currentScene
                      ? "w-2 bg-primary/40"
                      : "w-2 bg-muted-foreground/30"
                }`}
              />
            ))}
          </div>

          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => goToScene(currentScene - 1)}
              disabled={currentScene === 0}
              className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="19 20 9 12 19 4 19 20" />
                <line x1="5" x2="5" y1="19" y2="5" />
              </svg>
            </button>

            <button
              onClick={togglePlay}
              className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 active:scale-95"
            >
              {isPlaying ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="6 3 20 12 6 21 6 3" />
                </svg>
              )}
            </button>

            <button
              onClick={() => goToScene(currentScene + 1)}
              disabled={currentScene === scenes.length - 1}
              className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 4 15 12 5 20 5 4" />
                <line x1="19" x2="19" y1="5" y2="19" />
              </svg>
            </button>
          </div>

          <div className="flex justify-center">
            <button
              onClick={() => setShowNarration(!showNarration)}
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              {showNarration ? "Hide" : "Show"} narration text
            </button>
          </div>
        </div>
      </div>

      {/* Scene List Sidebar */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Scenes
        </h2>
        <div className="space-y-1.5">
          {scenes.map((s, i) => {
            const sImage = s.assets?.find((a) => a.asset_type === "image");
            const isActive = i === currentScene;
            return (
              <button
                key={s.id}
                onClick={() => goToScene(i)}
                className={`flex w-full items-center gap-3 rounded-xl p-2.5 text-left transition-all ${
                  isActive
                    ? "bg-primary/10 ring-1 ring-primary/30"
                    : "hover:bg-muted"
                }`}
              >
                <div className="h-14 w-10 flex-shrink-0 overflow-hidden rounded-lg bg-muted">
                  {sImage ? (
                    <img
                      src={`${API_BASE}${sImage.url}`}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                      {i + 1}
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${BEAT_COLORS[s.beat_label]?.replace("/80", "") || "bg-gray-400"}`}
                    />
                    <span className="text-sm font-medium capitalize truncate">
                      {s.beat_label.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground truncate">
                    {s.narration_text
                      ? s.narration_text.slice(0, 60) + (s.narration_text.length > 60 ? "..." : "")
                      : s.visual_description.slice(0, 60)}
                  </p>
                </div>
                <span className="flex-shrink-0 text-xs text-muted-foreground">
                  {(s.duration_sec || 0).toFixed(0)}s
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleAudioEnded}
        preload="auto"
      />
    </div>
  );
}
