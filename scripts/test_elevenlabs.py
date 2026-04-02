"""Quick test: verify ElevenLabs API key and voice IDs work."""

import os
import sys

import dotenv
dotenv.load_dotenv()

import httpx

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
if not API_KEY:
    print("ERROR: ELEVENLABS_API_KEY not set in .env")
    sys.exit(1)

print(f"Key loaded: {API_KEY[:8]}...{API_KEY[-4:]}")
print()

VOICES_TO_TEST = [
    ("EXAVITQu4vr4xnSDxMaL", "Sarah"),
    ("JBFqnCBsd6RMkjVDRZzb", "George"),
]

TEXT = "She sat at the kitchen table, staring at the envelope."

for voice_id, name in VOICES_TO_TEST:
    print(f"Testing {name} ({voice_id})...", end=" ")
    try:
        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": TEXT,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                },
            },
            timeout=30,
        )
        if resp.status_code == 200:
            print(f"OK ({len(resp.content):,} bytes)")
        else:
            print(f"FAILED — HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"ERROR — {e}")

print()
print("Done. If both show OK, the key and voices work.")
