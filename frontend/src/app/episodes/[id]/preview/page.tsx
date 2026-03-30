"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { ScenePlayer, type SceneWithAssets } from "@/components/scene-player";
import { apiFetch } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Episode {
  id: string;
  title: string | null;
  status: string;
  target_duration_sec: number;
}

export default function PreviewPage() {
  const { id: episodeId } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const [episode, setEpisode] = useState<Episode | null>(null);
  const [scenes, setScenes] = useState<SceneWithAssets[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasAssets, setHasAssets] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        const ep = await apiFetch<Episode>(
          `/api/v1/episodes/${episodeId}`,
          { token: token ?? undefined },
        );
        setEpisode(ep);

        try {
          const scenesData = await apiFetch<SceneWithAssets[]>(
            `/api/v1/episodes/${episodeId}/scenes-with-assets`,
            { token: token ?? undefined },
          );
          setScenes(scenesData);
          setHasAssets(scenesData.some((s) => s.assets.length > 0));
        } catch {
          const plainScenes = await apiFetch<SceneWithAssets[]>(
            `/api/v1/episodes/${episodeId}/scenes`,
            { token: token ?? undefined },
          );
          setScenes(plainScenes.map((s) => ({ ...s, assets: s.assets || [] })));
          setHasAssets(false);
        }
      } catch {
        router.push("/stories");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [episodeId, getToken, router]);

  async function handleShare() {
    setSharing(true);
    try {
      const token = await getToken();
      const result = await apiFetch<{ token: string; share_url: string }>(
        `/api/v1/episodes/${episodeId}/share`,
        { method: "POST", token: token ?? undefined },
      );
      const fullUrl = `${window.location.origin}${result.share_url}`;
      setShareUrl(fullUrl);
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create share link");
    } finally {
      setSharing(false);
    }
  }

  async function handleCopyLink() {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  }

  const handleDownloadScript = async () => {
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_BASE}/api/v1/episodes/${episodeId}/download/script`,
        { headers: { Authorization: `Bearer ${token}` } },
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
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading preview...</p>
        </div>
      </div>
    );
  }

  if (scenes.length === 0) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-3xl">
          ?
        </div>
        <h2 className="mt-4 text-xl font-bold">No scenes yet</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Generate your scenes first, then come back to preview.
        </p>
        <Button
          className="mt-6"
          onClick={() => router.push(`/episodes/${episodeId}/scenes`)}
        >
          Go to Scene Editor
        </Button>
      </div>
    );
  }

  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration_sec || 0), 0);

  return (
    <div className="mx-auto max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {episode?.title || "Untitled Episode"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {scenes.length} scenes &middot; {Math.round(totalDuration)}s
            {hasAssets && " &middot; AI-generated preview"}
          </p>
        </div>
        <div className="flex gap-2">
          {shareUrl ? (
            <Button variant="outline" size="sm" onClick={handleCopyLink}>
              {copied ? "Copied!" : "Copy Link"}
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={handleShare} disabled={sharing}>
              {sharing ? "Creating..." : "Share"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleDownloadScript}>
            Download Script
          </Button>
        </div>
      </div>

      {/* Player */}
      <div className="mt-6">
        <ScenePlayer scenes={scenes} title={episode?.title} />
      </div>

      {/* Bottom Actions */}
      <div className="mt-8 flex flex-wrap gap-3 border-t pt-6">
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
        {!hasAssets && (
          <Button
            onClick={() => router.push(`/episodes/${episodeId}/generate`)}
          >
            Generate Assets
          </Button>
        )}
        <Button variant="outline" onClick={() => router.push("/stories")}>
          My Stories
        </Button>
      </div>
    </div>
  );
}
