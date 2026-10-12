"""Kiểm thử đơn vị cho bộ điều phối huấn luyện Trainer (mma_ai.learning.trainer).

Đảm bảo tuân thủ chu trình TDD, kiến trúc functional core / imperative shell,
và bảo vệ các bất biến INV-002, INV-003, INV-004.
Truy vết yêu cầu: FR-001, FR-003, FR-005, FR-006, FR-007, FR-009, FR-010,
FR-013, FR-016, FR-017, INV-002, INV-003, INV-004, NFR-REL-001, API-003.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.learning.errors import NonFiniteError, TrainError
from mma_ai.learning.train_config import TrainConfig


def test_regress_tdd_red_trainer_module_is_present() -> None:
    """FR-001, API-003: Khẳng định độc lập mô-đun trainer tồn tại trên base."""
    assert importlib.util.find_spec("mma_ai.learning.trainer") is not None


def _torch() -> Any:
    return pytest.importorskip("torch")


class _MockToyEnv:
    """Môi trường đồ chơi tất định (deterministic toy environment) phục vụ kiểm thử."""

    def __init__(self, split: str = "train", fail_on_step: bool = False) -> None:
        self.split = split
        self.fail_on_step = fail_on_step
        self.model_sha256 = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"
        self.action_history: list[np.ndarray] = []
        self._step_count = 0

    def reset(self, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        self._step_count = 0
        obs = np.zeros(14, dtype=np.float32)
        info = {
            "target_split": self.split,
            "target_index": 0,
            "model_sha256": self.model_sha256,
        }
        return obs, info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.fail_on_step:
            raise PhysicsInstabilityError("Mô phỏng mất ổn định số học trong kiểm thử.")
        self._step_count += 1
        self.action_history.append(np.array(action, copy=True))
        reward = float(np.sum(action))
        done = self._step_count >= 4
        next_obs = np.ones(14, dtype=np.float32) * 0.1
        info = {"target_split": self.split}
        return next_obs, reward, done, False, info

    def model_record(self) -> dict[str, Any]:
        return {
            "sha256": self.model_sha256,
            "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
            "muscle_names": ["m1", "m2", "m3", "m4", "m5", "m6"],
        }


def _make_fast_config(*args: Any, **overrides: Any) -> TrainConfig:
    overrides_map = {
        "schedule.total_timesteps": overrides.get("total_timesteps", 16),
        "schedule.n_steps": overrides.get("n_steps", 8),
        "schedule.batch_size": overrides.get("batch_size", 4),
        "schedule.n_epochs": overrides.get("n_epochs", 1),
        "checkpoint.every_updates": overrides.get("every_updates", 1),
        "reproducibility.head_updates": 2,
    }
    return TrainConfig.load(overrides=overrides_map)


def test_trainer_runs_toy_env_and_writes_artifacts(tmp_path: Path) -> None:
    """FR-001, FR-010, FR-013, NFR-REL-001, API-003: Trainer chạy toy env tạo đủ tạo tác."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=16, n_steps=8)
    env = _MockToyEnv(split="train")
    run_dir = tmp_path / "run_test_01"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)
    result = trainer.run()

    assert result.status == "done"
    assert result.env_steps == 16
    assert result.n_updates >= 2
    assert result.wall_clock_seconds > 0
    assert result.env_steps_per_second > 0
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "metrics.jsonl").is_file()
    assert (run_dir / "progress.json").is_file()
    assert (run_dir / "checkpoints" / "latest.json").is_file()

    manifest_data = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["status"] == "done"
    assert len(manifest_data["checkpoints"]) >= 1


def test_actions_sent_to_env_in_unit_interval(tmp_path: Path) -> None:
    """FR-003, FR-005, INV-002: Hành động chuyển cho env luôn trong khoảng đơn vị (0, 1)^6."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=8, n_steps=8)
    env = _MockToyEnv(split="train")
    run_dir = tmp_path / "run_test_actions"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)
    trainer.run()

    assert len(env.action_history) == 8
    for act in env.action_history:
        assert act.shape == (6,)
        assert np.all(act > 0.0)
        assert np.all(act < 1.0)


def test_nonfinite_loss_raises_without_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-007, FR-017, INV-004, NFR-REL-001: Tổn thất không hữu hạn dừng run và không lưu ckpt."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=16, n_steps=8, every_updates=1)
    env = _MockToyEnv(split="train")
    run_dir = tmp_path / "run_test_nan"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)

    original_update = trainer.agent.update
    call_count = 0

    def mock_update(buffer: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise NonFiniteError("Tiêm giá trị NaN cố ý vào loss lượt 2.")
        return original_update(buffer)

    monkeypatch.setattr(trainer.agent, "update", mock_update)

    with pytest.raises(NonFiniteError, match="Tiêm giá trị NaN"):
        trainer.run()

    manifest_path = run_dir / "manifest.json"
    assert manifest_path.is_file()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["status"] == "error"
    assert manifest_data["error"]["kind"] == "non_finite"

    # Chỉ checkpoint của lượt 1 được lưu, lượt 2 không sinh checkpoint lỗi
    assert len(manifest_data["checkpoints"]) == 1


def test_checkpoint_cadence(tmp_path: Path) -> None:
    """FR-006, INV-004: Lưu checkpoint theo đúng chu kỳ every_updates được chỉ định."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=24, n_steps=8, every_updates=2)
    env = _MockToyEnv(split="train")
    run_dir = tmp_path / "run_test_cadence"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)
    result = trainer.run()

    # Với 24 steps / 8 steps mỗi update = 3 updates.
    # Chu kỳ every_updates = 2 => lưu tại update 2 (periodic) và cuối run (final).
    assert result.status == "done"
    ckpt_kinds = [c.kind for c in result.checkpoints]
    assert "periodic" in ckpt_kinds
    assert "final" in ckpt_kinds
    assert (run_dir / "checkpoints" / "ckpt_u000002.pt").is_file()
    assert (run_dir / "checkpoints" / "ckpt_u000003_final.pt").is_file()


