"""TopView Seedance 1.5 Pro text-to-video eval for Joyce's "Heart for Fun" episode.

Goal: see whether prompt-to-video (skipping the image-gen step) can produce
visually consistent characters across all 6 scenes when each scene's
visual_description is augmented with a shared character bible.

Strategy: hand-curated character bible (extracted from the story) is prepended
to every scene's visual_description. Character bibles are how Sora/Veo/Kling-
class models maintain identity across independent t2v generations — they don't
have actual cross-call state, so consistency comes from repeated description.

Episode: ab8bf1d4-cac4-47bd-bcb6-68e38144a6d0 ("The Heart for Fun")
Story:   "Finding joy in a simple walk" — Joyce Harris, 2026-04-26

Usage:
    TOPVIEW_API_KEY=... TOPVIEW_UID=... \
        python scripts/eval_topview_joyce_heart.py [--dry-run] [--scene N]

    --dry-run   Print augmented prompts only, don't call the API.
    --scene N   Generate only scene N (1-6) instead of all six.

Output: test_generations/joyce_heart_topview/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Character bible ────────────────────────────────────────────────────────
# Hand-curated from Joyce's "Finding joy in a simple walk" story. Prepended to
# every scene prompt to anchor character appearance across independent t2v
# generations. Keep it tight — verbose bibles dilute the scene-specific
# direction and exhaust prompt tokens.

CHARACTER_BIBLE = (
    "CHARACTERS (consistent across all scenes):\n"
    "- JOYCE: middle-aged Black woman, warm expressive face, wearing a "
    "comfortable casual outfit (dark cardigan, jeans, sturdy sneakers). "
    "Walks with two forearm crutches due to mobility challenges. "
    "Calm and observant demeanor.\n"
    "- REBECCA: middle-aged white woman, friend of Joyce, casual neighborhood "
    "wear, helpful and warm energy.\n"
    "- SCHOOL KIDS: roughly 6-9 years old, mixed group of boys and girls, "
    "playing behind a chain-link fence at a small Christian elementary "
    "school playground.\n"
    "STYLE: photorealistic, cinematic, warm afternoon light, suburban "
    "neighborhood street setting, vertical 9:16 portrait composition, "
    "shallow depth of field, gentle camera movement.\n\n"
    "SCENE:\n"
)

# ─── Scenes (frozen from production DB ab8bf1d4 on 2026-04-27) ──────────────

SCENES = [
    {
        "n": 1, "beat": "hook", "duration": 5,
        "visual": "Close-up of worn walking sticks (forearm crutches) being "
                 "gently placed on cracked asphalt, with children's laughter "
                 "echoing in the background. Soft afternoon sunlight creates "
                 "long shadows.",
        "narration": "Today I chose to just be.",
    },
    {
        "n": 2, "beat": "setup", "duration": 12,
        "visual": "Medium shot of Joyce looking toward a colorful playground "
                 "where children are playing. A bright red ball sits abandoned "
                 "against the street curb in the foreground.",
        "narration": "Instead of the gym, I took a walk. The school kids were "
                     "playing when their ball rolled into the street.",
    },
    {
        "n": 3, "beat": "escalation_1", "duration": 15,
        "visual": "Wide shot showing a young girl at the chain-link fence "
                 "pointing desperately toward the street, her face filled with "
                 "hope, while another colorful ball bounces into the road "
                 "behind the first red one.",
        "narration": "Could you get our ball? she called out. But as I "
                     "hobbled toward it, another ball flew into the street.",
    },
    {
        "n": 4, "beat": "escalation_2", "duration": 13,
        "visual": "Over-the-shoulder shot of Joyce calling out to Rebecca, "
                 "who is getting into her car in the distance. Joyce's arm "
                 "is raised in greeting. Two colorful balls visible on the "
                 "asphalt between them.",
        "narration": "Rebecca! I spotted my friend by her car. Can you help "
                     "me get the other ball? I called to her.",
    },
    {
        "n": 5, "beat": "climax", "duration": 18,
        "visual": "Heartwarming medium shot of Joyce and Rebecca working "
                 "together, throwing colorful playground balls over the "
                 "chain-link fence to eager children reaching through the "
                 "gaps. Golden hour lighting creates a warm glow.",
        "narration": "She quickly joined me. Together we threw both balls "
                     "back over the fence. The children cheered and "
                     "thanked us.",
    },
    {
        "n": 6, "beat": "button", "duration": 12,
        "visual": "Close-up of Joyce's hands clapping together with joy, "
                 "slightly weathered but full of life, with blurred "
                 "playground happiness in the soft-focus background.",
        "narration": "I clapped and remembered — I still have the heart "
                     "for fun.",
    },
]

MODEL_CONFIG = {
    "name": "seedance_1.5_pro",
    "model": "Seedance 1.5 pro",
    "aspectRatio": "9:16",
    "resolution": 720,
    "duration": 5,  # Seedance native; we'll repeat or trim during compose
    "sound": "off",  # we have ElevenLabs VO already; no need for native audio
}


def build_augmented_prompt(scene: dict) -> str:
    return CHARACTER_BIBLE + scene["visual"]


BASE_URL = "https://api.topview.ai"


def submit_task(prompt: str, api_key: str, uid: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Topview-Uid": uid}
    body = {
        "model": MODEL_CONFIG["model"],
        "prompt": prompt,
        "aspectRatio": MODEL_CONFIG["aspectRatio"],
        "resolution": MODEL_CONFIG["resolution"],
        "duration": MODEL_CONFIG["duration"],
        "sound": MODEL_CONFIG["sound"],
        "generatingCount": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/v1/common_task/text2video/task/submit",
        json=body, headers=headers, timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "200":
        raise RuntimeError(f"Submit failed: {data.get('message')} — {data}")
    return data["result"]["taskId"]


def poll_task(task_id: str, api_key: str, uid: str, max_wait: int = 900) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Topview-Uid": uid}
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        resp = requests.get(
            f"{BASE_URL}/v1/common_task/text2video/task/query",
            headers=headers, params={"taskId": task_id}, timeout=30,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        status = result.get("status", "unknown")
        if elapsed % 30 == 0 or status in ("success", "fail"):
            print(f"    [{elapsed}s] {status} (credit: {result.get('costCredit', '?')})")
        if status == "success":
            videos = result.get("videos") or []
            if not videos:
                raise RuntimeError(f"No video in successful result: {result}")
            return {
                "url": videos[0]["filePath"],
                "width": videos[0].get("width"),
                "height": videos[0].get("height"),
                "duration_ms": videos[0].get("duration"),
                "credit": result.get("costCredit"),
                "elapsed": elapsed,
            }
        if status == "fail":
            raise RuntimeError(f"Task failed: {result.get('errorMsg', 'unknown')}")
    raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")


def download_video(url: str, dest: Path) -> int:
    resp = requests.get(url, stream=True, timeout=180)
    resp.raise_for_status()
    total = 0
    with dest.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            f.write(chunk)
            total += len(chunk)
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="print prompts only, don't call API")
    parser.add_argument("--scene", type=int,
                        help="generate only scene N (1-6)")
    args = parser.parse_args()

    out_dir = Path("test_generations/joyce_heart_topview")
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = SCENES if args.scene is None else [s for s in SCENES if s["n"] == args.scene]

    print(f"Joyce's 'Heart for Fun' — TopView Seedance 1.5 Pro eval")
    print(f"Scenes: {len(targets)} | Output: {out_dir}/\n")

    if args.dry_run:
        for s in targets:
            print(f"=== Scene {s['n']} ({s['beat']}, {s['duration']}s) ===")
            print(build_augmented_prompt(s))
            print()
        return 0

    api_key = os.environ.get("TOPVIEW_API_KEY")
    uid = os.environ.get("TOPVIEW_UID")
    if not api_key or not uid:
        print("ERROR: TOPVIEW_API_KEY and TOPVIEW_UID required")
        return 1

    manifest = []
    for s in targets:
        prompt = build_augmented_prompt(s)
        print(f"--- Scene {s['n']} ({s['beat']}) ---")
        print(f"  prompt length: {len(prompt)} chars")

        try:
            task_id = submit_task(prompt, api_key, uid)
            print(f"  taskId: {task_id}")
            print(f"  Polling (typically 1-5 minutes)...")
            r = poll_task(task_id, api_key, uid)
            dest = out_dir / f"scene_{s['n']}_{s['beat']}.mp4"
            size = download_video(r["url"], dest)
            dims = f"{r.get('width')}x{r.get('height')}" if r.get("width") else "?"
            print(f"  saved {dest} ({size:,} bytes, {dims}, "
                  f"{r['elapsed']}s, credit={r.get('credit')})")
            manifest.append({
                "scene": s["n"], "beat": s["beat"], "task_id": task_id,
                "file": dest.name, "size": size, "dims": dims,
                "credit": r.get("credit"), "elapsed_s": r["elapsed"],
                "prompt": prompt,
            })
        except Exception as ex:
            print(f"  FAILED: {type(ex).__name__}: {ex}")
            manifest.append({
                "scene": s["n"], "beat": s["beat"], "error": str(ex),
                "prompt": prompt,
            })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {out_dir / 'manifest.json'}")
    print(f"Successful: {sum(1 for m in manifest if 'file' in m)}/{len(manifest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
