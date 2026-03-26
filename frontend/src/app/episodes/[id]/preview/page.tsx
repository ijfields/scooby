"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Episode {
  id: string;
  title: string | null;
  status: string;
  final_video_url: string | null;
  target_duration_sec: number;
}

interface Scene {
  id: string;
  scene_order: number;
  beat_label: string;
  visual_description: string;
  narration_text: string | null;
  duration_sec: number | null;
}

interface DownloadInfo {
  download_url: string;
  filename: string;
  duration_sec: number | null;
  resolution: string;
}

export default function PreviewPage() {
  const { id: episodeId } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const videoRef = useRef<HTMLVideoElement>(null);

  const [episode, setEpisode] = useState<Episode | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    async function load() {
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
      } catch {
        router.push("/stories");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [episodeId, getToken, router]);

  async function handleDownloadVideo() {
    setDownloading(true);
    try {
      const token = await getToken();
      const info = await apiFetch<DownloadInfo>(
        `/api/v1/episodes/${episodeId}/download/video`,
        { token: token ?? undefined },
      );
      // Open download URL in new tab
      window.open(info.download_url, "_blank");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  async function handleDownloadScript() {
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/episodes/${episodeId}/download/script`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      if (!res.ok) throw new Error("Failed to download script");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(episode?.title || "script").toLowerCase().replace(/\s+/g, "-")}-script.txt`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-muted-foreground">Loading preview...</p>
      </div>
    );
  }

  const hasVideo = episode?.status === "preview_ready" && episode.final_video_url;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {episode?.title || "Untitled Episode"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {scenes.length} scenes &middot;{" "}
            {scenes.reduce((sum, s) => sum + (s.duration_sec || 0), 0).toFixed(0)}s
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleDownloadScript}>
            Download Script
          </Button>
          {hasVideo && (
            <Button onClick={handleDownloadVideo} disabled={downloading}>
              {downloading ? "Preparing..." : "Download MP4"}
            </Button>
          )}
        </div>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[auto_1fr]">
        {/* Video Player */}
        <div className="flex justify-center">
          <div className="w-[270px] overflow-hidden rounded-2xl border bg-black shadow-lg sm:w-[324px]">
            {hasVideo ? (
              <video
                ref={videoRef}
                src={episode.final_video_url!}
                controls
                className="aspect-[9/16] w-full"
                poster=""
              >
                Your browser does not support the video tag.
              </video>
            ) : (
              <div className="flex aspect-[9/16] w-full items-center justify-center">
                <div className="text-center text-sm text-gray-400">
                  <p className="text-4xl">🎬</p>
                  <p className="mt-2">
                    {episode?.status === "generating"
                      ? "Video is being generated..."
                      : "No video yet"}
                  </p>
                  {episode?.status !== "preview_ready" && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() =>
                        router.push(`/episodes/${episodeId}/generate`)
                      }
                    >
                      Generate Video
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Scene List */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Scenes</h2>
          {scenes.map((scene) => (
            <div
              key={scene.id}
              className="rounded-lg border p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium">
                    {scene.scene_order}
                  </span>
                  <span className="text-sm font-medium capitalize">
                    {scene.beat_label.replace(/_/g, " ")}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {(scene.duration_sec || 0).toFixed(1)}s
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {scene.visual_description}
              </p>
              {scene.narration_text && (
                <p className="mt-1 text-sm italic text-muted-foreground/70">
                  &ldquo;{scene.narration_text}&rdquo;
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 flex gap-3">
        <Button
          variant="outline"
          onClick={() => router.push(`/episodes/${episodeId}/scenes`)}
        >
          Edit Scenes
        </Button>
        <Button
          variant="outline"
          onClick={() => router.push(`/episodes/${episodeId}/style`)}
        >
          Change Style
        </Button>
        <Button variant="outline" onClick={() => router.push("/stories")}>
          My Stories
        </Button>
      </div>
    </div>
  );
}
