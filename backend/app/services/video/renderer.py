"""FFmpeg-based video rendering service.

Composes scene images/animations + voiceovers + captions into a
final 9:16 vertical MP4 using ffmpeg subprocess calls.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video_asset import VideoAsset

logger = logging.getLogger(__name__)

# Output specs
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 30
CROSSFADE_SEC = 0.5

# Zoom headroom: scale images up so Ken Burns zoom doesn't reveal edges
ZOOM_HEADROOM = 1.2


class VideoRenderError(Exception):
    pass


def _get_font_path() -> str:
    """Get a bold font path for the current platform."""
    if sys.platform == "win32":
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            # ffmpeg filter syntax: inside single-quoted args, ':' separates
            # options, so it must be escaped with a single backslash. Backslashes
            # are the path separator on Windows — replace them with forward slashes first.
            return path.replace("\\", "/").replace(":", "\\:")
    return ""


def _run_ffmpeg(args: list[str], timeout: int = 120) -> None:
    """Run an ffmpeg command, raising VideoRenderError on failure."""
    cmd = [settings.FFMPEG_PATH] + args
    logger.debug("ffmpeg command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        logger.error("ffmpeg stderr: %s", result.stderr[-2000:])
        raise VideoRenderError(
            f"ffmpeg failed (exit {result.returncode}): {result.stderr[-500:]}"
        )


def _run_ffprobe(filepath: str) -> float:
    """Get duration of an audio/video file in seconds via ffprobe."""
    result = subprocess.run(
        [
            settings.FFPROBE_PATH,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            filepath,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def _prepare_assets(
    session: Session, composition: dict, tmp_dir: str
) -> dict[str, str]:
    """Extract asset blobs from DB to temp files.

    Returns mapping of asset_id -> filepath.
    """
    asset_paths: dict[str, str] = {}
    extensions = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "video/mp4": ".mp4",
        "audio/mpeg": ".mp3",
    }

    asset_ids: set[str] = set()
    for scene in composition.get("scenes", []):
        for key in ("imageAssetId", "voiceoverAssetId", "animationAssetId"):
            aid = scene.get(key)
            if aid:
                asset_ids.add(aid)

    for aid in asset_ids:
        asset = session.execute(
            select(VideoAsset).where(VideoAsset.id == aid)
        ).scalar_one_or_none()
        if not asset or not asset.file_data:
            logger.warning("Asset %s not found or has no data", aid)
            continue

        ext = extensions.get(asset.mime_type, ".bin")
        filepath = os.path.join(tmp_dir, f"asset_{aid}{ext}")
        with open(filepath, "wb") as f:
            f.write(asset.file_data)
        asset_paths[aid] = filepath

    logger.info("Extracted %d assets to %s", len(asset_paths), tmp_dir)
    return asset_paths


def _render_scene_clip(
    scene_spec: dict,
    asset_paths: dict[str, str],
    tmp_dir: str,
    scene_index: int,
) -> tuple[str, float]:
    """Render a single scene as a video clip. Returns (clip_path, duration_sec)."""
    anim_id = scene_spec.get("animationAssetId")
    image_id = scene_spec.get("imageAssetId")
    vo_id = scene_spec.get("voiceoverAssetId")

    # Determine scene duration from voiceover length or composition spec
    comp_duration = scene_spec.get("durationFrames", 150) / FPS
    vo_duration = 0.0
    if vo_id and vo_id in asset_paths:
        vo_duration = _run_ffprobe(asset_paths[vo_id])

    # Scene duration: voiceover length + 0.5s padding, or composition duration
    duration = max(vo_duration + 0.5, comp_duration) if vo_duration > 0 else comp_duration

    clip_path = os.path.join(tmp_dir, f"scene_{scene_index}.mp4")

    if anim_id and anim_id in asset_paths:
        # Animated scene: scale Kling clip to fit 1080x1920
        _render_animated_clip(asset_paths[anim_id], clip_path, duration)
    elif image_id and image_id in asset_paths:
        # Static image scene: Ken Burns zoom/pan
        kb = scene_spec.get("image", {}).get("animation", {})
        _render_ken_burns_clip(asset_paths[image_id], clip_path, duration, kb)
    else:
        # No visual asset — generate black frame
        _run_ffmpeg([
            "-f", "lavfi", "-i", f"color=black:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:r={FPS}",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            clip_path,
        ])

    return clip_path, duration


def _render_animated_clip(anim_path: str, output: str, duration: float) -> None:
    """Scale/pad a Kling animation clip to 1080x1920 and extend if needed."""
    _run_ffmpeg([
        "-i", anim_path,
        "-vf", (
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={FPS},format=yuv420p,"
            f"tpad=stop=-1:stop_mode=clone"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-an",
        output,
    ], timeout=60)


def _render_ken_burns_clip(
    image_path: str, output: str, duration: float, kb_params: dict
) -> None:
    """Apply Ken Burns zoom/pan to a static image.

    Uses half-resolution zoompan then upscales to avoid ffmpeg memory issues
    with large output resolutions.
    """
    end_scale = kb_params.get("endScale", 1.12)
    end_x = kb_params.get("endX", 0)
    end_y = kb_params.get("endY", 0)

    total_frames = int(duration * FPS)

    # Half-resolution for zoompan (avoids malloc failures on 1080x1920)
    half_w = OUTPUT_WIDTH // 2
    half_h = OUTPUT_HEIGHT // 2

    # Zoom increment per frame
    zoom_inc = (end_scale - 1.0) / max(total_frames, 1)

    # Pan expressions scaled to half-res
    pan_x = end_x / 2
    pan_y = end_y / 2

    _run_ffmpeg([
        "-loop", "1", "-i", image_path,
        "-vf", (
            f"scale={half_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={half_w}:{half_h},"
            f"zoompan=z='min(zoom+{zoom_inc:.6f},{end_scale})':"
            f"x='(iw-iw/zoom)/2+{pan_x}*on/{total_frames}':"
            f"y='(ih-ih/zoom)/2+{pan_y}*on/{total_frames}':"
            f"d={total_frames}:s={half_w}x{half_h}:fps={FPS},"
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
            f"format=yuv420p"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        output,
    ], timeout=120)


def _concat_with_transitions(
    scene_clips: list[tuple[str, float]], tmp_dir: str
) -> str:
    """Concatenate scene clips with crossfade transitions."""
    if len(scene_clips) == 1:
        return scene_clips[0][0]

    output = os.path.join(tmp_dir, "concat.mp4")

    # For simplicity with many scenes, use concat demuxer with short crossfades
    # xfade filter chains get complex with 6+ scenes
    if len(scene_clips) > 4:
        return _concat_simple(scene_clips, tmp_dir)

    # Build xfade filter chain for 2-4 scenes
    inputs = []
    for path, _ in scene_clips:
        inputs.extend(["-i", path])

    filter_parts = []
    offset = scene_clips[0][1] - CROSSFADE_SEC
    prev_label = "0:v"

    for i in range(1, len(scene_clips)):
        out_label = f"v{i}" if i < len(scene_clips) - 1 else "vout"
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition=fade:"
            f"duration={CROSSFADE_SEC}:offset={offset:.2f}[{out_label}]"
        )
        prev_label = out_label
        if i < len(scene_clips) - 1:
            offset += scene_clips[i][1] - CROSSFADE_SEC

    _run_ffmpeg(
        inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            output,
        ],
        timeout=180,
    )
    return output


def _concat_simple(
    scene_clips: list[tuple[str, float]], tmp_dir: str
) -> str:
    """Simple concat for 5+ scenes using concat demuxer (no crossfade)."""
    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for path, _ in scene_clips:
            f.write(f"file '{path}'\n")

    output = os.path.join(tmp_dir, "concat.mp4")
    _run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-an", output,
    ], timeout=180)
    return output


def _add_audio(
    video_path: str,
    scene_specs: list[dict],
    scene_durations: list[float],
    asset_paths: dict[str, str],
    tmp_dir: str,
) -> str:
    """Mix voiceovers at correct timestamps onto the video."""
    # Collect voiceover inputs and their delay offsets
    vo_inputs = []
    delays = []
    offset_sec = 0.0

    for i, (spec, dur) in enumerate(zip(scene_specs, scene_durations)):
        vo_id = spec.get("voiceoverAssetId")
        if vo_id and vo_id in asset_paths:
            vo_inputs.append(asset_paths[vo_id])
            # Add small offset for voiceover start (0.5s into scene)
            delay_ms = int((offset_sec + 0.5) * 1000)
            delays.append(delay_ms)
        offset_sec += dur

    if not vo_inputs:
        # No voiceovers — return video as-is
        return video_path

    output = os.path.join(tmp_dir, "with_audio.mp4")

    inputs = ["-i", video_path]
    for vo in vo_inputs:
        inputs.extend(["-i", vo])

    # Build filter: delay each voiceover, then amix
    filter_parts = []
    mix_inputs = []
    for i, delay_ms in enumerate(delays):
        label = f"a{i}"
        filter_parts.append(f"[{i + 1}]adelay={delay_ms}|{delay_ms}[{label}]")
        mix_inputs.append(f"[{label}]")

    mix_str = "".join(mix_inputs)
    filter_parts.append(f"{mix_str}amix=inputs={len(vo_inputs)}:normalize=0[aout]")

    _run_ffmpeg(
        inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output,
        ],
        timeout=120,
    )
    return output


def _burn_captions(
    video_path: str,
    scene_specs: list[dict],
    scene_durations: list[float],
    output_path: str,
) -> str:
    """Overlay caption text on the video using drawtext filter."""
    font_path = _get_font_path()
    if not font_path:
        logger.warning("No font found for captions — skipping")
        # Just copy the video
        _run_ffmpeg(["-i", video_path, "-c", "copy", output_path])
        return output_path

    drawtext_filters = []
    offset_sec = 0.0

    for spec, dur in zip(scene_specs, scene_durations):
        for caption in spec.get("captions", []):
            text = caption.get("text", "")
            if not text:
                continue

            # Escape special characters for ffmpeg drawtext
            text = (
                text.replace("\\", "\\\\")
                .replace("'", "\u2019")
                .replace(":", "\\:")
                .replace("%", "%%")
                .replace("\n", " ")
            )

            # Wrap long text (max ~35 chars per line for 1080px width)
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 35:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = f"{current_line} {word}" if current_line else word
            if current_line:
                lines.append(current_line)
            wrapped_text = "\\n".join(lines)

            start_t = offset_sec + caption.get("startFrame", 15) / FPS
            end_t = offset_sec + caption.get("endFrame", int(dur * FPS) - 5) / FPS

            drawtext_filters.append(
                f"drawtext=text='{wrapped_text}':"
                f"fontfile='{font_path}':"
                f"fontsize=42:fontcolor=white:"
                f"borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=h*0.75-text_h/2:"
                f"line_spacing=8:"
                f"enable='between(t,{start_t:.2f},{end_t:.2f})'"
            )

        offset_sec += dur

    if not drawtext_filters:
        _run_ffmpeg(["-i", video_path, "-c", "copy", output_path])
        return output_path

    vf = ",".join(drawtext_filters)
    _run_ffmpeg(
        [
            "-i", video_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "copy",
            output_path,
        ],
        timeout=180,
    )
    return output_path


def render_video(
    composition_data: dict, output_path: str, session: Session
) -> str:
    """Render a complete episode video from composition JSON.

    This is the main entry point, called by compose_and_render_task.

    Args:
        composition_data: JSON spec from build_composition_json()
        output_path: Where to write the final MP4
        session: SQLAlchemy session for reading asset blobs

    Returns:
        Path to the rendered MP4 file.
    """
    scenes = composition_data.get("scenes", [])
    if not scenes:
        raise VideoRenderError("No scenes in composition")

    with tempfile.TemporaryDirectory(prefix="scooby_render_") as tmp_dir:
        logger.info(
            "Rendering %d scenes to %s (tmp: %s)",
            len(scenes), output_path, tmp_dir,
        )

        # Step 1: Extract all asset blobs to temp files
        asset_paths = _prepare_assets(session, composition_data, tmp_dir)

        # Step 2: Render each scene as an individual clip
        scene_clips: list[tuple[str, float]] = []
        for i, scene_spec in enumerate(scenes):
            logger.info("Rendering scene %d/%d [%s]", i + 1, len(scenes), scene_spec.get("beatLabel", "?"))
            clip_path, duration = _render_scene_clip(scene_spec, asset_paths, tmp_dir, i)
            scene_clips.append((clip_path, duration))

        scene_durations = [d for _, d in scene_clips]

        # Step 3: Concatenate scenes
        logger.info("Concatenating %d scenes", len(scene_clips))
        concat_video = _concat_with_transitions(scene_clips, tmp_dir)

        # Step 4: Add voiceover audio
        logger.info("Mixing audio")
        video_with_audio = _add_audio(
            concat_video, scenes, scene_durations, asset_paths, tmp_dir
        )

        # Step 5: Burn captions
        logger.info("Burning captions")
        _burn_captions(video_with_audio, scenes, scene_durations, output_path)

    logger.info("Render complete: %s", output_path)
    return output_path
