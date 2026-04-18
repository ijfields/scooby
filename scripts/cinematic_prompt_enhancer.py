"""Transform Scooby's still-image scene descriptions into cinematic video-gen prompts.

Scooby's current visual_description prompts are optimized for image generation —
they describe what *is there* (subjects, attributes, lighting). Video models
need to know what *happens*: camera direction, motion, temporal arc.

This is the "Enhanced" preprocessor pattern from TopView Agent V2 (see
docs/research/Video Analysis - How to Create Long AI Videos with Topview Agent V2.md).
Adds three layers to each prompt:

  1. Camera direction  — what the camera does (push in, tracking, static hold)
  2. Motion verbs      — what moves in frame (breath, jaw, shadow, thumb)
  3. Temporal arc      — how the scene evolves across its duration

Usage:
    # Enhance a single prompt
    python scripts/cinematic_prompt_enhancer.py "Close-up of a man at a table, reading a letter"

    # Enhance every scene in a scenes.json manifest (from fetch_scooby_scene.py)
    python scripts/cinematic_prompt_enhancer.py --scenes-json \\
        test_generations/scooby_scenes/the-1-change-standoff/scenes.json

    # Same, but write back — adds video_description to each scene
    python scripts/cinematic_prompt_enhancer.py --scenes-json \\
        test_generations/scooby_scenes/the-1-change-standoff/scenes.json --write

Environment:
    ANTHROPIC_API_KEY must be set (loaded from .env by default).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic SDK not installed. Run: pip install anthropic")
    sys.exit(1)


# Current stable Sonnet (successor to backend's claude-sonnet-4-20250514).
# Prompt rewriting doesn't need Opus — this is a simple transformation.
DEFAULT_MODEL = "claude-sonnet-4-6"


# System prompt carries the full rubric plus 3 few-shot examples. At ~900
# tokens the prompt is under Sonnet 4.6's 2048-token cache minimum, so
# cache_control is a silent no-op for a single-run batch of 6-8 scenes —
# but it costs nothing and becomes meaningful if we later add more
# exemplars or a long scene-guideline appendix that pushes the prefix
# over 2K tokens.
SYSTEM_PROMPT = """You rewrite still-image scene descriptions into cinematic video-ready \
descriptions for AI video generation models (Kling, Seedance, Veo, Sora) used by Scooby \
— a serialized vertical drama platform.

Input scenes are 5–15 second 9:16 vertical clips driven by character emotion. Your \
rewrite preserves the subject, setting, and character details exactly and adds three \
layers:

1. CAMERA DIRECTION — what the camera physically does during the clip. Pick one primary
   movement per scene: slow push in, pull back, handheld drift, tracking shot, rack
   focus, static hold, tilt down, subtle dolly left/right.

2. MOTION VERBS — what moves IN frame during the clip. Be micro and specific:
   breath quickens, jaw tightens, hand trembles, light flickers, shadows lengthen,
   thumb hovers, eye twitches, dust floats, curtain stirs. Internal physical motion
   over broad dramatic action.

3. TEMPORAL ARC — how the scene evolves across its duration. One clear progression:
   warm-to-cool color shift, tension building to release, held silence breaking, slow
   realization dawning, resolve setting in, light fading.

Preserve the input's existing lighting, composition, and mood cues intact.

CONSTRAINTS

- Do not invent new characters, settings, or plot beats.
- Do not mention "9:16", "vertical", or aspect ratio — the downstream model already knows.
- Do not add preamble, labels, quotes, or commentary.
- Output ONLY the rewritten description — ready for direct injection into the
  video-gen prompt field.
- Length: roughly match the input or up to ~25% longer.

EXAMPLES

Input: Close-up of a tall, athletic blonde man's face illuminated by phone screen light \
in a dark room, his blue eyes intense and determined as he stares at his phone, finger \
hovering over the 'POST' button
Output: Extreme close-up, slow push in on the tall blonde man's face, lit only by the \
blue glow of his phone screen in a dark room. His jaw tightens; his breath quickens. \
The camera holds on his trembling finger hovering over 'POST'. Shallow depth of field, \
film grain. A subtle warm-to-cool color shift as resolve sets in. Tension held.

Input: Wide shot of modest living room with TV repairman in work clothes standing by \
wooden desk holding small television, customer Sam sitting on worn couch looking \
suspicious, afternoon light through window
Output: Static wide shot with a slow drift left. The repairman stands stiffly by the \
wooden desk, the small television cradled in his hands. On the worn couch, Sam watches — \
jaw set, eyes narrowing. Dust motes float in a slant of afternoon light through the \
window. Neither man moves. Handheld micro-tremor, 35mm film grain. The room holds its \
breath.

