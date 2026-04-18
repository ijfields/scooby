"""Test TopView AI text-to-video for Scooby scenes (9:16 vertical drama).

Evaluates whether TopView's Text2Video can skip the image generation step
entirely — feeding Scooby's existing scene prompts directly into video gen.

Use this side-by-side with test_topview_image2video.py to compare:
  - image → animate (current Scooby flow, preserves preview UX)
  - prompt → video  (one-shot, cheaper but no scene review stage)

Usage:
    TOPVIEW_API_KEY=your-key TOPVIEW_UID=your-uid \
        python scripts/test_topview_text2video.py [--model NAME]

    --model NAME  Run only the named model (veo_3.1_fast, sora_2_pro, kling_v3).
                  Default: run all three.

Outputs saved to: test_generations/topview_t2v/
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _topview_results import log_result  # noqa: E402

api_key = os.environ.get("TOPVIEW_API_KEY")
uid = os.environ.get("TOPVIEW_UID")
if not api_key or not uid:
    print("ERROR: Set TOPVIEW_API_KEY and TOPVIEW_UID environment variables")
    print("  Get them at: https://www.topview.ai/dashboard/api-settings")
    sys.exit(1)

parser = argparse.ArgumentParser(description="TopView text-to-video eval for Scooby")
parser.add_argument("--model", help="Run only the named model (e.g. veo_3.1_fast, sora_2_pro, kling_v3)")
args = parser.parse_args()

BASE_URL = "https://api.topview.ai"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Topview-Uid": uid,
}

# Real Scooby scene prompt — same one used in test_nanobanana2.py for apples-to-apples
# comparison. If image2video + this prompt produce similar results, text2video wins on
# cost; if image2video looks meaningfully better, the image stage is earning its keep.
SCENE_PROMPT = (
    "A dimly lit apartment kitchen at night. A woman in her 30s sits at a cluttered "
    "table, staring at a handwritten letter. Warm amber light from a single hanging "
    "bulb. Cinematic mood, shallow depth of field, slow push in, film grain. "
    "Vertical 9:16 portrait composition."
)

# Mirror the model set from test_topview_image2video.py for direct comparison.
TEST_MODELS = [
    {
        "name": "veo_3.1_fast",
        "model": "Veo 3.1 Fast",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 8,
        "sound": "on",
    },
    {
        "name": "sora_2_pro",
        "model": "Sora 2 Pro",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 8,
        "sound": "off",
    },
    {
        "name": "kling_v3",
        "model": "Kling V3",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 5,
        "sound": "on",
    },
    {
        "name": "seedance_1.5_pro",
        "model": "Seedance 1.5 pro",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 8,
        "sound": "on",  # native audio available on 1.5 pro
    },
]

if args.model:
    matching = [m for m in TEST_MODELS if m["name"] == args.model]
    if not matching:
        valid = ", ".join(m["name"] for m in TEST_MODELS)
        print(f"ERROR: Unknown model '{args.model}'. Valid: {valid}")
        sys.exit(1)
    TEST_MODELS = matching

output_dir = os.path.join("test_generations", "topview_t2v")
os.makedirs(output_dir, exist_ok=True)

print("TopView AI Text-to-Video Test (Scooby 9:16 drama eval)")
print("=" * 60)
print(f"Prompt: {SCENE_PROMPT[:100]}...")
print(f"Output: {output_dir}/")
print(f"Models: {len(TEST_MODELS)} ({', '.join(m['name'] for m in TEST_MODELS)})")
print()


def submit_task(config: dict) -> str:
    """Submit text2video task. Returns taskId."""
    body = {
        "model": config["model"],
        "prompt": SCENE_PROMPT,
        "aspectRatio": config["aspectRatio"],
        "resolution": config["resolution"],
        "duration": config["duration"],
        "sound": config["sound"],
        "generatingCount": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/v1/common_task/text2video/task/submit",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "200":
        raise RuntimeError(f"Submit failed: {data.get('message')} — {data}")
    return data["result"]["taskId"]


def poll_result(task_id: str, max_wait: int = 900) -> dict:
    """Poll for task completion. Returns result dict with video URL on success."""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        resp = requests.get(
            f"{BASE_URL}/v1/common_task/text2video/task/query",
            headers=HEADERS,
            params={"taskId": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        status = result.get("status", "unknown")

        if elapsed % 30 == 0 or status in ("success", "fail"):
            print(f"    [{elapsed}s] {status} (credit: {result.get('costCredit', '?')})")

        if status == "success":
            videos = result.get("videos") or []
            if not videos:
                return {"status": "no_video", "time": elapsed, "raw": result}
            v = videos[0]
            return {
                "status": "ok",
                "url": v["filePath"],
                "width": v.get("width"),
                "height": v.get("height"),
                "duration_ms": v.get("duration"),
                "credit": result.get("costCredit"),
                "time": elapsed,
            }
        if status == "fail":
            return {"status": "failed", "error": result.get("errorMsg"), "time": elapsed}

    return {"status": "timeout", "time": elapsed}


results = []
for i, config in enumerate(TEST_MODELS):
    print(f"[{i + 1}/{len(TEST_MODELS)}] {config['name']} — {config['model']} "
          f"({config['duration']}s, {config['resolution']}p, sound={config['sound']})")

    task_id = ""
    try:
        task_id = submit_task(config)
        print(f"  Task ID: {task_id}")
        print(f"  Polling (typically 1-5 minutes)...")

        result = poll_result(task_id)

        if result["status"] == "ok":
            video_resp = requests.get(result["url"], timeout=180)
            video_resp.raise_for_status()
            path = os.path.join(output_dir, f"{config['name']}_{config['duration']}s.mp4")
            with open(path, "wb") as f:
                f.write(video_resp.content)
            file_size = os.path.getsize(path)
            dims = f"{result['width']}x{result['height']}" if result.get("width") else "?"
            print(f"  Saved: {path} ({file_size / 1024:.0f} KB, {dims}, "
                  f"{result['time']}s, credit={result['credit']})")
            log_result({
                "kind": "t2v",
                "model_name": config["name"],
                "model_display": config["model"],
                "duration_s": config["duration"],
                "resolution": config["resolution"],
                "aspect_ratio": config["aspectRatio"],
                "sound": config["sound"],
                "prompt": SCENE_PROMPT,
                "task_id": task_id,
                "status": "ok",
                "gen_time_s": result["time"],
                "credits": result["credit"],
                "dims": dims,
                "file_size_kb": round(file_size / 1024),
                "output_path": path,
            })
            results.append({
                "name": config["name"],
                "status": "ok",
                "time": result["time"],
                "size": file_size,
                "dims": dims,
                "credit": result["credit"],
            })
        else:
            print(f"  {result['status'].upper()}: {result.get('error', 'unknown')} "
                  f"({result['time']}s)")
            results.append({
                "name": config["name"],
                "status": result["status"],
                "time": result["time"],
                "error": result.get("error"),
            })
            log_result({
                "kind": "t2v",
                "model_name": config["name"],
                "model_display": config["model"],
                "duration_s": config["duration"],
                "resolution": config["resolution"],
                "aspect_ratio": config["aspectRatio"],
                "sound": config["sound"],
                "prompt": SCENE_PROMPT,
                "task_id": task_id,
                "status": result["status"],
                "gen_time_s": result["time"],
                "error": str(result.get("error", ""))[:500],
            })

    except requests.HTTPError as e:
        body = e.response.text[:300] if e.response is not None else ""
        print(f"  HTTP ERROR: {e} — {body}")
        results.append({"name": config["name"], "status": "http_error", "error": str(e)})
        log_result({
            "kind": "t2v", "model_name": config["name"], "model_display": config["model"],
            "prompt": SCENE_PROMPT, "task_id": task_id,
            "status": "http_error", "error": f"{e} — {body}"[:500],
        })
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"name": config["name"], "status": "error", "error": str(e)})
        log_result({
            "kind": "t2v", "model_name": config["name"], "model_display": config["model"],
            "prompt": SCENE_PROMPT, "task_id": task_id,
            "status": "error", "error": str(e)[:500],
        })

    print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
ok = [r for r in results if r["status"] == "ok"]
print(f"  Generated: {len(ok)}/{len(TEST_MODELS)}")
if ok:
    avg_time = sum(r["time"] for r in ok) / len(ok)
    avg_size = sum(r["size"] for r in ok) / len(ok)
    print(f"  Avg generation time: {avg_time:.0f}s")
    print(f"  Avg file size: {avg_size / 1024 / 1024:.1f} MB")
    print(f"  Credits spent: {sum(float(r['credit']) for r in ok if r.get('credit')):.2f}")
    for r in ok:
        print(f"    - {r['name']}: {r['dims']}, {r['size'] / 1024:.0f} KB, credit={r['credit']}")
failed = [r for r in results if r["status"] != "ok"]
if failed:
    print(f"  Failed ({len(failed)}):")
    for r in failed:
        print(f"    - {r['name']}: {r['status']} — {r.get('error', '')[:120]}")
print(f"  Output dir: {output_dir}/")
print()
print("Compare against test_generations/topview/ (image2video) to judge whether the")
print("image-preview stage is earning its keep, or whether t2v is a cost-effective")
print("path for Freestyle Mode (see docs/Enhancements.md).")
