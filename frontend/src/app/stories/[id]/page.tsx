"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Story {
  id: string;
  title: string;
  raw_text: string;
  word_count: number;
  status: string;
  source_type: string;
  source_url: string | null;
  source_meta: Record<string, unknown> | null;
  created_at: string;
}

interface Episode {
  id: string;
  title: string | null;
  status: string;
  target_duration_sec: number;
  episode_number: number | null;
  series_angle: string | null;
  created_at: string;
  updated_at: string;
}

interface EpisodePlan {
  episode_number: number;
  title: string;
  angle: string;
  key_content: string;
  target_duration_sec: number;
  hook_suggestion: string;
}

interface SeriesPlan {
  series_title: string;
  series_thesis: string;
  total_episodes: number;
  episodes: EpisodePlan[];
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  processing: "bg-amber-100 text-amber-800",
  generating: "bg-blue-100 text-blue-800",
  importing: "bg-blue-100 text-blue-800",
  planning: "bg-blue-100 text-blue-800",
  plan_ready: "bg-green-100 text-green-800",
  plan_failed: "bg-red-100 text-red-800",
  import_failed: "bg-red-100 text-red-800",
};

export default function StoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const [story, setStory] = useState<Story | null>(null);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [breaking, setBreaking] = useState(false);
  const [approving, setApproving] = useState(false);
  const [removedEpisodes, setRemovedEpisodes] = useState<Set<number>>(new Set());

  const loadData = useCallback(async () => {
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
  }, [id, getToken, router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for status updates on importing/planning stories
  useEffect(() => {
    if (!story) return;
    const pollingStatuses = ["importing", "planning", "processing"];
    if (!pollingStatuses.includes(story.status)) return;

    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [story?.status, loadData]);

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

  async function handleApproveSeries() {
    if (!story) return;
    setApproving(true);
    try {
      const token = await getToken();

      const edits = removedEpisodes.size > 0
        ? Array.from(removedEpisodes).map((num) => ({
            episode_number: num,
            remove: true,
          }))
        : undefined;

      await apiFetch(`/api/v1/youtube/${story.id}/approve`, {
        method: "POST",
        token: token ?? undefined,
        body: JSON.stringify({ episodes: edits || null }),
      });

      // Reload to show processing state
      await loadData();
    } catch {
      // error handled
    } finally {
      setApproving(false);
    }
  }

  function toggleRemoveEpisode(num: number) {
    setRemovedEpisodes((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num);
      else next.add(num);
      return next;
    });
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

  const isYouTube = story.source_type === "youtube";
  const seriesPlan = story.source_meta?.series_plan as SeriesPlan | undefined;
  const sourceMeta = story.source_meta as Record<string, string> | null;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{story.title}</h1>
            {isYouTube && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                YouTube
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {story.word_count} words &middot;{" "}
            {new Date(story.created_at).toLocaleDateString()}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push("/stories")}>
          My Stories
        </Button>
      </div>

      {/* Attribution for YouTube sources */}
      {isYouTube && sourceMeta && (
        <div className="mt-4 rounded-lg border bg-muted/50 p-4">
          <p className="text-sm">
            Based on{" "}
            <a
              href={story.source_url ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
            >
              {(sourceMeta.video_title as string) || story.title}
            </a>{" "}
            by{" "}
            <span className="font-medium">
              {(sourceMeta.channel as string) || "Unknown Channel"}
            </span>
          </p>
        </div>
      )}

      {/* YouTube Import Status: Importing/Planning */}
      {isYouTube && ["importing", "planning"].includes(story.status) && (
        <div className="mt-6 rounded-xl border bg-card p-8 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 font-medium">
            {story.status === "importing"
              ? "Fetching transcript from YouTube..."
              : "AI is planning your series..."}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            This typically takes 30-60 seconds.
          </p>
        </div>
      )}

      {/* YouTube Import Failed */}
      {isYouTube && ["import_failed", "plan_failed"].includes(story.status) && (
        <div className="mt-6 rounded-xl border border-destructive/50 bg-destructive/5 p-6">
          <p className="font-medium text-destructive">
            {story.status === "import_failed"
              ? "Failed to import transcript"
              : "Failed to plan series"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {(sourceMeta?.error as string) || "An unexpected error occurred."}
          </p>
        </div>
      )}

      {/* Series Plan Review */}
      {isYouTube && story.status === "plan_ready" && seriesPlan && (
        <div className="mt-6 space-y-4">
          <div className="rounded-xl border bg-card p-6">
            <h2 className="text-lg font-semibold">{seriesPlan.series_title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {seriesPlan.series_thesis}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {seriesPlan.total_episodes} episodes planned &middot; Review and
              approve below
            </p>
          </div>

          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Episode Plan
          </h3>

          {seriesPlan.episodes.map((ep) => {
            const isRemoved = removedEpisodes.has(ep.episode_number);
            return (
              <div
                key={ep.episode_number}
                className={`rounded-xl border bg-card p-5 transition-opacity ${
                  isRemoved ? "opacity-40" : ""
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="flex-shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        Ep. {ep.episode_number}
                      </span>
                      <h4 className="font-medium truncate">{ep.title}</h4>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {ep.angle}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {ep.target_duration_sec}s &middot; Hook: &ldquo;{ep.hook_suggestion}&rdquo;
                    </p>
                  </div>
                  <button
                    onClick={() => toggleRemoveEpisode(ep.episode_number)}
                    className={`ml-3 flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      isRemoved
                        ? "bg-muted text-muted-foreground hover:bg-accent"
                        : "bg-destructive/10 text-destructive hover:bg-destructive/20"
                    }`}
                  >
                    {isRemoved ? "Restore" : "Remove"}
                  </button>
                </div>
              </div>
            );
          })}

          <div className="flex gap-3 pt-2">
            <Button
              onClick={handleApproveSeries}
              disabled={
                approving ||
                removedEpisodes.size === seriesPlan.episodes.length
              }
            >
              {approving ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  Approving...
                </span>
              ) : (
                `Approve & Generate ${seriesPlan.episodes.length - removedEpisodes.size} Episodes`
              )}
            </Button>
          </div>
        </div>
      )}

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
                  {ep.episode_number && (
                    <span className="flex-shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                      Ep. {ep.episode_number}
                    </span>
                  )}
                  <p className="font-medium truncate">
                    {ep.title || "Untitled Episode"}
                  </p>
                  <span
                    className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[ep.status] || "bg-green-100 text-green-800"}`}
                  >
                    {ep.status.replace(/_/g, " ")}
                  </span>
                </div>
                {ep.series_angle && (
                  <p className="mt-0.5 text-xs text-muted-foreground truncate">
                    {ep.series_angle}
                  </p>
                )}
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

      {/* Story Text — only show for original stories or after transcript is loaded */}
      {(!isYouTube || story.word_count > 0) && story.status !== "importing" && (
        <details className="mt-6">
          <summary className="cursor-pointer rounded-xl border bg-card p-4 font-medium hover:bg-accent/50">
            {isYouTube ? "View Transcript" : "View Story Text"} ({story.word_count} words)
          </summary>
          <div className="mt-2 rounded-xl border bg-card p-6">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {story.raw_text}
            </p>
          </div>
        </details>
      )}

      {/* New Episode CTA — only for original stories */}
      {!isYouTube && (
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
      )}
    </div>
  );
}
