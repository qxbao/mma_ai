"""Kiểm thử đơn vị cho chuẩn đo hiệu năng chi phí giao diện (test_benchmark_logic.py).

Hiện thực các bài kiểm thử xác nhận hợp đồng CMD-TRN-0004 và các bất biến:
- FR-023: Đo đạc chi phí tài nguyên (CPU/RAM/GPU/VRAM) của giao diện quan sát.
- NFR-PERF-001: Chi phí giao diện không làm giảm thông lượng quá 10% (ratio_median >= 0.90).
- CMD-TRN-0004: Giao diện dòng lệnh benchmark_train với các cờ tham số chuẩn.
- INV-005: Giao diện quan sát chỉ đọc và hoàn toàn độc lập với vòng lặp huấn luyện.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

import mma_ai.learning.benchmark as benchmark_module
from mma_ai.compat.display import DisplayProbe
from mma_ai.compat.platform_info import PlatformProfile
from mma_ai.learning.benchmark import (
    build_benchmark_report,
    calculate_median,
    calculate_ratio_median,
    calculate_ui_cost,
    evaluate_pass,
    evaluate_view3d_status,
    main,
    run_benchmark,
    write_benchmark_report,
)


def _load_schema() -> dict[str, Any]:
    """Nạp lược đồ JSON Schema của hợp đồng train-benchmark.schema.json."""
    schema_subpath = "specs/003-ppo-train-repro/contracts/train-benchmark.schema.json"
    candidates = [
        Path.cwd() / schema_subpath,
        Path(__file__).resolve().parents[2] / schema_subpath,
    ]
    for p in candidates:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    raise FileNotFoundError("Không tìm thấy tệp train-benchmark.schema.json")


def test_tdd_red_contract_module_exists() -> None:
    """FR-023, CMD-TRN-0004: Khẳng định độc lập mô-đun learning.benchmark tồn tại trên hệ thống."""
    assert importlib.util.find_spec("mma_ai.learning.benchmark") is not None


def test_ratio_median_and_pass_rule() -> None:
    """FR-023, NFR-PERF-001, CMD-TRN-0004: Kiểm thử tính trung vị, tỷ lệ và luật đạt ngưỡng."""
    # Tính trung vị (median) cho chuỗi lẻ và chẵn
    ui_off_steps = [1500.0, 1490.0, 1510.0, 1505.0, 1495.0]
    ui_on_steps = [1480.0, 1470.0, 1490.0, 1485.0, 1475.0]

    median_off = calculate_median(ui_off_steps)
    median_on = calculate_median(ui_on_steps)

    assert median_off == 1500.0
    assert median_on == 1480.0

    # Tính tỷ lệ trung vị (ratio_median = ui_on / ui_off)
    ratio = calculate_ratio_median(median_on, median_off)
    expected_ratio = round(1480.0 / 1500.0, 4)  # 0.9867
    assert round(ratio, 4) == expected_ratio

    # Đánh giá ngưỡng đạt (pass rule) với ngưỡng mặc định 0.90
    assert evaluate_pass(ratio, threshold=0.9) is True
    assert evaluate_pass(0.90, threshold=0.9) is True
    assert evaluate_pass(0.8999, threshold=0.9) is False
    assert evaluate_pass(0.75, threshold=0.9) is False

    # Trường hợp biên (edge case): chia cho 0 hoặc chuỗi rỗng
    with pytest.raises(ValueError, match="lớn hơn 0"):
        calculate_ratio_median(100.0, 0.0)

    with pytest.raises(ValueError, match="chuỗi rỗng"):
        calculate_median([])


def test_schema_valid() -> None:
    """FR-023, NFR-PERF-001, CMD-TRN-0004, INV-005: Kiểm thử hồ sơ khớp JSON Schema hợp đồng."""
    schema = _load_schema()

    ui_off_steps = [1500.0, 1490.0, 1510.0, 1505.0, 1495.0]
    ui_on_steps = [1480.0, 1470.0, 1490.0, 1485.0, 1475.0]
    ui_cost = {
        "cpu_utilization_pct_delta": 0.8,
        "ram_peak_mb_delta": 35.0,
        "vram_peak_mb_delta": None,
    }
    view3d = {
        "measured": False,
        "reason": "không có màn hình (DISPLAY chưa đặt)",
    }

    report = build_benchmark_report(
        seed=42,
        env_steps_per_run=8192,
        repeats=5,
        ui_off_steps=ui_off_steps,
        ui_on_steps=ui_on_steps,
        ui_cost=ui_cost,
        view3d=view3d,
        threshold=0.9,
        created_utc="2026-10-09T10:00:00Z",
    )

    # Thẩm định với jsonschema
    jsonschema.validate(instance=report, schema=schema)

    # Khẳng định các trường cốt lõi
    assert report["schema_version"] == "1.0.0"
    assert report["seed"] == 42
    assert report["env_steps_per_run"] == 8192
    assert report["repeats"] == 5
    assert report["threshold"] == 0.9
    assert report["passed"] is True
    assert report["ratio_median"] == 0.9867
    assert report["ui_off"]["median"] == 1500.0
    assert report["ui_on"]["median"] == 1480.0
    assert report["ui_cost"]["cpu_utilization_pct_delta"] == 0.8
    assert report["ui_cost"]["ram_peak_mb_delta"] == 35.0
    assert report["ui_cost"]["vram_peak_mb_delta"] is None
    assert report["view3d"]["measured"] is False
    assert report["view3d"]["reason"] == "không có màn hình (DISPLAY chưa đặt)"


def test_view3d_measured_false_without_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-022, FR-023, NFR-HEADLESS-001, INV-005: Kiểm thử view3d báo measured:false."""
    # Ca 1: Biến môi trường DISPLAY và WAYLAND_DISPLAY đều bị gỡ bỏ
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    view3d_status = evaluate_view3d_status()
    assert view3d_status["measured"] is False
    assert view3d_status["reason"] is not None
    assert "DISPLAY" in view3d_status["reason"] or "màn hình" in view3d_status["reason"]

    # Ca 2: Truyền cờ has_display tường minh
    status_explicit_false = evaluate_view3d_status(has_display=False)
    assert status_explicit_false["measured"] is False
    reason_false = status_explicit_false["reason"] or ""
    assert "DISPLAY" in reason_false or "màn hình" in reason_false

    # Ca 3: Có màn hình nhưng mặc định hiển thị 3D tắt trong benchmark
    status_explicit_true = evaluate_view3d_status(has_display=True)
    assert status_explicit_true["measured"] is False
    reason_true = status_explicit_true["reason"] or ""
    assert "tắt mặc định" in reason_true or "không kích hoạt" in reason_true


