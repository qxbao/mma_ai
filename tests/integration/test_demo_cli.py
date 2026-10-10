"""Kiểm thử tích hợp cho phiên chạy demo qua giao diện dòng lệnh (CLI).

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-2: Chạy demo từ checkpoint điều khiển khuỷu tay và lưu bản ghi episode.
- FR-002: Chạy phiên demo một episode trên môi trường khuỷu tay và lưu lại.
- FR-003: Chỉ kích thích cơ bắp (muscle excitation) u in [0, 1]^6 được đưa vào mô phỏng.
- FR-008: Ghi nguyên tử (atomic write) episode của demo khi chỉ định đường dẫn lưu, không ghi đè.
- FR-016: Demo cho phép chọn mục tiêu theo chỉ số (target index) trong tập kiểm thử (test split).
- INV-002: Đường điều khiển duy nhất là kích thích cơ; không can thiệp trạng thái mô phỏng.
- INV-005: Hoạt động chỉ đọc (read-only) đối với dữ liệu và checkpoint huấn luyện.
- NFR-REPRO-001: Tính tái lập (reproducibility) của demo theo seed.
- CMD-VIS-0001: Điểm vào dòng lệnh python -m mma_ai.visualization.cli.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.episode import read_episode


def test_demo_cli_contract_independent_assertion() -> None:
    """AC-2, CMD-VIS-0001, FR-002: Khẳng định hợp đồng độc lập cho CLI demo không phụ thuộc rl."""
    import inspect

    from mma_ai.visualization import cli, replay

    # 1. Hợp đồng điểm vào CLI mỏng và hàm main
    assert hasattr(cli, "main"), "Điểm vào cli.py phải chứa hàm main"
    assert callable(cli.main), "cli.main phải là một hàm gọi được"

    # 2. Hợp đồng hàm điều phối run_replay
    sig = inspect.signature(replay.run_replay)
    assert "argv" in sig.parameters or "args" in sig.parameters, (
        "run_replay phải nhận tham số dòng lệnh"
    )

    # 3. Chạy CLI với --help trả về mã thoát 0 và chứa các cờ hợp đồng AC-2
    proc = subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli", "--help"],
        capture_output=True,
        text=True,
        env=_get_clean_env(),
        timeout=10.0,
        check=False,
    )
    assert proc.returncode == 0
    assert "--checkpoint" in proc.stdout
    assert "--save-episode" in proc.stdout
    assert "--headless" in proc.stdout
    assert "--split" in proc.stdout
    assert "--target-index" in proc.stdout


def _get_contracts_dir() -> Path:
    """Trả về đường dẫn thư mục hợp đồng (contracts directory) của phân hệ 005."""
    return (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
    )


def _get_clean_env() -> dict[str, str]:
    """Tạo bản sao biến môi trường đã loại bỏ DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def _create_test_checkpoint(run_dir: Path, *, seed: int = 42) -> Path:
    """Tạo tệp điểm kiểm tra (checkpoint) hợp lệ phục vụ kiểm thử tích hợp CLI."""
    from mma_ai.learning.checkpoint import save_checkpoint
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.normalizer import RunningNorm
    from mma_ai.learning.ppo import PPOAgent
    from mma_ai.learning.train_config import TrainConfig

    cfg = TrainConfig.load()
    obs_dim = 14
    act_dim = 6

    # Khởi tạo bộ chuẩn hoá và cập nhật mẫu để vượt qua kiểm tra thống kê
    normalizer = RunningNorm(clip_obs=cfg.normalization.clip_obs)
    normalizer.update(np.zeros((4, obs_dim)))

    # Khởi tạo mạng ActorCritic và tác tử PPO
    model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=cfg)
    agent = PPOAgent(model=model, cfg=cfg)
    model_sha256 = load_muscle_model("myoelbow").info.sha256

    checkpoint_ctx = {
        "obs_normalizer": normalizer,
        "update_idx": 1,
        "env_steps": 256,
        "seed": seed,
        "model_sha256": model_sha256,
        "config": cfg,
    }
    save_checkpoint(agent=agent, run_dir=run_dir, kind="final", ctx=checkpoint_ctx)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001_final.pt"
    assert ckpt_path.exists(), f"Không tìm thấy tệp checkpoint vừa tạo tại {ckpt_path}"
    return ckpt_path


