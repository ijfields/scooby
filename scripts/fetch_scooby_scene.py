"""Fetch a real Scooby episode via its share token and prep TopView eval inputs.

Reads the public share endpoint, downloads each scene's image, and writes
a scenes.json manifest. Also prints copy-paste-ready commands for
running the TopView eval scripts against real production scenes and
prompts (instead of my synthetic test_scene.png + kitchen prompt).

Usage:
    python scripts/fetch_scooby_scene.py <share_token_or_url>

    Accepts either:
      - raw token:  QPd4Rou5OKqvuyUv75bLQpqCzovwJjDrIxeOtNbaxxU
      - full URL:   https://scooby-frontend-production.up.railway.app/share/<token>

Outputs to:
    test_generations/scooby_scenes/<story_slug>/
      - scene_01.png, scene_02.png, ... (downloaded image assets)
      - scenes.json (scenes + prompts + metadata, machine-readable)
      - README.md  (human-readable summary + suggested eval commands)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

import requests

BACKEND = "https://backend-production-67a9.up.railway.app"


def parse_token(arg: str) -> str:
    """Extract the share token from either a bare token or a full frontend URL."""
    if "/" in arg or arg.startswith("http"):
        parsed = urlparse(arg)
        # Expected path like /share/<token>
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[-1]:
            return parts[-1]
        raise ValueError(f"Can't find share token in URL: {arg}")
    return arg


def slugify(text: str) -> str:
    """Filesystem-safe slug from a free-form title."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "untitled"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Scooby scenes for TopView eval")
    parser.add_argument("token_or_url", help="Share token or full frontend share URL")
    args = parser.parse_args()

    token = parse_token(args.token_or_url)
    print(f"Fetching shared episode: token={token[:16]}...")

    resp = requests.get(f"{BACKEND}/api/v1/shared/{token}", timeout=30)
    if resp.status_code == 404:
        print("ERROR: Share link not found (404). Regenerate a share link from the frontend.")
        sys.exit(1)
    if resp.status_code == 410:
        print("ERROR: Share link expired (410). Create a fresh one.")
        sys.exit(1)
    resp.raise_for_status()
    data = resp.json()

    title = data.get("title") or "untitled"
    slug = slugify(title)
    scenes = data.get("scenes") or []
    attribution = data.get("attribution")

    out_dir = os.path.join("test_generations", "scooby_scenes", slug)
    os.makedirs(out_dir, exist_ok=True)

    print(f"Story: {title!r}")
    print(f"Scenes: {len(scenes)}")
    print(f"Output: {out_dir}/")
    print()

    manifest = {
        "title": title,
        "slug": slug,
        "target_duration_sec": data.get("target_duration_sec"),
        "attribution": attribution,
        "share_token": token,
        "scenes": [],
    }

    readme_lines = [
        f"# {title} — Scooby scene export",
        "",
        f"Exported from share token `{token[:16]}...` for TopView eval.",
        f"Target episode length: {data.get('target_duration_sec')}s across {len(scenes)} scenes.",
        "",
        "## Scenes",
        "",
    ]

    for scene in scenes:
        order = scene["scene_order"]
        beat = scene["beat_label"]
        prompt = scene["visual_description"]
        narration = scene.get("narration_text") or ""
        duration = scene.get("duration_sec")

        # First image asset (there may be audio too; we only want the image for i2v)
        image_asset = next(
            (a for a in scene.get("assets", []) if a.get("asset_type") == "image"),
            None,
        )
        local_image = ""
        if image_asset:
            asset_url = f"{BACKEND}{image_asset['url']}"
            local_image = os.path.join(out_dir, f"scene_{order:02d}.png")
            print(f"  [{order:02d}] {beat:20s} downloading...")
            img_resp = requests.get(asset_url, timeout=60)
            img_resp.raise_for_status()
            with open(local_image, "wb") as f:
                f.write(img_resp.content)

        manifest["scenes"].append({
            "scene_order": order,
            "beat_label": beat,
            "visual_description": prompt,
            "narration_text": narration,
            "duration_sec": duration,
            "local_image": local_image,
            "asset_id": image_asset["id"] if image_asset else None,
        })

        readme_lines.extend([
            f"### Scene {order:02d} — {beat} ({duration}s)",
            "",
            f"**Image:** `{os.path.basename(local_image)}`" if local_image else "_no image_",
            "",
            f"**Visual description (t2v prompt candidate):**",
            f"> {prompt}",
            "",
            f"**Narration:**",
            f"> {narration}",
            "",
        ])

    # Write manifest JSON
    manifest_path = os.path.join(out_dir, "scenes.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Pick suggested inputs for the TopView eval scripts:
    #   - Scene 1 image = the "hero" scene for i2v tests
    #   - Any earlier scene with the protagonist clearly visible = character ref
    hero_scene = manifest["scenes"][0] if manifest["scenes"] else None
    char_scene = next(
        (s for s in manifest["scenes"] if "close" in s["visual_description"].lower() or "face" in s["visual_description"].lower()),
        hero_scene,
    )
    # Prefer a different scene for character ref if possible (scene with character visible,
    # that's not the same as the hero scene — avoids feeding the same image twice)
    alt_char_scene = next(
        (s for s in manifest["scenes"] if s is not hero_scene),
        None,
    )

    readme_lines.extend([
        "## Suggested TopView eval commands",
        "",
        "Copy/paste these after `cd`ing to the scooby repo root.",
        "",
    ])

    if hero_scene and hero_scene["local_image"]:
        readme_lines.extend([
            "### Image → Video with a real Scooby scene image",
            "",
            "```powershell",
            f'python scripts/test_topview_image2video.py "{os.path.abspath(hero_scene["local_image"])}" --model kling_2.6',
            f'python scripts/test_topview_image2video.py "{os.path.abspath(hero_scene["local_image"])}" --model vidu_q3_pro',
            f'python scripts/test_topview_image2video.py "{os.path.abspath(hero_scene["local_image"])}" --model seedance_1.0_pro_fast',
            "```",
            "",
        ])

    if hero_scene:
        readme_lines.extend([
            "### Text → Video with the real Scooby scene prompt",
            "",
            "Edit `SCENE_PROMPT` in `scripts/test_topview_text2video.py` to:",
            "",
            f"> {hero_scene['visual_description']}",
            "",
            "Then:",
            "```powershell",
            "python scripts/test_topview_text2video.py --model seedance_1.5_pro",
            "python scripts/test_topview_text2video.py --model kling_v3",
            "```",
            "",
        ])

    if hero_scene and alt_char_scene and hero_scene["local_image"] and alt_char_scene["local_image"]:
        readme_lines.extend([
            "### Character-consistency test (Seedance 2.0 Standard)",
            "",
            "Passes the hero scene as `<<<Image1>>>` and a second scene (showing",
            "the same character) as `<<<Image2>>>`. If Seedance 2.0 locks the",
            "character's face/clothing across both references, that's the",
            "premium-tier win for Scooby.",
            "",
            "```powershell",
            f'python scripts/test_topview_omni_reference.py "{os.path.abspath(hero_scene["local_image"])}" "{os.path.abspath(alt_char_scene["local_image"])}" --model seedance_2.0_standard',
            "```",
            "",
            "```powershell",
            "# Also worth trying — single-image Seedance 2.0 Fast for direct comparison",
            f'python scripts/test_topview_omni_reference.py "{os.path.abspath(hero_scene["local_image"])}" --model seedance_2.0_fast',
            "```",
            "",
        ])

    readme_lines.extend([
        "---",
        "",
        f"See `scenes.json` for the full machine-readable manifest.",
    ])

    readme_path = os.path.join(out_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines))

    print()
    print("=" * 60)
    print(f"✓ {len(manifest['scenes'])} scenes exported")
    print(f"  Manifest: {manifest_path}")
    print(f"  README:   {readme_path}")
    print()
    print("Next steps are listed in the README. Key ones:")
    if hero_scene and hero_scene["local_image"]:
        print(f"  i2v test: use {hero_scene['local_image']}")
    if hero_scene:
        print(f"  t2v test: scene 1 prompt = {hero_scene['visual_description'][:80]}...")
    if hero_scene and alt_char_scene:
        print(f"  char-consistency: scene 1 + scene {alt_char_scene['scene_order']}")


if __name__ == "__main__":
    main()
