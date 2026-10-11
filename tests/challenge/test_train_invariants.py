"""Thử thách bất biến (challenge) INV-001..INV-005 của huấn luyện PPO (T338).

Mỗi test nhắm một bất biến của sản phẩm qua đầu vào mà người dùng/hệ thống gặp được.
Ca đỏ (finding) mang `xfail` KHÔNG strict với mã F-NNN trong `reason`; ca xanh là vector
đã thử mà không lách được (ghi vào `disproved_hypotheses`).

- INV-001 (AC-3): mỗi lần chạy có thư mục riêng; thư mục run cũ không bị ghi đè/sửa.
- INV-002 (AC-1): hành động đưa vào môi trường luôn nằm trong [0,1]^6.
- INV-003 (AC-1): huấn luyện chỉ dùng mục tiêu thuộc tập train.
- INV-004 (AC-2): checkpoint khứ hồi đủ trạng thái, không NaN/Inf, ghi nguyên tử.
- INV-005 (AC-7): giao diện quan sát chỉ đọc, không làm dừng train.
"""

# ruff: noqa: E402
from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

pytest.importorskip("torch", reason="Cần extra rl (torch) để thử thách huấn luyện PPO")
import torch

from mma_ai.learning.checkpoint import (
    CheckpointMeta,
    Policy,
    load_checkpoint,
    load_policy,
    save_checkpoint,
)
from mma_ai.learning.cli import main as train_main
from mma_ai.learning.errors import (
    CheckpointError,
    CheckpointIOError,
    NonFiniteError,
    RunDirError,
    TrainConfigError,
    TrainError,
)
from mma_ai.learning.networks import ActorCritic
from mma_ai.learning.normalizer import RunningNorm
from mma_ai.learning.ppo import PPOAgent
from mma_ai.learning.run_dir import create_run_dir
from mma_ai.learning.train_config import TrainConfig
from mma_ai.learning.trainer import Trainer
from mma_ai.monitoring import dashboard
from mma_ai.monitoring.cli import main as monitor_main

OBS_DIM = 14
ACT_DIM = 6
SMALL_NET: dict[str, Any] = {
    "network.actor_hidden": [16, 16],
    "network.critic_hidden": [16, 16],
}


# --------------------------------------------------------------------------------------
# Hàm dựng chung
# --------------------------------------------------------------------------------------


def _cfg(**overrides: Any) -> TrainConfig:
    merged = dict(SMALL_NET)
    merged.update(overrides)
    return TrainConfig.load(overrides=merged)


def _agent(seed: int = 0) -> PPOAgent:
    cfg = _cfg(seed=seed)
    torch.manual_seed(seed)
    return PPOAgent(ActorCritic(OBS_DIM, ACT_DIM, cfg), cfg)


def _buffer(n: int = 256, seed: int = 0) -> dict[str, torch.Tensor]:
    gen = torch.Generator().manual_seed(seed)
    return {
        "observations": torch.randn(n, OBS_DIM, generator=gen),
        "actions": torch.rand(n, ACT_DIM, generator=gen).clamp(0.01, 0.99),
        "old_log_probs": torch.randn(n, generator=gen) - 5.0,
        "returns": torch.randn(n, generator=gen),
        "advantages": torch.randn(n, generator=gen),
    }


def _trainer_ctx(agent: PPOAgent, norm: RunningNorm, update_idx: int) -> dict[str, Any]:
    """Ngữ cảnh đúng khuôn Trainer.run truyền cho save_checkpoint."""
    return {
        "update_idx": update_idx,
        "env_steps": update_idx * 64,
        "model_sha256": "a" * 64,
        "seed": agent.cfg.seed,
        "config": agent.cfg,
        "obs_normalizer": norm,
    }


def _norm() -> RunningNorm:
    norm = RunningNorm()
    norm.update(np.random.default_rng(1).normal(size=(32, OBS_DIM)))
    return norm


def _save(agent: PPOAgent, run_dir: Path, idx: int, kind: str = "periodic") -> CheckpointMeta:
    return save_checkpoint(agent, run_dir, kind=kind, ctx=_trainer_ctx(agent, _norm(), idx))


