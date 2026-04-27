"""One-shot: upload local MP4 copies into the new Postgres blob columns.

Used to recover the 2026-04-26 production renders (00adb67f, 3d7dae6b)
that lived on the worker's ephemeral /tmp before the LargeBinary
columns existed.

Usage (from local machine, with backend venv activated):
    DATABASE_URL='postgresql://postgres:...@gondola.proxy.rlwy.net:PORT/railway' \
        python scripts/backfill_episode_videos.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


# Episode ID -> local MP4 path
RECOVERIES = {
    "00adb67f-6fc7-4a43-9ddf-af97b186b703":
        "test_output/railway_render/00adb67f-betrayal_recording.mp4",
    "3d7dae6b-f6f2-4d0e-b6f5-ce71e354f7bc":
        "test_output/railway_render/3d7dae6b-change_standoff.mp4",
}


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment")
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.begin() as conn:
        for episode_id, local_path in RECOVERIES.items():
            path = Path(local_path)
            if not path.exists():
                print(f"  {episode_id[:8]}: {local_path} MISSING — skip")
                continue

            video_bytes = path.read_bytes()
            size = len(video_bytes)
            print(f"  {episode_id[:8]}: read {size:,} bytes from {local_path}")

            existing = conn.execute(
                text("SELECT final_video_size_bytes FROM episodes WHERE id = :id"),
                {"id": episode_id},
            ).scalar_one_or_none()
            if existing:
                print(f"    already has {existing:,} bytes in DB — skipping")
                continue

            conn.execute(
                text(
                    "UPDATE episodes SET "
                    "  final_video_data = :data, "
                    "  final_video_size_bytes = :size, "
                    "  final_video_mime_type = 'video/mp4' "
                    "WHERE id = :id"
                ),
                {"data": video_bytes, "size": size, "id": episode_id},
            )
            print(f"    uploaded -> DB")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
