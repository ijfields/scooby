"""Smoke test for the ffmpeg-based video renderer.

Generates synthetic inputs (solid-color images, silent audio) and runs them
through the full render_video() pipeline to validate ffmpeg command
construction end-to-end. No DB, no API keys, no real assets required.

Usage:
    python scripts/test_ffmpeg_renderer.py
    python scripts/test_ffmpeg_renderer.py --keep  (don't clean up tmp files)

Outputs:
    test_output/ffmpeg_renderer/
        inputs/   — synthetic source assets
        final_2scene.mp4
        final_5scene.mp4
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.video import renderer  # noqa: E402

OUT_DIR = Path("test_output/ffmpeg_renderer")
INPUTS_DIR = OUT_DIR / "inputs"


def _gen_color_image(path: Path, color: str, size: str = "1024x1536") -> None:
    """Generate a solid-color PNG via ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color={color}:s={size}:d=0.1",
            "-frames:v", "1",
            str(path),
        ],
        check=True, capture_output=True,
    )


def _gen_silent_audio(path: Path, duration: float) -> None:
    """Generate a silent MP3 of given duration."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(path),
        ],
        check=True, capture_output=True,
    )


def _build_composition(asset_paths: dict, scenes: list[dict]) -> dict:
    """Build a composition dict matching what composer.build_composition_json produces."""
    return {
        "episodeId": "test-episode",
        "totalDurationFrames": sum(s["durationFrames"] for s in scenes),
        "scenes": scenes,
    }


def _patch_prepare_assets(asset_paths: dict) -> None:
    """Monkeypatch _prepare_assets to skip DB and return our pre-built paths."""
    def fake(session, composition, tmp_dir):
        return asset_paths
    renderer._prepare_assets = fake


def _probe(path: Path) -> dict:
    """Run ffprobe and return a summary dict."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,nb_frames,codec_name",
            "-show_entries", "format=duration,size",
            "-of", "default=noprint_wrappers=1",
            str(path),
        ],
        capture_output=True, text=True,
    )
    return {
        "output": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def test_two_scene_render() -> Path:
    """Test: 2 scenes, one with animation clip, one with static image + Ken Burns.
    Both with voiceovers. Exercises xfade crossfade path."""
    print("\n=== Test 1: 2 scenes (static + animated) with crossfade ===")

    img1 = INPUTS_DIR / "img1.png"
    img2 = INPUTS_DIR / "img2.png"
    anim = INPUTS_DIR / "anim.mp4"
    vo1 = INPUTS_DIR / "vo1.mp3"
    vo2 = INPUTS_DIR / "vo2.mp3"

    _gen_color_image(img1, "blue")
    _gen_color_image(img2, "red")

    # Generate an animation clip: 3s of green fading to yellow
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=green:s=1024x1536:d=3:r=30",
            "-c:v", "libx264", "-preset", "ultrafast",
            str(anim),
        ],
        check=True, capture_output=True,
    )

    _gen_silent_audio(vo1, 2.5)
    _gen_silent_audio(vo2, 3.0)

    asset_paths = {
        "img1-id": str(img1),
        "img2-id": str(img2),
        "anim-id": str(anim),
        "vo1-id": str(vo1),
        "vo2-id": str(vo2),
    }
    _patch_prepare_assets(asset_paths)

    scenes = [
        {
            "sceneId": "s1",
            "beatLabel": "Opening",
            "imageAssetId": "img1-id",
            "voiceoverAssetId": "vo1-id",
            "durationFrames": 90,  # 3s
            "image": {"animation": {"endScale": 1.12, "endX": 20, "endY": 10}},
            "captions": [
                {"text": "This is the first scene caption.",
                 "startFrame": 15, "endFrame": 75},
            ],
        },
        {
            "sceneId": "s2",
            "beatLabel": "Hook",
            "animationAssetId": "anim-id",
            "voiceoverAssetId": "vo2-id",
            "durationFrames": 105,  # 3.5s
            "captions": [
                {"text": "Second scene with a longer caption to test wrapping.",
                 "startFrame": 15, "endFrame": 90},
            ],
        },
    ]

    composition = _build_composition(asset_paths, scenes)
    output = OUT_DIR / "final_2scene.mp4"

    renderer.render_video(composition, str(output), session=None)

    assert output.exists(), "Output file not created"
    assert output.stat().st_size > 10_000, "Output suspiciously small"

    probe = _probe(output)
    print(f"OK — {output}")
    print(f"  size: {output.stat().st_size:,} bytes")
    print(probe["output"])
    return output


def test_five_scene_render() -> Path:
    """Test: 5 scenes — exercises the concat_simple path (>4 scenes)."""
    print("\n=== Test 2: 5 scenes (concat demuxer path) ===")

    colors = ["blue", "red", "green", "yellow", "purple"]
    asset_paths: dict[str, str] = {}
    scenes: list[dict] = []

    for i, color in enumerate(colors):
        img = INPUTS_DIR / f"s{i}_img.png"
        _gen_color_image(img, color)
        asset_paths[f"img-{i}"] = str(img)
        scenes.append({
            "sceneId": f"s{i}",
            "beatLabel": f"Scene{i}",
            "imageAssetId": f"img-{i}",
            "durationFrames": 60,  # 2s each
            "image": {"animation": {"endScale": 1.10, "endX": 0, "endY": 0}},
            "captions": [],
        })

    _patch_prepare_assets(asset_paths)
    composition = _build_composition(asset_paths, scenes)
    output = OUT_DIR / "final_5scene.mp4"

    renderer.render_video(composition, str(output), session=None)

    assert output.exists()
    assert output.stat().st_size > 10_000

    probe = _probe(output)
    print(f"OK — {output}")
    print(f"  size: {output.stat().st_size:,} bytes")
    print(probe["output"])
    return output


def test_single_scene_fallback() -> Path:
    """Test: single scene — exercises the concat shortcut (len == 1)."""
    print("\n=== Test 3: 1 scene (no concat) ===")

    img = INPUTS_DIR / "single.png"
    _gen_color_image(img, "orange")

    asset_paths = {"single-id": str(img)}
    _patch_prepare_assets(asset_paths)

    scenes = [{
        "sceneId": "only",
        "beatLabel": "Solo",
        "imageAssetId": "single-id",
        "durationFrames": 60,
        "image": {"animation": {"endScale": 1.15, "endX": 30, "endY": -20}},
        "captions": [],
    }]
    composition = _build_composition(asset_paths, scenes)
    output = OUT_DIR / "final_1scene.mp4"

    renderer.render_video(composition, str(output), session=None)

    assert output.exists()
    probe = _probe(output)
    print(f"OK — {output}")
    print(f"  size: {output.stat().st_size:,} bytes")
    print(probe["output"])
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true",
                        help="keep inputs directory after run")
    args = parser.parse_args()

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    try:
        results.append(test_single_scene_fallback())
        results.append(test_two_scene_render())
        results.append(test_five_scene_render())
    except Exception as e:
        print(f"\nFAIL — {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n=== All {len(results)} tests passed ===")
    for r in results:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
