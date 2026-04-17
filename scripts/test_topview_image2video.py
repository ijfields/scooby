"""Test TopView AI image-to-video for Scooby scenes (9:16 vertical drama).

Evaluates whether TopView can replace/augment the Remotion compositing step
by animating a Scooby-generated scene image into a short video clip.

Usage:
    TOPVIEW_API_KEY=your-key TOPVIEW_UID=your-uid \
        python scripts/test_topview_image2video.py path/to/scene.png [--model NAME]

    --model NAME  Run only the named model (veo_3.1_fast, sora_2_pro, kling_v3).
                  Default: run all three.

Flow:
    1. Request upload credential (GET /v1/upload/credential)
    2. Upload local image to the returned pre-signed S3 URL (PUT)
    3. Submit image2video task for each model (POST /v2/common_task/image2video/task/submit)
    4. Poll until completion (GET /v2/common_task/image2video/task/query)
    5. Download resulting MP4

Outputs saved to: test_generations/topview/
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.environ.get("TOPVIEW_API_KEY")
uid = os.environ.get("TOPVIEW_UID")
if not api_key or not uid:
    print("ERROR: Set TOPVIEW_API_KEY and TOPVIEW_UID environment variables")
    print("  Get them at: https://www.topview.ai/dashboard/api-settings")
    sys.exit(1)

parser = argparse.ArgumentParser(description="TopView image-to-video eval for Scooby")
parser.add_argument("image_path", help="Local image file to animate")
parser.add_argument("--model", help="Run only the named model (e.g. veo_3.1_fast, sora_2_pro, kling_v3)")
args = parser.parse_args()

image_path = args.image_path
if not os.path.isfile(image_path):
    print(f"ERROR: File not found: {image_path}")
    sys.exit(1)

BASE_URL = "https://api.topview.ai"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Topview-Uid": uid,
}

# 9:16 vertical drama — same aspect + duration range Scooby scenes target.
# Picked to span price/quality: cheap/fast, narrative-strong, audio-native.
TEST_MODELS = [
    {
        "name": "veo_3.1_fast",
        "model": "Veo 3.1 Fast",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 8,
        "sound": "on",  # native audio
        "prompt": "Slow cinematic zoom in, warm amber light flickers, atmospheric dust floats. Moody drama.",
    },
    {
        "name": "sora_2_pro",
        "model": "Sora 2 Pro",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 8,
        "sound": "off",  # no audio
        "prompt": "Subtle camera push in, gentle motion, cinematic narrative drama, film grain.",
    },
    {
        "name": "kling_v3",
        "model": "Kling V3",
        # aspectRatio determined by image; omit
        "resolution": 720,
        "duration": 5,
        "sound": "on",  # native audio
        "prompt": "Emotional close-up, subtle breathing motion, soft light shift from warm to cool, intimate moment.",
    },
]

if args.model:
    matching = [m for m in TEST_MODELS if m["name"] == args.model]
    if not matching:
        valid = ", ".join(m["name"] for m in TEST_MODELS)
        print(f"ERROR: Unknown model '{args.model}'. Valid: {valid}")
        sys.exit(1)
    TEST_MODELS = matching

output_dir = os.path.join("test_generations", "topview")
os.makedirs(output_dir, exist_ok=True)

print("TopView AI Image-to-Video Test (Scooby 9:16 drama eval)")
print("=" * 60)
print(f"Image: {image_path}")
print(f"Output: {output_dir}/")
print(f"Models: {len(TEST_MODELS)} ({', '.join(m['name'] for m in TEST_MODELS)})")
print()


def upload_image(path: str) -> str:
    """Upload local image via TopView credential flow. Returns fileId."""
    ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"
    cred_resp = requests.get(
        f"{BASE_URL}/v1/upload/credential",
        headers=HEADERS,
        params={"format": ext},
        timeout=30,
    )
    cred_resp.raise_for_status()
    result = cred_resp.json()["result"]
    file_id = result["fileId"]
    upload_url = result["uploadUrl"]

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            data=f,
            headers={"Content-Type": content_type},
            timeout=120,
        )
    put_resp.raise_for_status()
    return file_id


def submit_task(file_id: str, config: dict) -> str:
    """Submit image2video task. Returns taskId."""
    body = {
        "model": config["model"],
        "firstFrameFileId": file_id,
        "prompt": config["prompt"],
        "resolution": config["resolution"],
        "duration": config["duration"],
        "sound": config["sound"],
        "generatingCount": 1,
    }
    if "aspectRatio" in config:
        body["aspectRatio"] = config["aspectRatio"]

    resp = requests.post(
        f"{BASE_URL}/v2/common_task/image2video/task/submit",
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
    """Poll for task completion. Returns result dict with videos array on success."""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        resp = requests.get(
            f"{BASE_URL}/v2/common_task/image2video/task/query",
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


print("Uploading image...")
try:
    file_id = upload_image(image_path)
    print(f"  File ID: {file_id}")
except Exception as e:
    print(f"  ERROR: upload failed: {e}")
    sys.exit(1)
print()

results = []
for i, config in enumerate(TEST_MODELS):
    print(f"[{i + 1}/{len(TEST_MODELS)}] {config['name']} — {config['model']} "
          f"({config['duration']}s, {config['resolution']}p, sound={config['sound']})")
    print(f"  Prompt: {config['prompt'][:80]}...")

    try:
        task_id = submit_task(file_id, config)
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

    except requests.HTTPError as e:
        body = e.response.text[:300] if e.response is not None else ""
        print(f"  HTTP ERROR: {e} — {body}")
        results.append({"name": config["name"], "status": "http_error", "error": str(e)})
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"name": config["name"], "status": "error", "error": str(e)})

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
print("Review .mp4 files side-by-side to judge drama aesthetic, 9:16 framing, "
      "and per-scene cost before wiring into the provider registry.")
