"""Upload the 6 Seedance 1.5 Pro clips as 'animation' VideoAssets tied to
Joyce's "Heart for Fun" scenes, so the next compose_and_render run picks
them up and produces a Movie Lite version (animated clips + Joyce's
existing ElevenLabs VO + captions) instead of the watercolor + Ken Burns
Storyboard.

Run once. Reads MP4s from test_generations/joyce_heart_topview/.

Usage:
    DATABASE_URL='postgresql://...@gondola.proxy.rlwy.net:.../railway' \
        python scripts/upload_joyce_movie_lite.py
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text


EPISODE_ID = "ab8bf1d4-cac4-47bd-bcb6-68e38144a6d0"

# scene_order (DB) -> Seedance clip filename
CLIPS = {
    1: "scene_1_hook.mp4",
    2: "scene_2_setup.mp4",
    3: "scene_3_escalation_1.mp4",
    4: "scene_4_escalation_2.mp4",
    5: "scene_5_climax.mp4",
    6: "scene_6_button.mp4",
}

CLIPS_DIR = Path("test_generations/joyce_heart_topview")


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.begin() as conn:
        # Pull scene IDs in order
        rows = conn.execute(text(
            "SELECT id::text, scene_order FROM scenes "
            "WHERE episode_id = :eid ORDER BY scene_order"
        ), {"eid": EPISODE_ID}).fetchall()
        scenes = {r[1]: r[0] for r in rows}
        if len(scenes) != 6:
            print(f"ERROR: expected 6 scenes, got {len(scenes)}")
            return 1

        for order, fname in CLIPS.items():
            path = CLIPS_DIR / fname
            if not path.exists():
                print(f"  scene {order}: {fname} MISSING — skip")
                continue
            scene_id = scenes[order]
            video_bytes = path.read_bytes()
            size = len(video_bytes)

            # Mark any existing animation assets for this scene inactive
            # so the composer's "latest active asset" query returns ours.
            conn.execute(text(
                "UPDATE video_assets SET is_active = false "
                "WHERE scene_id = :sid AND asset_type = 'animation'"
            ), {"sid": scene_id})

            # Insert the new animation asset
            conn.execute(text(
                "INSERT INTO video_assets "
                "(id, scene_id, asset_type, file_data, file_size_bytes, mime_type, "
                " metadata, version, is_active) "
                "VALUES "
                "(:aid, :sid, 'animation', :data, :size, 'video/mp4', "
                " :meta, 1, true)"
            ), {
                "aid": str(uuid.uuid4()),
                "sid": scene_id,
                "data": video_bytes,
                "size": size,
                "meta": '{"provider": "topview_seedance_1.5_pro", "duration_sec": 5, '
                        '"source": "scripts/eval_topview_joyce_heart.py"}',
            })
            print(f"  scene {order}: uploaded {fname} ({size:,} bytes) -> animation asset on scene {scene_id[:8]}")

    print("\nDone. Trigger compose_and_render_task on the episode to render.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