def _tree_hash(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        hasher.update(path.relative_to(root).as_posix().encode())
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _run_layout(tmp_path: Path, name: str = "run") -> Path:
    run_dir = tmp_path / name
    (run_dir / "checkpoints").mkdir(parents=True)
    return run_dir


# --------------------------------------------------------------------------------------
# INV-004 — checkpoint
# --------------------------------------------------------------------------------------


def _assert_checkpoint_dir_consistent(ckpt_dir: Path) -> None:
    """Không tệp .pt nửa vời; latest.json (nếu có) trỏ vào tệp lành khớp sha256."""
    for pt_file in ckpt_dir.glob("*.pt"):
        torch.load(pt_file, weights_only=True)
    for meta_file in ckpt_dir.glob("*.meta.json"):
        json.loads(meta_file.read_text(encoding="utf-8"))
    latest = ckpt_dir / "latest.json"
    if not latest.exists():
        return
    info = json.loads(latest.read_text(encoding="utf-8"))
    target = ckpt_dir / Path(info["path"]).name
    assert target.is_file(), "latest.json trỏ vào tệp không tồn tại"
    assert hashlib.sha256(target.read_bytes()).hexdigest() == info["sha256"], (
        "latest.json trỏ vào tệp có sha256 không khớp"
    )
    load_checkpoint(latest)


class _Kill(BaseException):
    """Mô phỏng tiến trình bị giết tại một bước (không chạy được khối except OSError)."""


def _inject(
    monkeypatch: pytest.MonkeyPatch, target: str, nth: int, exc: BaseException
) -> list[int]:
    """Làm lời gọi thứ `nth` của `target` ném `exc`; trả bộ đếm số lần đã kích hoạt."""
    import mma_ai.learning.checkpoint as ckpt_module

    fired: list[int] = []
    calls = {"n": 0}

    def wrap(real: Callable[..., Any]) -> Callable[..., Any]:
        def inner(*args: Any, **kwargs: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == nth:
                fired.append(1)
                raise exc
            return real(*args, **kwargs)

        return inner

    if target == "os.replace":
        monkeypatch.setattr(os, "replace", wrap(os.replace))
    elif target == "os.fsync":
        monkeypatch.setattr(os, "fsync", wrap(os.fsync))
    elif target == "torch.save":
        monkeypatch.setattr(torch, "save", wrap(torch.save))
    else:
        monkeypatch.setattr(ckpt_module, "_compute_sha256", wrap(ckpt_module._compute_sha256))
    return fired


@pytest.mark.parametrize("mode", ["oserror", "kill"])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("nth", [1, 2, 3])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("target", ["os.replace", "os.fsync", "torch.save", "sha256"])  # type: ignore[untyped-decorator]
def test_inv004_failure_at_each_save_step_keeps_dir_consistent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, nth: int, mode: str
) -> None:
    """Ngắt/ghi lỗi tại từng bước save_checkpoint (AC-2): không tệp nửa vời, latest.json lành."""
    agent = _agent()
    run_dir = _run_layout(tmp_path)
    _save(agent, run_dir, 1)
    exc: BaseException = _Kill() if mode == "kill" else OSError("đĩa đầy giả lập")
    fired = _inject(monkeypatch, target, nth, exc)
    try:
        _save(agent, run_dir, 2)
    except (CheckpointIOError, OSError, _Kill):
        pass
    if not fired:
        pytest.skip("bước này không được gọi lần thứ nth")
    monkeypatch.undo()
    _assert_checkpoint_dir_consistent(run_dir / "checkpoints")
    if mode == "oserror":
        leftovers = [p.name for p in (run_dir / "checkpoints").glob("*.tmp")]
        assert not leftovers, f"lỗi ghi để lại tệp tạm: {leftovers}"


def test_inv004_partial_write_raising_runtimeerror_leaves_no_tmp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """torch.save thật ném RuntimeError khi đĩa đầy (PytorchStreamWriter): phải dọn tệp tạm."""

    real_save = torch.save

    def partial_save(obj: Any, f: Any, *args: Any, **kwargs: Any) -> None:
        real_save({"x": torch.zeros(4)}, f)
        raise RuntimeError("PytorchStreamWriter failed writing file data/0: file write failed")

    monkeypatch.setattr(torch, "save", partial_save)
    agent = _agent()
    run_dir = _run_layout(tmp_path)
    with pytest.raises((CheckpointIOError, RuntimeError)):
        _save(agent, run_dir, 1)
    monkeypatch.undo()
    leftovers = sorted(p.name for p in (run_dir / "checkpoints").iterdir())
    assert not leftovers, f"tệp nửa vời còn lại sau lỗi ghi: {leftovers}"


def _poison(name: str, agent: PPOAgent, norm: RunningNorm) -> dict[str, Any]:
    """Đầu độc đúng một thành phần bằng NaN/Inf; trả ctx bổ sung."""
    extra: dict[str, Any] = {}
    if name == "actor":
        agent.model.actor[0].weight.data[0, 0] = float("nan")
    elif name == "critic":
        agent.model.critic[-1].bias.data[0] = float("inf")
    elif name == "log_std":
        agent.model.log_std.data[2] = float("-inf")
    elif name == "optimizer_state":
        state = next(iter(agent.optimizer.state.values()))
        state["exp_avg"][0] = float("nan")
    elif name == "normalizer":
        norm._m2 = np.full(OBS_DIM, np.nan)  # noqa: SLF001
    elif name == "config_float":
        extra["config"] = {"learning_rate": float("nan")}
    return extra


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "component", ["actor", "critic", "log_std", "optimizer_state", "normalizer", "config_float"]
)
def test_inv004_nonfinite_in_any_component_never_reaches_disk(
    tmp_path: Path, component: str
) -> None:
    agent = _agent()
    agent.update(_buffer(64))
    norm = _norm()
    extra = _poison(component, agent, norm)
    ctx = _trainer_ctx(agent, norm, 1)
    ctx.update(extra)
    run_dir = _run_layout(tmp_path)
    with pytest.raises(NonFiniteError):
        save_checkpoint(agent, run_dir, kind="periodic", ctx=ctx)
    assert list((run_dir / "checkpoints").iterdir()) == []


def test_inv004_checkpoint_stores_agent_numpy_rng_state(tmp_path: Path) -> None:
    """Checkpoint MUST chứa trạng thái sinh số ngẫu nhiên THỰC của agent (không phải seed gốc)."""
    agent = _agent(seed=7)
    agent.update(_buffer())
    agent.update(_buffer(seed=1))
    expected = copy.deepcopy(agent._rng.bit_generator.state)  # noqa: SLF001
    run_dir = _run_layout(tmp_path)
    _save(agent, run_dir, 2)
    loaded = load_checkpoint(run_dir / "checkpoints" / "latest.json")
    assert loaded.rng_state["numpy"] == expected, (
        "rng_state['numpy'] trong checkpoint là trạng thái seed gốc, không phải trạng thái đã tiến"
    )


def test_inv004_resume_continues_same_trajectory_as_uninterrupted(tmp_path: Path) -> None:
    """Train tiếp từ checkpoint cho đúng quỹ đạo như chạy liền (xáo minibatch liên tục)."""
    buffers = [_buffer(seed=s) for s in range(3)]
    straight = _agent(seed=3)
    resumed_src = _agent(seed=3)
    for buf in buffers[:2]:
        straight.update(buf)
        resumed_src.update(buf)
    straight.update(buffers[2])

    run_dir = _run_layout(tmp_path)
    _save(resumed_src, run_dir, 2)
    loaded = load_checkpoint(run_dir / "checkpoints" / "latest.json", for_training=True)

    fresh = _agent(seed=3)
    fresh.load_state_dict(
        {
            "actor": loaded.actor_state_dict,
            "critic": loaded.critic_state_dict,
            "log_std": loaded.log_std,
            "optimizer": loaded.optimizer_state_dict,
        }
    )
    if loaded.rng_state.get("numpy"):
        fresh._rng.bit_generator.state = loaded.rng_state["numpy"]  # noqa: SLF001
    fresh.update(buffers[2])

    for (name, left), (_, right) in zip(
        straight.model.named_parameters(), fresh.model.named_parameters(), strict=True
    ):
        assert torch.allclose(left, right, atol=1e-6), f"tham số {name} lệch sau khi train tiếp"


def test_inv004_control_restoring_true_rng_state_restores_trajectory(tmp_path: Path) -> None:
    """Đối chứng của F-001: nếu khôi phục đúng _rng thực thì quỹ đạo khớp chạy liền."""
    buffers = [_buffer(seed=s) for s in range(3)]
    straight = _agent(seed=3)
    source = _agent(seed=3)
    for buf in buffers[:2]:
        straight.update(buf)
        source.update(buf)
    straight.update(buffers[2])
    fresh = _agent(seed=3)
    fresh.load_state_dict(source.state_dict())
    fresh._rng.bit_generator.state = copy.deepcopy(source._rng.bit_generator.state)  # noqa: SLF001
    fresh.update(buffers[2])
    for (name, left), (_, right) in zip(
        straight.model.named_parameters(), fresh.model.named_parameters(), strict=True
    ):
        assert torch.allclose(left, right, atol=1e-6), f"tham số {name} lệch"


