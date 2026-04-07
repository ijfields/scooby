"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Story {
  id: string;
  title: string;
  word_count: number;
  status: string;
  source_type: string;
  created_at: string;
}

export default function StoriesPage() {
  const { getToken } = useAuth();
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        const data = await apiFetch<{ stories: Story[]; total: number }>(
          "/api/v1/stories",
          { token: token ?? undefined },
        );
        setStories(data.stories);
      } catch {
        // User may not be synced yet — that's OK, show empty state
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getToken]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-muted-foreground">Loading stories...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Stories</h1>
        <Link href="/stories/new">
          <Button>New Story</Button>
        </Link>
      </div>

      {stories.length === 0 ? (
        <div className="mt-16 flex flex-col items-center gap-4 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-8 w-8">
              <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
            </svg>
          </div>
          <div>
            <p className="text-lg font-medium">No stories yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Write your first story and watch it come to life with AI.
            </p>
          </div>
          <Link href="/stories/new">
            <Button size="lg">Start Your First Story</Button>
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-4">
          {stories.map((story) => (
            <Link
              key={story.id}
              href={`/stories/${story.id}`}
              className="block rounded-xl border bg-card p-5 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-semibold">{story.title}</h2>
                    {story.source_type === "youtube" && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                        YouTube Series
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {story.word_count} words &middot;{" "}
                    {new Date(story.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium capitalize text-muted-foreground">
                  {story.status.replace(/_/g, " ")}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
