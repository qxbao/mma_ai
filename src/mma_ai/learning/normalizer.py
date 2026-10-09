"""Bộ chuẩn hoá thống kê chạy cho quan sát."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class RunningNorm:
    """Bộ chuẩn hoá quan sát."""

    def __init__(self, clip_obs: float = 10.0) -> None:
        self.clip_obs = float(clip_obs)
        self._mean: NDArray[np.float64] | None = None
        self._m2: NDArray[np.float64] | None = None
        self._count = 0

    def update(self, batch: np.ndarray) -> None:
        values = np.asarray(batch, dtype=np.float64)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        if values.ndim == 0 or values.shape[0] == 0:
            raise ValueError("batch không được rỗng")
        n = values.shape[0]
        mean = np.mean(values, axis=0)
        m2 = np.sum((values - mean) ** 2, axis=0)
        if self._mean is None:
            self._mean, self._m2, self._count = mean, m2, n
            return
        total = self._count + n
        delta = mean - self._mean
        self._mean += delta * n / total
        self._m2 += m2 + delta * delta * self._count * n / total
        self._count = total

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        if self._mean is None or self._m2 is None:
            raise ValueError("chưa có thống kê quan sát")
        values = np.asarray(obs, dtype=np.float64)
        result = (values - self._mean) / np.sqrt(self._m2 / self._count + 1e-8)
        return np.clip(result, -self.clip_obs, self.clip_obs)

    def state_dict(self) -> dict[str, Any]:
        if self._mean is None or self._m2 is None:
            return {"mean": np.array([]), "var": np.array([]), "count": 0}
        return {
            "mean": self._mean.copy(),
            "var": (self._m2 / self._count).copy(),
            "count": self._count,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        count = int(state["count"])
        mean = np.asarray(state["mean"], dtype=np.float64)
        var = np.asarray(state["var"], dtype=np.float64)
        if count < 0 or mean.shape != var.shape or np.any(var < 0):
            raise ValueError("trạng thái chuẩn hoá không hợp lệ")
        self._mean = mean.copy() if count else None
        self._m2 = var * count if count else None
        self._count = count
