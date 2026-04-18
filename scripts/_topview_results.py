"""Shared CSV append helper for TopView eval scripts.

Writes one row per model run to test_generations/topview_results.csv so all
evaluation data lands in a single spot you can open in Excel/Cursor.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

RESULTS_CSV = os.path.join("test_generations", "topview_results.csv")

FIELDS = [
    "timestamp",
    "kind",            # i2v | t2v
    "model_name",      # slug used in --model
    "model_display",   # TopView's display name
    "duration_s",
    "resolution",
    "aspect_ratio",
    "sound",
    "input_image",     # path or empty
    "prompt",
    "task_id",
    "status",          # ok | failed | timeout | error
    "gen_time_s",
    "credits",
    "dims",            # widthxheight
    "file_size_kb",
    "output_path",
    "error",
]


def log_result(row: dict) -> None:
    """Append one run to the results CSV, writing header if new."""
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    new_file = not os.path.isfile(RESULTS_CSV)
    # Auto-fill timestamp unless caller provided one
    if not row.get("timestamp"):
        row["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Normalize to exactly FIELDS columns, filling missing keys with ""
    row = {k: row.get(k, "") for k in FIELDS}
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
