"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Scene {
  id: string;
  episode_id: string;
  scene_order: number;
  beat_label: string;
  visual_description: string;
  narration_text: string | null;
  dialogue_text: string | null;
  duration_sec: number | null;
  image_url?: string | null;
}

interface SceneAsset {
  asset_type: string;
  url: string;
}

interface SceneWithAssets {
  id: string;
  assets: SceneAsset[];
}

interface Episode {
  id: string;
  title: string | null;
  status: string;
  target_duration_sec: number;
}

interface GenerationJob {
  id: string;
  job_type: string;
  status: string;
  stage: string | null;
  error_message: string | null;
  created_at: string;
}

const BEAT_COLORS: Record<string, string> = {
  hook: "bg-red-100 text-red-800",
  setup: "bg-blue-100 text-blue-800",
  escalation_1: "bg-amber-100 text-amber-800",
  escalation_2: "bg-orange-100 text-orange-800",
  escalation_3: "bg-rose-100 text-rose-800",
  climax: "bg-purple-100 text-purple-800",
  button: "bg-green-100 text-green-800",
};

export default function SceneEditorPage() {
  const { id: episodeId } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [breakdownError, setBreakdownError] = useState<string | null>(null);
  // Per-scene image regeneration state, keyed by scene id.
  const [regenerating, setRegenerating] = useState<Record<string, boolean>>({});
  const [regenError, setRegenError] = useState<Record<string, string>>({});
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});

  const loadImages = useCallback(async () => {
    try {
      const token = await getToken();
      const withAssets = await apiFetch<SceneWithAssets[]>(
        `/api/v1/episodes/${episodeId}/scenes-with-assets`,
        { token: token ?? undefined },
      );
      const urlBySceneId: Record<string, string | null> = {};
      for (const s of withAssets) {
        const img = s.assets.find((a) => a.asset_type === "image");
        urlBySceneId[s.id] = img ? `${API_BASE}${img.url}` : null;
      }
      setScenes((prev) =>
        prev.map((s) => ({ ...s, image_url: urlBySceneId[s.id] ?? null })),
      );
    } catch {
      // No assets yet (e.g. before first generation) — leave thumbnails empty.
    }
  }, [episodeId, getToken]);

  const loadData = useCallback(async () => {
    try {
      const token = await getToken();
      const [ep, sc, jobs] = await Promise.all([
        apiFetch<Episode>(`/api/v1/episodes/${episodeId}`, {
          token: token ?? undefined,
        }),
        apiFetch<Scene[]>(`/api/v1/episodes/${episodeId}/scenes`, {
          token: token ?? undefined,
        }),
        apiFetch<GenerationJob[]>(`/api/v1/episodes/${episodeId}/jobs`, {
          token: token ?? undefined,
        }).catch(() => [] as GenerationJob[]),
      ]);
      setEpisode(ep);
      setScenes(sc);
      if (sc.length > 0) loadImages();

      // Decide whether to keep polling. Three relevant states:
      //   - breakdown succeeded -> scenes will be loaded; stop polling
      //   - breakdown failed   -> show the error so the user isn't stuck on a spinner
      //   - breakdown still running (or never started) -> keep polling
      if (ep.status === "draft" && sc.length === 0) {
        const breakdownJob = jobs.find((j) => j.job_type === "scene_breakdown");
        if (breakdownJob?.status === "failed") {
          setPolling(false);
          setBreakdownError(
            breakdownJob.error_message ||
              "The scene breakdown failed. Please try again or contact support.",
          );
        } else {
          setPolling(true);
          setBreakdownError(null);
        }
      } else {
        setPolling(false);
        setBreakdownError(null);
      }
    } catch {
      router.push("/stories");
    } finally {
      setLoading(false);
    }
  }, [episodeId, getToken, router, loadImages]);

  const regenerateImage = useCallback(
    async (sceneId: string) => {
      setRegenError((prev) => {
        const next = { ...prev };
        delete next[sceneId];
        return next;
      });
      setRegenerating((prev) => ({ ...prev, [sceneId]: true }));
      try {
        const token = await getToken();
        await apiFetch(
          `/api/v1/episodes/${episodeId}/scenes/${sceneId}/regenerate-image`,
          { method: "POST", token: token ?? undefined },
        );

        // Poll the per-scene job until it finishes (image gen is ~100s).
        const deadline = Date.now() + 5 * 60 * 1000;
        while (Date.now() < deadline) {
          await new Promise((r) => setTimeout(r, 3000));
          const jobToken = await getToken();
          const job = await apiFetch<GenerationJob | null>(
            `/api/v1/episodes/${episodeId}/scenes/${sceneId}/regenerate-image/status`,
            { token: jobToken ?? undefined },
          );
          if (job?.status === "completed") {
            await loadImages();
            return;
          }
          if (job?.status === "failed") {
            setRegenError((prev) => ({
              ...prev,
              [sceneId]: job.error_message || "Image regeneration failed.",
            }));
            return;
          }
        }
        setRegenError((prev) => ({
          ...prev,
          [sceneId]: "Timed out waiting for the new image.",
        }));
      } catch (err) {
        setRegenError((prev) => ({
          ...prev,
          [sceneId]:
            err instanceof Error ? err.message : "Failed to start regeneration.",
        }));
      } finally {
        setRegenerating((prev) => ({ ...prev, [sceneId]: false }));
      }
    },
    [episodeId, getToken, loadImages],
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [polling, loadData]);

  const saveScene = useCallback(
    async (sceneId: string, updates: Partial<Scene>) => {
      const token = await getToken();
      await apiFetch(`/api/v1/episodes/${episodeId}/scenes/${sceneId}`, {
        method: "PATCH",
        token: token ?? undefined,
        body: JSON.stringify(updates),
      });
    },
    [episodeId, getToken],
  );

  const debouncedSave = useCallback(
    (sceneId: string, updates: Partial<Scene>) => {
      if (saveTimers.current[sceneId]) {
        clearTimeout(saveTimers.current[sceneId]);
      }
      saveTimers.current[sceneId] = setTimeout(() => {
        saveScene(sceneId, updates);
      }, 800);
    },
    [saveScene],
  );

  const updateSceneLocal = (sceneId: string, field: keyof Scene, value: string) => {
    setScenes((prev) =>
      prev.map((s) => (s.id === sceneId ? { ...s, [field]: value } : s)),
    );
    debouncedSave(sceneId, { [field]: value });
  };

  const deleteScene = async (sceneId: string) => {
    const token = await getToken();
    await apiFetch(`/api/v1/episodes/${episodeId}/scenes/${sceneId}`, {
      method: "DELETE",
      token: token ?? undefined,
    });
    setScenes((prev) => prev.filter((s) => s.id !== sceneId));
  };

  const moveScene = (index: number, direction: -1 | 1) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= scenes.length) return;
    const newScenes = [...scenes];
    [newScenes[index], newScenes[newIndex]] = [newScenes[newIndex], newScenes[index]];
    newScenes.forEach((s, i) => {
      s.scene_order = i + 1;
      saveScene(s.id, { scene_order: i + 1 });
    });
    setScenes(newScenes);
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-muted-foreground">Loading scenes...</p>
      </div>
    );
  }

  if (breakdownError) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-3xl">
          !
        </div>
        <h2 className="text-xl font-bold">Scene breakdown failed</h2>
        <p className="text-sm text-muted-foreground">{breakdownError}</p>
        <div className="flex gap-2 pt-2">
          <Button variant="outline" onClick={() => router.push("/stories")}>
            Back to Stories
          </Button>
          <Button
            onClick={() => router.push(`/stories/${episode?.id ? "" : ""}`)}
            disabled
            title="Retry coming soon"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (polling) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-lg font-medium">Analyzing your story...</p>
        <p className="text-sm text-muted-foreground">
          AI is breaking your story into dramatic scenes. This takes 10-30 seconds.
        </p>
      </div>
    );
  }

  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration_sec || 0), 0);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{episode?.title || "Scene Editor"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {scenes.length} scenes &middot; {Math.round(totalDuration)}s total
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/episodes/${episodeId}/preview`)}
            disabled={scenes.length === 0}
          >
            Preview
          </Button>
          <Button
            onClick={() => router.push(`/episodes/${episodeId}/style`)}
            disabled={scenes.length === 0}
          >
            Choose Style & Generate
          </Button>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        {scenes.map((scene, index) => (
          <div
            key={scene.id}
            className="rounded-xl border bg-card p-5 transition-shadow hover:shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${BEAT_COLORS[scene.beat_label] || "bg-muted text-muted-foreground"}`}
                >
                  {scene.beat_label.replace("_", " ")}
                </span>
                {scene.duration_sec && (
                  <span className="text-xs text-muted-foreground">
                    {scene.duration_sec}s
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => moveScene(index, -1)}
                  disabled={index === 0}
                  className="rounded p-1 text-muted-foreground hover:bg-muted disabled:opacity-30"
                  title="Move up"
                >
                  ↑
                </button>
                <button
                  onClick={() => moveScene(index, 1)}
                  disabled={index === scenes.length - 1}
                  className="rounded p-1 text-muted-foreground hover:bg-muted disabled:opacity-30"
                  title="Move down"
                >
                  ↓
                </button>
                <button
                  onClick={() => deleteScene(scene.id)}
                  className="rounded p-1 text-destructive hover:bg-destructive/10"
                  title="Delete scene"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="mt-3 space-y-3">
              {/* Generated image — driven by the Visual Description below */}
              <div className="flex items-start gap-3">
                <div className="relative h-28 w-20 shrink-0 overflow-hidden rounded-lg border bg-muted">
                  {scene.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={scene.image_url}
                      alt={`Scene ${scene.scene_order}`}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-center text-[10px] text-muted-foreground">
                      No image yet
                    </div>
                  )}
                  {regenerating[scene.id] && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => regenerateImage(scene.id)}
                    disabled={regenerating[scene.id]}
                  >
                    {regenerating[scene.id]
                      ? "Regenerating…"
                      : scene.image_url
                        ? "Regenerate image"
                        : "Generate image"}
                  </Button>
                  <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
                    The image is generated from the <strong>Visual Description</strong>.
                    Edit that text, then regenerate. Narration only affects the voiceover.
                  </p>
                  {regenError[scene.id] && (
                    <p className="mt-1 text-[11px] text-red-500">{regenError[scene.id]}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Visual Description
                </label>
                <textarea
                  value={scene.visual_description}
                  onChange={(e) =>
                    updateSceneLocal(scene.id, "visual_description", e.target.value)
                  }
                  rows={2}
                  className="mt-1 block w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Narration
                </label>
                <textarea
                  value={scene.narration_text || ""}
                  onChange={(e) =>
                    updateSceneLocal(scene.id, "narration_text", e.target.value)
                  }
                  rows={2}
                  className="mt-1 block w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {scenes.length > 0 && (
        <div className="mt-8 flex justify-end">
          <Button onClick={() => router.push(`/episodes/${episodeId}/style`)}>
            Choose Style & Generate
          </Button>
        </div>
      )}
    </div>
  );
}
