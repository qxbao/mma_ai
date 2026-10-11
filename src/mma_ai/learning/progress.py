"""Ghi ảnh chụp tiến trình nguyên tử cho giao diện chỉ đọc."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def prepare_snapshot(
    snapshot: Mapping[str, Any], *, timestamp_utc: str, history_points: int
) -> dict[str, Any]:
    """Dựng bản sao ảnh chụp có history đồng bộ và mốc thời gian do writer sở hữu."""
    if history_points < 1:
        raise ValueError("history_points phải lớn hơn hoặc bằng 1")
    history = snapshot.get("history")
    if not isinstance(history, Mapping):
        raise ValueError("Ảnh chụp phải có history dạng mapping")
    keys = ("env_steps", "mean_return", "value_loss")
    values: dict[str, list[Any]] = {}
    for key in keys:
        value = history.get(key)
        if not isinstance(value, list):
            raise ValueError(f"history.{key} phải là danh sách")
        values[key] = value[-history_points:]
    if len({len(value) for value in values.values()}) != 1:
        raise ValueError("Các danh sách history phải có cùng số điểm")

    prepared = dict(snapshot)
    prepared["timestamp_utc"] = timestamp_utc
    prepared["history"] = values
    return prepared


class ProgressWriter:
    """Giới hạn nhịp và thay thế nguyên tử tệp progress.json của một run."""

    def __init__(
        self,
        run_dir: str | Path,
        *,
        snapshot_interval_s: float,
        history_points: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if snapshot_interval_s < 0:
            raise ValueError("snapshot_interval_s không được âm")
        if history_points < 1:
            raise ValueError("history_points phải lớn hơn hoặc bằng 1")
        self._run_dir = Path(run_dir)
        self._snapshot_interval_s = snapshot_interval_s
        self._history_points = history_points
        self._clock = clock or time.time
        self._last_written_at: float | None = None
        self._last_timestamp: float | None = None

    def write(self, snapshot: Mapping[str, Any], *, final: bool = False) -> bool:
        """Ghi ảnh chụp khi đến hạn, hoặc luôn ghi ảnh cuối; trả về việc có ghi hay không."""
        now = self._clock()
        if (
            not final
            and self._last_written_at is not None
            and now - self._last_written_at < self._snapshot_interval_s
        ):
            return False

        timestamp = now if self._last_timestamp is None else max(now, self._last_timestamp)
        payload = prepare_snapshot(
            snapshot,
            timestamp_utc=_format_timestamp(timestamp),
            history_points=self._history_points,
        )
        self._write_atomically(payload)
        self._last_written_at = now
        self._last_timestamp = timestamp
        return True

    def _write_atomically(self, payload: Mapping[str, Any]) -> None:
        self._run_dir.mkdir(parents=True, exist_ok=True)
        target = self._run_dir / "progress.json"
        temporary = self._run_dir / "progress.json.tmp"
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)


def _format_timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")
