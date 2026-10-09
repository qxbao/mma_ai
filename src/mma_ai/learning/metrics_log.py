"""Ghi chỉ số huấn luyện ra TensorBoard và JSONL."""

from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
from typing import Any, Sequence, TypeAlias

from .errors import NonFiniteError

MetricRecord: TypeAlias = dict[str, int | float]


def build_metrics_record(
    *,
    update: int,
    env_steps: int,
    policy_loss: float,
    value_loss: float,
    entropy: float,
    mean_return: float,
    activations: Sequence[float],
    env_steps_per_second: float,
    muscle_names: Sequence[str],
) -> MetricRecord:
    """Dựng bản ghi hợp lệ hoàn toàn trước khi shell thực hiện I/O."""
    if len(muscle_names) != 6 or len(activations) != 6:
        raise ValueError("Kích hoạt và tên cơ phải có đúng 6 phần tử")
    if len(set(muscle_names)) != 6 or any(not name.strip() for name in muscle_names):
        raise ValueError("Tên của sáu cơ phải khác nhau và không rỗng")

    record: MetricRecord = {
        "update": update,
        "env_steps": env_steps,
        "loss/policy": policy_loss,
        "loss/value": value_loss,
        "loss/entropy": entropy,
        "reward/mean_return": mean_return,
        "throughput/env_steps_per_second": env_steps_per_second,
    }
    record.update({f"activation/{name}": value for name, value in zip(muscle_names, activations)})
    invalid_tag = next((tag for tag, value in record.items() if not math.isfinite(value)), None)
    if invalid_tag is not None:
        raise NonFiniteError(f"Lượt {update} có giá trị không hữu hạn tại {invalid_tag}")
    return record


class MetricsLogger:
    """Ghi mỗi lượt cập nhật ra hai định dạng quan sát được."""

    def __init__(self, run_dir: Path, muscle_names: Sequence[str]) -> None:
        self._run_dir = Path(run_dir)
        self._muscle_names = tuple(muscle_names)
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._metrics_file = (self._run_dir / "metrics.jsonl").open("a", encoding="utf-8")
        self._summary_writer = self._create_summary_writer(self._run_dir / "tb")
        self._closed = False

    @staticmethod
    def _create_summary_writer(log_dir: Path) -> Any:
        tensorboard = importlib.import_module("torch.utils.tensorboard")
        return tensorboard.SummaryWriter(log_dir=str(log_dir))

    def log_update(
        self,
        *,
        update: int,
        env_steps: int,
        policy_loss: float,
        value_loss: float,
        entropy: float,
        mean_return: float,
        activations: Sequence[float],
        env_steps_per_second: float,
    ) -> None:
        """Xác thực trọn lượt rồi ghi TensorBoard và JSONL theo số bước môi trường."""
        if self._closed:
            raise RuntimeError("Không thể ghi MetricsLogger đã đóng")
        record = build_metrics_record(
            update=update,
            env_steps=env_steps,
            policy_loss=policy_loss,
            value_loss=value_loss,
            entropy=entropy,
            mean_return=mean_return,
            activations=activations,
            env_steps_per_second=env_steps_per_second,
            muscle_names=self._muscle_names,
        )
        for tag, value in record.items():
            if tag not in {"update", "env_steps"}:
                self._summary_writer.add_scalar(tag, value, global_step=env_steps)
        self._summary_writer.flush()
        self._metrics_file.write(json.dumps(record, allow_nan=False) + "\n")
        self._metrics_file.flush()

    def close(self) -> None:
        """Đóng sạch hai tài nguyên ghi và cho phép gọi lặp lại an toàn."""
        if not self._closed:
            self._summary_writer.close()
            self._metrics_file.close()
            self._closed = True

    def __enter__(self) -> MetricsLogger:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
