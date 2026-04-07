"""YouTube transcript extraction and cleaning service."""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


@dataclass
class TranscriptResult:
    video_id: str
    title: str
    channel: str
    duration_sec: int
    raw_transcript: str
    clean_transcript: str
    word_count: int


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def fetch_transcript(video_id: str, lang: str = "en") -> str:
    """Fetch transcript using youtube-transcript-api.

    Returns raw transcript text with timestamps stripped.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=[lang])
        # Build raw text from transcript snippets
        raw_lines = [snippet.text for snippet in transcript]
        return "\n".join(raw_lines)
    except Exception as e:
        logger.error("youtube-transcript-api failed for %s: %s", video_id, e)
        raise


def clean_transcript(raw_text: str) -> str:
    """Clean and deduplicate YouTube transcript text.

    Auto-generated captions have overlapping segments with duplicate lines.
    This removes duplicates while preserving speaking order, strips HTML tags,
    and merges into clean paragraphs.
    """
    seen: set[str] = set()
    clean_lines: list[str] = []

    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip HTML tags (YouTube sometimes includes <font> etc.)
        line = re.sub(r"<[^>]*>", "", line)
        # Decode HTML entities
        line = line.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")
        line = line.replace("&#39;", "'").replace("&quot;", '"')

        if line and line not in seen:
            clean_lines.append(line)
            seen.add(line)

    # Join into paragraphs — group sentences together
    text = " ".join(clean_lines)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_metadata(video_id: str) -> dict:
    """Fetch video metadata using yt-dlp --print.

    Returns dict with channel, title, duration, upload_date.
    """
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--print", "%(channel)s",
                "--print", "%(title)s",
                "--print", "%(duration)s",
                "--print", "%(upload_date)s",
                "--no-download",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("yt-dlp metadata failed: %s", result.stderr)
            raise RuntimeError(f"yt-dlp failed: {result.stderr}")

        lines = result.stdout.strip().split("\n")
        return {
            "channel": lines[0] if len(lines) > 0 else "Unknown",
            "title": lines[1] if len(lines) > 1 else "Unknown",
            "duration_sec": int(lines[2]) if len(lines) > 2 else 0,
            "upload_date": lines[3] if len(lines) > 3 else "",
        }
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timed out for video %s", video_id)
        raise RuntimeError("Metadata fetch timed out")


def fetch_full_transcript(url: str) -> TranscriptResult:
    """Full pipeline: extract video ID, fetch transcript + metadata, clean.

    This is the main entry point for the YouTube import flow.
    """
    video_id = extract_video_id(url)
    raw_text = fetch_transcript(video_id)
    clean_text = clean_transcript(raw_text)
    metadata = fetch_metadata(video_id)

    return TranscriptResult(
        video_id=video_id,
        title=metadata["title"],
        channel=metadata["channel"],
        duration_sec=metadata["duration_sec"],
        raw_transcript=raw_text,
        clean_transcript=clean_text,
        word_count=len(clean_text.split()),
    )