def _saved_checkpoint(tmp_path: Path) -> tuple[Path, Path]:
    agent = _agent()
    agent.update(_buffer(64))
    run_dir = _run_layout(tmp_path)
    meta = _save(agent, run_dir, 1)
    return run_dir, run_dir / meta.path


def _tensors_equal(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return bool(torch.equal(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_tensors_equal(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_tensors_equal(a, b) for a, b in zip(left, right))
    return bool(left == right)


def test_inv004_truncated_checkpoint_raises_checkpoint_error_with_cause(tmp_path: Path) -> None:
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    blob = pt_file.read_bytes()
    rng = np.random.default_rng(11)
    cuts = sorted(
        {0, 1, 8, len(blob) - 1, len(blob) // 2, *rng.integers(1, len(blob), 25).tolist()}
    )
    for cut in cuts:
        pt_file.write_bytes(blob[:cut])
        with pytest.raises(CheckpointError) as err:
            load_checkpoint(pt_file)
        assert str(pt_file.name) in str(err.value) or "hỏng" in str(err.value)


def test_inv004_random_bitflip_never_loads_silently_different(tmp_path: Path) -> None:
    """Lật bit tại vị trí ngẫu nhiên: hoặc lỗi CheckpointError, hoặc nạp được dữ liệu y hệt."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    original = load_checkpoint(pt_file)
    blob = bytearray(pt_file.read_bytes())
    rng = np.random.default_rng(2024)
    silent: list[int] = []
    raw: list[str] = []
    for position in rng.integers(0, len(blob), 60).tolist():
        mutated = bytearray(blob)
        mutated[position] ^= 1 << int(rng.integers(0, 8))
        pt_file.write_bytes(bytes(mutated))
        try:
            loaded = load_checkpoint(pt_file)
        except CheckpointError:
            continue
        except Exception as err:  # noqa: BLE001
            raw.append(f"{position}:{type(err).__name__}")
            continue
        same = _tensors_equal(
            loaded.actor_state_dict, original.actor_state_dict
        ) and _tensors_equal(loaded.critic_state_dict, original.critic_state_dict)
        if not same:
            silent.append(position)
    pt_file.write_bytes(bytes(blob))
    assert not raw, f"lật bit làm lộ ngoại lệ thô (không phải CheckpointError): {raw}"
    assert not silent, f"lật bit nạp thành công nhưng trọng số khác gốc, tại byte {silent}"


def _locate_float32(blob: bytes, value: torch.Tensor) -> int:
    return blob.find(value.detach().numpy().astype(np.float32).tobytes())


@pytest.mark.parametrize("bits", [0x7FC00000, 0x7F800000, 0xFF800000], ids=["nan", "+inf", "-inf"])  # type: ignore[untyped-decorator]
def test_inv004_load_rejects_nonfinite_weights_in_corrupt_file(tmp_path: Path, bits: int) -> None:
    """Tệp bị hỏng thành NaN/Inf (lật bit mũ): nạp MUST lỗi, không trao NaN cho policy."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    original = load_checkpoint(pt_file)
    first = original.actor_state_dict["0.weight"].reshape(-1)[:4]
    blob = bytearray(pt_file.read_bytes())
    offset = _locate_float32(bytes(blob), first)
    assert offset >= 0, "không định vị được dữ liệu trọng số trong tệp (hỏng fixture)"
    blob[offset : offset + 4] = bits.to_bytes(4, "little")
    pt_file.write_bytes(bytes(blob))
    with pytest.raises(CheckpointError):
        load_checkpoint(pt_file)


def test_inv004_load_verifies_sha256_recorded_in_pointer(tmp_path: Path) -> None:
    """latest.json ghi sha256: tệp trỏ tới bị sửa thì nạp qua con trỏ MUST từ chối."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    original = load_checkpoint(pt_file)
    first = original.actor_state_dict["0.weight"].reshape(-1)[:4]
    blob = bytearray(pt_file.read_bytes())
    offset = _locate_float32(bytes(blob), first)
    blob[offset : offset + 4] = np.float32(0.123456).tobytes()
    pt_file.write_bytes(bytes(blob))
    with pytest.raises(CheckpointError):
        load_checkpoint(run_dir / "checkpoints" / "latest.json")


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "pointer",
    ["", "{", "[]", "{}", '{"path": 7}', '{"path": "checkpoints/missing.pt"}', "\x00"],
)
def test_inv004_broken_latest_pointer_raises_checkpoint_error(tmp_path: Path, pointer: str) -> None:
    run_dir, _ = _saved_checkpoint(tmp_path)
    latest = run_dir / "checkpoints" / "latest.json"
    latest.write_text(pointer, encoding="utf-8")
    with pytest.raises(CheckpointError):
        load_checkpoint(latest)


def test_inv004_concurrent_reader_never_sees_inconsistent_pointer(tmp_path: Path) -> None:
    """Người đọc (giao diện 3D) đọc latest.json trong lúc train ghi checkpoint mới."""
    agent = _agent()
    run_dir = _run_layout(tmp_path)
    _save(agent, run_dir, 1)
    stop = threading.Event()
    errors: list[str] = []

    def reader() -> None:
        latest = run_dir / "checkpoints" / "latest.json"
        while not stop.is_set():
            try:
                load_checkpoint(latest)
            except Exception as err:  # noqa: BLE001
                errors.append(f"{type(err).__name__}: {err}")
                return

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        for idx in range(2, 22):
            _save(agent, run_dir, idx)
    finally:
        stop.set()
        thread.join(10)
    assert not errors, errors[:1]


# --------------------------------------------------------------------------------------
# INV-002 — hành động trong [0,1]^6
# --------------------------------------------------------------------------------------

EXTREMES = [1e30, -1e30, 3.0e38, -3.0e38, 1e-45, 0.0, 100.0, -100.0, 17.0, -104.0]


def _model_with_constant_mean(value: float, log_std: float = -0.5) -> ActorCritic:
    cfg = _cfg()
    model = ActorCritic(OBS_DIM, ACT_DIM, cfg)
    for layer in model.actor:
        if isinstance(layer, torch.nn.Linear):
            layer.weight.data.zero_()
    model.actor[-1].bias.data.fill_(value)
    model.log_std.data.fill_(log_std)
    return model


@pytest.mark.parametrize("value", EXTREMES)  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("deterministic", [True, False])  # type: ignore[untyped-decorator]
def test_inv002_extreme_raw_output_stays_inside_unit_cube(
    value: float, deterministic: bool
) -> None:
    """Đầu ra thô cực đoan (AC-1): hành động luôn nằm trong [0,1]^6."""
    model = _model_with_constant_mean(value)
    obs = torch.randn(32, OBS_DIM)
    action, _, _ = model.act(obs, deterministic=deterministic)
    assert action.shape == (32, ACT_DIM)
    assert bool(torch.isfinite(action).all())
    assert bool(((action >= 0.0) & (action <= 1.0)).all())


@pytest.mark.parametrize("log_std", [-200.0, -20.0, 20.0, 60.0, 88.0, 100.0, float("nan")])  # type: ignore[untyped-decorator]
def test_inv002_extreme_log_std_never_emits_out_of_range_action(log_std: float) -> None:
    model = _model_with_constant_mean(0.0, log_std=log_std)
    try:
        action, _, _ = model.act(torch.randn(16, OBS_DIM), deterministic=False)
    except (NonFiniteError, ValueError):
        return
    assert bool(torch.isfinite(action).all())
    assert bool(((action >= 0.0) & (action <= 1.0)).all())


@pytest.mark.parametrize("scale", [1e6, 1e30, 3e38])  # type: ignore[untyped-decorator]
def test_inv002_policy_deterministic_action_with_huge_observation(scale: float) -> None:
    cfg = _cfg()
    policy = Policy(ActorCritic(OBS_DIM, ACT_DIM, cfg), _norm())
    obs = np.full(OBS_DIM, scale, dtype=np.float64)
    action = policy.act_deterministic(obs)
    assert action.shape == (ACT_DIM,)
    assert np.all(np.isfinite(action)) and np.all(action >= 0.0) and np.all(action <= 1.0)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])  # type: ignore[untyped-decorator]
def test_inv002_nonfinite_observation_never_yields_out_of_range_action(bad: float) -> None:
    """NaN/Inf từ môi trường: hoặc dừng bằng NonFiniteError, hoặc (Inf bị cắt) vẫn trong [0,1]."""
    cfg = _cfg()
    policy = Policy(ActorCritic(OBS_DIM, ACT_DIM, cfg), _norm())
    obs = np.zeros(OBS_DIM)
    obs[3] = bad
    try:
        action = policy.act_deterministic(obs)
    except NonFiniteError:
        return
    assert np.all(np.isfinite(action)) and np.all(action >= 0.0) and np.all(action <= 1.0)


@pytest.mark.parametrize("shape", [(0,), (13,), (15,), (2, 3, 14)])  # type: ignore[untyped-decorator]
def test_inv002_wrong_shape_observation_raises_or_stays_in_range(shape: tuple[int, ...]) -> None:
    cfg = _cfg()
    policy = Policy(ActorCritic(OBS_DIM, ACT_DIM, cfg), _norm())
    try:
        action = policy.act_deterministic(np.zeros(shape))
    except Exception:  # noqa: BLE001
        return
    assert np.all(np.isfinite(action)) and np.all(action >= 0.0) and np.all(action <= 1.0)


# --------------------------------------------------------------------------------------
# INV-003 — chỉ mục tiêu tập train
# --------------------------------------------------------------------------------------


class _StubEnv:
    """Môi trường giả tối thiểu để thử Trainer; `infos` quyết định target_split mỗi lần reset."""

    def __init__(self, infos: list[dict[str, Any]], split: str | None = None) -> None:
        self.observation_space = types.SimpleNamespace(shape=(OBS_DIM,))
        self.action_space = types.SimpleNamespace(shape=(ACT_DIM,))
        self.model_sha256 = "b" * 64
        self._infos = infos
        self.resets = 0
        self.steps = 0
        if split is not None:
            self.split = split

    def reset(self, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        info = self._infos[min(self.resets, len(self._infos) - 1)]
        self.resets += 1
        return np.zeros(OBS_DIM), dict(info)

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        self.steps += 1
        assert np.all(action >= 0.0) and np.all(action <= 1.0)
        return np.zeros(OBS_DIM), 0.0, True, False, {}


def _tiny_cfg(tmp_path: Path) -> TrainConfig:
    return _cfg(
        **{
            "schedule.total_timesteps": 16,
            "schedule.n_steps": 8,
            "schedule.batch_size": 8,
            "schedule.n_epochs": 1,
            "paths.runs_dir": "runs",
            "ui.mode": "none",
        }
    )


@pytest.mark.parametrize("split", ["test", "Test", "TRAIN", " train", "train\x00", "", "val"])  # type: ignore[untyped-decorator]
def test_inv003_trainer_rejects_non_train_env_split(tmp_path: Path, split: str) -> None:
    env = _StubEnv([{"target_split": "train"}], split=split)
    with pytest.raises(TrainError):
        Trainer(_tiny_cfg(tmp_path), env, tmp_path / "run")
    assert env.resets == 0


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "infos",
    [
        [{"target_split": "test"}],
        [{}],
        [{"target_split": None}],
        [{"target_split": "Train"}],
        [{"target_split": "train"}, {"target_split": "test"}],
        [{"target_split": "train"}] * 3 + [{"target_split": "test"}],
    ],
    ids=["test", "missing", "none", "case", "second-reset", "fourth-reset"],
)
def test_inv003_wrapped_env_without_split_attr_still_stops_on_foreign_target(
    tmp_path: Path, infos: list[dict[str, Any]]
) -> None:
    """Bọc môi trường làm mất thuộc tính split: kiểm tra qua info ở mọi lần reset vẫn dừng train."""
    env = _StubEnv(infos)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    trainer = Trainer(_tiny_cfg(tmp_path), env, run_dir)
    with pytest.raises(TrainError):
        trainer.run()
    assert not list((run_dir / "checkpoints").glob("*.pt")), (
        "đã ghi checkpoint sau khi bốc mục tiêu lạ"
    )


def test_inv003_real_env_test_split_rejected_and_train_split_reports_train(tmp_path: Path) -> None:
    """Môi trường thật (AC-1): split test bị từ chối, split train luôn báo train."""
    from mma_ai.environment.single_agent import make_env

    with pytest.raises(TrainError):
        Trainer(_tiny_cfg(tmp_path), make_env(split="test"), tmp_path / "run")
    env = make_env(split="train")
    for seed in range(12):
        _, info = env.reset(seed=seed)
        assert info["target_split"] == "train"
    for _ in range(12):
        _, info = env.reset()
        assert info["target_split"] == "train"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "overrides",
    [
        {"env.split": "test"},
        {"split": "test"},
        {"schedule.split": "test"},
        {"ui.split": "test"},
        {"paths.split": "test"},
    ],
)
def test_inv003_config_cannot_force_split(overrides: dict[str, Any]) -> None:
    with pytest.raises(TrainConfigError):
        TrainConfig.load(overrides=overrides)


@pytest.mark.parametrize("flag", [["--split", "test"], ["--split=test"], ["--env-split", "test"]])  # type: ignore[untyped-decorator]
def test_inv003_cli_has_no_split_flag(flag: list[str]) -> None:
    assert train_main(flag) == 2


# --------------------------------------------------------------------------------------
# INV-001 — thư mục run riêng, không ghi đè
# --------------------------------------------------------------------------------------


def _freeze_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    import mma_ai.learning.run_dir as run_dir_module

    class _Fixed:
        @staticmethod
        def now(tz: Any = None) -> Any:
            import datetime as dt

            return dt.datetime(2026, 10, 10, 1, 2, 3, tzinfo=tz)

    monkeypatch.setattr(run_dir_module, "datetime", _Fixed)


def test_inv001_same_second_same_seed_never_overwrites_prepopulated_runs_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cùng giây, cùng seed (AC-3): không ghi đè run cũ."""
    _freeze_clock(monkeypatch)
    root = tmp_path / "runs"
    first = create_run_dir(root, "elbow", 42)
    (first.path / "checkpoints" / "ckpt_u000001.pt").write_bytes(b"cha")
    (first.path / "manifest.json").write_text("{}", encoding="utf-8")
    before = _tree_hash(first.path)
    second = create_run_dir(root, "elbow", 42)
    assert second.path != first.path and second.run_id != first.run_id
    assert _tree_hash(first.path) == before


def test_inv001_concurrent_creation_same_second_yields_unique_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _freeze_clock(monkeypatch)
    root = tmp_path / "runs"
    results: list[str] = []
    errors: list[str] = []
    barrier = threading.Barrier(40)

    def worker() -> None:
        barrier.wait()
        try:
            results.append(create_run_dir(root, "elbow", 42).run_id)
        except Exception as err:  # noqa: BLE001
            errors.append(f"{type(err).__name__}: {err}")

    threads = [threading.Thread(target=worker) for _ in range(40)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert not errors, errors[:1]
    assert len(set(results)) == 40
    assert all((root / run_id / "checkpoints").is_dir() for run_id in results)


@pytest.mark.requires_symlink(  # type: ignore[untyped-decorator]
    reason="Tạo liên kết tượng trưng (symlink) cần quyền đặc biệt trên Windows"
)
def test_inv001_symlinked_and_file_collisions_do_not_write_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _freeze_clock(monkeypatch)
    root = tmp_path / "runs"
    root.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("giữ", encoding="utf-8")
    base = "20261010T010203Z_elbow_s42"
    (root / base).symlink_to(victim, target_is_directory=True)
    (root / f"{base}-2").symlink_to(tmp_path / "dangling")
    (root / f"{base}-3").write_text("tệp thường", encoding="utf-8")
    before = _tree_hash(victim)
    created = create_run_dir(root, "elbow", 42)
    assert created.run_id == f"{base}-4"
    assert _tree_hash(victim) == before
    assert not (tmp_path / "dangling").exists()


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False,
    reason=(
        "F-005: create_run_dir nhận stage chứa dấu phân cách đường dẫn: ném FileNotFoundError "
        "thô hoặc tạo thư mục ngoài runs_dir (chỉ chạm được qua API; CLI ép stage='elbow')"
    ),
)
@pytest.mark.parametrize("stage", ["a/b", "x_s1/../../escape"])  # type: ignore[untyped-decorator]
def test_inv001_stage_with_path_separators_cannot_leave_runs_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """API nhận stage tuỳ ý: không được tạo/đi ra ngoài runs_dir; lỗi MUST là RunDirError."""
    _freeze_clock(monkeypatch)
    root = tmp_path / "area" / "runs"
    root.mkdir(parents=True)
    create_run_dir(root, "x", 1)
    try:
        created = create_run_dir(root, stage, 1)
    except RunDirError:
        return
    except Exception as err:  # noqa: BLE001
        pytest.fail(f"lỗi thô {type(err).__name__} thay cho RunDirError: {err}")
    assert created.path.resolve().parent == root.resolve()


def _write_smoke_yaml(tmp_path: Path, **ui: Any) -> Path:
    import importlib.resources

    text = (
        importlib.resources.files("mma_ai.learning").joinpath("train_elbow_smoke.yaml")
    ).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    data["schedule"].update(
        {"total_timesteps": 1536, "n_steps": 64, "batch_size": 64, "n_epochs": 2}
    )
    data["network"].update({"actor_hidden": [16, 16], "critic_hidden": [16, 16]})
    data["paths"]["runs_dir"] = "runs"
    data["ui"].update(ui)
    path = tmp_path / "smoke.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def test_inv001_resume_creates_new_run_and_leaves_parent_untouched(tmp_path: Path) -> None:
    config = _write_smoke_yaml(tmp_path, mode="none")
    cmd = [sys.executable, "-m", "mma_ai.learning.cli", "--config", str(config), "--ui", "none"]
    first = subprocess.run(
        cmd, capture_output=True, text=True, env=_cli_env(), timeout=300, cwd=tmp_path
    )
    assert first.returncode == 0, first.stderr
    runs = sorted(p for p in (tmp_path / "runs").iterdir() if p.is_dir())
    assert len(runs) == 1
    parent = runs[0]
    parent_hash = _tree_hash(parent)
    parent_stat = {p.name: p.stat().st_mtime_ns for p in parent.rglob("*") if p.is_file()}
    second = subprocess.run(
        [*cmd, "--resume", str(parent / "checkpoints" / "latest.json")],
        capture_output=True,
        text=True,
        env=_cli_env(),
        timeout=300,
        cwd=tmp_path,
    )
    assert second.returncode == 0, second.stderr
    runs_after = sorted(p for p in (tmp_path / "runs").iterdir() if p.is_dir())
    assert len(runs_after) == 2
    assert _tree_hash(parent) == parent_hash
    assert parent_stat == {p.name: p.stat().st_mtime_ns for p in parent.rglob("*") if p.is_file()}


# --------------------------------------------------------------------------------------
# INV-005 — giao diện chỉ đọc
# --------------------------------------------------------------------------------------


@pytest.fixture()  # type: ignore[untyped-decorator]
def served_run(tmp_path: Path) -> Iterator[tuple[Path, dashboard.Server]]:
    (tmp_path / "secret.txt").write_text("TOPSECRET", encoding="utf-8")
    run_dir = tmp_path / "run"
    (run_dir / "checkpoints").mkdir(parents=True)
    (run_dir / "progress.json").write_text('{"status": "running"}', encoding="utf-8")
    (run_dir / "checkpoints" / "latest.json").write_text("{}", encoding="utf-8")
    (run_dir / "config.json").write_text('{"seed": 1}', encoding="utf-8")
    server = dashboard.serve(run_dir, host="127.0.0.1", port=0)
    try:
        yield run_dir, server
    finally:
        server.close()


def _raw_request(port: int, payload: bytes, read_limit: int = 1 << 16) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(payload)
        chunks: list[bytes] = []
        total = 0
        try:
            while total < read_limit:
                data = sock.recv(8192)
                if not data:
                    break
                chunks.append(data)
                total += len(data)
        except (TimeoutError, ConnectionError):
            pass
        return b"".join(chunks)


def _status(response: bytes) -> int:
    parts = response.split(b" ", 2)
    return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0


METHODS = [
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
    "HEAD",
    "TRACE",
    "CONNECT",
    "FOO",
    "PROPFIND",
    "MKCOL",
    "COPY",
    "MOVE",
    "get",
    "G\x00T",
    "LOCK",
    "PURGE",
]


@pytest.mark.parametrize("method", METHODS)  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("path", ["/api/progress", "/", "/checkpoints/latest.json", "/config.json"])  # type: ignore[untyped-decorator]
def test_inv005_unusual_methods_never_modify_run_dir(
    served_run: tuple[Path, dashboard.Server], method: str, path: str
) -> None:
    run_dir, server = served_run
    before = _tree_hash(run_dir)
    body = b"x" * 512
    request = (
        f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("latin-1") + body
    response = _raw_request(server.port, request)
    assert _status(response) != 500
    assert b"TOPSECRET" not in response
    assert _tree_hash(run_dir) == before
    assert _status(_raw_request(server.port, b"GET /api/progress HTTP/1.0\r\n\r\n")) == 200


TRAVERSAL_TARGETS = [
    "/../secret.txt",
    "/%2e%2e/secret.txt",
    "/%2E%2E%2Fsecret.txt",
    "/api/progress/../../secret.txt",
    "/api/progress/%2e%2e/%2e%2e/secret.txt",
    "/..%2fsecret.txt",
    "/api/progress%00.json",
    "//api/progress",
    "/api//progress",
    "/./api/progress",
    "/api/progress/",
    "/api/progress;x=1",
    "/%2fetc/passwd",
    "/..\\secret.txt",
    "/api/progress\\..\\..\\secret.txt",
    "/checkpoints/latest.json",
    "/config.json",
    "/progress.json",
    "/ui.json",
    "/.git/config",
    "/api/../progress.json",
    "http://127.0.0.1/../secret.txt",
    "/api/progress?file=../secret.txt",
]


@pytest.mark.parametrize("target", TRAVERSAL_TARGETS)  # type: ignore[untyped-decorator]
def test_inv005_path_traversal_and_encoded_dots_never_read_outside_progress(
    served_run: tuple[Path, dashboard.Server], target: str
) -> None:
    run_dir, server = served_run
    before = _tree_hash(run_dir)
    request = f"GET {target} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode(
        "latin-1"
    )
    response = _raw_request(server.port, request)
    assert b"TOPSECRET" not in response
    assert b'"seed"' not in response, "lộ config.json qua đường dẫn lạ"
    assert _status(response) != 500
    assert _tree_hash(run_dir) == before


def test_inv005_hostile_connections_do_not_stop_the_server(
    served_run: tuple[Path, dashboard.Server],
) -> None:
    run_dir, server = served_run
    before = _tree_hash(run_dir)
    idle = [socket.create_connection(("127.0.0.1", server.port), timeout=5) for _ in range(60)]
    try:
        assert _status(_raw_request(server.port, b"GET /api/progress HTTP/1.0\r\n\r\n")) == 200
        for _ in range(150):
            sock = socket.create_connection(("127.0.0.1", server.port), timeout=5)
            sock.sendall(b"GET /api/progress HTTP/1.1\r\nHost: x\r\n\r\n")
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, b"\x01\x00\x00\x00\x00\x00\x00\x00"
            )
            sock.close()
        huge = b"GET /" + b"A" * 200_000 + b" HTTP/1.1\r\n\r\n"
        assert _status(_raw_request(server.port, huge)) in (414, 400, 431, 0)
        huge_header = b"GET / HTTP/1.1\r\nX: " + b"B" * 200_000 + b"\r\n\r\n"
        assert _status(_raw_request(server.port, huge_header)) in (431, 400, 0)
        assert _status(_raw_request(server.port, b"\x00\xff\xfe\r\n\r\n")) in (400, 0, 505, 501)
        assert _status(_raw_request(server.port, b"GET /api/progress HTTP/1.0\r\n\r\n")) == 200
    finally:
        for sock in idle:
            sock.close()
    assert _tree_hash(run_dir) == before


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "host",
    [
        "0.0.0.0",
        "",
        "::",
        "192.168.1.5",
        "10.0.0.1",
        "LOCALHOST",
        "127.0.0.1 ",
        "127.1",
        "localhost.",
        "0",
        "example.com",
        "127.0.0.1\x00.evil",
        "[::1]",
        "::ffff:0.0.0.0",
        "*",
    ],
)
def test_inv005_serve_rejects_non_loopback_hosts(tmp_path: Path, host: str) -> None:
    (tmp_path / "run").mkdir()
    with pytest.raises(ValueError):
        dashboard.serve(tmp_path / "run", host=host, port=0)


def test_inv005_localhost_binds_to_a_loopback_address(tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    server = dashboard.serve(tmp_path / "run", host="localhost", port=0)
    try:
        bound = server._httpd.server_address[0]  # noqa: SLF001
        assert ipaddress.ip_address(str(bound)).is_loopback
    finally:
        server.close()


def test_inv005_monitor_cli_non_loopback_host_fails_without_writing_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "progress.json").write_text("{}", encoding="utf-8")
    before = _tree_hash(run_dir)
    assert monitor_main(["--run", str(run_dir), "--host", "0.0.0.0", "--port", "0"]) != 0
    assert _tree_hash(run_dir) == before
    assert not (run_dir / "ui.json").exists()


def test_inv005_monitor_cli_only_writes_ui_json_and_leaves_checkpoints_alone(
    tmp_path: Path,
) -> None:
    agent = _agent()
    run_dir = _run_layout(tmp_path)
    _save(agent, run_dir, 1)
    (run_dir / "progress.json").write_text('{"status":"running"}', encoding="utf-8")
    (run_dir / "config.json").write_text("{}", encoding="utf-8")
    before = {
        p.relative_to(run_dir).as_posix(): p.read_bytes() for p in run_dir.rglob("*") if p.is_file()
    }
    stop = threading.Event()
    thread = threading.Thread(
        target=monitor_main,
        args=(["--run", str(run_dir), "--port", "0"],),
        kwargs={"stop_event": stop},
    )
    thread.start()
    deadline = time.time() + 20
    while not (run_dir / "ui.json").exists() and time.time() < deadline:
        time.sleep(0.05)
    port = int(
        json.loads((run_dir / "ui.json").read_text(encoding="utf-8"))["url"].rsplit(":", 1)[1]
    )
    for method in ("POST", "PUT", "DELETE"):
        _raw_request(port, f"{method} /api/progress HTTP/1.0\r\nContent-Length: 0\r\n\r\n".encode())
    stop.set()
    thread.join(20)
    after = {
        p.relative_to(run_dir).as_posix(): p.read_bytes() for p in run_dir.rglob("*") if p.is_file()
    }
    after.pop("ui.json", None)
    assert after == before, "giao diện đã thêm/sửa tệp ngoài ui.json"


def test_inv005_load_policy_for_viewer_is_read_only(tmp_path: Path) -> None:
    agent = _agent()
    agent.update(_buffer(64))
    run_dir = _run_layout(tmp_path)
    _save(agent, run_dir, 1)
    before = _tree_hash(run_dir)
    stats = {p.name: p.stat().st_mtime_ns for p in run_dir.rglob("*") if p.is_file()}
    policy = load_policy(run_dir / "checkpoints" / "latest.json")
    action = policy.act_deterministic(np.zeros(OBS_DIM))
    assert action.shape == (ACT_DIM,)
    assert _tree_hash(run_dir) == before
    assert stats == {p.name: p.stat().st_mtime_ns for p in run_dir.rglob("*") if p.is_file()}


def test_inv005_killing_ui_process_mid_train_does_not_stop_training(tmp_path: Path) -> None:
    """Giết giao diện (SIGKILL) ngay khi có ui.json (AC-7): train vẫn xong, lưu checkpoint cuối."""
    config = _write_smoke_yaml(tmp_path, mode="web")
    proc = subprocess.Popen(
        [sys.executable, "-m", "mma_ai.learning.cli", "--config", str(config), "--ui", "web"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_cli_env(),
        cwd=tmp_path,
    )
    killed = False
    deadline = time.time() + 120
    try:
        while proc.poll() is None and time.time() < deadline:
            ui_files = list((tmp_path / "runs").glob("*/ui.json"))
            if ui_files and not killed:
                pid = int(json.loads(ui_files[0].read_text(encoding="utf-8"))["pid"])
                os.kill(pid, signal.SIGKILL)
                killed = True
            time.sleep(0.05)
        out, err = proc.communicate(timeout=300)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert killed, "không thấy ui.json để giết giao diện"
    assert proc.returncode == 0, err
    finals = list((tmp_path / "runs").glob("*/checkpoints/*_final.pt"))
    assert finals, "train không lưu được checkpoint cuối sau khi giao diện bị giết"


def test_inv005_two_servers_in_one_process_keep_their_own_run_dir(tmp_path: Path) -> None:
    servers: list[dashboard.Server] = []
    try:
        for name in ("a", "b"):
            run_dir = tmp_path / name
            run_dir.mkdir()
            (run_dir / "progress.json").write_text(json.dumps({"run": name}), encoding="utf-8")
            servers.append(dashboard.serve(run_dir, host="127.0.0.1", port=0))
        first = _raw_request(servers[0].port, b"GET /api/progress HTTP/1.0\r\n\r\n")
        assert b'"run": "a"' in first
    finally:
        for server in servers:
            server.close()


# --------------------------------------------------------------------------------------
# Vòng 2 — vector mới mở ra bởi bản vá F-001/F-002/F-003 (đối chiếu sha256, quét hữu hạn,
# RNG numpy thực): đường nạp qua Trainer, qua meta.json, và tệp bị sửa NHẤT QUÁN với sha
# --------------------------------------------------------------------------------------


def _train_cfg_steps(total: int) -> TrainConfig:
    return _cfg(
        **{
            "schedule.total_timesteps": total,
            "schedule.n_steps": 8,
            "schedule.batch_size": 8,
            "schedule.n_epochs": 2,
            "paths.runs_dir": "runs",
            "ui.mode": "none",
        }
    )


def _run_trainer(
    tmp_path: Path, name: str, total: int, resume: Path | None = None
) -> tuple[Trainer, Path]:
    run_dir = tmp_path / name
    run_dir.mkdir()
    env = _StubEnv([{"target_split": "train"}], split="train")
    torch.manual_seed(5)
    trainer = Trainer(_train_cfg_steps(total), env, run_dir, resume_checkpoint=resume)
    trainer.run()
    return trainer, run_dir


def test_inv004_trainer_checkpoints_store_live_agent_rng_state(tmp_path: Path) -> None:
    """AC-2: checkpoint do Trainer thật ghi (periodic và final) chứa RNG numpy THỰC của agent."""
    trainer, run_dir = _run_trainer(tmp_path, "run", 24)
    final = sorted((run_dir / "checkpoints").glob("*_final.pt"))
    assert final, "Trainer không lưu checkpoint cuối"
    loaded = load_checkpoint(final[-1])
    assert loaded.rng_state["numpy"] == trainer.agent._rng.bit_generator.state  # noqa: SLF001


def test_inv004_trainer_resume_matches_uninterrupted_run(tmp_path: Path) -> None:
    """AC-2: chạy 2 lượt, lưu, train tiếp 1 lượt (qua Trainer thật) khớp chạy liền 3 lượt."""
    straight, _ = _run_trainer(tmp_path, "straight", 24)
    first, first_dir = _run_trainer(tmp_path, "first", 16)
    final = sorted((first_dir / "checkpoints").glob("*_final.pt"))[-1]
    resumed, _ = _run_trainer(tmp_path, "resumed", 24, resume=final)
    for name, tensor in straight.agent.model.state_dict().items():
        other = resumed.agent.model.state_dict()[name]
        assert torch.allclose(tensor, other, atol=1e-5), f"tham số {name} lệch sau khi train tiếp"


def _rewrite_consistently(pt_file: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    """Sửa nội dung tệp rồi cập nhật sha256 ở meta.json và latest.json cho khớp (kẻ sửa tinh vi)."""
    data = dict(torch.load(pt_file, weights_only=True))
    mutate(data)
    torch.save(data, pt_file)
    digest = hashlib.sha256(pt_file.read_bytes()).hexdigest()
    for sidecar in (
        pt_file.with_name(f"{pt_file.stem}.meta.json"),
        pt_file.parent / "latest.json",
    ):
        info = json.loads(sidecar.read_text(encoding="utf-8"))
        info["sha256"] = digest
        sidecar.write_text(json.dumps(info), encoding="utf-8")


def _poison_optimizer(data: dict[str, Any]) -> None:
    state = data["optimizer"]["state"]
    first = next(iter(state.values()))
    first["exp_avg"] = first["exp_avg"].clone()
    first["exp_avg"].view(-1)[0] = float("nan")


def _poison_normalizer(data: dict[str, Any]) -> None:
    norm = dict(data["obs_normalizer"])
    for key, value in norm.items():
        if isinstance(value, np.ndarray):
            bad = value.astype(float).copy()
            bad.reshape(-1)[0] = float("inf")
            norm[key] = bad
            break
        if isinstance(value, torch.Tensor) and value.is_floating_point():
            bad_t = value.clone()
            bad_t.view(-1)[0] = float("inf")
            norm[key] = bad_t
            break
        if isinstance(value, float):
            norm[key] = float("nan")
            break
    data["obs_normalizer"] = norm


def _poison_log_std(data: dict[str, Any]) -> None:
    bad = data["log_std"].clone()
    bad.view(-1)[0] = float("-inf")
    data["log_std"] = bad


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "mutate",
    [_poison_optimizer, _poison_normalizer, _poison_log_std],
    ids=["optimizer-nan", "normalizer-inf", "log_std-neginf"],
)
def test_inv004_consistent_sha_but_nonfinite_component_is_rejected(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], None]
) -> None:
    """Sha khớp nhưng thành phần (optimizer/normalizer/log_std) chứa NaN/Inf: nạp MUST lỗi."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    _rewrite_consistently(pt_file, mutate)
    for target in (pt_file, run_dir / "checkpoints" / "latest.json"):
        with pytest.raises(CheckpointError):
            load_checkpoint(target, for_training=True)


def test_inv004_meta_json_path_also_verifies_sha256(tmp_path: Path) -> None:
    """Nạp qua *.meta.json (không phải latest.json): lật bit vẫn MUST bị từ chối."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    blob = bytearray(pt_file.read_bytes())
    first = load_checkpoint(pt_file).actor_state_dict["0.weight"].reshape(-1)[:4]
    offset = _locate_float32(bytes(blob), first)
    blob[offset : offset + 4] = np.float32(0.654321).tobytes()
    pt_file.write_bytes(bytes(blob))
    meta = pt_file.with_name(f"{pt_file.stem}.meta.json")
    with pytest.raises(CheckpointError):
        load_checkpoint(meta)


def test_inv004_pointer_with_wrong_sha_rejects_even_valid_file(tmp_path: Path) -> None:
    """Con trỏ ghi sha sai (tệp .pt còn nguyên): không được nạp như thể hợp lệ."""
    run_dir, pt_file = _saved_checkpoint(tmp_path)
    latest = run_dir / "checkpoints" / "latest.json"
    info = json.loads(latest.read_text(encoding="utf-8"))
    info["sha256"] = "0" * 64
    latest.write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(CheckpointError):
        load_checkpoint(latest)


@pytest.mark.parametrize("how", ["flip", "nan"])  # type: ignore[untyped-decorator]
def test_inv004_trainer_resume_rejects_corrupt_checkpoint_with_checkpoint_error(
    tmp_path: Path, how: str
) -> None:
    """Resume qua Trainer: tệp hỏng phải báo CheckpointError (mã 4), không train tiếp."""
    agent = _agent()
    agent.update(_buffer(64))
    run_dir = _run_layout(tmp_path)
    ctx = _trainer_ctx(agent, _norm(), 1)
    ctx["model_sha256"] = "b" * 64
    meta = save_checkpoint(agent, run_dir, kind="final", ctx=ctx)
    pt_file = run_dir / meta.path
    blob = bytearray(pt_file.read_bytes())
    first = load_checkpoint(pt_file).actor_state_dict["0.weight"].reshape(-1)[:4]
    offset = _locate_float32(bytes(blob), first)
    bits = np.float32(0.5).tobytes() if how == "flip" else (0x7FC00000).to_bytes(4, "little")
    blob[offset : offset + 4] = bits
    pt_file.write_bytes(bytes(blob))
    env = _StubEnv([{"target_split": "train"}], split="train")
    resume_run = tmp_path / "resume_run"
    resume_run.mkdir()
    with pytest.raises(CheckpointError):
        Trainer(_train_cfg_steps(24), env, resume_run, resume_checkpoint=pt_file)


class _PickleBomb:
    """Đối tượng mà unpickle sẽ ghi tệp đánh dấu — mô phỏng checkpoint độc hại."""

    def __init__(self, marker: Path) -> None:
        self.marker = marker

    def __reduce__(self) -> tuple[Callable[..., Any], tuple[Any, ...]]:
        return (Path.write_text, (self.marker, "đã thực thi", "utf-8"))


def test_inv004_malicious_pickle_checkpoint_is_rejected_without_executing(tmp_path: Path) -> None:
    """Checkpoint là pickle có `__reduce__` độc hại: MUST là CheckpointError, không chạy mã."""
    marker = tmp_path / "marker.txt"
    evil = tmp_path / "evil.pt"
    torch.save({"actor": _PickleBomb(marker)}, evil)
    with pytest.raises(CheckpointError):
        load_checkpoint(evil)
    assert not marker.exists()