Input: Cliff standing alone in a dimly lit room, looking conflicted and troubled, with \
shadows casting across his face as he holds his phone, spiritual imagery like candles or \
crystals visible in the background
Output: Medium shot, slow push in on Cliff. Candlelight flickers across his face, \
shadows shifting as he turns the phone slowly in his hand. Behind him, crystals catch \
the amber flame. His thumb brushes the screen, hovers, pulls back. The color temperature \
drifts cooler as his expression hardens toward resolve. Silence but for the flame's \
faint rustle."""


def get_client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY in .env or the environment.")
        print("  .env.example has a placeholder; copy to .env and fill in your key.")
        sys.exit(1)
    return anthropic.Anthropic()


def enhance_prompt(client: anthropic.Anthropic, prompt: str, model: str) -> tuple[str, dict]:
    """Rewrite a single prompt cinematically. Returns (enhanced_text, usage_dict)."""
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": f"Input: {prompt}\nOutput:"}
        ],
    )

    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    # Some models prepend "Output:" even when we already did — strip if present.
    if text.lower().startswith("output:"):
        text = text[len("output:"):].lstrip()

    usage = {
        "input": resp.usage.input_tokens,
        "output": resp.usage.output_tokens,
        "cache_write": getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read": getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
    }
    return text, usage


def add_usage(total: dict, usage: dict) -> None:
    for k, v in usage.items():
        total[k] = total.get(k, 0) + v


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite Scooby scene descriptions into cinematic video-gen prompts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  %(prog)s "Close-up of a man reading a letter in dim light"\n'
            "  %(prog)s --scenes-json test_generations/scooby_scenes/foo/scenes.json\n"
            "  %(prog)s --scenes-json test_generations/scooby_scenes/foo/scenes.json --write"
        ),
    )
    parser.add_argument("prompt", nargs="?", help="Single prompt string to enhance")
    parser.add_argument(
        "--scenes-json",
        help="Path to a scenes.json manifest (output of fetch_scooby_scene.py)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write enhanced prompts back into the scenes.json as 'video_description'",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model ID (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    if not args.prompt and not args.scenes_json:
        parser.error("Provide either a prompt string or --scenes-json PATH")
    if args.write and not args.scenes_json:
        parser.error("--write requires --scenes-json")

    client = get_client()
    total_usage: dict = {}

    # --- single-prompt mode ---
    if args.prompt and not args.scenes_json:
        enhanced, usage = enhance_prompt(client, args.prompt, args.model)
        add_usage(total_usage, usage)
        print(enhanced)
        print(
            f"\n[tokens: in={usage['input']} out={usage['output']} "
            f"cache_read={usage['cache_read']}]",
            file=sys.stderr,
        )
        return

    # --- scenes.json mode ---
    with open(args.scenes_json, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes") or []
    if not scenes:
        print(f"ERROR: no scenes in {args.scenes_json}")
        sys.exit(1)

    print(f"Enhancing {len(scenes)} scenes from: {manifest.get('title', '?')!r}")
    print(f"Model: {args.model}")
    print()

    for scene in scenes:
        order = scene.get("scene_order", "?")
        beat = scene.get("beat_label", "?")
        original = scene.get("visual_description")
        if not original:
            print(f"[{order:02d}] {beat}  — skipping (no visual_description)")
            continue

        print(f"[{order:02d}] {beat}")
        print(f"  BEFORE: {original}")
        try:
            enhanced, usage = enhance_prompt(client, original, args.model)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        add_usage(total_usage, usage)
        print(f"  AFTER:  {enhanced}")
        print(
            f"  [tokens: in={usage['input']} out={usage['output']} "
            f"cache_read={usage['cache_read']}]"
        )
        print()

        if args.write:
            scene["video_description"] = enhanced

    if args.write:
        with open(args.scenes_json, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"✓ Updated {args.scenes_json} — each scene now has a video_description field")

    print()
    print("=" * 60)
    print(
        f"Total tokens: input={total_usage.get('input', 0)} "
        f"output={total_usage.get('output', 0)}"
    )
    print(
        f"  Cache creation: {total_usage.get('cache_write', 0)}  "
        f"Cache read: {total_usage.get('cache_read', 0)}"
    )
    if total_usage.get("cache_read", 0) == 0:
        print(
            f"  (note: system prompt is under {args.model}'s 2048-token cache minimum — "
            "expected no-op; pad with more exemplars to cross the threshold)"
        )


if __name__ == "__main__":
    main()
