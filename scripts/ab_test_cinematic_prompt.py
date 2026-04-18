"""A/B test one Scooby scene — original vs cinematic prompt — through TopView.

Runs the same source image through the same video model twice, varying only
the prompt: once with the scene's `visual_description` (Scooby's current
image-gen style), once with the `video_description` (cinematic rewrite from
cinematic_prompt_enhancer.py). Same image, same model, same duration — the
only variable is the prompt.

Usage:
    python scripts/ab_test_cinematic_prompt.py \
        --scenes-json test_generations/scooby_scenes/the-betrayal-recording/scenes.json \
        --scene 1 \
        --model kling_2.6

    --scene N       Scene order number to test (default: 1)
    --model NAME    kling_2.6 | vidu_q3_pro | seedance_1.0_pro_fast (default: kling_2.6)

Outputs saved to: test_generations/topview_ab/<story_slug>/scene_<N>_<model>_{original,cinematic}.mp4
"""

from __future__ import annotations

import argparse
import json
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
    sys.exit(1)

BASE_URL = "https://api.topview.ai"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Topview-Uid": uid,
}

# Same single-image i2v models as test_topview_image2video.py — must support
# a single source image (no first/last frame pair).
MODEL_CONFIGS = {
    "kling_2.6": {
        "model": "Kling 2.6",
        "duration": 5,
        "sound": "on",
    },
    "vidu_q3_pro": {
        "model": "Vidu Q3 Pro",
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 5,
        "sound": "on",
    },
    "seedance_1.0_pro_fast": {
        "model": "Seedance 1.0 Pro Fast",
        "resolution": 720,
        "duration": 5,
        "sound": "off",
    },
}


def upload_image(path: str) -> str:
    ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"
    cred_resp = requests.get(
        f"{BASE_URL}/v1/upload/credential",
        headers=HEADERS,
        params={"format": ext},
        timeout=30,
    )
    cred_resp.raise_for_status()
    result = cred_resp.json()["result"]
    upload_url = result["uploadUrl"]
    file_id = result["fileId"]

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


def submit_task(file_id: str, prompt: str, cfg: dict) -> str:
    body = {
        "model": cfg["model"],
        "firstFrameFileId": file_id,
        "prompt": prompt,
        "duration": cfg["duration"],
        "sound": cfg["sound"],
        "generatingCount": 1,
    }
    if "aspectRatio" in cfg:
        body["aspectRatio"] = cfg["aspectRatio"]
    if "resolution" in cfg:
        body["resolution"] = cfg["resolution"]

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
                return {"status": "no_video", "time": elapsed}
            v = videos[0]
            return {
                "status": "ok",
                "url": v["filePath"],
                "width": v.get("width"),
                "height": v.get("height"),
                "credit": result.get("costCredit"),
                "time": elapsed,
            }
        if status == "fail":
            return {"status": "failed", "error": result.get("errorMsg"), "time": elapsed}

    return {"status": "timeout", "time": elapsed}


