"""Test Nanobanana 2 image generation with Scooby scene prompts.

Usage:
    GOOGLE_API_KEY=your-key python scripts/test_nanobanana2.py

Outputs saved to: test_generations/nanobanana2/
"""

from __future__ import annotations

import os
import sys
import time

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: Set GOOGLE_API_KEY environment variable")
    print("  Get one free at: https://ai.google.dev/")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Test prompts matching Scooby's vertical drama style (9:16 portrait)
TEST_PROMPTS = [
    {
        "name": "scene_1_kitchen_night",
        "prompt": (
            "A dimly lit apartment kitchen at night. A woman in her 30s sits at a "
            "cluttered table, staring at a handwritten letter. Warm amber light from "
            "a single hanging bulb. Cinematic mood, shallow depth of field. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
    {
        "name": "scene_2_city_street",
        "prompt": (
            "A bustling city street at golden hour. A young man walks away from "
            "camera, shoulders hunched, carrying a worn leather bag. Neon signs "
            "reflect off wet pavement. Shallow depth of field, dramatic lighting. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
    {
        "name": "scene_3_cafe_hands",
        "prompt": (
            "Close-up of two hands reaching across a small cafe table, fingers "
            "almost touching. Steam rises from coffee cups. Soft warm bokeh "
            "background with fairy lights. Emotional, intimate moment. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
]

output_dir = os.path.join("test_generations", "nanobanana2")
os.makedirs(output_dir, exist_ok=True)

print(f"Generating {len(TEST_PROMPTS)} images with Nanobanana 2...")
print(f"Model: gemini-3.1-flash-image-preview")
print(f"Output: {output_dir}/")
print()

results = []
for i, test in enumerate(TEST_PROMPTS):
    print(f"[{i + 1}/{len(TEST_PROMPTS)}] {test['name']}")
    print(f"  Prompt: {test['prompt'][:80]}...")

    start = time.time()
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[test["prompt"]],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        elapsed = time.time() - start
        saved = False
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                path = os.path.join(output_dir, f"{test['name']}.png")
                image.save(path)
                file_size = os.path.getsize(path)
                print(f"  Saved: {path} ({file_size / 1024:.0f} KB, {elapsed:.1f}s)")
                results.append({"name": test["name"], "status": "ok", "time": elapsed, "size": file_size})
                saved = True
            elif part.text:
                print(f"  Text: {part.text[:120]}")

        if not saved:
            print(f"  WARNING: No image returned ({elapsed:.1f}s)")
            results.append({"name": test["name"], "status": "no_image", "time": elapsed})

    except Exception as e:
        elapsed = time.time() - start
        print(f"  ERROR: {e} ({elapsed:.1f}s)")
        results.append({"name": test["name"], "status": "error", "time": elapsed, "error": str(e)})

    print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
ok = [r for r in results if r["status"] == "ok"]
print(f"  Generated: {len(ok)}/{len(TEST_PROMPTS)}")
if ok:
    avg_time = sum(r["time"] for r in ok) / len(ok)
    avg_size = sum(r["size"] for r in ok) / len(ok)
    print(f"  Avg time: {avg_time:.1f}s")
    print(f"  Avg size: {avg_size / 1024:.0f} KB")
print(f"  Output dir: {output_dir}/")
print()
print("Next: Compare with Stability AI outputs, or run test_kling_animation.py")
