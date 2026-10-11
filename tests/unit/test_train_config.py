"""Kiểm thử cấu hình huấn luyện tập trung."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml


def _default_data() -> dict[str, Any]:
    config_path = Path(__file__).parents[2] / "src/mma_ai/learning/train_elbow.yaml"
    return cast(dict[str, Any], yaml.safe_load(config_path.read_text(encoding="utf-8")))


def _config_error() -> type[Exception]:
    from mma_ai.learning.errors import TrainConfigError

    return TrainConfigError


def _write_config(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "train.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_defaults_load() -> None:
    """FR-018, FR-002, FR-004: mặc định có các giá trị PPO và mạng đã chốt."""
    from mma_ai.learning.train_config import TrainConfig

    config = TrainConfig.load()

    assert config.network.actor_hidden == (256, 256)
    assert config.network.critic_hidden == (256, 256)
    assert config.schedule.total_timesteps == 100_000
    assert config.checkpoint.every_updates == 10
    assert config.reproducibility.rel_tolerance == pytest.approx(1e-6)
    assert config.reproducibility.head_updates == 10
    assert config.reproducibility.torch_threads == 1
    assert config.to_dict()["ui"]["host"] == "127.0.0.1"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("path", "value"),
    [
        (("ppo", "learning_rate"), 0),
        (("schedule", "total_timesteps"), 0),
        (("checkpoint", "every_updates"), 0),
        (("normalization", "epsilon"), -1),
    ],
)
def test_invalid_values_raise(tmp_path: Path, path: tuple[str, str], value: Any) -> None:
    """FR-018: số không dương bị từ chối trước khi huấn luyện."""
    from mma_ai.learning.train_config import TrainConfig

    data = _default_data()
    data[path[0]][path[1]] = value

    with pytest.raises(_config_error(), match=path[1]):
        TrainConfig.load(_write_config(tmp_path, data))


def test_missing_key_raises(tmp_path: Path) -> None:
    """FR-018: thiếu khoá bắt buộc phải nêu đúng ngữ cảnh khoá."""
    from mma_ai.learning.train_config import TrainConfig

    data = _default_data()
    del data["schedule"]["n_epochs"]

    with pytest.raises(_config_error(), match="schedule.n_epochs"):
        TrainConfig.load(_write_config(tmp_path, data))


def test_batch_size_gt_n_steps_raises(tmp_path: Path) -> None:
    """FR-018: batch_size không được lớn hơn n_steps."""
    from mma_ai.learning.train_config import TrainConfig

    data = _default_data()
    data["schedule"]["batch_size"] = data["schedule"]["n_steps"] + 1

    with pytest.raises(_config_error(), match="batch_size"):
        TrainConfig.load(_write_config(tmp_path, data))


def test_n_steps_gt_total_timesteps_raises(tmp_path: Path) -> None:
    """FR-018: n_steps không được vượt tổng bước huấn luyện."""
    from mma_ai.learning.train_config import TrainConfig

    data = _default_data()
    data["schedule"]["n_steps"] = data["schedule"]["total_timesteps"] + 1

    with pytest.raises(_config_error(), match="n_steps"):
        TrainConfig.load(_write_config(tmp_path, data))


def test_non_loopback_host_raises(tmp_path: Path) -> None:
    """INV-005: giao diện quan sát chỉ được lắng nghe tại loopback."""
    from mma_ai.learning.train_config import TrainConfig

    data = _default_data()
    data["ui"]["host"] = "0.0.0.0"

    with pytest.raises(_config_error(), match="ui.host"):
        TrainConfig.load(_write_config(tmp_path, data))


def test_overrides_applied() -> None:
    """FR-018: ghi đè CLI được phản ánh trong cấu hình đã phân giải."""
    from mma_ai.learning.train_config import TrainConfig

    config = TrainConfig.load(
        overrides={
            "seed": 7,
            "schedule.total_timesteps": 4_096,
            "ui.mode": "none",
        }
    )

    assert config.seed == 7
    assert config.schedule.total_timesteps == 4_096
    assert config.ui.mode == "none"
    assert config.to_dict()["schedule"]["total_timesteps"] == 4_096


def test_smoke_config_total_4096() -> None:
    """FR-018: cấu hình smoke giữ ngân sách ngắn và giao diện tắt."""
    from mma_ai.learning.train_config import TrainConfig

    smoke_path = Path(__file__).parents[2] / "src/mma_ai/learning/train_elbow_smoke.yaml"
    config = TrainConfig.load(smoke_path)

    assert config.schedule.total_timesteps == 4_096
    assert config.schedule.n_steps == 2_048
    assert config.checkpoint.every_updates == 1
    assert config.ui.mode == "none"


def teardown_module() -> None:
    """Dọn import trì hoãn để bảo toàn kiểm thử ranh giới gói."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)
