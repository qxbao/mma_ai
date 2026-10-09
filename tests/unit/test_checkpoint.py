"""Kiểm thử đơn vị cho lưu, nạp checkpoint và policy (FR-006...FR-009, INV-004, API-003)."""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest


def test_regress_tdd_red_checkpoint_module_is_present() -> None:
    """FR-006: mô-đun checkpoint phải được đóng gói trong mma_ai.learning."""
    assert importlib.util.find_spec("mma_ai.learning.checkpoint") is not None


def _torch() -> Any:
    return pytest.importorskip("torch")


class _DummyAgent:
    """Agent giả lập duck-typing cho lưu/nạp checkpoint."""

    def __init__(self, obs_dim: int = 14, act_dim: int = 6) -> None:
        torch = _torch()
        from mma_ai.learning.networks import ActorCritic
        from mma_ai.learning.train_config import TrainConfig

        self.cfg = TrainConfig.load()
        self.model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=self.cfg)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

    def state_dict(self) -> dict[str, Any]:
        return {
            "actor": self.model.actor.state_dict(),
            "critic": self.model.critic.state_dict(),
            "log_std": self.model.log_std.detach().clone(),
            "optimizer": self.optimizer.state_dict(),
        }


def _dummy_context(update_idx: int = 10, env_steps: int = 20480) -> dict[str, Any]:
    from mma_ai.learning.normalizer import RunningNorm

    norm = RunningNorm()
    norm.update(np.ones((5, 14), dtype=np.float64))
    return {
        "update_idx": update_idx,
        "env_steps": env_steps,
        "model_sha256": "0" * 64,
        "seed": 42,
        "obs_normalizer": norm,
    }


def test_roundtrip_same_action(tmp_path: Path) -> None:
    """FR-008, INV-004, NFR-REPRO-001, AC-2: nạp lại cho cùng hành động <= 1e-6 (lô 64 obs)."""
    torch = _torch()
    from mma_ai.learning.checkpoint import load_policy, save_checkpoint

    agent = _DummyAgent()
    ctx = _dummy_context(update_idx=10, env_steps=20480)
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    obs_batch = np.random.default_rng(123).normal(size=(64, 14)).astype(np.float64)

    # Tính action trước khi lưu bằng model gốc và normalizer
    norm = ctx["obs_normalizer"]
    obs_norm = torch.as_tensor(norm(obs_batch), dtype=torch.float32)
    with torch.no_grad():
        expected_action = torch.sigmoid(agent.model.actor(obs_norm)).cpu().numpy()

    # Nạp lại policy chỉ-đọc
    ckpt_path = tmp_path / meta.path
    policy = load_policy(ckpt_path)
    restored_action = policy.act_deterministic(obs_batch)

    max_diff = float(np.max(np.abs(expected_action - restored_action)))
    assert max_diff <= 1e-6


