import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Nav } from "@/components/nav";

function PenIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
    </svg>
  );
}

function LayoutIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect width="7" height="7" x="3" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="14" rx="1" />
      <rect width="7" height="7" x="3" y="14" rx="1" />
    </svg>
  );
}

function PlayIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polygon points="6 3 20 12 6 21 6 3" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    </svg>
  );
}

function PaletteIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
    </svg>
  );
}

function ZapIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" x2="12" y1="15" y2="3" />
    </svg>
  );
}

const steps = [
  {
    icon: PenIcon,
    title: "Write",
    description: "Paste or type your story. Any length, any genre.",
  },
  {
    icon: LayoutIcon,
    title: "Edit",
    description: "AI breaks your story into visual scenes you can refine.",
  },
  {
    icon: PlayIcon,
    title: "Share",
    description: "Choose a style, generate your video, and export.",
  },
];

const features = [
  {
    icon: SparklesIcon,
    title: "AI Scene Breakdown",
    description:
      "Your story is automatically split into cinematic beats — hook, setup, escalation, climax, and button.",
  },
  {
    icon: PaletteIcon,
    title: "Visual Style Presets",
    description:
      "Pick from curated looks — soft realistic, moody graphic novel, watercolor, cinematic dark — and matching voice & music.",
  },
  {
    icon: ZapIcon,
    title: "One-Click Video",
    description:
      "AI generates images, voiceover, and music. Remotion composites everything into a polished 9:16 vertical drama.",
  },
  {
    icon: DownloadIcon,
    title: "Instant Export",
    description:
      "Download your MP4 and share on TikTok, Reels, Shorts — or anywhere you want your story seen.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col flex-1">
      <Nav />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(109,40,217,0.12),transparent)]" />
          <div className="mx-auto flex max-w-3xl flex-col items-center px-4 pt-24 pb-20 text-center sm:px-6 sm:pt-32 sm:pb-28">
            <p className="mb-4 text-sm font-medium tracking-widest uppercase text-muted-foreground">
              Canva for stories
            </p>
            <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Your stories deserve
              <br />
              to be{" "}
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                seen
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Turn your raw story text into stunning 60-second vertical drama
              videos. Write it, watch AI break it into scenes, pick a style, and
              export — no production skills needed.
            </p>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row">
              <Link href="/stories/new">
                <Button size="lg" className="h-12 px-8 text-base">
                  Start Your Story
                </Button>
              </Link>
              <a href="#how-it-works">
                <Button variant="outline" size="lg" className="h-12 px-8 text-base">
                  See How It Works
                </Button>
              </a>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="border-t bg-muted/30 py-20 sm:py-24">
          <div className="mx-auto max-w-5xl px-4 sm:px-6">
            <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
              Three steps. One video.
            </h2>
            <p className="mt-3 text-center text-muted-foreground">
              From raw text to a finished vertical drama in minutes.
            </p>
            <div className="mt-14 grid gap-8 sm:grid-cols-3">
              {steps.map((step, i) => (
                <div
                  key={step.title}
                  className="flex flex-col items-center text-center"
                >
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                    <step.icon className="h-6 w-6" />
                  </div>
                  <div className="mt-2 flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
                    {i + 1}
                  </div>
                  <h3 className="mt-3 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 sm:py-24">
          <div className="mx-auto max-w-5xl px-4 sm:px-6">
            <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to bring stories to life
            </h2>
            <div className="mt-14 grid gap-6 sm:grid-cols-2">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-xl border bg-card p-6 transition-shadow hover:shadow-md"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Preview Experience */}
        <section className="border-t bg-muted/30 py-20 sm:py-24">
          <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              See it in action
            </h2>
            <p className="mt-3 text-muted-foreground">
              Each scene gets an AI-generated image and narrated voiceover.
              <br />
              Preview your story as an immersive slideshow before exporting.
            </p>
            <div className="mx-auto mt-10 flex max-w-xs flex-col items-center gap-6">
              <div className="relative aspect-[9/16] w-full overflow-hidden rounded-2xl border-2 border-border bg-gradient-to-b from-[oklch(0.2_0.05_292)] to-[oklch(0.12_0.03_292)] shadow-xl">
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6">
                  <div className="rounded-full bg-primary/20 p-4">
                    <PlayIcon className="h-10 w-10 text-primary" />
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-sm font-medium text-white/90">Scene-by-scene preview</p>
                    <p className="text-xs text-white/50">AI images + narrated audio + auto-advance</p>
                  </div>
                </div>
                {/* Fake scene dots */}
                <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-1.5">
                  <div className="h-1.5 w-5 rounded-full bg-accent" />
                  <div className="h-1.5 w-1.5 rounded-full bg-white/30" />
                  <div className="h-1.5 w-1.5 rounded-full bg-white/30" />
                  <div className="h-1.5 w-1.5 rounded-full bg-white/30" />
                  <div className="h-1.5 w-1.5 rounded-full bg-white/30" />
                </div>
              </div>
              <Link href="/stories/new">
                <Button size="lg" className="h-12 px-8 text-base">
                  Try It Now
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 sm:py-24">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Ready to turn your story into a video?
            </h2>
            <p className="mt-3 text-muted-foreground">
              No credit card. No production experience. Just your words.
            </p>
            <div className="mt-8">
              <Link href="/stories/new">
                <Button size="lg" className="h-12 px-8 text-base">
                  Start Your Story
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 text-center text-sm text-muted-foreground sm:flex-row sm:justify-between sm:px-6 sm:text-left">
          <p>Built for writers.</p>
          <p>&copy; {new Date().getFullYear()} Scooby. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
