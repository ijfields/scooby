"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface StylePreset {
  id: string;
  name: string;
  category: string;
  description: string | null;
}

interface Episode {
  id: string;
  title: string | null;
  visual_style_id: string | null;
  voice_style_id: string | null;
  music_style_id: string | null;
  target_duration_sec: number;
  generation_tier: string;
}

// Three distinct video-quality tiers (map to the backend's animation tiers).
const QUALITY_TIERS = [
  {
    value: "standard",
    label: "Storyboard",
    desc: "Still images with gentle motion (Ken Burns). Fastest and cheapest.",
    cost: "~$0.40 / episode",
  },
  {
    value: "movie_lite",
    label: "Movie Lite",
    desc: "Every scene animated into video (Kling Standard).",
    cost: "~$2.50–3.40 / episode",
  },
  {
    value: "movie_pro",
    label: "Movie Pro",
    desc: "Every scene animated in premium quality (Kling Pro).",
    cost: "~$3.40–4.50 / episode",
  },
] as const;

export default function StyleSelectionPage() {
  const { id: episodeId } = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [visualId, setVisualId] = useState<string | null>(null);
  const [voiceId, setVoiceId] = useState<string | null>(null);
  const [musicId, setMusicId] = useState<string | null>(null);
  const [duration, setDuration] = useState<60 | 90>(90);
  const [tier, setTier] = useState<string>("standard");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const token = await getToken();
        const [ep, styles] = await Promise.all([
          apiFetch<Episode>(`/api/v1/episodes/${episodeId}`, {
            token: token ?? undefined,
          }),
          apiFetch<StylePreset[]>("/api/v1/styles", {
            token: token ?? undefined,
          }),
        ]);
        setEpisode(ep);
        setPresets(styles);
        setVisualId(ep.visual_style_id);
        setVoiceId(ep.voice_style_id);
        setMusicId(ep.music_style_id);
        setDuration(ep.target_duration_sec === 60 ? 60 : 90);
        setTier(ep.generation_tier || "standard");
      } catch {
        router.push("/stories");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [episodeId, getToken, router]);

  const visualPresets = presets.filter((p) => p.category === "visual");
  const voicePresets = presets.filter((p) => p.category === "voice");
  const musicPresets = presets.filter((p) => p.category === "music");

  async function handleSave() {
    setSaving(true);
    try {
      const token = await getToken();
      await apiFetch(`/api/v1/episodes/${episodeId}`, {
        method: "PATCH",
        token: token ?? undefined,
        body: JSON.stringify({
          visual_style_id: visualId,
          voice_style_id: voiceId,
          music_style_id: musicId,
          target_duration_sec: duration,
          generation_tier: tier,
        }),
      });
      router.push(`/episodes/${episodeId}/generate`);
    } catch {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-muted-foreground">Loading styles...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold">Choose Your Style</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Select a visual look, narrator voice, and background music for your video.
      </p>

      {/* Duration Toggle */}
      <div className="mt-8">
        <h2 className="font-semibold">Duration</h2>
        <div className="mt-2 flex gap-2">
          {([60, 90] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDuration(d)}
              className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                duration === d
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card hover:bg-muted"
              }`}
            >
              {d} seconds
            </button>
          ))}
        </div>
      </div>

      {/* Video Quality / Tier */}
      <div className="mt-8">
        <h2 className="font-semibold">Video Quality</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Storyboard uses still images with motion. Movie tiers animate every
          scene into real video — higher quality, higher cost.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {QUALITY_TIERS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTier(t.value)}
              className={`rounded-xl border p-4 text-left transition-all ${
                tier === t.value
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <p className="font-medium">{t.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{t.desc}</p>
              <p className="mt-2 text-xs font-medium text-foreground">{t.cost}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Visual Style */}
      <div className="mt-8">
        <h2 className="font-semibold">Visual Style</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {visualPresets.map((p) => (
            <button
              key={p.id}
              onClick={() => setVisualId(p.id)}
              className={`rounded-xl border p-4 text-left transition-all ${
                visualId === p.id
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <p className="font-medium">{p.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {p.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Voice */}
      <div className="mt-8">
        <h2 className="font-semibold">Narrator Voice</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {voicePresets.map((p) => (
            <button
              key={p.id}
              onClick={() => setVoiceId(p.id)}
              className={`rounded-xl border p-4 text-left transition-all ${
                voiceId === p.id
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <p className="font-medium">{p.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {p.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Music */}
      <div className="mt-8">
        <h2 className="font-semibold">Background Music</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {musicPresets.map((p) => (
            <button
              key={p.id}
              onClick={() => setMusicId(p.id)}
              className={`rounded-xl border p-4 text-left transition-all ${
                musicId === p.id
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border hover:border-primary/50"
              }`}
            >
              <p className="font-medium">{p.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {p.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-10 flex gap-3">
        <Button
          onClick={handleSave}
          disabled={saving || !visualId || !voiceId || !musicId}
        >
          {saving ? "Saving..." : "Save & Generate Video"}
        </Button>
        <Button
          variant="outline"
          onClick={() => router.push(`/episodes/${episodeId}/scenes`)}
        >
          Back to Scenes
        </Button>
      </div>
    </div>
  );
}
