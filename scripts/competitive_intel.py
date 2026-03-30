"""
Scooby — Competitive Intelligence Report Generator

Uses FireCrawl to scrape competitor landing pages in the AI video/story space,
then generates a Markdown report with design patterns, trust signals, SEO insights,
and a recommended blueprint for Scooby's branding.

Usage:
    pip install -r scripts/requirements.txt
    python scripts/competitive_intel.py
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COMPETITORS = [
    {"name": "Pictory", "url": "https://pictory.ai", "category": "AI text-to-video"},
    {"name": "InVideo", "url": "https://invideo.io", "category": "AI video creation"},
    {"name": "Lumen5", "url": "https://lumen5.com", "category": "Blog-to-video"},
    {"name": "Kapwing", "url": "https://kapwing.com", "category": "Online video editor"},
    {"name": "Canva Video", "url": "https://canva.com/video", "category": "Design platform (video)"},
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "docs" / "research" / "raw"
REPORT_PATH = PROJECT_ROOT / "docs" / "research" / "Competitive_Intelligence.md"

# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------


def scrape_competitor(app: FirecrawlApp, competitor: dict) -> dict:
    """Scrape a single competitor landing page and return structured data."""
    name = competitor["name"]
    url = competitor["url"]
    print(f"  Scraping {name} ({url})...")

    try:
        result = app.scrape_url(
            url,
            params={
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
            },
        )
    except Exception as e:
        print(f"  WARNING: Failed to scrape {name}: {e}")
        return {
            "name": name,
            "url": url,
            "category": competitor["category"],
            "error": str(e),
        }

    metadata = result.get("metadata", {})
    markdown = result.get("markdown", "")
    html = result.get("html", "")

    # Extract structured fields from metadata and content
    data = {
        "name": name,
        "url": url,
        "category": competitor["category"],
        "scraped_at": datetime.now().isoformat(),
        "metadata": {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "og_title": metadata.get("og:title", metadata.get("ogTitle", "")),
            "og_description": metadata.get("og:description", metadata.get("ogDescription", "")),
            "og_image": metadata.get("og:image", metadata.get("ogImage", "")),
            "keywords": metadata.get("keywords", ""),
        },
        "content": {
            "markdown_length": len(markdown),
            "markdown_preview": markdown[:3000],
            "headings": extract_headings(markdown),
            "cta_phrases": extract_ctas(markdown),
            "trust_signals": extract_trust_signals(markdown),
        },
        "colors": extract_colors_from_html(html),
    }

    return data


def extract_headings(markdown: str) -> list[str]:
    """Pull all headings from markdown content."""
    return re.findall(r"^#{1,3}\s+(.+)$", markdown, re.MULTILINE)[:20]


def extract_ctas(markdown: str) -> list[str]:
    """Find CTA-like phrases in the content."""
    cta_patterns = [
        r"(?i)(get started[^.\n]*)",
        r"(?i)(start free[^.\n]*)",
        r"(?i)(try .{0,30} free[^.\n]*)",
        r"(?i)(sign up[^.\n]*)",
        r"(?i)(create .{0,20} now[^.\n]*)",
        r"(?i)(start creating[^.\n]*)",
        r"(?i)(no credit card[^.\n]*)",
        r"(?i)(free trial[^.\n]*)",
        r"(?i)(join .{0,30} users[^.\n]*)",
        r"(?i)(transform .{0,40}video[^.\n]*)",
    ]
    results = []
    for pattern in cta_patterns:
        matches = re.findall(pattern, markdown)
        results.extend(m.strip() for m in matches)
    return list(dict.fromkeys(results))[:15]  # dedupe, cap at 15


def extract_trust_signals(markdown: str) -> list[str]:
    """Find trust signals: numbers, social proof, brand mentions."""
    patterns = [
        r"(?i)(\d[\d,.]+ (?:million|users|customers|creators|videos|businesses)[^.\n]*)",
        r"(?i)(trusted by[^.\n]*)",
        r"(?i)(used by[^.\n]*)",
        r"(?i)(as (?:seen|featured) (?:in|on)[^.\n]*)",
        r"(?i)(rated \d[^.\n]*)",
        r"(?i)(\d+\+?\s*(?:star|stars)[^.\n]*)",
        r"(?i)(enterprise[- ]grade[^.\n]*)",
        r"(?i)(SOC\s*2[^.\n]*)",
        r"(?i)(GDPR[^.\n]*)",
    ]
    results = []
    for pattern in patterns:
        matches = re.findall(pattern, markdown)
        results.extend(m.strip() for m in matches)
    return list(dict.fromkeys(results))[:15]


def extract_colors_from_html(html: str) -> list[str]:
    """Extract hex color values mentioned in inline styles or CSS."""
    if not html:
        return []
    hex_colors = re.findall(r"#[0-9a-fA-F]{6}\b", html)
    # Count frequency, return top colors
    from collections import Counter
    counts = Counter(hex_colors)
    # Filter out common black/white/gray
    boring = {"#000000", "#ffffff", "#FFFFFF", "#000", "#fff", "#333333", "#666666", "#999999", "#cccccc", "#CCCCCC"}
    interesting = [(c, n) for c, n in counts.most_common(20) if c.upper() not in {b.upper() for b in boring}]
    return [c for c, _ in interesting[:8]]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(all_data: list[dict]) -> str:
    """Generate the Markdown competitive intelligence report."""
    now = datetime.now().strftime("%Y-%m-%d")
    successful = [d for d in all_data if "error" not in d]
    failed = [d for d in all_data if "error" in d]

    lines = [
        "# Scooby — Competitive Intelligence Report",
        "",
        f"> **Generated:** {now}",
        f"> **Competitors analyzed:** {len(successful)}/{len(all_data)}",
        "> **Tool:** FireCrawl API + automated extraction",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    # Summary
    all_ctas = []
    all_trust = []
    all_colors = []
    for d in successful:
        all_ctas.extend(d["content"].get("cta_phrases", []))
        all_trust.extend(d["content"].get("trust_signals", []))
        all_colors.extend(d.get("colors", []))

    lines.append(f"Analyzed {len(successful)} competitor landing pages in the AI video creation space. ")
    lines.append("Key findings:")
    lines.append("")

    # Common CTA themes
    cta_lower = [c.lower() for c in all_ctas]
    free_count = sum(1 for c in cta_lower if "free" in c)
    lines.append(f"- **CTA patterns:** {len(all_ctas)} CTAs found across competitors; {free_count} mention \"free\" — low-friction entry is table stakes")

    if all_trust:
        lines.append(f"- **Trust signals:** {len(all_trust)} social proof elements found — user counts, brand logos, and ratings dominate")

    if all_colors:
        from collections import Counter
        top_colors = Counter(all_colors).most_common(5)
        color_str = ", ".join(f"`{c}` ({n}x)" for c, n in top_colors)
        lines.append(f"- **Dominant brand colors:** {color_str}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Individual competitor profiles
    lines.append("## Competitor Profiles")
    lines.append("")

    for d in successful:
        meta = d["metadata"]
        content = d["content"]
        colors = d.get("colors", [])

        lines.append(f"### {d['name']}")
        lines.append(f"**URL:** {d['url']}  ")
        lines.append(f"**Category:** {d['category']}")
        lines.append("")

        # Meta / positioning
        lines.append("**Positioning:**")
        if meta.get("title"):
            lines.append(f"- Title: *{meta['title']}*")
        if meta.get("description"):
            lines.append(f"- Meta description: *{meta['description'][:200]}*")
        if meta.get("og_title") and meta["og_title"] != meta.get("title"):
            lines.append(f"- OG title: *{meta['og_title']}*")
        lines.append("")

        # Page structure
        headings = content.get("headings", [])
        if headings:
            lines.append("**Page Structure (headings):**")
            for h in headings[:10]:
                lines.append(f"- {h}")
            lines.append("")

        # CTAs
        ctas = content.get("cta_phrases", [])
        if ctas:
            lines.append("**CTAs:**")
            for c in ctas[:8]:
                lines.append(f"- {c}")
            lines.append("")

        # Trust signals
        trust = content.get("trust_signals", [])
        if trust:
            lines.append("**Trust Signals:**")
            for t in trust[:8]:
                lines.append(f"- {t}")
            lines.append("")

        # Colors
        if colors:
            lines.append("**Brand Colors (from CSS):**")
            color_blocks = " ".join(f"`{c}`" for c in colors[:6])
            lines.append(color_blocks)
            lines.append("")

        lines.append("---")
        lines.append("")

    # Failed scrapes
    if failed:
        lines.append("### Scrape Failures")
        lines.append("")
        for d in failed:
            lines.append(f"- **{d['name']}** ({d['url']}): {d['error']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Common patterns
    lines.append("## Common Patterns Across Winners")
    lines.append("")

    # Aggregate headings to find common section types
    all_headings_lower = []
    for d in successful:
        all_headings_lower.extend(h.lower() for h in d["content"].get("headings", []))

    section_types = {
        "pricing": sum(1 for h in all_headings_lower if "pric" in h),
        "features": sum(1 for h in all_headings_lower if "feature" in h or "what you" in h),
        "how it works": sum(1 for h in all_headings_lower if "how" in h and "work" in h),
        "testimonials": sum(1 for h in all_headings_lower if "testimon" in h or "review" in h or "customer" in h),
        "use cases": sum(1 for h in all_headings_lower if "use case" in h or "who" in h),
        "integrations": sum(1 for h in all_headings_lower if "integrat" in h),
        "FAQ": sum(1 for h in all_headings_lower if "faq" in h or "question" in h),
    }

    lines.append("**Landing page sections by frequency:**")
    lines.append("")
    lines.append("| Section | Competitors with it |")
    lines.append("|---------|-------------------|")
    for section, count in sorted(section_types.items(), key=lambda x: -x[1]):
        if count > 0:
            lines.append(f"| {section.title()} | {count}/{len(successful)} |")
    lines.append("")

    lines.append("**Shared patterns:**")
    lines.append("- Hero with bold headline + subheadline + primary CTA above the fold")
    lines.append("- Social proof near the top (user counts, brand logos)")
    lines.append("- \"How it works\" 3-step explainer (matches Scooby's existing pattern)")
    lines.append("- Feature grid with icons")
    lines.append("- Free tier or trial as the primary CTA — removes friction")
    lines.append("- Footer with product links, social links, trust badges")
    lines.append("")
    lines.append("---")
    lines.append("")

    # SEO landscape
    lines.append("## SEO Landscape")
    lines.append("")
    lines.append("**Keywords extracted from competitor meta tags and headings:**")
    lines.append("")

    all_keywords = set()
    for d in successful:
        kw = d["metadata"].get("keywords", "")
        if kw:
            all_keywords.update(k.strip().lower() for k in kw.split(",") if k.strip())
        for h in d["content"].get("headings", []):
            words = h.lower()
            if any(term in words for term in ["video", "ai", "create", "edit", "story", "content", "text"]):
                all_keywords.add(h.lower().strip())

    if all_keywords:
        for kw in sorted(all_keywords)[:25]:
            lines.append(f"- {kw}")
    else:
        lines.append("- *(No explicit keyword meta tags found — competitors may rely on content-based SEO)*")
    lines.append("")

    lines.append("**Opportunity keywords for Scooby:**")
    lines.append("- \"story to video\" / \"turn story into video\"")
    lines.append("- \"AI story video maker\"")
    lines.append("- \"writer video tool\"")
    lines.append("- \"vertical drama creator\"")
    lines.append("- \"short story video generator\"")
    lines.append("- \"text to vertical video\"")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Blueprint
    lines.append("## Recommended Blueprint for Scooby")
    lines.append("")
    lines.append("Based on the patterns above, here's the recommended landing page structure:")
    lines.append("")
    lines.append("### Page Structure")
    lines.append("1. **Hero** — Bold headline + subheadline + primary CTA + scroll-triggered animation (story text → video)")
    lines.append("2. **Social proof bar** — User count, testimonials, or \"as seen in\" logos")
    lines.append("3. **How it works** — 3-step visual (Write → Edit → Watch) — already exists, refine")
    lines.append("4. **Feature showcase** — 4-6 feature cards with icons — already exists, refine")
    lines.append("5. **Live demo / preview** — Interactive before/after or embedded preview")
    lines.append("6. **Use cases** — \"For fiction writers\", \"For BookTok creators\", \"For educators\"")
    lines.append("7. **Testimonials** — Real quotes (start with cofounder, early testers)")
    lines.append("8. **Final CTA** — Repeat primary CTA with urgency or benefit")
    lines.append("9. **Footer** — Links, social, legal")
    lines.append("")
    lines.append("### Color Direction")
    lines.append("- Review the competitor color palettes above")
    lines.append("- Current Scooby: monochrome with violet-to-indigo gradient (hero text only)")
    lines.append("- Recommendation: strengthen the violet/indigo as the primary brand color, add a warm accent for CTAs")
    lines.append("- Avoid: pure blue (too generic/corporate), pure red (too aggressive)")
    lines.append("")
    lines.append("### Hero Animation Concept")
    lines.append("- Scroll-triggered transformation: raw story text on the left dissolves into a finished video scene on the right")
    lines.append("- Communicates the core value prop instantly without reading a word of copy")
    lines.append("- Technique: generate before/after images, create a video transition, embed as scroll-locked element")
    lines.append("")
    lines.append("### Trust Signals to Add")
    lines.append("- Number of stories transformed (even if small: \"50+ stories brought to life\")")
    lines.append("- Processing time (\"90 seconds of video in under 5 minutes\")")
    lines.append("- Writer-focused positioning (\"Built for writers, not editors\")")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key or api_key.startswith("fc-your-"):
        print("ERROR: Set FIRECRAWL_API_KEY in .env (sign up at https://firecrawl.dev)")
        sys.exit(1)

    print(f"FireCrawl Competitive Intelligence — {len(COMPETITORS)} competitors")
    print(f"Output: {REPORT_PATH}")
    print()

    app = FirecrawlApp(api_key=api_key)

    # Ensure output dirs exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_data = []
    for i, competitor in enumerate(COMPETITORS):
        data = scrape_competitor(app, competitor)
        all_data.append(data)

        # Save raw data
        safe_name = competitor["name"].lower().replace(" ", "_")
        raw_path = RAW_DIR / f"{safe_name}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved raw data to {raw_path}")

        # Rate limit courtesy — don't hammer the API
        if i < len(COMPETITORS) - 1:
            print("  Waiting 2s...")
            time.sleep(2)

    print()
    print("Generating report...")
    report = generate_report(all_data)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to {REPORT_PATH}")
    print("Done!")


if __name__ == "__main__":
    main()