def test_demo_saves_episode_headless(tmp_path: Path) -> None:
    """005 AC-2, FR-002, FR-008, FR-010: Chạy demo không màn hình và lưu episode nguyên tử."""
    run_dir = tmp_path / "run_demo_save"
    saved_ep_path = tmp_path / "episodes" / "demo_output.json"
    ckpt_path = _create_test_checkpoint(run_dir, seed=123)
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(saved_ep_path),
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )

    assert proc.returncode == 0, (
        f"Kỳ vọng mã thoát 0 nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # 1. Thẩm định tóm tắt JSON xuất ra stdout tuân thủ hợp đồng replay-summary.schema.json
    summary_schema_file = _get_contracts_dir() / "replay-summary.schema.json"
    assert summary_schema_file.exists(), f"Thiếu tệp lược đồ: {summary_schema_file}"
    summary_schema = json.loads(summary_schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(summary_schema)

    # Tìm khối JSON hợp lệ từ stdout
    parsed_summary: dict[str, Any] | None = None
    for line in proc.stdout.splitlines():
        if line.strip().startswith("{"):
            idx = proc.stdout.find(line)
            parsed_summary = json.loads(proc.stdout[idx:])
            break

    assert parsed_summary is not None, f"Không tìm thấy JSON hợp lệ trong stdout:\n{proc.stdout}"
    errors = list(validator.iter_errors(parsed_summary))
    assert not errors, f"Lược đồ tóm tắt vi phạm replay-summary schema: {errors}"

    assert parsed_summary["mode"] == "demo"
    assert parsed_summary["headless"] is True
    assert parsed_summary["model_check"]["match"] is True

    # 2. Thẩm định tệp episode lưu trên đĩa tồn tại và hợp lệ theo episode.schema.json
    assert saved_ep_path.exists(), "Tệp episode chỉ định lưu không tồn tại trên đĩa"
    episode_schema_file = _get_contracts_dir() / "episode.schema.json"
    assert episode_schema_file.exists(), f"Thiếu tệp lược đồ episode: {episode_schema_file}"
    ep_schema = json.loads(episode_schema_file.read_text(encoding="utf-8"))
    ep_validator = Draft202012Validator(ep_schema)

    ep_dict = json.loads(saved_ep_path.read_text(encoding="utf-8"))
    ep_errors = list(ep_validator.iter_errors(ep_dict))
    assert not ep_errors, f"Tệp episode lưu không khớp với episode schema: {ep_errors}"

    # Đọc lại bằng hàm thư viện read_episode
    loaded_ep = read_episode(saved_ep_path)
    assert len(loaded_ep.frames) >= 2, "Episode phải ghi nhận ít nhất 2 khung hình"
    assert loaded_ep.source is not None, "Episode từ checkpoint phải lưu nguồn (source record)"
    assert ckpt_path.name in loaded_ep.source.checkpoint_path
    assert len(loaded_ep.source.checkpoint_sha256) == 64


def test_demo_only_muscle_excitation_in_unit_interval(tmp_path: Path) -> None:
    """FR-003, INV-002, AC-2: Kích thích cơ bắp u đều nằm trong khoảng đơn vị [0, 1]^6."""
    run_dir = tmp_path / "run_demo_bounds"
    saved_ep_path = tmp_path / "demo_bounded.json"
    ckpt_path = _create_test_checkpoint(run_dir, seed=777)
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(saved_ep_path),
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc.returncode == 0, f"Thực thi demo thất bại: {proc.stderr}"

    episode = read_episode(saved_ep_path)
    assert len(episode.frames) >= 2, "Số lượng khung hình phải >= 2"

    # Khung 0: excitation luôn là None theo luật R4
    assert episode.frames[0].excitation is None, "Khung đầu tiên excitation phải là None"

    # Từ khung 1 trở đi: excitation có đúng 6 phần tử và mọi giá trị thuộc [0.0, 1.0]
    for idx, frame in enumerate(episode.frames[1:], start=1):
        assert frame.excitation is not None, f"Khung hình {idx} thiếu giá trị excitation"
        assert len(frame.excitation) == 6, (
            f"Khung {idx} phải có đúng 6 giá trị kích thích cơ, nhận: {len(frame.excitation)}"
        )
        for muscle_idx, u in enumerate(frame.excitation):
            assert 0.0 <= u <= 1.0, (
                f"Khung {idx}, cơ bắp {muscle_idx}: kích thích cơ {u} nằm ngoài khoảng [0, 1]"
            )

        # Kiểm tra activation cũng phải nằm trong [0.0, 1.0]
        assert len(frame.activation) == 6, f"Khung {idx} phải có đúng 6 activation"
        for muscle_idx, a in enumerate(frame.activation):
            assert 0.0 <= a <= 1.0, (
                f"Khung {idx}, cơ bắp {muscle_idx}: activation {a} nằm ngoài khoảng [0, 1]"
            )


def test_demo_selects_requested_target(tmp_path: Path) -> None:
    """FR-016, AC-2: Demo cho phép chọn mục tiêu theo chỉ số trong tập kiểm thử (test split)."""
    run_dir = tmp_path / "run_demo_target"
    saved_ep_path = tmp_path / "demo_target1.json"
    ckpt_path = _create_test_checkpoint(run_dir, seed=42)
    clean_env = _get_clean_env()

    # Yêu cầu chỉ số mục tiêu 1 thuộc tập test
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(saved_ep_path),
            "--split",
            "test",
            "--target-index",
            "1",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc.returncode == 0, f"Thực thi demo thất bại: {proc.stderr}"

    episode = read_episode(saved_ep_path)
    assert episode.target.split == "test", (
        f"Kỳ vọng split 'test' nhưng nhận: {episode.target.split}"
    )
    assert episode.target.index == 1, f"Kỳ vọng target index 1 nhưng nhận: {episode.target.index}"

    # Vị trí mục tiêu ba chiều (3D coordinate) phải là bộ 3 số hữu hạn
    pos = episode.target.position_m
    assert len(pos) == 3, f"Toạ độ mục tiêu phải gồm 3 thành phần (x, y, z), nhận: {pos}"
    for coord in pos:
        assert isinstance(coord, float) and np.isfinite(coord)


def test_demo_same_seed_same_episode(tmp_path: Path) -> None:
    """NFR-REPRO-001, AC-2: Hai lần demo cùng seed cho chuỗi hành động và trạng thái giống hệt."""
    run_dir = tmp_path / "run_demo_repro"
    ep1_path = tmp_path / "demo_run1.json"
    ep2_path = tmp_path / "demo_run2.json"
    ckpt_path = _create_test_checkpoint(run_dir, seed=123)
    clean_env = _get_clean_env()

    cmd = [
        sys.executable,
        "-m",
        "mma_ai.visualization.cli",
        "--checkpoint",
        str(ckpt_path),
        "--headless",
        "--seed",
        "999",
        "--split",
        "test",
        "--target-index",
        "0",
    ]

    # Lần chạy 1
    proc1 = subprocess.run(
        cmd + ["--save-episode", str(ep1_path)],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc1.returncode == 0, f"Lần chạy 1 thất bại: {proc1.stderr}"

    # Lần chạy 2
    proc2 = subprocess.run(
        cmd + ["--save-episode", str(ep2_path)],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc2.returncode == 0, f"Lần chạy 2 thất bại: {proc2.stderr}"

    ep1 = read_episode(ep1_path)
    ep2 = read_episode(ep2_path)

    # 1. Số lượng khung hình phải hoàn toàn bằng nhau
    assert len(ep1.frames) == len(ep2.frames), (
        f"Số lượng khung hình không khớp: {len(ep1.frames)} != {len(ep2.frames)}"
    )

    # 2. Chuỗi hành động kích thích cơ (muscle excitation) giống hệt (0 khác biệt)
    actions1 = [f.excitation for f in ep1.frames[1:]]
    actions2 = [f.excitation for f in ep2.frames[1:]]
    assert actions1 == actions2, "Chuỗi hành động kích thích cơ giữa 2 lần chạy có sự sai khác"

    # 3. Mọi trường số học (numerical fields) lệch tuyệt đối <= 1e-6 (NFR-REPRO-001)
    for i, (f1, f2) in enumerate(zip(ep1.frames, ep2.frames)):
        np.testing.assert_allclose(
            f1.qpos,
            f2.qpos,
            atol=1e-6,
            err_msg=f"Khung {i}: qpos lệch vượt ngưỡng 1e-6",
        )
        np.testing.assert_allclose(
            f1.qvel,
            f2.qvel,
            atol=1e-6,
            err_msg=f"Khung {i}: qvel lệch vượt ngưỡng 1e-6",
        )
        np.testing.assert_allclose(
            f1.activation,
            f2.activation,
            atol=1e-6,
            err_msg=f"Khung {i}: activation lệch vượt ngưỡng 1e-6",
        )
        np.testing.assert_allclose(
            f1.fingertip_position_m,
            f2.fingertip_position_m,
            atol=1e-6,
            err_msg=f"Khung {i}: vị trí đầu ngón tay lệch vượt ngưỡng 1e-6",
        )
        assert abs(f1.distance_m - f2.distance_m) <= 1e-6, (
            f"Khung {i}: khoảng cách distance_m lệch vượt ngưỡng 1e-6"
        )
        assert abs(f1.reward - f2.reward) <= 1e-6, (
            f"Khung {i}: phần thưởng reward lệch vượt ngưỡng 1e-6"
        )


def test_no_file_written_without_save_flag(tmp_path: Path) -> None:
    """FR-008, INV-005, AC-2: Không ghi tệp episode khi không truyền cờ --save-episode."""
    run_dir = tmp_path / "run_demo_nosave"
    ckpt_path = _create_test_checkpoint(run_dir, seed=555)
    clean_env = _get_clean_env()

    # Liệt kê danh sách tệp trước khi chạy
    files_before = set(tmp_path.rglob("*"))

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(ckpt_path),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc.returncode == 0, f"Thực thi demo thất bại: {proc.stderr}"

    # Liệt kê danh sách tệp sau khi chạy
    files_after = set(tmp_path.rglob("*"))
    new_files = files_after - files_before

    # Không được phép có tệp episode hoặc tệp mới nào ngoài các tệp ban đầu
    for f in new_files:
        assert not f.name.endswith(".json"), (
            f"Phát hiện tệp JSON mới được ghi ngầm khi không có cờ --save-episode: {f}"
        )
