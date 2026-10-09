"""Kiểm thử tích hợp qua CLI huấn luyện thật (T322).

Hiện thực và xác minh:
- FR-001, AC-1, US1: Huấn luyện PPO qua giao diện dòng lệnh với seed xác định.
- FR-005, INV-002: Không gian hành động chỉ nhận 6 cơ [0,1]^6, không điều khiển lực.
- FR-006, INV-004: Lưu checkpoint định kỳ và final, latest.json trỏ hợp lệ, không ghi đè.
- FR-010: Ghi nhận chỉ số TensorBoard (loss, reward, activation cho 6 cơ theo bước).
- FR-013, AC-3: Báo cáo env steps/second và thời gian thực wall-clock do máy đo.
- FR-018, SC-001: Từ chối cấu hình sai (mốc checkpoint 0, tổng bước <= 0) với mã 2.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from train_fixtures import list_runs, load_manifest, run_train_cli, smoke_config

from mma_ai.learning.cli import _build_parser

_SIX_MUSCLE_NAMES = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")


def test_cli_smoke_contract_independent_assertion() -> None:
    """FR-005, FR-018, INV-002, SC-001: Khẳng định độc lập trên base về giao diện dòng lệnh.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn (optional dependency).
    Xác minh bộ phân tích cú pháp CLI tuyệt đối không nhận cờ điều khiển lực hoặc toạ độ tay.
    """
    # 1. Kiểm tra bộ phân tích cú pháp CLI hỗ trợ đủ các cờ hợp đồng
    parser = _build_parser()
    actions = {action.dest for action in parser._actions}
    expected_flags = {
        "stage",
        "seed",
        "config",
        "total_steps",
        "resume",
        "runs_dir",
        "ui",
        "ui_port",
        "view3d",
    }
    assert expected_flags.issubset(actions), (
        f"Thiếu cờ hợp đồng trong CLI parser: {expected_flags - actions}"
    )

    # 2. INV-002: Bảo vệ tính bất biến không gian hành động — nghiêm cấm cờ nhận lực/toạ độ tay
    forbidden_terms = {
        "force",
        "torque",
        "hand_pos",
        "hand_coord",
        "muscle_force",
        "direct_action",
    }
    for dest in actions:
        for forbidden in forbidden_terms:
            assert forbidden not in dest.lower(), f"Phát hiện cờ bị cấm '{dest}' vi phạm INV-002"

    # 3. Xác thực tệp cấu hình smoke đóng gói sẵn
    root_dir = Path(__file__).resolve().parents[2]
    smoke_yaml_path = root_dir / "src" / "mma_ai" / "learning" / "train_elbow_smoke.yaml"
    assert smoke_yaml_path.is_file(), f"Không tìm thấy cấu hình smoke: {smoke_yaml_path}"
    raw_cfg = yaml.safe_load(smoke_yaml_path.read_text(encoding="utf-8"))
    assert isinstance(raw_cfg, dict), "Cấu hình smoke phải là mapping"
    assert raw_cfg["schedule"]["total_timesteps"] == 4096, (
        "total_timesteps trong smoke phải là 4096"
    )
    assert raw_cfg["schedule"]["n_steps"] == 2048, "n_steps trong smoke phải là 2048"
    assert raw_cfg["checkpoint"]["every_updates"] == 1, "every_updates trong smoke phải là 1"


def test_invalid_checkpoint_frequency_rejected(tmp_path: Path) -> None:
    """FR-018, AC-1: Cấu hình checkpoint.every_updates bằng 0 bị từ chối với mã 2."""
    config_file = smoke_config(tmp_path, every_updates=0)
    runs_dir = tmp_path / "runs"

    result = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file)],
        timeout=30.0,
    )

    assert result.exit_code == 2, (
        f"Kỳ vọng mã thoát 2 nhưng nhận {result.exit_code}.\nStderr: {result.stderr}"
    )
    assert (
        "checkpoint.every_updates" in result.stderr
        or "Cấu hình huấn luyện không hợp lệ" in result.stderr
    ), f"Thông báo lỗi không nêu lý do cấu hình không hợp lệ: {result.stderr}"
    assert list_runs(runs_dir) == [], "Không được tạo thư mục run khi cấu hình không hợp lệ"


def test_total_steps_le_zero_rejected(tmp_path: Path) -> None:
    """FR-018, AC-1: Tham số --total-steps <= 0 bị từ chối với mã 2 trước khi tạo run."""
    config_file = smoke_config(tmp_path)
    runs_dir = tmp_path / "runs"

    result = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file), "--total-steps", "0"],
        timeout=30.0,
    )

    assert result.exit_code == 2, (
        f"Kỳ vọng mã thoát 2 nhưng nhận {result.exit_code}.\nStderr: {result.stderr}"
    )
    assert (
        "schedule.total_timesteps" in result.stderr
        or "Cấu hình huấn luyện không hợp lệ" in result.stderr
    ), f"Thông báo lỗi không nêu lý do cấu hình không hợp lệ: {result.stderr}"
    assert list_runs(runs_dir) == [], "Không được tạo thư mục run khi cấu hình không hợp lệ"


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def smoke_cli_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Khởi chạy duy nhất một lượt huấn luyện smoke qua CLI thật với hook kiểm của test."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    pytest.importorskip("tensorboard", reason="Cần tensorboard để kiểm tra nhật ký chỉ số")

    tmp_dir = tmp_path_factory.mktemp("cli_smoke_integration")
    config_file = smoke_config(tmp_dir)
    runs_dir = tmp_dir / "runs"
    actions_log_file = tmp_dir / "recorded_actions.json"

    # Kịch bản thực thi CLI huấn luyện tích hợp hook kiểm tra mọi hành động gửi tới môi trường
    escaped_actions = str(actions_log_file)
    escaped_config = str(config_file)
    test_runner_script = (
        "import sys\n"
        "import json\n"
        "import numpy as np\n"
        "from pathlib import Path\n"
        "import mma_ai.environment.single_agent as sa\n"
        "import mma_ai.learning.cli as cli_mod\n"
        f"actions_path = Path({escaped_actions!r})\n"
        "recorded_actions = []\n"
        "orig_step = sa.ElbowReachEnv.step\n"
        "def hooked_step(self, action):\n"
        "    arr = np.asarray(action, dtype=np.float64)\n"
        "    recorded_actions.append(arr.tolist())\n"
        "    return orig_step(self, action)\n"
        "sa.ElbowReachEnv.step = hooked_step\n"
        "exit_code = 1\n"
        "try:\n"
        f"    exit_code = cli_mod.main(['--stage', 'elbow', '--seed', '42', "
        f"'--config', {escaped_config!r}])\n"
        "finally:\n"
        "    actions_path.write_text(json.dumps(recorded_actions), encoding='utf-8')\n"
        "sys.exit(exit_code)\n"
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.run(
        [sys.executable, "-c", test_runner_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=180.0,
        cwd=str(Path.cwd()),
        check=False,
    )

    created_runs = list_runs(runs_dir)
    run_dir = created_runs[-1] if created_runs else None

    return {
        "proc": proc,
        "runs_dir": runs_dir,
        "run_dir": run_dir,
        "actions_log_file": actions_log_file,
    }


def test_smoke_train_exit0(smoke_cli_run: dict[str, Any]) -> None:
    """FR-001, SC-001, AC-1, US1: Lượt huấn luyện smoke kết thúc thành công với mã 0."""
    proc: subprocess.CompletedProcess[str] = smoke_cli_run["proc"]
    assert proc.returncode == 0, (
        f"Huấn luyện thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    run_dir: Path | None = smoke_cli_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Không tìm thấy thư mục lượt chạy được tạo"

    manifest = load_manifest(run_dir)
    status = manifest.get("status")
    assert status == "done", f"Trạng thái lượt chạy không phải 'done': {status}"
    assert manifest.get("error") is None, f"Hồ sơ lượt chạy ghi nhận lỗi: {manifest.get('error')}"
    assert manifest.get("stage") == "elbow", "Giai đoạn lượt chạy không khớp 'elbow'"
    assert manifest.get("seed") == 42, "Seed trong hồ sơ không khớp 42"


def test_tensorboard_scalars_present(smoke_cli_run: dict[str, Any]) -> None:
    """FR-010, AC-1: TensorBoard chứa đầy đủ loss, reward và activation cho 6 cơ theo bước."""
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    run_dir: Path | None = smoke_cli_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Thư mục lượt chạy không tồn tại"

    tb_dir = run_dir / "tb"
    assert tb_dir.is_dir(), f"Thư mục TensorBoard không tồn tại: {tb_dir}"

    accumulator = EventAccumulator(str(tb_dir))
    accumulator.Reload()
    scalar_tags = set(accumulator.Tags().get("scalars", []))

    # 1. Kiểm tra sự hiện diện của các nhóm thẻ chính
    expected_core_tags = {
        "loss/policy",
        "loss/value",
        "loss/entropy",
        "reward/mean_return",
        "throughput/env_steps_per_second",
    }
    assert expected_core_tags.issubset(scalar_tags), (
        f"Thiếu các thẻ chỉ số cốt lõi trong TensorBoard: {expected_core_tags - scalar_tags}"
    )

    # 2. Kiểm tra đủ thẻ kích hoạt cho đúng 6 cơ cánh tay khuỷu
    expected_activation_tags = {f"activation/{muscle}" for muscle in _SIX_MUSCLE_NAMES}
    assert expected_activation_tags.issubset(scalar_tags), (
        f"Thiếu thẻ kích hoạt 6 cơ trong TensorBoard: {expected_activation_tags - scalar_tags}"
    )

    # 3. Kiểm tra các sự kiện được ghi theo bước môi trường (step > 0)
    policy_loss_events = accumulator.Scalars("loss/policy")
    assert len(policy_loss_events) >= 1, "Không có sự kiện loss/policy nào được ghi"
    assert policy_loss_events[0].step > 0, "Chỉ số phải được gắn nhãn theo số bước môi trường"

    # 4. Xác minh đối ứng với tệp nhật ký metrics.jsonl
    metrics_file = run_dir / "metrics.jsonl"
    assert metrics_file.is_file(), f"Không tìm thấy tệp nhật ký metrics.jsonl: {metrics_file}"
    raw_lines = metrics_file.read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in raw_lines if line.strip()]
    assert len(lines) >= 1, "Tệp metrics.jsonl rỗng"
    first_record = json.loads(lines[0])
    for muscle in _SIX_MUSCLE_NAMES:
        act_key = f"activation/{muscle}"
        assert act_key in first_record, f"Thiếu khoá '{act_key}' trong dòng đầu của metrics.jsonl"


def test_actions_in_unit_interval(smoke_cli_run: dict[str, Any]) -> None:
    """FR-005, INV-002, AC-1: Mọi hành động đưa vào môi trường đều trong [0,1]^6."""
    # 1. Kiểm tra dữ liệu thu thập được từ hook kiểm của test
    actions_log_file: Path = smoke_cli_run["actions_log_file"]
    assert actions_log_file.is_file(), f"Không tìm thấy tệp nhật ký hành động: {actions_log_file}"

    actions_data = json.loads(actions_log_file.read_text(encoding="utf-8"))
    assert len(actions_data) > 0, "Không thu thập được hành động nào qua hook kiểm"

    for idx, act in enumerate(actions_data):
        assert len(act) == 6, f"Hành động tại bước {idx} không có đúng 6 chiều: {len(act)}"
        for m_idx, val in enumerate(act):
            assert 0.0 <= val <= 1.0, (
                f"Kích hoạt cơ thứ {m_idx} tại bước {idx} vượt ra ngoài [0, 1]: {val}"
            )

    # 2. Kiểm tra chỉ số kích hoạt trung bình trong metrics.jsonl
    run_dir: Path | None = smoke_cli_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Thư mục lượt chạy không tồn tại"
    metrics_file = run_dir / "metrics.jsonl"
    for line in metrics_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for muscle in _SIX_MUSCLE_NAMES:
            act_val = float(record[f"activation/{muscle}"])
            assert 0.0 <= act_val <= 1.0, (
                f"Kích hoạt trung bình '{muscle}' ngoài đoạn [0, 1]: {act_val}"
            )


def test_periodic_and_final_checkpoint(smoke_cli_run: dict[str, Any]) -> None:
    """FR-006, INV-004, AC-1: Lưu checkpoint định kỳ và final, latest.json trỏ hợp lệ."""
    run_dir: Path | None = smoke_cli_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Thư mục lượt chạy không tồn tại"

    ckpt_dir = run_dir / "checkpoints"
    assert ckpt_dir.is_dir(), f"Thư mục checkpoints không tồn tại: {ckpt_dir}"

    # 1. Kiểm tra con trỏ latest.json tồn tại và hợp lệ
    latest_json = ckpt_dir / "latest.json"
    assert latest_json.is_file(), f"Không tìm thấy latest.json tại: {latest_json}"
    latest_data = json.loads(latest_json.read_text(encoding="utf-8"))
    assert "path" in latest_data, "latest.json thiếu trường 'path'"
    latest_ckpt_file = run_dir / latest_data["path"]
    assert latest_ckpt_file.is_file(), (
        f"Tệp checkpoint do latest.json trỏ tới không tồn tại: {latest_ckpt_file}"
    )

    # 2. Kiểm tra sự tồn tại của checkpoint định kỳ và checkpoint final
    all_pt_files = sorted(ckpt_dir.glob("*.pt"))
    assert len(all_pt_files) >= 2, (
        f"Kỳ vọng ít nhất 2 tệp checkpoint (.pt) nhưng nhận {len(all_pt_files)}: {all_pt_files}"
    )

    final_ckpts = [p for p in all_pt_files if p.name.endswith("_final.pt")]
    periodic_ckpts = [p for p in all_pt_files if not p.name.endswith("_final.pt")]

    assert len(final_ckpts) == 1, f"Kỳ vọng đúng 1 checkpoint final: {final_ckpts}"
    assert len(periodic_ckpts) >= 1, f"Kỳ vọng có ít nhất 1 checkpoint định kỳ: {periodic_ckpts}"

    # 3. Khẳng định các checkpoint cũ không bị ghi đè (tồn tại độc lập với kích thước hợp lệ)
    for ckpt_path in all_pt_files:
        assert ckpt_path.stat().st_size > 0, f"Tệp checkpoint bị rỗng: {ckpt_path}"
        meta_path = ckpt_path.with_suffix(".meta.json")
        assert meta_path.is_file(), f"Thiếu tệp siêu dữ liệu cho checkpoint: {meta_path}"


def test_report_has_steps_per_second_and_wallclock(smoke_cli_run: dict[str, Any]) -> None:
    """FR-013, AC-3, US1: Báo cáo stdout nêu env steps/second và wall-clock do máy đo."""
    proc: subprocess.CompletedProcess[str] = smoke_cli_run["proc"]
    stdout = proc.stdout

    # 1. Khẳng định thông lượng env steps/second được in ra và có giá trị dương
    throughput_match = re.search(
        r"(?:env steps/second|Thông lượng môi trường \(env steps/second\)):\s*([0-9.]+)",
        stdout,
    )
    assert throughput_match is not None, (
        f"Không tìm thấy thông lượng env steps/second trong stdout:\n{stdout}"
    )
    steps_per_sec = float(throughput_match.group(1))
    assert steps_per_sec > 0.0, f"Thông lượng env steps/second phải > 0, nhận: {steps_per_sec}"

    # 2. Khẳng định thời gian chạy thực wall-clock được in ra và có giá trị dương
    wallclock_match = re.search(
        r"(?:wall-clock|Thời gian chạy thực \(wall-clock\)):\s*([0-9.]+)\s*s?",
        stdout,
    )
    assert wallclock_match is not None, (
        f"Không tìm thấy thời gian chạy thực wall-clock trong stdout:\n{stdout}"
    )
    wall_clock = float(wallclock_match.group(1))
    assert wall_clock > 0.0, f"Thời gian chạy thực wall-clock phải > 0, nhận: {wall_clock}"
