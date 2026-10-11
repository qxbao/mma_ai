"""Kiểm thử chế độ không hiển thị (headless) và độ tin cậy số học qua CLI (T323).

Hiện thực và xác minh:
- NFR-HEADLESS-001: Huấn luyện chạy không giao diện đồ hoạ khi biến DISPLAY/WAYLAND_DISPLAY bỏ đặt.
- NFR-REL-001: Độ tin cậy số học (numerical reliability) với 0 NaN và 0 Inf trong loss và tham số.
- SC-001, AC-1, US1: Khởi chạy lệnh huấn luyện smoke qua CLI và đảm bảo không nạp mujoco.viewer.
- INV-004: Điểm kiểm tra cuối cùng (final checkpoint) lưu trữ toàn bộ tensor hữu hạn.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from train_fixtures import list_runs, load_manifest, smoke_config

from mma_ai.learning.cli import _build_parser


def test_headless_smoke_contract_independent_assertion() -> None:
    """NFR-HEADLESS-001, US1: Khẳng định độc lập trên base về cấu hình và giao diện không đồ hoạ.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn (optional dependency).
    """
    # 1. Xác thực cấu hình smoke đóng gói sẵn mặc định tắt giao diện và tắt 3D
    root_dir = Path(__file__).resolve().parents[2]
    smoke_yaml_path = root_dir / "src" / "mma_ai" / "learning" / "train_elbow_smoke.yaml"
    assert smoke_yaml_path.is_file(), f"Không tìm thấy cấu hình smoke: {smoke_yaml_path}"
    raw_cfg = yaml.safe_load(smoke_yaml_path.read_text(encoding="utf-8"))
    assert isinstance(raw_cfg, dict), "Cấu hình smoke phải là từ điển YAML"
    assert raw_cfg.get("ui", {}).get("mode") == "none", "ui.mode trong smoke phải là 'none'"
    assert raw_cfg.get("ui", {}).get("view3d") is False, "ui.view3d trong smoke phải là False"

    # 2. Xác thực bộ phân tích cú pháp CLI mặc định tắt hiển thị 3D (headless mặc định)
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.view3d is False, "Cờ --view3d của CLI huấn luyện phải mặc định tắt (False)"

    # 3. Đảm bảo nạp mô-đun CLI không gây hiệu ứng phụ nạp mujoco.viewer
    assert "mujoco.viewer" not in sys.modules, (
        "Không được nạp mujoco.viewer khi tương tác với giao diện dòng lệnh huấn luyện"
    )


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def smoke_headless_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Khởi chạy một lượt huấn luyện smoke duy nhất trong môi trường không màn hình."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")

    tmp_dir = tmp_path_factory.mktemp("headless_smoke")
    config_file = smoke_config(tmp_dir)
    runs_dir = tmp_dir / "runs"

    # Tiến trình con thực thi CLI huấn luyện và kiểm tra bất biến không nạp mujoco.viewer
    headless_script = (
        "import os\n"
        "import sys\n"
        "from mma_ai.learning.cli import main\n"
        f"exit_code = main(['--config', {str(config_file)!r}, '--seed', '42'])\n"
        "if exit_code != 0:\n"
        "    sys.exit(exit_code)\n"
        "if 'mujoco.viewer' in sys.modules:\n"
        "    sys.stderr.write('LỖI_NHẬP_VIEWER: nạp viewer trong tiến trình headless!\\n')\n"
        "    sys.exit(98)\n"
        "sys.exit(0)\n"
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.run(
        [sys.executable, "-c", headless_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=180.0,
        cwd=str(Path.cwd()),
        check=False,
    )

    created_runs = list_runs(runs_dir)
    return {
        "proc": proc,
        "runs_dir": runs_dir,
        "run_dir": created_runs[-1] if created_runs else None,
    }


def test_smoke_without_display(smoke_headless_run: dict[str, Any]) -> None:
    """NFR-HEADLESS-001, SC-001, AC-1: Huấn luyện hoàn tất mã 0 khi không có DISPLAY."""
    proc: subprocess.CompletedProcess[str] = smoke_headless_run["proc"]
    assert proc.returncode == 0, (
        f"Lượt huấn luyện smoke thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )
    assert "LỖI_NHẬP_VIEWER" not in proc.stderr, "Phát hiện mujoco.viewer bị nạp"
    assert "Huấn luyện hoàn tất thành công" in proc.stdout, "Thiếu thông điệp thành công"
    assert smoke_headless_run["run_dir"] is not None, "Không tạo được thư mục lượt chạy"


def test_zero_nan_inf_counters_in_manifest(smoke_headless_run: dict[str, Any]) -> None:
    """NFR-REL-001, SC-001, AC-1: numeric_health bằng 0 NaN và 0 Inf cho loss và tham số."""
    run_dir: Path | None = smoke_headless_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Thư mục lượt chạy không tồn tại"

    manifest = load_manifest(run_dir)
    status = manifest.get("status")
    assert status == "done", f"Trạng thái lượt chạy không phải done: {status}"
    assert manifest.get("error") is None, f"Hồ sơ ghi nhận lỗi: {manifest.get('error')}"

    numeric_health = manifest.get("numeric_health")
    assert isinstance(numeric_health, dict), "Thiếu numeric_health trong hồ sơ"
    nan_count = numeric_health.get("nan_count")
    inf_count = numeric_health.get("inf_count")
    assert nan_count == 0, f"Số lượng NaN vượt ngưỡng: {nan_count}"
    assert inf_count == 0, f"Số lượng Inf vượt ngưỡng: {inf_count}"


def test_params_finite_in_final_checkpoint(smoke_headless_run: dict[str, Any]) -> None:
    """NFR-REL-001, INV-004, SC-001, AC-1: Mọi tensor trong checkpoint cuối đều hữu hạn."""
    import torch

    from mma_ai.learning.checkpoint import load_checkpoint

    run_dir: Path | None = smoke_headless_run["run_dir"]
    assert run_dir is not None and run_dir.is_dir(), "Thư mục lượt chạy không tồn tại"

    latest_json = run_dir / "checkpoints" / "latest.json"
    assert latest_json.is_file(), f"Không tìm thấy latest.json tại: {latest_json}"

    loaded = load_checkpoint(latest_json)

    # 1. Kiểm tra tính hữu hạn của toàn bộ trọng số mạng actor
    for name, tensor in loaded.actor_state_dict.items():
        assert isinstance(tensor, torch.Tensor), f"Trọng số actor {name} không phải Tensor"
        assert torch.isfinite(tensor).all().item(), f"Trọng số actor '{name}' chứa NaN/Inf"

    # 2. Kiểm tra tính hữu hạn của toàn bộ trọng số mạng critic
    for name, tensor in loaded.critic_state_dict.items():
        assert isinstance(tensor, torch.Tensor), f"Trọng số critic {name} không phải Tensor"
        assert torch.isfinite(tensor).all().item(), f"Trọng số critic '{name}' chứa NaN/Inf"

    # 3. Kiểm tra tính hữu hạn của tham số log_std nếu có
    if loaded.log_std is not None:
        assert torch.isfinite(loaded.log_std).all().item(), "Tham số log_std chứa NaN/Inf"

    # 4. Kiểm tra tính hữu hạn của thống kê chuẩn hoá quan sát (observation normalizer)
    norm_sd = loaded.obs_normalizer_state_dict
    for stat_key in ("mean", "var"):
        if stat_key in norm_sd and isinstance(norm_sd[stat_key], torch.Tensor):
            stat_tensor = norm_sd[stat_key]
            assert torch.isfinite(stat_tensor).all().item(), (
                f"Thống kê normalizer '{stat_key}' chứa NaN/Inf"
            )
