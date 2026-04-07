"""Side-by-side comparison: Stability AI vs Nanobanana 2.

Usage:
    STABILITY_API_KEY=xxx GOOGLE_API_KEY=xxx python scripts/compare_generations.py

Generates the same 3 scene prompts via both providers and saves outputs
side by side for visual comparison.

Outputs saved to: test_generations/comparison/
"""

from __future__ import annotations

import os
import sys
import time

# Check API keys
stability_key = os.environ.get("STABILITY_API_KEY")
google_key = os.environ.get("GOOGLE_API_KEY")

missing = []
if not stability_key:
    missing.append("STABILITY_API_KEY")
if not google_key:
    missing.append("GOOGLE_API_KEY")
if missing:
    print(f"ERROR: Set environment variables: {', '.join(missing)}")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

# Shared test prompts
PROMPTS = [
    {
        "name": "kitchen_night",
        "text": (
            "A dimly lit apartment kitchen at night. A woman in her 30s sits at a "
            "cluttered table, staring at a handwritten letter. Warm amber light from "
            "a single hanging bulb. Cinematic mood, shallow depth of field. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
    {
        "name": "city_street",
        "text": (
            "A bustling city street at golden hour. A young man walks away from "
            "camera, shoulders hunched, carrying a worn leather bag. Neon signs "
            "reflect off wet pavement. Shallow depth of field, dramatic lighting. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
    {
        "name": "cafe_hands",
        "text": (
            "Close-up of two hands reaching across a small cafe table, fingers "
            "almost touching. Steam rises from coffee cups. Soft warm bokeh "
            "background with fairy lights. Emotional, intimate moment. "
            "Vertical 9:16 portrait composition, 1080x1920."
        ),
    },
]

output_dir = os.path.join("test_generations", "comparison")
os.makedirs(output_dir, exist_ok=True)


def generate_stability(prompt: str) -> tuple[bytes | None, float]:
    """Generate image via Stability AI SDXL. Returns (png_bytes, elapsed_seconds)."""
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    start = time.time()
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {stability_key}",
                "Content-Type": "application/json",
                "Accept": "image/png",
            },
            json={
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "width": 768,
                "height": 1344,
                "samples": 1,
                "steps": 30,
            },
        )
        elapsed = time.time() - start
        if resp.status_code == 200:
            return resp.content, elapsed
        else:
            print(f"    Stability error {resp.status_code}: {resp.text[:200]}")
            return None, elapsed


def generate_nanobanana2(prompt: str) -> tuple[bytes | None, float]:
    """Generate image via Nanobanana 2. Returns (png_bytes, elapsed_seconds)."""
    import io

    client = genai.Client(api_key=google_key)
    start = time.time()
    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )
    elapsed = time.time() - start

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return buf.getvalue(), elapsed

    return None, elapsed


print("Side-by-Side Comparison: Stability AI vs Nanobanana 2")
print("=" * 55)
print(f"Prompts: {len(PROMPTS)}")
print(f"Output: {output_dir}/")
print()

stability_results = []
nb2_results = []

for i, p in enumerate(PROMPTS):
    print(f"[{i + 1}/{len(PROMPTS)}] {p['name']}")

    # Stability AI
    print("  Stability AI SDXL...", end=" ", flush=True)
    try:
        img_bytes, elapsed = generate_stability(p["text"])
        if img_bytes:
            path = os.path.join(output_dir, f"{p['name']}_stability.png")
            with open(path, "wb") as f:
                f.write(img_bytes)
            print(f"OK ({elapsed:.1f}s, {len(img_bytes) / 1024:.0f} KB)")
            stability_results.append({"name": p["name"], "ok": True, "time": elapsed, "size": len(img_bytes)})
        else:
            print(f"NO IMAGE ({elapsed:.1f}s)")
            stability_results.append({"name": p["name"], "ok": False, "time": elapsed})
    except Exception as e:
        print(f"ERROR: {e}")
        stability_results.append({"name": p["name"], "ok": False, "error": str(e)})

    # Nanobanana 2
    print("  Nanobanana 2.......", end=" ", flush=True)
    try:
        img_bytes, elapsed = generate_nanobanana2(p["text"])
        if img_bytes:
            path = os.path.join(output_dir, f"{p['name']}_nanobanana2.png")
            with open(path, "wb") as f:
                f.write(img_bytes)
            print(f"OK ({elapsed:.1f}s, {len(img_bytes) / 1024:.0f} KB)")
            nb2_results.append({"name": p["name"], "ok": True, "time": elapsed, "size": len(img_bytes)})
        else:
            print(f"NO IMAGE ({elapsed:.1f}s)")
            nb2_results.append({"name": p["name"], "ok": False, "time": elapsed})
    except Exception as e:
        print(f"ERROR: {e}")
        nb2_results.append({"name": p["name"], "ok": False, "error": str(e)})

    print()

# Summary
print("=" * 55)
print("COMPARISON SUMMARY")
print("=" * 55)
print()
print(f"{'':20s} {'Stability AI':>15s} {'Nanobanana 2':>15s}")
print("-" * 55)

s_ok = [r for r in stability_results if r.get("ok")]
n_ok = [r for r in nb2_results if r.get("ok")]

print(f"{'Success':20s} {len(s_ok)}/{len(PROMPTS):>13} {len(n_ok)}/{len(PROMPTS):>13}")

if s_ok:
    s_avg_t = sum(r["time"] for r in s_ok) / len(s_ok)
    s_avg_s = sum(r["size"] for r in s_ok) / len(s_ok) / 1024
else:
    s_avg_t = s_avg_s = 0

if n_ok:
    n_avg_t = sum(r["time"] for r in n_ok) / len(n_ok)
    n_avg_s = sum(r["size"] for r in n_ok) / len(n_ok) / 1024
else:
    n_avg_t = n_avg_s = 0

print(f"{'Avg time':20s} {s_avg_t:>14.1f}s {n_avg_t:>14.1f}s")
print(f"{'Avg size':20s} {s_avg_s:>12.0f} KB {n_avg_s:>12.0f} KB")
print(f"{'Est. cost/image':20s} {'~$0.03-0.06':>15s} {'~$0.067':>15s}")
print(f"{'Batch cost/image':20s} {'N/A':>15s} {'~$0.034':>15s}")
print()
print(f"Output: {output_dir}/")
print("Open both images side by side to compare quality visually.")
