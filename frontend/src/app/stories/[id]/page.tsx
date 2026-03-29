"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Story {
  id: string;
  title: string;
  raw_text: string;
  word_count: number;
  status: string;
  created_at: string;
}

interface Episode {
  id: string;
  title: string | null;
  status: string;
  target_duration_sec: number;
  created_at: string;
  updated_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  processing: "bg-amber-100 text-amber-800",
  generating: "bg-blue-100 text-blue-800",
};

export default function StoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const [story, setStory] = useState<Story | null>(null);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [breaking, setBreaking] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        const [storyData, episodesData] = await Promise.all([
          apiFetch<Story>(`/api/v1/stories/${id}`, {
            token: token ?? undefined,
          }),
          apiFetch<Episode[]>(`/api/v1/episodes/by-story/${id}`, {
            token: token ?? undefined,
          }).catch(() => [] as Episode[]),
        ]);
        setStory(storyData);
        setEpisodes(episodesData);
      } catch {
        router.push("/stories");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, getToken, router]);

  async function handleBreakdown() {
    if (!story) return;
    setBreaking(true);
    try {
      const token = await getToken();
      const episode = await apiFetch<{ id: string }>(
        `/api/v1/episodes/from-story/${story.id}`,
        { method: "POST", token: token ?? undefined },
      );
      router.push(`/episodes/${episode.id}/scenes`);
    } catch {
      setBreaking(false);
    }
  }

  function getEpisodeLink(ep: Episode) {
    if (ep.status === "generating") return `/episodes/${ep.id}/generate`;
    return `/episodes/${ep.id}/preview`;
  }

  function getEpisodeAction(ep: Episode) {
    if (ep.status === "generating") return "View Progress";
    if (ep.status === "draft") return "Continue Editing";
    return "Preview";
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-muted-foreground">Loading story...</p>
      </div>
    );
  }

  if (!story) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{story.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {story.word_count} words &middot;{" "}
            {new Date(story.created_at).toLocaleDateString()}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push("/stories")}>
          My Stories
        </Button>
      </div>

      {/* Existing Episodes */}
      {episodes.length > 0 && (
        <div className="mt-6 space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Episodes
          </h2>
          {episodes.map((ep) => (
            <div
              key={ep.id}
              className="flex items-center justify-between rounded-xl border bg-card p-4 transition-shadow hover:shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium truncate">
                    {ep.title || "Untitled Episode"}
                  </p>
                  <span
                    className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[ep.status] || "bg-green-100 text-green-800"}`}
                  >
                    {ep.status}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {ep.target_duration_sec}s &middot; {new Date(ep.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div className="ml-3 flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => router.push(`/episodes/${ep.id}/scenes`)}
                >
                  Scenes
                </Button>
                <Button
                  size="sm"
                  onClick={() => router.push(getEpisodeLink(ep))}
                >
                  {getEpisodeAction(ep)}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Story Text */}
      <div className="mt-6 rounded-xl border bg-card p-6">
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {story.raw_text}
        </p>
      </div>

      {/* New Episode CTA */}
      <div className="mt-6 rounded-xl border bg-card p-6">
        <h2 className="font-semibold">
          {episodes.length > 0
            ? "Create another version?"
            : "Ready to bring this to life?"}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          AI will break your story into cinematic scenes with hooks, escalations, and a climax.
        </p>
        <div className="mt-4">
          <Button onClick={handleBreakdown} disabled={breaking}>
            {breaking ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Analyzing...
              </span>
            ) : episodes.length > 0 ? (
              "New Episode"
            ) : (
              "Break Down My Story"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