def run_variant(file_id: str, label: str, prompt: str, cfg: dict, out_path: str) -> dict:
    """Run one variant (original or cinematic), download the MP4, return summary."""
    print(f"[{label}]")
    print(f"  Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    try:
        task_id = submit_task(file_id, prompt, cfg)
        print(f"  Task ID: {task_id}")
        print("  Polling (typically 1-5 minutes)...")
        result = poll_result(task_id)
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"label": label, "status": "error", "error": str(e)}

    if result["status"] != "ok":
        print(f"  {result['status'].upper()}: {result.get('error', 'unknown')}")
        return {"label": label, "status": result["status"], "error": result.get("error")}

    try:
        video_resp = requests.get(result["url"], timeout=180)
        video_resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(video_resp.content)
    except Exception as e:
        print(f"  ERROR downloading video: {e}")
        return {"label": label, "status": "download_failed", "error": str(e)}

    size = os.path.getsize(out_path)
    dims = f"{result['width']}x{result['height']}" if result.get("width") else "?"
    print(
        f"  Saved: {out_path} ({size / 1024:.0f} KB, {dims}, "
        f"{result['time']}s, credit={result['credit']})"
    )
    return {
        "label": label,
        "status": "ok",
        "path": out_path,
        "size": size,
        "dims": dims,
        "time": result["time"],
        "credit": result["credit"],
        "task_id": task_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A/B test original vs cinematic prompt on one Scooby scene",
    )
    parser.add_argument(
        "--scenes-json",
        required=True,
        help="Path to scenes.json (must have been run through cinematic_prompt_enhancer.py --write)",
    )
    parser.add_argument("--scene", type=int, default=1, help="Scene order number (default: 1)")
    parser.add_argument(
        "--model",
        default="kling_2.6",
        choices=list(MODEL_CONFIGS.keys()),
        help="Video model to A/B test against (default: kling_2.6)",
    )
    args = parser.parse_args()

    with open(args.scenes_json, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenes = manifest.get("scenes") or []
    scene = next((s for s in scenes if s.get("scene_order") == args.scene), None)
    if not scene:
        available = [s.get("scene_order") for s in scenes]
        print(f"ERROR: scene {args.scene} not found. Available: {available}")
        sys.exit(1)

    original_prompt = scene.get("visual_description")
    cinematic_prompt = scene.get("video_description")
    image_path = scene.get("local_image")

    if not original_prompt:
        print(f"ERROR: scene {args.scene} has no visual_description")
        sys.exit(1)
    if not cinematic_prompt:
        print(f"ERROR: scene {args.scene} has no video_description — run cinematic_prompt_enhancer.py --write first")
        sys.exit(1)
    if not image_path or not os.path.isfile(image_path):
        print(f"ERROR: scene {args.scene} image not found at {image_path}")
        sys.exit(1)

    cfg = MODEL_CONFIGS[args.model]
    story_slug = manifest.get("slug", "untitled")
    out_dir = os.path.join("test_generations", "topview_ab", story_slug)
    os.makedirs(out_dir, exist_ok=True)

    base = f"scene_{args.scene:02d}_{args.model}_{cfg['duration']}s"
    original_path = os.path.join(out_dir, f"{base}_A_original.mp4")
    cinematic_path = os.path.join(out_dir, f"{base}_B_cinematic.mp4")

    print("=" * 60)
    print(f"A/B test — {manifest.get('title', '?')} scene {args.scene}")
    print(f"Model: {args.model} ({cfg['model']}) · {cfg['duration']}s · sound={cfg['sound']}")
    print(f"Image: {image_path}")
    print(f"Output: {out_dir}/")
    print("=" * 60)
    print()

    # Upload the image ONCE, reuse for both variants — same fileId = same starting frame
    print("Uploading source image...")
    try:
        file_id = upload_image(image_path)
        print(f"  File ID: {file_id}")
    except Exception as e:
        print(f"  ERROR uploading image: {e}")
        sys.exit(1)
    print()

    # A: original visual_description
    a = run_variant(file_id, "A — ORIGINAL (visual_description)", original_prompt, cfg, original_path)
    log_result({
        "kind": "i2v_ab_original",
        "model_name": args.model,
        "model_display": cfg["model"],
        "duration_s": cfg["duration"],
        "resolution": cfg.get("resolution", ""),
        "aspect_ratio": cfg.get("aspectRatio", ""),
        "sound": cfg["sound"],
        "input_image": image_path,
        "prompt": original_prompt,
        "task_id": a.get("task_id", ""),
        "status": a["status"],
        "gen_time_s": a.get("time", ""),
        "credits": a.get("credit", ""),
        "dims": a.get("dims", ""),
        "file_size_kb": round(a["size"] / 1024) if a.get("size") else "",
        "output_path": a.get("path", ""),
        "error": str(a.get("error", ""))[:500],
    })
    print()

    # B: cinematic video_description
    b = run_variant(file_id, "B — CINEMATIC (video_description)", cinematic_prompt, cfg, cinematic_path)
    log_result({
        "kind": "i2v_ab_cinematic",
        "model_name": args.model,
        "model_display": cfg["model"],
        "duration_s": cfg["duration"],
        "resolution": cfg.get("resolution", ""),
        "aspect_ratio": cfg.get("aspectRatio", ""),
        "sound": cfg["sound"],
        "input_image": image_path,
        "prompt": cinematic_prompt,
        "task_id": b.get("task_id", ""),
        "status": b["status"],
        "gen_time_s": b.get("time", ""),
        "credits": b.get("credit", ""),
        "dims": b.get("dims", ""),
        "file_size_kb": round(b["size"] / 1024) if b.get("size") else "",
        "output_path": b.get("path", ""),
        "error": str(b.get("error", ""))[:500],
    })
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in (a, b):
        if r["status"] == "ok":
            print(f"  {r['label']}: {r['path']} — credit={r['credit']}, {r['time']}s")
        else:
            print(f"  {r['label']}: {r['status'].upper()} — {r.get('error', '')[:120]}")
    print()
    if a["status"] == "ok" and b["status"] == "ok":
        print("Play the two MP4s back-to-back and judge:")
        print("  - Does CINEMATIC have more purposeful camera motion?")
        print("  - Is the per-scene 'feel' stronger (mood, tension, pacing)?")
        print("  - Did the enhancer's specific motion verbs actually land on screen?")
        print("  - Or did the terser ORIGINAL produce equally good or better motion?")
        print()
        print("If cinematic wins consistently across scenes, promote the enhancer to a")
        print("permanent step in the pipeline — Scene.video_description as a DB column.")


if __name__ == "__main__":
    main()