def test_final_checkpoint_always(tmp_path: Path) -> None:
    """FR-006, API-003: Luôn lưu checkpoint final ở cuối lượt train dù lệch chu kỳ."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=8, n_steps=8, every_updates=10)
    env = _MockToyEnv(split="train")
    run_dir = tmp_path / "run_test_final_always"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)
    result = trainer.run()

    assert result.status == "done"
    assert len(result.checkpoints) == 1
    assert result.checkpoints[0].kind == "final"
    assert (run_dir / "checkpoints" / "ckpt_u000001_final.pt").is_file()


def test_env_instability_propagates(tmp_path: Path) -> None:
    """FR-017, NFR-REL-001: Ngoại lệ PhysicsInstabilityError truyền nguyên văn."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=16, n_steps=8)
    env = _MockToyEnv(split="train", fail_on_step=True)
    run_dir = tmp_path / "run_test_instability"

    trainer = Trainer(cfg=config, env=env, run_dir=run_dir)

    with pytest.raises(PhysicsInstabilityError, match="Mô phỏng mất ổn định số học"):
        trainer.run()

    manifest_data = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["status"] == "error"
    assert manifest_data["error"]["kind"] == "env_instability"


def test_only_train_split_requested(tmp_path: Path) -> None:
    """FR-016, INV-003: Từ chối môi trường không thuộc tập train và kiểm tra ở mọi lần reset."""
    _torch()
    from mma_ai.learning.trainer import Trainer

    config = _make_fast_config(tmp_path, total_timesteps=8, n_steps=8)

    # 1. Khởi tạo với split không phải train bị từ chối
    env_test = _MockToyEnv(split="test")
    with pytest.raises(TrainError, match="split='train'"):
        Trainer(cfg=config, env=env_test, run_dir=tmp_path / "run_split_1")

    # 2. Reset trả về split không phải train bị từ chối
    env_cheating = _MockToyEnv(split="train")
    trainer = Trainer(cfg=config, env=env_cheating, run_dir=tmp_path / "run_split_2")
    env_cheating.split = "test"
    with pytest.raises(TrainError, match="INV-003"):
        trainer.run()


def test_resume_from_checkpoint(tmp_path: Path) -> None:
    """FR-009, INV-004: Khôi phục và tiếp tục huấn luyện từ một checkpoint hợp lệ."""
    _torch()
    from mma_ai.learning.checkpoint import load_checkpoint
    from mma_ai.learning.trainer import Trainer

    # Lượt chạy gốc tạo 1 checkpoint
    config_1 = _make_fast_config(tmp_path, total_timesteps=8, n_steps=8, every_updates=1)
    env_1 = _MockToyEnv(split="train")
    run_dir_1 = tmp_path / "run_parent"

    trainer_1 = Trainer(cfg=config_1, env=env_1, run_dir=run_dir_1)
    res_1 = trainer_1.run()
    assert res_1.status == "done"
    ckpt_path = run_dir_1 / "checkpoints" / "ckpt_u000001_final.pt"
    assert ckpt_path.is_file()

    loaded = load_checkpoint(ckpt_path, for_training=True)

    # Lượt chạy con tiếp tục từ checkpoint
    config_2 = _make_fast_config(tmp_path, total_timesteps=16, n_steps=8, every_updates=1)
    env_2 = _MockToyEnv(split="train")
    run_dir_2 = tmp_path / "run_child"

    trainer_2 = Trainer(cfg=config_2, env=env_2, run_dir=run_dir_2, resume_checkpoint=loaded)
    res_2 = trainer_2.run()

    assert res_2.status == "done"
    assert res_2.env_steps == 16
    assert res_2.n_updates == 2

    manifest_child = json.loads((run_dir_2 / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_child["resumed_from"] is not None
    assert manifest_child["resumed_from"]["checkpoint"] == "checkpoints/ckpt_u000001_final.pt"


def teardown_module() -> None:
    """Dọn dẹp các mô-đun đã nạp sau kiểm thử để bảo vệ ranh giới import (bài học tự sinh)."""
    import sys

    for mod in list(sys.modules):
        if mod.startswith("mma_ai.learning") or mod == "torch" or mod.startswith("torch."):
            sys.modules.pop(mod, None)


def test_inv_005_resumed_checkpoint_path_uses_portable_record_form() -> None:
    """INV-005: Đường dẫn checkpoint tiếp tục luôn tương đối và dùng dấu `/`."""
    _torch()
    from mma_ai.learning.trainer import _record_checkpoint_path

    assert _record_checkpoint_path(r"C:\runs\checkpoints\state.pt") == (
        "runs/checkpoints/state.pt"
    )
