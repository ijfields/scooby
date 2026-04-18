"""Test TopView Omni Reference endpoint with Seedance 2.0.

This endpoint (different from image2video V2) gives access to Seedance 2.0
Standard / Fast with multi-image + multi-video reference via the
<<<Image1>>>, <<<Image2>>>, <<<Video1>>> prompt syntax.

For Scooby, the killer feature is **multi-image reference for character
consistency** — pass a character lookbook (up to 9 images) once, reference
specific characters by name in the prompt across 8 scenes.

Usage:
    # Single-image reference (like i2v, but via Omni endpoint)
    TOPVIEW_API_KEY=... TOPVIEW_UID=... \
        python scripts/test_topview_omni_reference.py scene.png --model seedance_2.0_fast

    # Two-image reference (character consistency test)
    TOPVIEW_API_KEY=... TOPVIEW_UID=... \
        python scripts/test_topview_omni_reference.py scene.png character.png --model seedance_2.0_standard

    --model NAME     seedance_2.0_fast | seedance_2.0_standard
                     (omit to run both in sequence)

Outputs saved to: test_generations/topview_omni/
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _topview_results import log_result  # noqa: E402

api_key = os.environ.get("TOPVIEW_API_KEY")
uid = os.environ.get("TOPVIEW_UID")
if not api_key or not uid:
    print("ERROR: Set TOPVIEW_API_KEY and TOPVIEW_UID environment variables")
    print("  Get them at: https://www.topview.ai/dashboard/api-settings")
    sys.exit(1)

parser = argparse.ArgumentParser(description="TopView Omni Reference eval (Seedance 2.0)")
parser.add_argument("images", nargs="+", help="1–9 reference image paths (uploaded in order, bound to <<<Image1>>>, <<<Image2>>>, ...)")
parser.add_argument("--model", help="Run only the named model (seedance_2.0_fast, seedance_2.0_standard)")
args = parser.parse_args()

for p in args.images:
    if not os.path.isfile(p):
        print(f"ERROR: File not found: {p}")
        sys.exit(1)

if len(args.images) > 9:
    print("ERROR: Omni Reference accepts up to 9 images")
    sys.exit(1)

BASE_URL = "https://api.topview.ai"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Topview-Uid": uid,
}

# Prompts are tailored to the number of images supplied:
#   1 image  → treats it as the scene; character/motion driven by prompt
#   2 images → Image1 = scene setting, Image2 = character; test consistency
SINGLE_IMAGE_PROMPT = (
    "<<<Image1>>> comes alive: slow cinematic push in, warm amber light flickers, "
    "atmospheric dust floats through the scene. Moody vertical drama, film grain."
)
TWO_IMAGE_PROMPT = (
    "The character from <<<Image2>>> sits at the table shown in <<<Image1>>>, "
    "reading the letter with a quiet, emotional expression. Slow push in, "
    "warm amber light flickers, film grain. Preserve the character's likeness "
    "and clothing from <<<Image2>>>. Vertical 9:16 drama."
)

TEST_MODELS = [
    {
        "name": "seedance_2.0_fast",
        "model": "Fast",          # TopView display name for Seedance 2.0 Fast
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 5,
        "sound": "on",             # native audio free on this model
    },
    {
        "name": "seedance_2.0_standard",
        "model": "Standard",       # TopView display name for Seedance 2.0
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 5,
        "sound": "on",
    },
]

if args.model:
    matching = [m for m in TEST_MODELS if m["name"] == args.model]
    if not matching:
        valid = ", ".join(m["name"] for m in TEST_MODELS)
        print(f"ERROR: Unknown model '{args.model}'. Valid: {valid}")
        sys.exit(1)
    TEST_MODELS = matching

output_dir = os.path.join("test_generations", "topview_omni")
os.makedirs(output_dir, exist_ok=True)

# Pick the prompt based on image count — matches character-consistency test design
PROMPT = TWO_IMAGE_PROMPT if len(args.images) >= 2 else SINGLE_IMAGE_PROMPT
mode_label = f"{len(args.images)}-image reference" + (" (character consistency)" if len(args.images) >= 2 else "")

print("TopView AI Omni Reference Test — Seedance 2.0")
print("=" * 60)
print(f"Mode:   {mode_label}")
print(f"Images: {', '.join(args.images)}")
print(f"Output: {output_dir}/")
print(f"Models: {len(TEST_MODELS)} ({', '.join(m['name'] for m in TEST_MODELS)})")
print()


def upload_image(path: str) -> str:
    """Upload one image, return fileId."""
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


def submit_task(file_ids: list[str], config: dict) -> str:
    """Submit an Omni Reference task. Returns taskId."""
    input_images = [
        {"fileId": fid, "name": f"Image{i + 1}"}
        for i, fid in enumerate(file_ids)
    ]
    body = {
        "model": config["model"],
        "prompt": PROMPT,
        "inputImages": input_images,
        "aspectRatio": config["aspectRatio"],
        "resolution": config["resolution"],
        "duration": config["duration"],
        "generatingCount": 1,
    }
    # sound is controlled by the prompt/model itself on Omni; include if Standard/Fast supports it
    if config.get("sound"):
        body["sound"] = config["sound"]

    resp = requests.post(
        f"{BASE_URL}/v1/common_task/omni_reference/task/submit",
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
    """Poll for task completion."""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        resp = requests.get(
            f"{BASE_URL}/v1/common_task/omni_reference/task/query",
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


# Upload all reference images once, reuse fileIds across both models
print(f"Uploading {len(args.images)} reference image(s)...")
file_ids: list[str] = []
for i, path in enumerate(args.images):
    try:
        fid = upload_image(path)
        file_ids.append(fid)
        print(f"  [{i + 1}] <<<Image{i + 1}>>> = {fid}  ({path})")
    except Exception as e:
        print(f"  ERROR uploading {path}: {e}")
        sys.exit(1)
print()

results = []
for i, config in enumerate(TEST_MODELS):
    name_suffix = f"{len(args.images)}img"
    print(f"[{i + 1}/{len(TEST_MODELS)}] {config['name']} — {config['model']} "
          f"({config['duration']}s, {config['resolution']}p, sound={config['sound']}, "
          f"{len(args.images)} ref img{'s' if len(args.images) > 1 else ''})")
    print(f"  Prompt: {PROMPT[:90]}...")

    task_id = ""
    try:
        task_id = submit_task(file_ids, config)
        print(f"  Task ID: {task_id}")
        print(f"  Polling (typically 1-5 minutes)...")

        result = poll_result(task_id)

        if result["status"] == "ok":
            video_resp = requests.get(result["url"], timeout=180)
            video_resp.raise_for_status()
            out_path = os.path.join(
                output_dir,
                f"{config['name']}_{name_suffix}_{config['duration']}s.mp4",
            )
            with open(out_path, "wb") as f:
                f.write(video_resp.content)
            file_size = os.path.getsize(out_path)
            dims = f"{result['width']}x{result['height']}" if result.get("width") else "?"
            print(f"  Saved: {out_path} ({file_size / 1024:.0f} KB, {dims}, "
                  f"{result['time']}s, credit={result['credit']})")
            log_result({
                "kind": "omni",
                "model_name": config["name"],
                "model_display": config["model"],
                "duration_s": config["duration"],
                "resolution": config["resolution"],
                "aspect_ratio": config["aspectRatio"],
                "sound": config["sound"],
                "input_image": ";".join(args.images),  # semicolon-separated — commas would break CSV quoting
                "prompt": PROMPT,
                "task_id": task_id,
                "status": "ok",
                "gen_time_s": result["time"],
                "credits": result["credit"],
                "dims": dims,
                "file_size_kb": round(file_size / 1024),
                "output_path": out_path,
            })
            results.append({"name": config["name"], "status": "ok",
                            "time": result["time"], "size": file_size,
                            "dims": dims, "credit": result["credit"]})
        else:
            print(f"  {result['status'].upper()}: {result.get('error', 'unknown')} "
                  f"({result['time']}s)")
            log_result({
                "kind": "omni",
                "model_name": config["name"],
                "model_display": config["model"],
                "duration_s": config["duration"],
                "resolution": config["resolution"],
                "aspect_ratio": config["aspectRatio"],
                "sound": config["sound"],
                "input_image": ";".join(args.images),
                "prompt": PROMPT,
                "task_id": task_id,
                "status": result["status"],
                "gen_time_s": result["time"],
                "error": str(result.get("error", ""))[:500],
            })
            results.append({"name": config["name"], "status": result["status"],
                            "time": result["time"], "error": result.get("error")})

    except requests.HTTPError as e:
        body = e.response.text[:300] if e.response is not None else ""
        print(f"  HTTP ERROR: {e} — {body}")
        log_result({
            "kind": "omni", "model_name": config["name"], "model_display": config["model"],
            "input_image": ";".join(args.images), "prompt": PROMPT, "task_id": task_id,
            "status": "http_error", "error": f"{e} — {body}"[:500],
        })
        results.append({"name": config["name"], "status": "http_error", "error": str(e)})
    except Exception as e:
        print(f"  ERROR: {e}")
        log_result({
            "kind": "omni", "model_name": config["name"], "model_display": config["model"],
            "input_image": ";".join(args.images), "prompt": PROMPT, "task_id": task_id,
            "status": "error", "error": str(e)[:500],
        })
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
        print(f"    - {r['name']}: {r['status']} — {str(r.get('error', ''))[:120]}")
print(f"  Output dir: {output_dir}/")
print()
if len(args.images) >= 2:
    print("Character consistency test — compare character likeness in the output")
    print("against the <<<Image2>>> reference. If the face/clothing hold up across")
    print("scenes, this is Scooby's premium tier winner.")
else:
    print("Compare Seedance 2.0 output against the i2v models (Kling 2.6, Vidu Q3")
    print("Pro) to decide if the 2× cost premium is worth it for the default flow.")
