"""Kiểm chứng thuộc tính của cấu hình huấn luyện."""

from __future__ import annotations

import random
import string
from pathlib import Path
from typing import Any, cast

import pytest
import yaml


def _default_data() -> dict[str, Any]:
    path = Path(__file__).parents[2] / "src/mma_ai/learning/train_elbow.yaml"
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def _config_error() -> type[Exception]:
    from mma_ai.learning.errors import TrainConfigError

    return TrainConfigError


def test_inv_005_only_loopback_hosts_are_accepted(tmp_path: Path) -> None:
    """INV-005: 100 địa chỉ sinh ngẫu nhiên ngoài loopback luôn bị từ chối."""
    from mma_ai.learning.train_config import TrainConfig

    rng = random.Random(20261009)
    for case in range(100):
        host = "".join(rng.choice(string.ascii_lowercase) for _ in range(12)) + ".example"
        data = _default_data()
        data["ui"]["host"] = host
        path = tmp_path / f"invalid-host-{case}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        with pytest.raises(_config_error(), match="ui.host"):
            TrainConfig.load(path)


def teardown_module() -> None:
    """Dọn import trì hoãn để bảo toàn kiểm thử ranh giới gói."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)
