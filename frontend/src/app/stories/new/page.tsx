"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

const MIN_CHARS = 100;
const MAX_CHARS = 5000;

type Tab = "write" | "youtube";

export default function NewStoryPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("write");

  // Write a Story state
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");

  // YouTube Import state
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [relationship, setRelationship] = useState<string>("");
  const [fairUseAcknowledged, setFairUseAcknowledged] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const charCount = rawText.length;
  const isWriteValid =
    title.trim().length > 0 && charCount >= MIN_CHARS && charCount <= MAX_CHARS;
  const isYoutubeValid =
    youtubeUrl.match(/youtube\.com|youtu\.be/) &&
    relationship !== "" &&
    fairUseAcknowledged;

  async function handleWriteSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isWriteValid) return;

    setSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      const story = await apiFetch<{ id: string }>("/api/v1/stories", {
        method: "POST",
        token: token ?? undefined,
        body: JSON.stringify({ title: title.trim(), raw_text: rawText }),
      });
      router.push(`/stories/${story.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleYoutubeSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isYoutubeValid) return;

    setSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      const story = await apiFetch<{ id: string }>("/api/v1/youtube/import", {
        method: "POST",
        token: token ?? undefined,
        body: JSON.stringify({
          youtube_url: youtubeUrl.trim(),
          relationship,
          fair_use_acknowledged: fairUseAcknowledged,
        }),
      });
      router.push(`/stories/${story.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Create New Content</h1>
      <p className="mt-2 text-muted-foreground">
        Write an original story or import from YouTube to create a visual series.
      </p>

      {/* Tab Switcher */}
      <div className="mt-6 flex rounded-lg border bg-muted p-1">
        <button
          onClick={() => { setActiveTab("write"); setError(null); }}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "write"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Write a Story
        </button>
        <button
          onClick={() => { setActiveTab("youtube"); setError(null); }}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "youtube"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Import from YouTube
        </button>
      </div>

      {/* Write a Story Tab */}
      {activeTab === "write" && (
        <form onSubmit={handleWriteSubmit} className="mt-6 space-y-6">
          <div>
            <label htmlFor="title" className="text-sm font-medium">
              Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Give your story a title..."
              maxLength={200}
              className="mt-1.5 block w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
          </div>

          <div>
            <label htmlFor="raw-text" className="text-sm font-medium">
              Story Text
            </label>
            <textarea
              id="raw-text"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="She sat at the kitchen table, staring at the envelope..."
              rows={12}
              maxLength={MAX_CHARS}
              className="mt-1.5 block w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm leading-relaxed outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
            <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
              <span>
                {charCount < MIN_CHARS
                  ? `${MIN_CHARS - charCount} more characters needed`
                  : `${charCount.toLocaleString()} / ${MAX_CHARS.toLocaleString()} characters`}
              </span>
              <span>{rawText.split(/\s+/).filter(Boolean).length} words</span>
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3">
            <Button type="submit" disabled={!isWriteValid || submitting}>
              {submitting ? "Saving..." : "Save & Continue"}
            </Button>
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {/* Import from YouTube Tab */}
      {activeTab === "youtube" && (
        <form onSubmit={handleYoutubeSubmit} className="mt-6 space-y-6">
          <div>
            <label htmlFor="youtube-url" className="text-sm font-medium">
              YouTube URL
            </label>
            <input
              id="youtube-url"
              type="url"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="mt-1.5 block w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              AI will fetch the transcript and plan a series of 3-8 visual story episodes.
            </p>
          </div>

          <div>
            <label className="text-sm font-medium">
              Your relationship to this content
            </label>
            <div className="mt-2 space-y-2">
              {[
                { value: "creator", label: "I created this video" },
                { value: "permission", label: "I have permission from the creator" },
                { value: "fair_use", label: "Fair use (commentary, education, criticism)" },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                    relationship === opt.value
                      ? "border-ring bg-accent"
                      : "hover:bg-accent/50"
                  }`}
                >
                  <input
                    type="radio"
                    name="relationship"
                    value={opt.value}
                    checked={relationship === opt.value}
                    onChange={(e) => setRelationship(e.target.value)}
                    className="accent-primary"
                  />
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-start gap-3 rounded-lg border p-4 bg-muted/50">
            <input
              type="checkbox"
              checked={fairUseAcknowledged}
              onChange={(e) => setFairUseAcknowledged(e.target.checked)}
              className="mt-0.5 accent-primary"
            />
            <span className="text-sm text-muted-foreground">
              I confirm that I am the creator of this content, have permission from the
              creator, or my use qualifies as fair use (commentary, education, criticism).
              Generated episodes will include attribution to the original creator.
            </span>
          </label>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3">
            <Button type="submit" disabled={!isYoutubeValid || submitting}>
              {submitting ? "Importing..." : "Import & Plan Series"}
            </Button>
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
