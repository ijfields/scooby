"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface GenerationJob {
  id: string;
  episode_id: string;
  job_type: string;
  status: string;
  progress: number | null;
  stage: string | null;
  error_message: string | null;
  created_at: string;
}

const STAGE_LABELS: Record<string, string> = {
  "Starting pipeline": "Setting things up...",
  "Generating images": "Creating scene images with AI...",
  "Generating voiceovers": "Recording narration...",
  "Rendering video": "Composing your video...",
  "Video ready": "Your video is ready!",
};

export default function GeneratePage() {
  const { id: episodeId } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const [job, setJob] = useState<GenerationJob | null>(null);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const token = await getToken();
      const result = await apiFetch<GenerationJob | null>(
        `/api/v1/episodes/${episodeId}/generate/status`,
        { token: token ?? undefined },
      );
      if (result) {
        setJob(result);
        if (result.status === "completed" || result.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      }
    } catch {
      // Silently retry on next poll
    }
  }, [episodeId, getToken]);

  async function startGeneration() {
    setError(null);
    setStarted(true);
    try {
      const token = await getToken();
      const result = await apiFetch<GenerationJob>(
        `/api/v1/episodes/${episodeId}/generate`,
        { method: "POST", token: token ?? undefined },
      );
      setJob(result);

      // Start polling
      pollRef.current = setInterval(pollStatus, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start generation");
      setStarted(false);
    }
  }

  // Check for existing in-progress job on mount
  useEffect(() => {
    async function checkExisting() {
      try {
        const token = await getToken();
        const result = await apiFetch<GenerationJob | null>(
          `/api/v1/episodes/${episodeId}/generate/status`,
          { token: token ?? undefined },
        );
        if (result) {
          setJob(result);
          setStarted(true);
          if (result.status === "running" || result.status === "pending") {
            pollRef.current = setInterval(pollStatus, 3000);
          }
        }
      } catch {
        // No existing job
      }
    }
    checkExisting();

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [episodeId, getToken, pollStatus]);

  const progress = job?.progress ?? 0;
  const stage = job?.stage ?? "";
  const stageLabel = STAGE_LABELS[stage] ?? stage;
  const isRunning = job?.status === "running" || job?.status === "pending";
  const isComplete = job?.status === "completed";
  const isFailed = job?.status === "failed";

  return (
    <div className="mx-auto max-w-xl py-10">
      <h1 className="text-2xl font-bold">Generate Video</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        AI will create images, narration, and compose your video.
      </p>

      {!started && (
        <div className="mt-8">
          <Button onClick={startGeneration} size="lg">
            Start Generation
          </Button>
          {error && (
            <p className="mt-3 text-sm text-red-500">{error}</p>
          )}
        </div>
      )}

      {started && (
        <div className="mt-8 space-y-6">
          {/* Progress bar */}
          <div>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{stageLabel}</span>
              <span className="text-muted-foreground">{Math.round(progress)}%</span>
            </div>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Stage timeline */}
          <div className="space-y-3">
            {["Generating images", "Generating voiceovers", "Rendering video"].map(
              (s) => {
                const stageProgress = job?.progress ?? 0;
                const stageOrder = ["Generating images", "Generating voiceovers", "Rendering video"];
                const currentIdx = stageOrder.indexOf(stage);
                const thisIdx = stageOrder.indexOf(s);
                const isDone = currentIdx > thisIdx || isComplete;
                const isCurrent = currentIdx === thisIdx && isRunning;

                return (
                  <div key={s} className="flex items-center gap-3">
                    <div
                      className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                        isDone
                          ? "bg-green-500 text-white"
                          : isCurrent
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {isDone ? "\u2713" : thisIdx + 1}
                    </div>
                    <span
                      className={`text-sm ${
                        isCurrent ? "font-medium" : isDone ? "text-muted-foreground line-through" : "text-muted-foreground"
                      }`}
                    >
                      {STAGE_LABELS[s] ?? s}
                    </span>
                    {isCurrent && (
                      <span className="ml-auto text-xs text-muted-foreground animate-pulse">
                        In progress...
                      </span>
                    )}
                  </div>
                );
              },
            )}
          </div>

          {/* Completed */}
          {isComplete && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center dark:border-green-900 dark:bg-green-950">
              <p className="text-lg font-semibold text-green-700 dark:text-green-300">
                Your video is ready!
              </p>
              <div className="mt-4 flex justify-center gap-3">
                <Button onClick={() => router.push(`/episodes/${episodeId}/preview`)}>
                  Preview Video
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.push(`/episodes/${episodeId}/scenes`)}
                >
                  Back to Scenes
                </Button>
              </div>
            </div>
          )}

          {/* Failed */}
          {isFailed && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950">
              <p className="font-semibold text-red-700 dark:text-red-300">
                Generation failed
              </p>
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                {job?.error_message || "An unexpected error occurred."}
              </p>
              <div className="mt-4 flex gap-3">
                <Button
                  onClick={() => {
                    setStarted(false);
                    setJob(null);
                    setError(null);
                  }}
                >
                  Try Again
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.push(`/episodes/${episodeId}/style`)}
                >
                  Back to Styles
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {!started && (
        <div className="mt-6">
          <Button
            variant="outline"
            onClick={() => router.push(`/episodes/${episodeId}/style`)}
          >
            Back to Styles
          </Button>
        </div>
      )}
    </div>
  );
}
