"""TopView Seedance 2.0 (Omni Reference) eval for Joyce's "Heart for Fun".

Strategy: instead of a text-only character bible (yesterday's
eval_topview_joyce_heart.py with Seedance 1.5 Pro), pass an actual
reference image of Joyce as <<<Image1>>>. The model anchors her
appearance to the image instead of trying to interpret text
descriptions, which should fix the close-up drift we saw on scene 6
("hands clapping" — text-only bible produced a noticeably older woman
because the prompt had no character context for the bible to anchor to).

Reference image: test_generations/joyce_heart_topview/thumb_5.jpg
  — Joyce alone, full body, gray cardigan, blue jeans, light sneakers,
    natural curly hair, grey background. Strongest character shot in
    the 1.5 Pro batch.

Scenes (frozen from production DB ab8bf1d4 on 2026-04-27, same as the
1.5 Pro eval).

Endpoints:
- POST /v1/upload/credential   (get presigned PUT URL)
- POST /v1/common_task/omni_reference/task/submit
- GET  /v1/common_task/omni_reference/task/query

Usage:
    TOPVIEW_API_KEY=... TOPVIEW_UID=... \
        python scripts/eval_topview_joyce_seedance_2.py [--dry-run] [--scene N]

    --dry-run   Print augmented prompts only, don't call the API.
    --scene N   Generate only scene N (1-6).
    --model M   "Seedance 2.0 Standard" (default) or "Seedance 2.0 Fast"

Output: test_generations/joyce_heart_seedance_2_omni/
"""

from __future__ import annotations

import argparse
import json
import mimetypes
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


CHARACTER_REF_IMAGE = Path("test_generations/joyce_heart_topview/thumb_5.jpg")

# Scene-specific prompts: each references <<<Image1>>> (Joyce) so the model
# anchors her identity to the reference. Trimmed and rewritten relative to
# the 1.5 Pro bible-style prompts since the visual anchor handles
# identity — we just need to describe action + setting.
SCENES = [
    {
        "n": 1, "beat": "hook", "duration": 5,
        "prompt": (
            "<<<Image1>>> places her two forearm crutches gently onto cracked "
            "asphalt in close-up. Soft afternoon sunlight, long shadows, "
            "children's laughter audible in background. Cinematic, vertical 9:16."
        ),
    },
    {
        "n": 2, "beat": "setup", "duration": 5,
        "prompt": (
            "<<<Image1>>> looks toward a colorful playground where children "
            "are playing behind a chain-link fence. A bright red ball sits "
            "abandoned against the street curb in the foreground. Medium shot, "
            "warm light, suburban neighborhood. Vertical 9:16."
        ),
    },
    {
        "n": 3, "beat": "escalation_1", "duration": 5,
        # Story-faithful rewrite: Joyce is hobbling toward the ball when the
        # second one drops. Earlier prompt focused only on the kid at the
        # fence and triggered the TopView API error
        # "InputImage 'Image1' is not referenced in prompt" because every
        # uploaded ref must appear in the prompt. Putting Joyce back in
        # frame fixes the API error AND matches the narration arc.
        "prompt": (
            "Wide shot: <<<Image1>>> hobbles toward a red ball lying at the "
            "street curb. A young girl on the playground side of a "
            "chain-link fence points desperately toward another colorful "
            "ball that has just bounced into the road behind the first. "
            "Daytime, cinematic. Vertical 9:16."
        ),
    },
    {
        "n": 4, "beat": "escalation_2", "duration": 5,
        "prompt": (
            "Over-the-shoulder shot: <<<Image1>>> calling out, arm raised in "
            "greeting, to a middle-aged white woman (Rebecca) getting into "
            "her car in the distance. Two colorful balls on the asphalt "
            "between them. Cinematic, warm afternoon light. Vertical 9:16."
        ),
    },
    {
        "n": 5, "beat": "climax", "duration": 5,
        "prompt": (
            "Heartwarming medium shot: <<<Image1>>> and a middle-aged white "
            "woman (Rebecca) work together throwing colorful playground "
            "balls over a chain-link fence to eager children reaching "
            "through the gaps. Golden hour lighting, warm glow. Vertical 9:16."
        ),
    },
    {
        "n": 6, "beat": "button", "duration": 5,
        "prompt": (
            "Close-up: <<<Image1>>>'s hands clapping together with joy, "
            "slightly weathered but full of life. Blurred playground "
            "happiness in the soft-focus background. Cinematic, warm. "
            "Vertical 9:16."
        ),
    },
]

BASE_URL = "https://api.topview.ai"


def headers() -> dict[str, str]:
    api_key = os.environ["TOPVIEW_API_KEY"]
    uid = os.environ["TOPVIEW_UID"]
    return {"Authorization": f"Bearer {api_key}", "Topview-Uid": uid}


