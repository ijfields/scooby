"""Build a shareable HTML review page for TopView eval videos.

Reads test_generations/topview_results.csv, groups successful runs by
kind (i2v / t2v), and emits test_generations/partner_review.html — a
single-file page a non-technical reviewer can open in any browser,
watch the clips side-by-side, and type notes in.

Usage:
    python scripts/build_topview_review_page.py

To share: zip test_generations/partner_review.html together with
the topview/ and topview_t2v/ subfolders (so the relative video paths
resolve). Or drop the whole test_generations folder into Google Drive
and share that link.
"""

from __future__ import annotations

import csv
import html
import os
from datetime import datetime

RESULTS_CSV = os.path.join("test_generations", "topview_results.csv")
# Named index.html so Netlify (or any static host) serves it at the site root.
OUTPUT_HTML = os.path.join("test_generations", "index.html")

# Human-readable labels, grouped by kind. Keep technical model names in
# small text below for reference but lead with the partner-friendly summary.
FRIENDLY = {
    "kling_2.6": {
        "title": "Option A — Warm & cheap",
        "subtitle": "Kling 2.6",
        "blurb": "Budget tier. Includes sound. Good starting point.",
        "tier_badge": "💰 budget",
    },
    "vidu_q3_pro": {
        "title": "Option B — Mid-range with sound",
        "subtitle": "Vidu Q3 Pro",
        "blurb": "Flexible scene length (1–16s). Includes sound.",
        "tier_badge": "💰💰 mid",
    },
    "seedance_1.0_pro_fast": {
        "title": "Option C — Ultra cheap, no sound",
        "subtitle": "Seedance 1.0 Pro Fast",
        "blurb": "Remarkably cheap — roughly 10× cheaper per second than Option A. No sound though; we'd need to add music/voiceover separately.",
        "tier_badge": "💰 ultra-budget",
    },
    "seedance_2.0_fast": {
        "title": "Option H — Latest model (fast tier)",
        "subtitle": "Seedance 2.0 Fast",
        "blurb": "ByteDance's newest model — supports multi-image reference for character consistency across scenes. Premium price (~5 credits for 5s with sound, free audio included).",
        "tier_badge": "💎 premium",
    },
    "seedance_2.0_standard": {
        "title": "Option I — Latest model, best quality",
        "subtitle": "Seedance 2.0 Standard",
        "blurb": "ByteDance's flagship. Multi-image reference for character consistency — lets us lock a character's look once and keep it across all 8 scenes of an episode. Free native audio.",
        "tier_badge": "💎💎 flagship",
    },
    "sora_2_pro_i2v": {
        "title": "Option D — Blocked",
        "subtitle": "Sora 2 Pro (Image → Video)",
        "blurb": "Rejected by the model's safety filter because the source image shows a person's face. Not a viable option for character-driven scenes.",
        "tier_badge": "⛔ blocked",
    },
    # t2v variants — same models, different mode
    "kling_v3": {
        "title": "Option E — Cheap tier, with sound",
        "subtitle": "Kling V3 (prompt only)",
        "blurb": "Budget option for the prompt-only path. Includes sound.",
        "tier_badge": "💰 budget",
    },
    "sora_2_pro": {
        "title": "Option F — Premium tier, no sound",
        "subtitle": "Sora 2 Pro (prompt only)",
        "blurb": "Most expensive of the bunch. No sound. Known for realistic motion.",
        "tier_badge": "💰💰💰 premium",
    },
    "seedance_1.5_pro": {
        "title": "Option G — Premium with sound",
        "subtitle": "Seedance 1.5 pro (prompt only)",
        "blurb": "Premium quality with native sound. Cheaper than Option F.",
        "tier_badge": "💰💰 mid-premium",
    },
}


