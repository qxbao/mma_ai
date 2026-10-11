"""Linux characterization tests for the pre-migration platform behavior."""

from __future__ import annotations

import json
import resource
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from mma_ai.evaluation.errors import EvalConfigError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.learning import benchmark, checkpoint, manifest, progress, resources
from mma_ai.learning.errors import TrainConfigError
from mma_ai.learning.train_config import TrainConfig
from mma_ai.monitoring.viewer3d import View3D
from mma_ai.visualization import display
from mma_ai.visualization.episode import write_episode

pytestmark = [
    pytest.mark.linux_only(reason="Đặc tả hành vi nền Linux trước khi chuyển đổi."),
    pytest.mark.posix_only(reason="Đặc tả định dạng tệp POSIX hiện có."),
]


def test_linux_kib_formula_matches_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-001, INV-007, AC-1, AC-2: Linux quy đổi ru_maxrss từ KiB."""
    monkeypatch.setattr(
        resource,
        "getrusage",
        lambda _who: SimpleNamespace(ru_maxrss=262144),
    )
    monkeypatch.setattr(resources, "_load_torch", lambda: None)
    snapshot = resources.collect_resources()
    assert snapshot["ram_peak_mb"] == 256.0


def test_display_unset_message_matches_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-001, AC-3: thông điệp cũ giữ nguyên khi thiếu cả hai biến."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    fake_glfw = SimpleNamespace(init=lambda: 0, terminate=lambda: None)
    monkeypatch.setitem(sys.modules, "glfw", fake_glfw)
    status = display.display_available()
    assert status.available is False
    assert status.reason == (
        "Không phát hiện màn hình hiển thị: cả hai biến môi trường DISPLAY và "
        "WAYLAND_DISPLAY đều chưa được thiết lập. Vui lòng kiểm tra hoặc dùng "
        "chế độ không màn hình (--headless)."
    )


def test_view3d_has_display_matches_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-001, AC-3: viewer 3D dựa vào DISPLAY hoặc WAYLAND_DISPLAY."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert View3D.has_display() is False
    monkeypatch.setenv("DISPLAY", ":99")
    assert View3D.has_display() is True
    monkeypatch.delenv("DISPLAY")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert View3D.has_display() is True
    monkeypatch.delenv("WAYLAND_DISPLAY")
    no_display = {
        "measured": False,
        "reason": "không có màn hình (DISPLAY chưa đặt)",
    }
    assert benchmark.evaluate_view3d_status() == no_display
    assert benchmark.evaluate_view3d_status(has_display=False) == no_display
    assert benchmark.evaluate_view3d_status(has_display=True) == {
        "measured": False,
        "reason": "chế độ hiển thị 3D tắt mặc định trong lượt đo benchmark",
    }


def test_atomic_write_bytes_match_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-001, AC-4: các writer giữ nguyên byte tệp Linux trước chuyển đổi."""

    class Agent:
        cfg = None

        def state_dict(self) -> dict[str, object]:
            return {"actor": {}, "critic": {}, "optimizer": {}}

    checkpoint_bytes = b"legacy-checkpoint-bytes"
    fake_torch = SimpleNamespace(
        Tensor=type("Tensor", (), {}),
        __version__="test",
        cuda=SimpleNamespace(is_available=lambda: False),
        empty=lambda _size: [],
        get_rng_state=lambda: b"rng",
        save=lambda _payload, stream: stream.write(checkpoint_bytes),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    meta = checkpoint.save_checkpoint(
        Agent(),
        tmp_path,
        kind="periodic",
        ctx={"update_idx": 10, "env_steps": 20480, "model_sha256": "0" * 64, "seed": 42},
    )
    checkpoint_dir = tmp_path / "checkpoints"
    meta_bytes = json.dumps(meta.to_dict(), indent=2).encode("utf-8")
    assert (checkpoint_dir / "ckpt_u000010.pt").read_bytes() == checkpoint_bytes
    assert (checkpoint_dir / "ckpt_u000010.meta.json").read_bytes() == meta_bytes
    assert (checkpoint_dir / "latest.json").read_bytes() == meta_bytes

    manifest_payload = {"x": "á", "n": 1, "status": "running"}
    manifest.write_manifest(tmp_path, manifest_payload)
    assert (tmp_path / "manifest.json").read_bytes() == (
        '{\n  "x": "á",\n  "n": 1,\n  "status": "running"\n}'
    ).encode("utf-8")

    snapshot = {
        "schema_version": "1.0.0",
        "run_id": "legacy",
        "stage": "elbow",
        "seed": 1,
        "status": "running",
        "timestamp_utc": "1970-01-01T00:00:00Z",
        "update_idx": 1,
        "env_steps": 1,
        "total_steps": 1,
        "env_steps_per_second": 1.0,
        "mean_return": None,
        "loss": None,
        "activation": None,
        "checkpoint": None,
        "history": {"env_steps": [], "mean_return": [], "value_loss": []},
    }
    progress.ProgressWriter(
        tmp_path, snapshot_interval_s=0, history_points=1, clock=lambda: 0
    ).write(snapshot)
    assert (tmp_path / "progress.json").read_bytes() == json.dumps(
        snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")

    report_path = tmp_path / "benchmark.json"
    benchmark.write_benchmark_report(report_path, {"x": "á", "n": 1})
    assert report_path.read_bytes() == b'{\n  "x": "\xc3\xa1",\n  "n": 1\n}\n'

    episode = {
        "schema_version": "1.0.0",
        "created_utc": "2026-10-09T08:00:00Z",
        "seed": 12345,
        "model": {
            "sha256": "3" * 64,
            "source": "model.xml",
            "muscle_names": ["a", "b", "c", "d", "e", "f"],
            "nq": 1,
            "nv": 1,
        },
        "target": {
            "position_m": [0.0, 0.0, 1.0],
            "split": "test",
            "index": 0,
            "tolerance_m": 0.02,
        },
        "source": {
            "checkpoint_path": "runs/example/checkpoint.pt",
            "checkpoint_sha256": "5" * 64,
            "run_id": "example",
            "update_idx": 1,
        },
        "library_versions": {"mujoco": "3.15.0", "numpy": "2.4.6", "python": "3.11.15"},
        "timing": {"action_dt_s": 0.04, "physics_timestep_s": 0.0025},
        "outcome": {
            "terminated": True,
            "truncated": False,
            "end_reason": "reached",
            "reached": True,
            "n_actions": 1,
            "final_distance_m": 0.01,
        },
        "frames": [
            {
                "t_s": 0.0,
                "qpos": [0.0],
                "qvel": [0.0],
                "activation": [0.0] * 6,
                "excitation": None,
                "fingertip_position_m": [0.0, 0.0, 1.0],
                "distance_m": 0.01,
                "reward": 1.0,
            },
            {
                "t_s": 0.04,
                "qpos": [0.1],
                "qvel": [1.0],
                "activation": [0.1] * 6,
                "excitation": [0.1] * 6,
                "fingertip_position_m": [0.0, 0.0, 1.0],
                "distance_m": 0.01,
                "reward": 1.0,
            },
        ],
    }
    episode_path = tmp_path / "episode.json"
    write_episode(episode, episode_path)
    assert episode_path.read_bytes() == json.dumps(
        episode, allow_nan=False, indent=2, ensure_ascii=False
    ).encode("utf-8")


def test_runs_dir_leading_slash_error_matches_legacy() -> None:
    """INV-001, AC-4: config từ chối runs_dir tuyệt đối với lỗi cũ."""
    with pytest.raises(TrainConfigError) as train_error:
        TrainConfig.load(overrides={"paths.runs_dir": "/abs/path"})
    assert str(train_error.value) == (
        "Khoá 'paths.runs_dir' phải là đường dẫn tương đối hợp lệ, nhận '/abs/path'."
    )

    with pytest.raises(EvalConfigError) as eval_error:
        EvalConfig.load(overrides={"paths.runs_dir": "/abs/path"})
    assert str(eval_error.value) == (
        "Giá trị 'paths.runs_dir' phải là đường dẫn tương đối không rỗng và "
        "không bắt đầu bằng '/', nhận được: '/abs/path'"
    )
