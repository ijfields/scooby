"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Scene {
  id: string;
  episode_id: string;
  scene_order: number;
  beat_label: string;
  visual_description: string;
  narration_text: string | null;
  dialogue_text: string | null;
  duration_sec: number | null;
}

interface Episode {
  id: string;
  title: string | null;
  status: string;
  target_duration_sec: number;
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
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});

  const loadData = useCallback(async () => {
    try {
      const token = await getToken();
      const [ep, sc] = await Promise.all([
        apiFetch<Episode>(`/api/v1/episodes/${episodeId}`, {
          token: token ?? undefined,
        }),
        apiFetch<Scene[]>(`/api/v1/episodes/${episodeId}/scenes`, {
          token: token ?? undefined,
        }),
      ]);
      setEpisode(ep);
      setScenes(sc);

      if (ep.status === "draft" && sc.length === 0) {
        setPolling(true);
      } else {
        setPolling(false);
      }
    } catch {
      router.push("/stories");
    } finally {
      setLoading(false);
    }
  }, [episodeId, getToken, router]);

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