def test_inv_001_ac_3_view3d_uses_shared_linux_display_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """006 AC-3, INV-001: benchmark dùng phép dò chung và giữ lý do Linux."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("MMA_AI_FORCE_NO_DISPLAY", raising=False)
    calls: list[bool] = []
    profile = PlatformProfile("linux", "6", "x86_64", (3, 11, 0), False, True)

    def fake_probe(selected: PlatformProfile) -> DisplayProbe:
        calls.append(selected.kind == "linux")
        return DisplayProbe(False, "Không phát hiện màn hình --headless.")

    monkeypatch.setattr(
        benchmark_module,
        "probe_display",
        fake_probe,
        raising=False,
    )
    monkeypatch.setattr(benchmark_module, "detect_platform", lambda: profile, raising=False)

    status = evaluate_view3d_status()

    assert status == {
        "measured": False,
        "reason": "không có màn hình (DISPLAY chưa đặt)",
    }
    assert calls == [True]


def test_ac_3_view3d_reports_shared_probe_reason_for_non_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """006 AC-3: benchmark chuyển nguyên lý do phép dò trên hệ điều hành khác."""
    monkeypatch.setattr(
        benchmark_module,
        "probe_display",
        lambda selected: DisplayProbe(False, "Không tìm thấy màn hình chính (--headless)."),
        raising=False,
    )
    monkeypatch.setattr(
        benchmark_module,
        "detect_platform",
        lambda: PlatformProfile("windows", "11", "AMD64", (3, 11, 0), False, True),
        raising=False,
    )

    status = evaluate_view3d_status()

    assert status["reason"] == "Không tìm thấy màn hình chính (--headless)."


def test_inv_003_ac_4_benchmark_report_uses_atomic_text_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """006 AC-4, INV-003: báo cáo được ghi qua bộ ghi văn bản nguyên tử."""
    report_file = tmp_path / "benchmark.json"
    captured: dict[str, str] = {}
    atomic_writer = getattr(benchmark_module, "write_text_atomic")

    def capture(path: Path | str, text: str) -> None:
        captured["path"] = str(path)
        captured["text"] = text
        atomic_writer(path, text)

    monkeypatch.setattr(benchmark_module, "write_text_atomic", capture, raising=False)
    result = write_benchmark_report(report_file, {"ok": True})

    assert result == report_file
    assert captured["path"] == str(report_file)
    assert captured["text"] == '{\n  "ok": true\n}\n'
    assert report_file.read_bytes() == b'{\n  "ok": true\n}\n'


def test_ac_4_main_configures_utf8_before_argument_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """006 AC-4: CLI cấu hình UTF-8 trước khi xử lý tham số."""
    calls: list[str] = []
    parser_builder = benchmark_module._build_parser

    def build_parser() -> Any:
        calls.append("parser")
        return parser_builder()

    monkeypatch.setattr(
        benchmark_module, "ensure_utf8_stdio", lambda: calls.append("utf8"), raising=False
    )
    monkeypatch.setattr(benchmark_module, "_build_parser", build_parser)

    assert main(["--repeats", "4"]) == 2
    assert calls == ["utf8", "parser"]


def test_ui_cost_delta_calculation() -> None:
    """FR-023: Kiểm thử tính toán độ chênh lệch tài nguyên (resource delta) giữa hai chế độ."""
    ui_off_res = [
        {"cpu_utilization_pct": 12.0, "ram_peak_mb": 150.0, "vram_peak_mb": None},
        {"cpu_utilization_pct": 12.4, "ram_peak_mb": 152.0, "vram_peak_mb": None},
    ]
    ui_on_res = [
        {"cpu_utilization_pct": 13.0, "ram_peak_mb": 185.0, "vram_peak_mb": None},
        {"cpu_utilization_pct": 13.2, "ram_peak_mb": 187.0, "vram_peak_mb": None},
    ]

    cost = calculate_ui_cost(ui_on_res, ui_off_res)

    assert cost["cpu_utilization_pct_delta"] is not None
    assert round(cost["cpu_utilization_pct_delta"], 2) == 0.9  # (13.1 - 12.2)
    assert cost["ram_peak_mb_delta"] is not None
    assert round(cost["ram_peak_mb_delta"], 1) == 35.0  # (186.0 - 151.0)
    assert cost["vram_peak_mb_delta"] is None

    # Ca có thông tin VRAM (GPU CUDA)
    ui_off_gpu = [{"cpu_utilization_pct": None, "ram_peak_mb": 100.0, "vram_peak_mb": 500.0}]
    ui_on_gpu = [{"cpu_utilization_pct": None, "ram_peak_mb": 120.0, "vram_peak_mb": 550.0}]
    cost_gpu = calculate_ui_cost(ui_on_gpu, ui_off_gpu)
    assert cost_gpu["cpu_utilization_pct_delta"] is None
    assert cost_gpu["ram_peak_mb_delta"] == 20.0
    assert cost_gpu["vram_peak_mb_delta"] == 50.0


def test_write_benchmark_report_atomic(tmp_path: Path) -> None:
    """FR-023, INV-001, INV-005: Kiểm thử ghi báo cáo benchmark nguyên tử xuống đĩa."""
    report_file = tmp_path / "logs" / "m1" / "benchmark_train.json"

    ui_off_steps = [1500.0, 1490.0, 1510.0, 1505.0, 1495.0]
    ui_on_steps = [1480.0, 1470.0, 1490.0, 1485.0, 1475.0]
    ui_cost = {
        "cpu_utilization_pct_delta": None,
        "ram_peak_mb_delta": 10.0,
        "vram_peak_mb_delta": None,
    }
    report = build_benchmark_report(
        seed=42,
        env_steps_per_run=4096,
        repeats=5,
        ui_off_steps=ui_off_steps,
        ui_on_steps=ui_on_steps,
        ui_cost=ui_cost,
        view3d={"measured": False, "reason": "chưa hỗ trợ màn hình"},
        threshold=0.9,
    )

    written_path = write_benchmark_report(report_file, report)
    assert written_path.is_file()

    # Kiểm tra nội dung đọc lại hợp lệ
    loaded = json.loads(written_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "1.0.0"
    assert loaded["passed"] is True
    assert loaded["seed"] == 42


def test_benchmark_cli_parser_and_validation(capsys: pytest.CaptureFixture[str]) -> None:
    """CMD-TRN-0004: Kiểm thử phân tích tham số dòng lệnh và các mã lỗi tham số không hợp lệ."""
    # Tham số repeats < 5 bị từ chối với mã thoát 2
    exit_code_repeats = main(["--repeats", "4"])
    captured = capsys.readouterr()
    assert exit_code_repeats == 2
    assert "tối thiểu 5" in captured.err or "repeats" in captured.err

    # Tham số seed < 0 bị từ chối với mã thoát 2
    exit_code_seed = main(["--seed", "-1"])
    captured = capsys.readouterr()
    assert exit_code_seed == 2
    assert "seed" in captured.err


def test_run_benchmark_mock_runner(tmp_path: Path) -> None:
    """NFR-PERF-001, CMD-TRN-0004: Kiểm thử quy trình chạy xen kẽ với mock runner."""
    out_file = tmp_path / "benchmark.json"

    # Giả lập runner trả về thông lượng và tài nguyên
    # Với 5 lần lặp xen kẽ: 5 lượt ui_off, 5 lượt ui_on
    call_history: list[str] = []

    def mock_runner_pass(
        seed: int,
        ui_mode: str,
        runs_dir: Path,
        config_path: Path | None,
        total_steps: int | None,
    ) -> dict[str, Any]:
        call_history.append(ui_mode)
        tp = 1500.0 if ui_mode == "none" else 1450.0  # 1450 / 1500 = 0.9667 >= 0.90
        return {
            "throughput": {"env_steps_per_second": tp, "env_steps": 4096},
            "resources": {"cpu_utilization_pct": 10.0, "ram_peak_mb": 120.0, "vram_peak_mb": None},
        }

    report, passed = run_benchmark(
        seed=42,
        repeats=5,
        output_path=out_file,
        runner=mock_runner_pass,
    )

    assert passed is True
    assert report["passed"] is True
    assert len(call_history) == 10
    # Khẳng định xen kẽ: none, web, none, web, ...
    expected_order = [
        "none", "web", "none", "web", "none", "web", "none", "web", "none", "web"
    ]
    assert call_history == expected_order
    assert out_file.is_file()

    # Ca 2: Hiệu năng giảm quá 10% (ví dụ ui_on còn 1200 / 1500 = 0.80 < 0.90)
    out_fail = tmp_path / "benchmark_fail.json"

    def mock_runner_fail(
        seed: int,
        ui_mode: str,
        runs_dir: Path,
        config_path: Path | None,
        total_steps: int | None,
    ) -> dict[str, Any]:
        tp = 1500.0 if ui_mode == "none" else 1200.0
        return {
            "throughput": {"env_steps_per_second": tp, "env_steps": 4096},
            "resources": {"cpu_utilization_pct": 10.0, "ram_peak_mb": 120.0, "vram_peak_mb": None},
        }

    report_fail, passed_fail = run_benchmark(
        seed=42,
        repeats=5,
        output_path=out_fail,
        runner=mock_runner_fail,
    )
    assert passed_fail is False
    assert report_fail["passed"] is False
    assert report_fail["ratio_median"] == 0.8
