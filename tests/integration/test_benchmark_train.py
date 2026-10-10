"""Kiểm thử tích hợp cho chuẩn đo hiệu năng chi phí giao diện quan sát (T334).

Hiện thực các bài kiểm thử xác nhận hợp đồng CMD-TRN-0004 và các bất biến:
- FR-023: Đo đạc chi phí tài nguyên (CPU/RAM/GPU/VRAM) của giao diện quan sát (observation UI).
- NFR-PERF-001: Chi phí giao diện không làm giảm thông lượng quá 10% (ratio_median >= 0.90).
- SC-007, AC-7: Đo đạc hiệu năng và thẩm định báo cáo theo lược đồ train-benchmark.schema.json.
- INV-005: Giao diện quan sát chỉ đọc dữ liệu huấn luyện, hoàn toàn độc lập với vòng lặp.
- CMD-TRN-0004: Giao diện dòng lệnh benchmark_train với các tham số chuẩn.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from train_fixtures import load_schema_registry, smoke_config

from mma_ai.learning.benchmark import (
    _build_parser,
    build_benchmark_report,
    calculate_median,
    calculate_ratio_median,
    evaluate_pass,
    evaluate_view3d_status,
    main,
    run_benchmark,
)


def _load_benchmark_schema() -> dict[str, Any]:
    """Nạp tệp JSON Schema của train-benchmark.schema.json từ thư mục contracts."""
    candidate_paths = [
        Path.cwd() / "specs/003-ppo-train-repro/contracts/train-benchmark.schema.json",
        Path(__file__).resolve().parents[2]
        / "specs/003-ppo-train-repro/contracts/train-benchmark.schema.json",
    ]
    for p in candidate_paths:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    raise FileNotFoundError("Không tìm thấy tệp train-benchmark.schema.json")


def _is_cuda_available() -> bool:
    """Kiểm tra tính khả dụng của GPU CUDA mà không làm gãy khi thiếu torch."""
    if importlib.util.find_spec("torch") is None:
        return False
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def test_benchmark_contract_independent_assertion(tmp_path: Path) -> None:
    """FR-023, NFR-PERF-001, SC-007, AC-7, INV-005, CMD-TRN-0004: Khẳng định độc lập trên base.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn torch.
    Xác minh hợp đồng dòng lệnh (CLI), tính bất biến của không gian tham số và tính toán thuần:
    - Mô-đun mma_ai.learning.benchmark tồn tại trên hệ thống.
    - Bộ phân tích cú pháp CLI hỗ trợ đủ các cờ CMD-TRN-0004.
    - Không tồn tại cờ vi phạm INV-002 (nhận lực hoặc toạ độ tay).
    - Từ chối các giá trị tham số không hợp lệ với mã thoát 2.
    - Logic tính toán trung vị (median), tỷ lệ trung vị (ratio median) và luật đạt chuẩn.
    - Báo cáo sinh ra hợp chuẩn với JSON Schema Draft 2020-12.
    """
    # 1. Khẳng định mô-đun tồn tại trên hệ thống
    assert importlib.util.find_spec("mma_ai.learning.benchmark") is not None, (
        "Mô-đun mma_ai.learning.benchmark phải tồn tại"
    )

    # 2. Kiểm tra bộ phân tích cú pháp CLI hỗ trợ đủ cờ hợp đồng CMD-TRN-0004
    parser = _build_parser()
    actions = {action.dest for action in parser._actions}
    expected_flags = {
        "seed",
        "repeats",
        "config",
        "total_steps",
        "output",
        "runs_dir",
        "threshold",
    }
    assert expected_flags.issubset(actions), (
        f"Thiếu cờ hợp đồng trong benchmark CLI parser: {expected_flags - actions}"
    )

    # 3. INV-002: Nghiêm cấm mọi cờ nhận lực hoặc toạ độ tay từ người dùng
    forbidden_terms = {"force", "torque", "hand_pos", "hand_coord", "direct_action"}
    for dest in actions:
        for forbidden in forbidden_terms:
            assert forbidden not in dest.lower(), f"Phát hiện cờ bị cấm '{dest}' vi phạm INV-002"

    # 4. Kiểm tra từ chối các tham số không hợp lệ với mã thoát 2 (CMD-TRN-0004)
    # repeats < 5 bị từ chối theo NFR-PERF-001
    assert main(["--repeats", "4"]) == 2
    # seed âm bị từ chối
    assert main(["--seed", "-1"]) == 2
    # threshold <= 0 bị từ chối
    assert main(["--threshold", "0"]) == 2
    # config không tồn tại bị từ chối
    non_existent_config = str(tmp_path / "non_existent_config.yaml")
    assert main(["--config", non_existent_config]) == 2

    # 5. Kiểm tra logic tính toán thuần (pure math logic)
    sample_off = [1000.0, 1020.0, 1010.0, 1005.0, 1015.0]
    sample_on = [950.0, 970.0, 960.0, 955.0, 965.0]
    med_off = calculate_median(sample_off)
    med_on = calculate_median(sample_on)
    assert med_off == 1010.0
    assert med_on == 960.0

    ratio = calculate_ratio_median(med_on, med_off)
    assert round(ratio, 4) == round(960.0 / 1010.0, 4)
    assert evaluate_pass(ratio, threshold=0.9) is True
    assert evaluate_pass(0.89, threshold=0.9) is False

    # 6. Kiểm tra thẩm định schema hợp đồng bằng jsonschema validator và registry
    schema = _load_benchmark_schema()
    registry = load_schema_registry()
    sample_report = build_benchmark_report(
        seed=42,
        env_steps_per_run=4096,
        repeats=5,
        ui_off_steps=sample_off,
        ui_on_steps=sample_on,
        ui_cost={
            "cpu_utilization_pct_delta": 0.5,
            "ram_peak_mb_delta": 25.0,
            "vram_peak_mb_delta": None,
        },
        view3d=evaluate_view3d_status(has_display=False),
        threshold=0.9,
    )
    validator = Draft202012Validator(schema, registry=registry)
    validator.validate(sample_report)


@pytest.fixture  # type: ignore[untyped-decorator]
def benchmark_sample_report(tmp_path: Path) -> dict[str, Any]:
    """Khởi tạo một báo cáo chuẩn đo hiệu năng thực tế (benchmark report) trong thư mục tạm."""
    out_file = tmp_path / "logs" / "m1" / "benchmark_train.json"
    runs_dir = tmp_path / "runs"

    has_torch = importlib.util.find_spec("torch") is not None
    has_tb = importlib.util.find_spec("tensorboard") is not None

    if has_torch and has_tb:
        # Nếu có đầy đủ phụ thuộc rl, sử dụng cấu hình rút ngắn để đo lường qua runner thực tế
        cfg_file = smoke_config(
            tmp_path,
            total_timesteps=64,
            n_steps=64,
            batch_size=64,
            every_updates=1,
            **{"schedule.n_epochs": 1, "ui.snapshot_interval_s": 0.05},
        )
        report, passed = run_benchmark(
            seed=42,
            repeats=5,
            config_path=cfg_file,
            total_steps=64,
            output_path=out_file,
            runs_dir=runs_dir,
            threshold=0.9,
        )
    else:
        # Môi trường cô lập không có torch: sử dụng mock runner mô phỏng thông lượng và tài nguyên
        def _mock_runner(
            seed: int,
            ui_mode: str,
            runs_dir: Path,
            config_path: Path | None,
            total_steps: int | None,
        ) -> dict[str, Any]:
            tp = 1500.0 if ui_mode == "none" else 1450.0
            return {
                "throughput": {"env_steps_per_second": tp, "env_steps": 4096},
                "resources": {
                    "cpu_utilization_pct": 15.0 if ui_mode == "web" else 14.0,
                    "ram_peak_mb": 180.0 if ui_mode == "web" else 150.0,
                    "vram_peak_mb": None,
                },
            }

        report, passed = run_benchmark(
            seed=42,
            repeats=5,
            output_path=out_file,
            runs_dir=runs_dir,
            threshold=0.9,
            runner=_mock_runner,
        )

    assert out_file.is_file(), f"Tệp kết quả chuẩn đo không được tạo tại: {out_file}"
    loaded_report = json.loads(out_file.read_text(encoding="utf-8"))
    return {
        "report": loaded_report,
        "output_path": out_file,
        "passed": passed,
    }


def test_benchmark_schema_and_ratio(benchmark_sample_report: dict[str, Any]) -> None:
    """FR-023, NFR-PERF-001, SC-007, AC-7, INV-005: Khẳng định hồ sơ hợp chuẩn và tỷ lệ trung vị.

    Xác minh:
    - Báo cáo benchmark_train.json hợp chuẩn JSON Schema train-benchmark.schema.json.
    - repeats tối thiểu 5 lần lặp xen kẽ theo NFR-PERF-001.
    - ratio_median đúng bằng trung vị bật (ui_on) chia cho trung vị tắt (ui_off).
    - passed nhất quán với quy tắc ratio_median >= threshold (0.90).
    - Lưu ý: Không ép passed phải là True trên máy kiểm thử phát triển.
    """
    report = benchmark_sample_report["report"]
    schema = _load_benchmark_schema()
    registry = load_schema_registry()

    # Thẩm định với JSON Schema draft 2020-12
    validator = Draft202012Validator(schema, registry=registry)
    validator.validate(report)

    # Kiểm tra các trường hợp đồng cốt lõi
    assert report["schema_version"] == "1.0.0"
    assert report["seed"] == 42
    assert report["repeats"] >= 5
    assert report["threshold"] == 0.9

    ui_off_steps = report["ui_off"]["env_steps_per_second"]
    ui_on_steps = report["ui_on"]["env_steps_per_second"]
    assert len(ui_off_steps) == report["repeats"]
    assert len(ui_on_steps) == report["repeats"]

    # Kiểm tra tính toán trung vị độc lập
    calculated_med_off = calculate_median(ui_off_steps)
    calculated_med_on = calculate_median(ui_on_steps)
    assert report["ui_off"]["median"] == pytest.approx(calculated_med_off, rel=1e-5)
    assert report["ui_on"]["median"] == pytest.approx(calculated_med_on, rel=1e-5)

    # Khẳng định tỷ lệ trung vị (ratio median)
    expected_ratio = calculate_ratio_median(calculated_med_on, calculated_med_off)
    assert report["ratio_median"] == pytest.approx(expected_ratio, rel=1e-4)

    # Khẳng định tính nhất quán của trạng thái đạt chuẩn (pass status)
    expected_passed = report["ratio_median"] >= report["threshold"]
    assert report["passed"] is expected_passed


def test_benchmark_records_ui_cost(benchmark_sample_report: dict[str, Any]) -> None:
    """FR-023, NFR-PERF-001, SC-007, AC-7: Đo đạc chi phí tài nguyên của giao diện quan sát.

    Xác minh:
    - ui_cost ghi nhận đầy đủ 3 trường: cpu_utilization_pct_delta,
      ram_peak_mb_delta, vram_peak_mb_delta.
    - Khi không có GPU CUDA, vram_peak_mb_delta ghi nhận tường minh null (None trong Python),
      không bao giờ bị lược bỏ trường (tuân thủ nguyên tắc thiết kế bất biến).
    - ram_peak_mb_delta và cpu_utilization_pct_delta là kiểu số (float) hoặc None.
    """
    report = benchmark_sample_report["report"]
    ui_cost = report.get("ui_cost")
    assert isinstance(ui_cost, dict), "Báo cáo phải chứa khối đối tượng ui_cost"

    # Kiểm tra đầy đủ 3 trường bắt buộc theo hợp đồng schema
    assert "cpu_utilization_pct_delta" in ui_cost
    assert "ram_peak_mb_delta" in ui_cost
    assert "vram_peak_mb_delta" in ui_cost

    # Khi không có GPU CUDA, vram_peak_mb_delta bắt buộc là None
    if not _is_cuda_available():
        assert ui_cost["vram_peak_mb_delta"] is None, (
            "vram_peak_mb_delta phải là null khi môi trường không có GPU CUDA"
        )

    if ui_cost["cpu_utilization_pct_delta"] is not None:
        assert isinstance(ui_cost["cpu_utilization_pct_delta"], (int, float))

    if ui_cost["ram_peak_mb_delta"] is not None:
        assert isinstance(ui_cost["ram_peak_mb_delta"], (int, float))


def test_view3d_not_used_in_routine_benchmark(benchmark_sample_report: dict[str, Any]) -> None:
    """FR-022, FR-023, NFR-HEADLESS-001, INV-005, SC-007, AC-7: 3D viewer tắt trong benchmark.

    Xác minh:
    - view3d.measured bắt buộc là False trong chuẩn đo hiệu năng thường quy (routine benchmark).
    - view3d.reason là chuỗi giải thích rõ ràng (tắt mặc định hoặc không có DISPLAY).
    - Không mở cửa sổ MuJoCo đồ hoạ hay tiến trình 3D viewer gây suy hao hiệu năng.
    """
    report = benchmark_sample_report["report"]
    view3d = report.get("view3d")
    assert isinstance(view3d, dict), "Báo cáo phải chứa khối đối tượng view3d"

    assert view3d["measured"] is False, (
        "Khung nhìn 3D không được kích hoạt đo trong chuẩn đo thường quy"
    )
    assert isinstance(view3d["reason"], str) and len(view3d["reason"].strip()) > 0, (
        "view3d phải có chuỗi lý do không rỗng giải thích trạng thái"
    )


def test_benchmark_cli_real_subprocess_execution(tmp_path: Path) -> None:
    """FR-023, NFR-PERF-001, CMD-TRN-0004, SC-007, AC-7: Kiểm thử tiến trình con CLI thật.

    Khởi chạy mma_ai.learning.benchmark qua tiến trình con (subprocess) thực tế khi có extra rl.
    Xác minh:
    - Mã thoát (exit code): 0 khi passed == True, 1 khi passed == False (không bao giờ thoát 2).
    - Stdout in báo cáo tóm tắt bằng tiếng Việt với các thuật ngữ song ngữ chuẩn hoá.
    - Tệp JSON đầu ra được tạo nguyên tử tại đường dẫn được chỉ định qua cờ --output.
    """
    pytest.importorskip("torch", reason="Cần extra rl (torch) để chạy tích hợp tiến trình CLI thật")
    pytest.importorskip("tensorboard", reason="Cần tensorboard để ghi nhận chỉ số đo lường")

    cfg_file = smoke_config(
        tmp_path,
        total_timesteps=64,
        n_steps=64,
        batch_size=64,
        every_updates=1,
        **{"schedule.n_epochs": 1, "ui.snapshot_interval_s": 0.05},
    )
    out_file = tmp_path / "logs" / "m1" / "benchmark_train.json"
    runs_dir = tmp_path / "runs"

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    cmd = [
        sys.executable,
        "-m",
        "mma_ai.learning.benchmark",
        "--seed",
        "42",
        "--repeats",
        "5",
        "--config",
        str(cfg_file),
        "--output",
        str(out_file),
        "--runs-dir",
        str(runs_dir),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=180.0,
    )

    # Tiến trình chỉ được thoát 0 (đạt) hoặc 1 (không đạt), tuyệt đối không được thoát 2 (lỗi cờ)
    assert proc.returncode in (0, 1), (
        f"Kỳ vọng mã thoát 0 hoặc 1 nhưng nhận {proc.returncode}.\nStderr: {proc.stderr}"
    )

    assert out_file.is_file(), f"Tệp kết quả không tồn tại tại: {out_file}"
    report_data = json.loads(out_file.read_text(encoding="utf-8"))

    # Mã thoát 0 tương ứng với passed == True
    expected_exit = 0 if report_data["passed"] else 1
    assert proc.returncode == expected_exit, (
        f"Mã thoát {proc.returncode} không khớp trạng thái passed {report_data['passed']}"
    )

    # Xác minh stdout in thông tin tóm tắt bằng tiếng Việt
    assert "=== Báo cáo chuẩn đo hiệu năng" in proc.stdout
    assert "Hạt giống ngẫu nhiên" in proc.stdout
    assert "Tỷ lệ trung vị" in proc.stdout
    assert "Kết quả đánh giá" in proc.stdout
