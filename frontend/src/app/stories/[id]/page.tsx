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

export default function StoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(true);
  const [breaking, setBreaking] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        const data = await apiFetch<Story>(`/api/v1/stories/${id}`, {
          token: token ?? undefined,
        });
        setStory(data);
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
        <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium capitalize text-muted-foreground">
          {story.status}
        </span>
      </div>

      <div className="mt-6 rounded-xl border bg-card p-6">
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {story.raw_text}
        </p>
      </div>

      <div className="mt-8 flex gap-3">
        <Button onClick={handleBreakdown} disabled={breaking}>
          {breaking ? "Breaking down..." : "Break Down My Story"}
        </Button>
        <Button variant="outline" onClick={() => router.push("/stories")}>
          Back to Stories
        </Button>
      </div>
    </div>
  );
}
