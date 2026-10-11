"""Kiểm thử thuộc tính của ảnh chụp tiến trình chỉ đọc."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


def _snapshot(size: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": "run",
        "stage": "elbow",
        "seed": 0,
        "status": "running",
        "update_idx": 0,
        "env_steps": 0,
        "total_steps": 1,
        "env_steps_per_second": None,
        "mean_return": None,
        "loss": None,
        "activation": None,
        "checkpoint": {"count": 0, "every_updates": 1, "last_path": None, "last_update_idx": None},
        "history": {
            "env_steps": list(range(size)),
            "mean_return": [float(item) for item in range(size)],
            "value_loss": [float(item) for item in range(size)],
        },
    }


def test_inv_005_generated_history_is_bounded_and_read_only(tmp_path: Path) -> None:
    """INV-005: 100 history ngẫu nhiên được cắt đồng bộ trước khi giao diện đọc."""
    from mma_ai.learning.progress import ProgressWriter

    rng = random.Random(20261010)
    for case in range(100):
        size = rng.randint(0, 100)
        limit = rng.randint(1, 25)
        snapshot = _snapshot(size)
        writer = ProgressWriter(tmp_path / str(case), snapshot_interval_s=0.0, history_points=limit)
        assert writer.write(snapshot) is True
        written = json.loads((tmp_path / str(case) / "progress.json").read_text(encoding="utf-8"))
        expected = list(range(max(0, size - limit), size))
        assert written["history"]["env_steps"] == expected
        assert written["history"]["mean_return"] == [float(item) for item in expected]
        assert written["history"]["value_loss"] == [float(item) for item in expected]
        assert "timestamp_utc" not in snapshot