def upload_reference(path: Path) -> str:
    """Upload a local file via TopView's presigned-URL flow. Returns fileId."""
    ext = path.suffix.lstrip(".").lower() or "png"
    cred = requests.get(
        f"{BASE_URL}/v1/upload/credential",
        headers=headers(), params={"format": ext}, timeout=30,
    )
    cred.raise_for_status()
    result = cred.json()["result"]
    file_id = result["fileId"]
    upload_url = result["uploadUrl"]

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with path.open("rb") as f:
        put = requests.put(
            upload_url, data=f,
            headers={"Content-Type": content_type}, timeout=180,
        )
    put.raise_for_status()
    return file_id


def submit(model: str, prompt: str, file_ids: list[str]) -> str:
    body = {
        "model": model,
        "prompt": prompt,
        "inputImages": [
            {"fileId": fid, "name": f"Image{i + 1}"}
            for i, fid in enumerate(file_ids)
        ],
        "aspectRatio": "9:16",
        "resolution": 720,
        "duration": 5,
        "generatingCount": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/v1/common_task/omni_reference/task/submit",
        json=body, headers={**headers(), "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "200":
        raise RuntimeError(f"Submit failed: {data.get('message')} — {data}")
    return data["result"]["taskId"]


def poll(task_id: str, max_wait: int = 900) -> dict:
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(10)
        elapsed += 10
        resp = requests.get(
            f"{BASE_URL}/v1/common_task/omni_reference/task/query",
            headers=headers(), params={"taskId": task_id}, timeout=30,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        status = (result.get("status") or "").lower()
        if elapsed % 30 == 0 or status in ("success", "fail"):
            print(f"    [{elapsed}s] {status} (credit: {result.get('costCredit', '?')})")
        if status == "success":
            videos = result.get("videos") or []
            if not videos:
                raise RuntimeError(f"No video in successful result: {result}")
            v = videos[0]
            return {
                "url": v["filePath"], "width": v.get("width"),
                "height": v.get("height"), "duration_ms": v.get("duration"),
                "credit": result.get("costCredit"), "elapsed": elapsed,
            }
        if status == "fail":
            raise RuntimeError(f"Task failed: {result.get('errorMsg')}")
    raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")


def download(url: str, dest: Path) -> int:
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
                        help="print prompts only; don't call the API")
    parser.add_argument("--scene", type=int, help="generate only scene N (1-6)")
    parser.add_argument("--model", default="Standard",
                        help='Omni Reference model display name. "Standard" '
                             '(Seedance 2.0 Standard, default) or "Fast" '
                             '(Seedance 2.0 Fast). The "Seedance 2.0 " prefix '
                             'is implicit since the endpoint itself is the '
                             'Seedance 2.0 endpoint.')
    args = parser.parse_args()

    out_dir = Path("test_generations/joyce_heart_seedance_2_omni")
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = SCENES if args.scene is None else [s for s in SCENES if s["n"] == args.scene]

    print(f"Joyce 'Heart for Fun' — Seedance 2.0 Omni Reference eval")
    print(f"Reference: {CHARACTER_REF_IMAGE}")
    print(f"Model:     {args.model}")
    print(f"Scenes:    {len(targets)} of 6")
    print(f"Output:    {out_dir}/")
    print()

    if args.dry_run:
        for s in targets:
            print(f"=== Scene {s['n']} ({s['beat']}, {s['duration']}s) ===")
            print(s["prompt"])
            print()
        return 0

    if not os.environ.get("TOPVIEW_API_KEY") or not os.environ.get("TOPVIEW_UID"):
        print("ERROR: TOPVIEW_API_KEY and TOPVIEW_UID required")
        return 1
    if not CHARACTER_REF_IMAGE.exists():
        print(f"ERROR: reference image missing: {CHARACTER_REF_IMAGE}")
        return 1

    print(f"Uploading reference image...")
    ref_file_id = upload_reference(CHARACTER_REF_IMAGE)
    print(f"  <<<Image1>>> fileId = {ref_file_id}")
    print()

    manifest = []
    for s in targets:
        print(f"--- Scene {s['n']} ({s['beat']}) ---")
        print(f"  prompt: {s['prompt'][:80]}...")
        try:
            task_id = submit(args.model, s["prompt"], [ref_file_id])
            print(f"  taskId: {task_id}")
            print(f"  Polling...")
            r = poll(task_id)
            dest = out_dir / f"scene_{s['n']}_{s['beat']}.mp4"
            size = download(r["url"], dest)
            dims = f"{r.get('width')}x{r.get('height')}" if r.get("width") else "?"
            print(f"  saved {dest} ({size:,} bytes, {dims}, {r['elapsed']}s, "
                  f"credit={r.get('credit')})")
            manifest.append({
                "scene": s["n"], "beat": s["beat"], "model": args.model,
                "task_id": task_id, "file": dest.name, "size": size,
                "dims": dims, "credit": r.get("credit"),
                "elapsed_s": r["elapsed"], "prompt": s["prompt"],
                "ref_file_id": ref_file_id,
            })
        except Exception as ex:
            print(f"  FAILED: {type(ex).__name__}: {ex}")
            manifest.append({
                "scene": s["n"], "beat": s["beat"], "model": args.model,
                "error": str(ex), "prompt": s["prompt"],
            })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {out_dir / 'manifest.json'}")
    print(f"Successful: {sum(1 for m in manifest if 'file' in m)}/{len(manifest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
