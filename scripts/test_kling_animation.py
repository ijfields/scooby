"""Test Kling 3.0 image-to-video via WaveSpeed API.

Usage:
    WAVESPEED_API_KEY=your-key python scripts/test_kling_animation.py

Requires a publicly accessible image URL as input.
Outputs saved to: test_generations/kling/
"""

from __future__ import annotations

import os
import sys
import time

import requests

api_key = os.environ.get("WAVESPEED_API_KEY")
if not api_key:
    print("ERROR: Set WAVESPEED_API_KEY environment variable")
    print("  Sign up at: https://wavespeed.ai/")
    sys.exit(1)

BASE_URL = "https://api.wavespeed.ai/api/v3"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}

# Animation test configurations
TEST_ANIMATIONS = [
    {
        "name": "slow_zoom_5s",
        "prompt": "Slow cinematic zoom in, warm light flickering, atmospheric dust particles floating",
        "duration": 5,
        "model": "kling-v3.0-std",
    },
    {
        "name": "pan_left_5s",
        "prompt": "Gentle camera pan left to right, subtle motion in background elements, soft ambient lighting",
        "duration": 5,
        "model": "kling-v3.0-std",
    },
    {
        "name": "dramatic_push_8s",
        "prompt": "Dramatic push in toward subject, lighting shifts from warm to cool, atmospheric tension builds",
        "duration": 8,
        "model": "kling-v3.0-std",
    },
]

output_dir = os.path.join("test_generations", "kling")
os.makedirs(output_dir, exist_ok=True)

print("Kling 3.0 Image-to-Video Test (via WaveSpeed)")
print("=" * 50)
print()

# Get image URL
image_url = input("Enter public URL of a test scene image: ").strip()
if not image_url:
    print("ERROR: Image URL required. Generate one with test_nanobanana2.py first,")
    print("  then upload to a public host or use your Scooby backend asset URL.")
    sys.exit(1)

print(f"\nImage: {image_url}")
print(f"Output: {output_dir}/")
print(f"Animations: {len(TEST_ANIMATIONS)}")
print()


def submit_task(anim: dict) -> str | None:
    """Submit an animation task, return request ID."""
    resp = requests.post(
        f"{BASE_URL}/kwaivgi/{anim['model']}/image-to-video",
        headers=HEADERS,
        json={
            "image": image_url,
            "prompt": anim["prompt"],
            "duration": anim["duration"],
            "cfg_scale": 0.5,
            "shot_type": "customize",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def poll_result(request_id: str, max_wait: int = 600) -> dict:
    """Poll for task completion. Returns result dict."""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        result = requests.get(
            f"{BASE_URL}/predictions/{request_id}/result",
            headers=HEADERS,
            timeout=30,
        )
        data = result.json().get("data", {})
        status = data.get("status", "unknown")

        if elapsed % 30 == 0 or status in ("completed", "failed"):
            print(f"    [{elapsed}s] {status}")

        if status == "completed":
            return {"status": "ok", "url": data["outputs"][0], "time": elapsed}
        elif status == "failed":
            return {"status": "failed", "error": str(data), "time": elapsed}

    return {"status": "timeout", "time": elapsed}


results = []
for i, anim in enumerate(TEST_ANIMATIONS):
    print(f"[{i + 1}/{len(TEST_ANIMATIONS)}] {anim['name']} ({anim['duration']}s, {anim['model']})")
    print(f"  Prompt: {anim['prompt'][:70]}...")

    try:
        request_id = submit_task(anim)
        print(f"  Task ID: {request_id}")
        print(f"  Polling (this takes 2-6 minutes)...")

        result = poll_result(request_id)

        if result["status"] == "ok":
            # Download the video
            video_resp = requests.get(result["url"], timeout=120)
            path = os.path.join(output_dir, f"{anim['name']}_{anim['duration']}s.mp4")
            with open(path, "wb") as f:
                f.write(video_resp.content)
            file_size = os.path.getsize(path)
            print(f"  Saved: {path} ({file_size / 1024:.0f} KB, {result['time']}s)")
            results.append({"name": anim["name"], "status": "ok", "time": result["time"], "size": file_size})
        else:
            print(f"  {result['status'].upper()}: {result.get('error', 'unknown')} ({result['time']}s)")
            results.append({"name": anim["name"], "status": result["status"], "time": result["time"]})

    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"name": anim["name"], "status": "error", "error": str(e)})

    print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
ok = [r for r in results if r["status"] == "ok"]
print(f"  Generated: {len(ok)}/{len(TEST_ANIMATIONS)}")
if ok:
    avg_time = sum(r["time"] for r in ok) / len(ok)
    avg_size = sum(r["size"] for r in ok) / len(ok)
    print(f"  Avg generation time: {avg_time:.0f}s")
    print(f"  Avg file size: {avg_size / 1024 / 1024:.1f} MB")
print(f"  Output dir: {output_dir}/")
failed = [r for r in results if r["status"] != "ok"]
if failed:
    print(f"  Failed: {', '.join(r['name'] for r in failed)}")
print()
print("Review the .mp4 files to evaluate animation quality.")
