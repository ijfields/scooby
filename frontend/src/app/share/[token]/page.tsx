"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ScenePlayer, type SceneWithAssets } from "@/components/scene-player";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Attribution {
  channel: string | null;
  video_title: string | null;
  youtube_url: string | null;
}

interface SharedPreview {
  title: string | null;
  target_duration_sec: number;
  scenes: SceneWithAssets[];
  attribution: Attribution | null;
}

export default function SharedPreviewPage() {
  const { token } = useParams<{ token: string }>();
  const [preview, setPreview] = useState<SharedPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/shared/${token}`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Preview not found");
        }
        const data: SharedPreview = await res.json();
        setPreview(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <SharedNav />
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-muted-foreground">Loading preview...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="flex min-h-screen flex-col">
        <SharedNav />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-3xl">
            ?
          </div>
          <h1 className="text-xl font-bold">Preview not found</h1>
          <p className="text-sm text-muted-foreground">
            {error || "This share link may have expired or been removed."}
          </p>
          <Link href="/">
            <Button>Go to Scooby</Button>
          </Link>
        </div>
      </div>
    );
  }

  const totalDuration = preview.scenes.reduce(
    (sum, s) => sum + (s.duration_sec || 0),
    0,
  );

  return (
    <div className="flex min-h-screen flex-col">
      <SharedNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-heading)" }}>
            {preview.title || "Untitled"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {preview.scenes.length} scenes &middot; {Math.round(totalDuration)}s
          </p>
        </div>

        {/* Attribution */}
        {preview.attribution && (
          <div className="mb-4 rounded-lg border bg-muted/50 p-3">
            <p className="text-sm text-muted-foreground">
              Based on{" "}
              <a
                href={preview.attribution.youtube_url ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-foreground underline underline-offset-2 hover:text-primary"
              >
                {preview.attribution.video_title || "original video"}
              </a>{" "}
              by{" "}
              <span className="font-medium text-foreground">
                {preview.attribution.channel || "Unknown Channel"}
              </span>
            </p>
          </div>
        )}

        {/* Player */}
        <ScenePlayer scenes={preview.scenes} title={preview.title} />

        {/* CTA */}
        <div className="mt-10 rounded-xl border bg-card p-6 text-center">
          <p className="font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
            Want to create your own?
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Turn any story into an AI-powered visual drama in minutes.
          </p>
          <div className="mt-4">
            <Link href="/stories/new">
              <Button>Start Your Story</Button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

function SharedNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="text-xl font-bold italic tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          scooby
        </Link>
        <Link href="/sign-up">
          <Button size="sm">Sign Up</Button>
        </Link>
      </div>
    </header>
  );
}
