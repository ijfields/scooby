"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

const MIN_CHARS = 100;
const MAX_CHARS = 5000;

export default function NewStoryPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const charCount = rawText.length;
  const isValid = title.trim().length > 0 && charCount >= MIN_CHARS && charCount <= MAX_CHARS;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;

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

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">New Story</h1>
      <p className="mt-2 text-muted-foreground">
        Paste or write your story below. We&apos;ll break it into scenes for you.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
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

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={!isValid || submitting}>
            {submitting ? "Saving..." : "Save & Continue"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