def test_atomic_write_no_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-007, INV-004: ngắt giữa lúc ghi không để lại file partial hoặc tệp hỏng."""
    _torch()
    from mma_ai.learning.checkpoint import save_checkpoint
    from mma_ai.learning.errors import CheckpointIOError

    agent = _DummyAgent()
    ctx = _dummy_context(update_idx=10)

    def _failing_replace(src: Any, dst: Any) -> None:
        raise OSError("Mô phỏng lỗi đĩa giữa chừng")

    import os

    monkeypatch.setattr(os, "replace", _failing_replace)

    with pytest.raises(CheckpointIOError):
        save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    # Kiểm tra không có tệp .tmp bị bỏ lại và chưa có checkpoint hoàn tất
    checkpoints_dir = tmp_path / "checkpoints"
    if checkpoints_dir.exists():
        tmp_files = list(checkpoints_dir.glob("*.tmp"))
        assert len(tmp_files) == 0
        assert not (checkpoints_dir / "latest.json").exists()


def test_nan_not_written(tmp_path: Path) -> None:
    """FR-007, INV-004: quét hữu hạn từ chối NaN/Inf, ném NonFiniteError và không ghi đĩa."""
    _torch()
    from mma_ai.learning.checkpoint import save_checkpoint
    from mma_ai.learning.errors import NonFiniteError

    agent = _DummyAgent()
    # Gán NaN vào trọng số của actor
    for param in agent.model.actor.parameters():
        param.data.fill_(float("nan"))
        break

    ctx = _dummy_context(update_idx=5)
    with pytest.raises(NonFiniteError):
        save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    # Không ghi tệp checkpoint ra đĩa
    checkpoints_dir = tmp_path / "checkpoints"
    pt_files = list(checkpoints_dir.glob("*.pt")) if checkpoints_dir.exists() else []
    assert len(pt_files) == 0


def test_missing_component_raises(tmp_path: Path) -> None:
    """FR-008, INV-004: thiếu 1 trong 6 thành phần ném CheckpointError nêu nguyên nhân."""
    torch = _torch()
    from mma_ai.learning.checkpoint import load_checkpoint
    from mma_ai.learning.errors import CheckpointError

    # Tạo tệp .pt thiếu "optimizer"
    corrupt_data = {
        "actor": {},
        "critic": {},
        "obs_normalizer": {"mean": torch.zeros(14), "var": torch.ones(14), "count": 1},
        "seed": 42,
        "rng_state": {},
        # Thiếu "optimizer"
    }
    ckpt_file = tmp_path / "corrupt.pt"
    torch.save(corrupt_data, ckpt_file)

    with pytest.raises(CheckpointError) as exc_info:
        load_checkpoint(ckpt_file)
    assert "optimizer" in str(exc_info.value) or "thiếu" in str(exc_info.value).lower()


def test_shape_mismatch_raises(tmp_path: Path) -> None:
    """FR-008, AC-2: checkpoint có hình dạng mạng không khớp ném CheckpointError."""
    _torch()
    from mma_ai.learning.checkpoint import load_checkpoint, save_checkpoint
    from mma_ai.learning.errors import CheckpointError
    from mma_ai.learning.train_config import TrainConfig

    # Lưu agent với obs_dim=14
    agent = _DummyAgent(obs_dim=14, act_dim=6)
    ctx = _dummy_context()
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    # Tải lại với cấu hình mong đợi obs_dim khác (hoặc expected_cfg với network khác)
    cfg_diff = TrainConfig.load()
    with pytest.raises(CheckpointError):
        load_checkpoint(tmp_path / meta.path, expected_cfg=cfg_diff, expected_obs_dim=99)


def test_xml_hash_mismatch_refuses_training(tmp_path: Path) -> None:
    """FR-008, AC-2: hash XML khác từ chối khi train tiếp, cảnh báo khi suy luận."""
    _torch()
    from mma_ai.learning.checkpoint import load_checkpoint, save_checkpoint
    from mma_ai.learning.errors import CheckpointError

    agent = _DummyAgent()
    ctx = _dummy_context()
    ctx["model_sha256"] = "a" * 64
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    ckpt_path = tmp_path / meta.path

    # Khi for_training=True: từ chối nếu XML hash khác
    with pytest.raises(CheckpointError):
        load_checkpoint(ckpt_path, for_training=True, expected_model_sha256="b" * 64)

    # Khi for_training=False: chỉ cảnh báo, không ném lỗi
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        load_checkpoint(ckpt_path, for_training=False, expected_model_sha256="b" * 64)
        assert len(recorded_warnings) >= 1
        assert any(
            "mô hình" in str(w.message).lower() or "hash" in str(w.message).lower()
            for w in recorded_warnings
        )


def test_load_weights_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-008, API-003: nạp checkpoint đảm bảo sử dụng weights_only=True."""
    torch = _torch()
    from mma_ai.learning.checkpoint import load_checkpoint, save_checkpoint

    agent = _DummyAgent()
    ctx = _dummy_context()
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    original_load = torch.load
    called_with_weights_only = False

    def _spy_load(*args: Any, **kwargs: Any) -> Any:
        nonlocal called_with_weights_only
        if kwargs.get("weights_only") is True:
            called_with_weights_only = True
        return original_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", _spy_load)
    load_checkpoint(tmp_path / meta.path)
    assert called_with_weights_only is True


def test_latest_pointer_after_complete_write(tmp_path: Path) -> None:
    """FR-006, FR-007, AC-1: latest.json cập nhật sau khi checkpoint và metadata ghi hoàn tất."""
    _torch()
    import json

    import jsonschema

    from mma_ai.learning.checkpoint import save_checkpoint

    agent = _DummyAgent()
    ctx = _dummy_context(update_idx=10)
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    latest_file = tmp_path / "checkpoints" / "latest.json"
    assert latest_file.exists()

    latest_data = json.loads(latest_file.read_text(encoding="utf-8"))
    assert latest_data["path"] == meta.path
    assert latest_data["sha256"] == meta.sha256
    assert latest_data["update_idx"] == 10

    # Đảm bảo tệp .pt và .meta.json đều tồn tại đầy đủ
    assert (tmp_path / meta.path).exists()
    meta_file = tmp_path / "checkpoints" / "ckpt_u000010.meta.json"
    assert meta_file.exists()

    # Xác thực meta json theo schema checkpoint-meta.schema.json
    schema_path = (
        Path(__file__).parents[2]
        / "specs/003-ppo-train-repro/contracts/checkpoint-meta.schema.json"
    )
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        meta_dict = json.loads(meta_file.read_text(encoding="utf-8"))
        jsonschema.validate(instance=meta_dict, schema=schema)


def test_old_checkpoints_not_overwritten(tmp_path: Path) -> None:
    """FR-007, INV-004: checkpoint cũ không bị ghi đè khi ghi checkpoint ở lượt mới."""
    _torch()
    from mma_ai.learning.checkpoint import save_checkpoint

    agent = _DummyAgent()
    ctx1 = _dummy_context(update_idx=10)
    meta1 = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx1)

    ctx2 = _dummy_context(update_idx=20)
    meta2 = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx2)

    assert meta1.path != meta2.path
    assert (tmp_path / meta1.path).exists()
    assert (tmp_path / meta2.path).exists()
    assert (tmp_path / "checkpoints" / "ckpt_u000010.pt").exists()
    assert (tmp_path / "checkpoints" / "ckpt_u000020.pt").exists()


def test_version_mismatch_warns(tmp_path: Path) -> None:
    """FR-008: cảnh báo khi phiên bản PyTorch hoặc NumPy của checkpoint khác phiên bản hiện tại."""
    _torch()
    from mma_ai.learning.checkpoint import load_checkpoint, save_checkpoint

    agent = _DummyAgent()
    ctx = _dummy_context()
    ctx["library_versions"] = {"torch": "0.0.1", "numpy": "0.0.1"}
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)

    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        load_checkpoint(tmp_path / meta.path)
        assert len(recorded_warnings) >= 1
        assert any("phiên bản" in str(w.message).lower() for w in recorded_warnings)