def load_runs() -> list[dict]:
    """Load successful runs from the results CSV."""
    if not os.path.isfile(RESULTS_CSV):
        raise SystemExit(f"ERROR: {RESULTS_CSV} not found — run the eval scripts first.")
    with open(RESULTS_CSV, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Keep successful ones + the interesting moderation failure
    return [
        r for r in rows
        if r["status"] in ("ok", "failed")
    ]


def friendly_key(row: dict) -> str:
    """Map a row to its FRIENDLY entry key."""
    # Distinguish sora_2_pro i2v (blocked) from sora_2_pro t2v (ok)
    if row["model_name"] == "sora_2_pro" and row["kind"] == "i2v":
        return "sora_2_pro_i2v"
    return row["model_name"]


def render_card(row: dict) -> str:
    """Render one video card."""
    key = friendly_key(row)
    meta = FRIENDLY.get(key, {
        "title": row["model_display"],
        "subtitle": row["model_name"],
        "blurb": "",
        "tier_badge": "",
    })

    video_path = row["output_path"].replace("\\", "/") if row["output_path"] else ""
    # Make the video path relative to the HTML file (HTML is in test_generations/)
    rel_path = video_path.replace("test_generations/", "") if video_path else ""

    duration_s = row.get("duration_s", "")
    credits = row.get("credits", "")
    dims = row.get("dims", "")
    sound = row.get("sound", "")
    status = row["status"]

    # Blocked runs show a message instead of a video
    if status != "ok":
        video_block = (
            f'<div class="blocked-notice">'
            f'<strong>⛔ Blocked:</strong> {html.escape(row.get("error", "Generation failed."))}'
            f'</div>'
        )
        facts = f'<span>⏱ tried {duration_s}s</span>'
    else:
        video_block = (
            f'<video controls preload="metadata" playsinline>'
            f'<source src="{html.escape(rel_path)}" type="video/mp4">'
            f'Your browser does not support the video tag.'
            f'</video>'
        )
        fact_bits = [f'<span>⏱ {duration_s}s clip</span>']
        if sound == "on":
            fact_bits.append('<span>🔊 with sound</span>')
        else:
            fact_bits.append('<span>🔇 no sound</span>')
        if credits:
            # Back-of-envelope per-episode cost (8 scenes × clip duration)
            try:
                per_sec = float(credits) / float(duration_s)
                per_episode = per_sec * 8 * 5  # 8 scenes × 5s average
                fact_bits.append(f'<span>💳 ~{per_episode:.1f} credits per episode</span>')
            except (ValueError, ZeroDivisionError):
                pass
        if dims:
            fact_bits.append(f'<span>📱 {dims}</span>')
        facts = "".join(fact_bits)

    return f"""
    <div class="card">
        <h3>{html.escape(meta["title"])} <span class="badge">{html.escape(meta["tier_badge"])}</span></h3>
        <p class="subtitle">{html.escape(meta["subtitle"])}</p>
        {video_block}
        <div class="facts">{facts}</div>
        <p class="blurb">{html.escape(meta["blurb"])}</p>
        <label>
            <span class="label-text">Your thoughts on this one:</span>
            <textarea placeholder="Does this feel like drama? What's off? What's right?"></textarea>
        </label>
    </div>
    """


def render_page(runs: list[dict]) -> str:
    """Render the full HTML page."""
    i2v_runs = [r for r in runs if r["kind"] == "i2v"]
    t2v_runs = [r for r in runs if r["kind"] == "t2v"]
    omni_runs = [r for r in runs if r["kind"] == "omni"]

    i2v_cards = "".join(render_card(r) for r in i2v_runs)
    omni_cards = "".join(render_card(r) for r in omni_runs)

    # Only emit the Omni Reference section if there are actual omni runs — otherwise
    # don't show an empty/confusing section to the non-technical partner.
    if omni_cards:
        omni_section = f"""
<div class="section">
  <div class="section-intro">
    <h2>Seedance 2.0 — multi-image reference (character consistency test)</h2>
    <p>ByteDance's newest model lets us pass multiple reference images at once — a scene setting <em>and</em> a character's likeness — and keep the character consistent across every scene. This is the premium tier. Does the character hold up?</p>
  </div>
  <div class="grid">
    {omni_cards}
  </div>
</div>
"""
    else:
        omni_section = ""
    t2v_cards = "".join(render_card(r) for r in t2v_runs)

    generated = datetime.now().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scooby — TopView AI Video Review</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --violet: #4a2c6f;
    --violet-light: #6b4694;
    --amber: #f4b55e;
    --amber-soft: #fce6bf;
    --cream: #faf8f5;
    --text: #2d1f3a;
    --muted: #6b5e80;
    --border: #e8dfee;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 20px;
    background: var(--cream);
    color: var(--text);
    line-height: 1.5;
  }}
  h1, h2, h3 {{
    font-family: 'Playfair Display', Georgia, serif;
    color: var(--violet);
    line-height: 1.2;
  }}
  h1 {{ font-size: 2.4rem; margin: 0 0 8px; }}
  h2 {{ font-size: 1.6rem; margin: 0 0 8px; }}
  h3 {{ font-size: 1.15rem; margin: 0 0 4px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }}
  .tagline {{ color: var(--muted); font-style: italic; margin-top: 0; }}
  .intro, .footer, .cost-table {{
    background: #fff;
    padding: 24px 28px;
    border-radius: 14px;
    border: 1px solid var(--border);
    box-shadow: 0 2px 12px rgba(74, 44, 111, 0.04);
    margin-bottom: 32px;
  }}
  .intro p {{ margin: 0 0 12px; }}
  .intro ul {{ margin: 8px 0 12px 24px; }}
  .callout {{
    background: var(--amber-soft);
    padding: 12px 16px;
    border-radius: 8px;
    border-left: 4px solid var(--amber);
    margin-top: 12px;
  }}
  .section {{ margin-top: 48px; }}
  .section-intro {{
    background: #fff;
    padding: 20px 24px;
    border-radius: 14px;
    border-left: 4px solid var(--violet);
    margin-bottom: 24px;
  }}
  .section-intro p {{ margin: 8px 0 0; color: var(--muted); }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 20px;
  }}
  .card {{
    background: #fff;
    border-radius: 14px;
    padding: 20px;
    border: 1px solid var(--border);
    box-shadow: 0 2px 12px rgba(74, 44, 111, 0.06);
  }}
  .card .subtitle {{
    font-size: 0.85rem;
    color: var(--muted);
    margin: 0 0 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .card video {{
    width: 100%;
    max-height: 600px;
    object-fit: contain;
    border-radius: 10px;
    background: #000;
    margin: 8px 0 10px;
  }}
  .blocked-notice {{
    background: #fce3e3;
    color: #8b2e2e;
    border: 1px solid #f4b5b5;
    padding: 20px;
    border-radius: 10px;
    margin: 8px 0 10px;
    text-align: center;
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .facts {{ font-size: 0.88rem; color: var(--muted); margin: 6px 0 10px; }}
  .facts span {{ display: inline-block; margin-right: 14px; white-space: nowrap; }}
  .blurb {{ font-size: 0.95rem; color: var(--text); margin: 8px 0 16px; }}
  .badge {{
    display: inline-block;
    background: var(--amber-soft);
    color: var(--violet);
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
  }}
  .label-text {{
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--muted);
    margin-bottom: 4px;
  }}
  textarea {{
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-family: inherit;
    font-size: 0.92rem;
    min-height: 70px;
    resize: vertical;
    background: var(--cream);
  }}
  textarea:focus {{
    outline: none;
    border-color: var(--violet-light);
    background: #fff;
  }}
  .cost-table table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  .cost-table th, .cost-table td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  .cost-table th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  .cost-table tr:last-child td {{ border-bottom: none; }}
  .footer h3 {{ margin-top: 0; }}
  .footer .big-textarea {{ min-height: 120px; }}
  .save-hint {{
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: 12px;
    font-style: italic;
  }}
  .generated {{
    text-align: center;
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 40px;
  }}
</style>
</head>
<body>

<h1>🎬 Scooby — Which AI video feels like drama?</h1>
<p class="tagline">Quick review: pick your favorites and tell me why.</p>

<div class="intro">
  <p>Hi! I'm testing <strong>TopView AI</strong> as the video generation engine for Scooby. Below are short clips from different AI models, all using the same kitchen scene we made earlier (woman at a table, reading a letter).</p>

  <p><strong>There are two sections:</strong></p>
  <ul>
    <li><strong>Image → Video</strong> — our current planned flow. We make a still scene image first (you've seen these in Scooby's preview), then animate it. Lets us review the image before committing.</li>
    <li><strong>Prompt → Video</strong> — skips the image step. Cheaper and faster, but we lose the ability to preview/fix the scene before making the video.</li>
  </ul>

  <div class="callout">
    <strong>All I need from you:</strong> Watch the clips, pick your top 2–3 favorites, type gut-feel notes in the boxes under each one. Ignore the technical labels — just tell me which ones <em>feel right</em> for a drama scene.
  </div>
</div>

<div class="section">
  <div class="section-intro">
    <h2>Image → Video (our default flow)</h2>
    <p>Same source image, animated three different ways. Which movement/mood fits a story scene best?</p>
  </div>
  <div class="grid">
    {i2v_cards}
  </div>
</div>

<div class="section">
  <div class="section-intro">
    <h2>Prompt → Video (no source image)</h2>
    <p>Same written description, each AI model interprets it differently. Which one actually "gets" a dramatic kitchen scene?</p>
  </div>
  <div class="grid">
    {t2v_cards}
  </div>
</div>

{omni_section}

<div class="cost-table">
  <h2>💰 Rough cost per episode</h2>
  <p>For context — an episode is about 8 scenes × 5 seconds each = 40 seconds total. Costs here are in <strong>TopView credits</strong> (we pay for these with our Pro subscription).</p>
  <table>
    <thead>
      <tr>
        <th>Option</th>
        <th>Credits per episode (approx)</th>
        <th>Sound?</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Seedance Fast (Image → Video)</td><td>~3</td><td>❌</td></tr>
      <tr><td>Kling 2.6 (Image → Video)</td><td>~26</td><td>✅</td></tr>
      <tr><td>Vidu Q3 Pro (Image → Video)</td><td>~36</td><td>✅</td></tr>
      <tr><td>Seedance 2.0 Fast (multi-image ref)</td><td>~38</td><td>✅ free</td></tr>
      <tr><td>Seedance 2.0 Standard (multi-image ref)</td><td>~48</td><td>✅ free</td></tr>
      <tr><td>Kling V3 (Prompt only)</td><td>~32</td><td>✅</td></tr>
      <tr><td>Seedance 1.5 pro (Prompt only)</td><td>~10</td><td>✅</td></tr>
      <tr><td>Sora 2 Pro (Prompt only)</td><td>~67</td><td>❌</td></tr>
    </tbody>
  </table>
</div>

<div class="footer">
  <h3>📝 Overall thoughts</h3>
  <p>Any top-line feedback? Favorite of the bunch? Anything that feels off about the whole approach?</p>
  <textarea class="big-textarea" placeholder="Your overall take..."></textarea>
  <p class="save-hint">💡 When you're done, press <strong>Ctrl+S</strong> (or Cmd+S on Mac) to save this page with your notes typed in, and email it back to me. Or just reply with your thoughts in plain text.</p>
</div>

<p class="generated">Generated {generated} · Scooby Phase 0 eval</p>

</body>
</html>
"""


def main() -> None:
    runs = load_runs()
    html_out = render_page(runs)
    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"✓ Built review page: {OUTPUT_HTML}")
    print(f"  {len([r for r in runs if r['kind'] == 'i2v'])} i2v clips")
    print(f"  {len([r for r in runs if r['kind'] == 't2v'])} t2v clips")
    print()
    print("To share with partner:")
    print("  1. Zip test_generations/partner_review.html + test_generations/topview/ + test_generations/topview_t2v/")
    print("  2. Email the zip, or drop the test_generations/ folder into Google Drive and share the link")
    print("  3. They double-click the HTML file, watch, type notes, Ctrl+S to save, email back")


if __name__ == "__main__":
    main()
