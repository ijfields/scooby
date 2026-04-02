"""Test all AI service API keys from .env — run locally to verify before deploying."""

import os
import sys

import dotenv
dotenv.load_dotenv()

PASS = "OK"
FAIL = "FAIL"

results = []


def test_elevenlabs():
    import httpx
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        return FAIL, "ELEVENLABS_API_KEY not set"
    resp = httpx.post(
        "https://api.elevenlabs.io/v1/text-to-speech/JBFqnCBsd6RMkjVDRZzb",
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={"text": "Test.", "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=30,
    )
    if resp.status_code == 200:
        return PASS, f"{len(resp.content):,} bytes audio"
    return FAIL, f"HTTP {resp.status_code}: {resp.text[:100]}"


def test_anthropic():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return FAIL, "ANTHROPIC_API_KEY not set"
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say OK"}],
    )
    text = msg.content[0].text.strip()
    return PASS, f'Response: "{text}"'


def test_stability():
    import httpx
    key = os.environ.get("STABILITY_API_KEY", "")
    if not key:
        return FAIL, "STABILITY_API_KEY not set"
    # Just check auth with account endpoint (no credits used)
    resp = httpx.get(
        "https://api.stability.ai/v1/user/account",
        headers={"Authorization": f"Bearer {key}"},
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        credits = data.get("credits", "?")
        return PASS, f"Credits: {credits}"
    return FAIL, f"HTTP {resp.status_code}: {resp.text[:100]}"


print()
print("=" * 60)
print("  Scooby — API Key Verification")
print("=" * 60)
print()

for name, fn in [("ElevenLabs (TTS)", test_elevenlabs),
                 ("Anthropic (Claude)", test_anthropic),
                 ("Stability AI (Images)", test_stability)]:
    print(f"  {name}...", end=" ", flush=True)
    try:
        status, detail = fn()
        print(f"{status} — {detail}")
        results.append((name, status))
    except Exception as e:
        print(f"{FAIL} — {e}")
        results.append((name, FAIL))

print()
print("-" * 60)
passed = sum(1 for _, s in results if s == PASS)
print(f"  {passed}/{len(results)} services OK")

if passed < len(results):
    print()
    print("  IMPORTANT: All three keys must be set on the Railway")
    print("  WORKER service (not just backend) for generation to work.")
    print()
    print("  Railway worker needs: ANTHROPIC_API_KEY, STABILITY_API_KEY,")
    print("  ELEVENLABS_API_KEY, DATABASE_URL, CELERY_BROKER_URL,")
    print("  CELERY_RESULT_BACKEND")

print()
print("=" * 60)
