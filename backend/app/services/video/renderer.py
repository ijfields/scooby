"""Remotion video rendering service."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

REMOTION_PROJECT_DIR = Path(settings.REMOTION_SIDECAR_PATH)


class VideoRenderError(Exception):
    pass


def render_video(composition_data: dict, output_path: str) -> str:
    """Invoke Remotion CLI to render the final video.

    Returns path to the rendered MP4 file.
    """
    props_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    json.dump(composition_data, props_file)
    props_file.close()

    total_frames = composition_data["totalDurationFrames"]

    cmd = [
        "npx",
        "remotion",
        "render",
        str(REMOTION_PROJECT_DIR / "src" / "index.ts"),
        "EpisodeVideo",
        output_path,
        f"--props={props_file.name}",
        "--width=1080",
        "--height=1920",
        "--fps=30",
        f"--frames=0-{total_frames - 1}",
        "--codec=h264",
        "--crf=18",
        "--pixel-format=yuv420p",
        "--audio-codec=aac",
        "--audio-bitrate=192K",
        "--log=verbose",
        "--timeout=600000",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(REMOTION_PROJECT_DIR),
    )

    if result.returncode != 0:
        raise VideoRenderError(
            f"Remotion render failed (exit code {result.returncode}):\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    return output_path
