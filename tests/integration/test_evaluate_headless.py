"""Kiểm thử tích hợp đánh giá không cần màn hình và xử lý nhật ký qua CLI (T418).

Hiện thực các kịch bản kiểm thử tích hợp (integration test) và chấp nhận (acceptance test)
cho chế độ không màn hình (headless mode) và tính chống chịu với nhật ký (training log):
- 004 US3, 004 AC-3, FR-010, FR-011, NFR-HEADLESS-001: Biến môi trường DISPLAY và WAYLAND_DISPLAY
  bị bỏ đặt (unset) vẫn hoàn tất đánh giá với mã thoát 0, sinh đủ 3 tệp ảnh PNG (loss, reward,
  activation) khác rỗng và báo cáo biểu đồ hoàn tất (complete).
- 004 US3, 004 AC-3, FR-011: Nhật ký thiếu chuỗi kích hoạt cơ (activation series) thì thoát mã 6,
  kết quả số và báo cáo vẫn được lưu đầy đủ với trạng thái done_charts_incomplete, thông điệp lỗi
  trên đầu ra lỗi tiêu chuẩn (stderr) nêu rõ biểu đồ thiếu và nguyên nhân, tuyệt đối không tạo
  ảnh rỗng giả thay thế.
- 004 US3, 004 AC-3, FR-012, NFR-REL-001: Nhật ký chứa giá trị không hữu hạn (NaN/Inf) thì các
  điểm này bị loại trừ, không vẽ thành giá trị giả 0; số điểm bị bỏ (points_dropped) và lý do được
  phản ánh trung thực trong báo cáo đánh giá (report.json).
- 004 US3, 004 AC-3, FR-010, FR-013, Edge Cases: Nhật ký của phiên chạy dở dang hoặc lỗi (running,
  error, interrupted) vẫn được kết xuất phần dữ liệu đã có; báo cáo ghi đúng trạng thái thực tế
  của phiên chạy, tuyệt đối không tự nhận là phiên chạy hoàn chỉnh (done).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from eval_fixtures import make_run_dir, run_cli

from mma_ai.evaluation.charts import ChartResult, render_charts
from mma_ai.evaluation.metrics import TrainingLog
from mma_ai.evaluation.runner import evaluate_checkpoint

PNG_MAGIC_BYTES: bytes = b"\x89PNG\r\n\x1a\n"
DEFAULT_MUSCLE_NAMES: tuple[str, ...] = (
    "BIClong",
    "BICshort",
    "BRA",
    "TRIlong",
    "TRIlat",
    "TRImed",
)


def _eval_deps() -> tuple[Any, Any, Any]:
    """Kiểm tra và nạp các thư viện phụ thuộc tùy chọn (optional dependencies) eval và rl."""
    pd = pytest.importorskip("pandas", reason="Cần extra eval (pandas) để đọc nhật ký")
    mpl = pytest.importorskip("matplotlib", reason="Cần extra eval (matplotlib) vẽ biểu đồ")
    torch = pytest.importorskip("torch", reason="Cần extra rl (torch) để chạy CLI")
    return pd, mpl, torch


def _assert_no_nonfinite(obj: Any, path: str = "$") -> None:
    """Quét đệ quy cấu trúc dữ liệu bảo đảm không chứa NaN hoặc Infinity (NFR-REL-001, FR-017)."""
    if isinstance(obj, float):
        assert not math.isnan(obj), f"Phát hiện NaN tại {path}"
        assert not math.isinf(obj), f"Phát hiện Infinity tại {path}"
    elif isinstance(obj, str):
        lowered = obj.strip().lower()
        nonfinite_words = {"nan", "infinity", "-infinity", "+infinity", "inf", "-inf"}
        assert lowered not in nonfinite_words, (
            f"Phát hiện chuỗi số không hữu hạn '{obj}' tại {path}"
        )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_nonfinite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _assert_no_nonfinite(item, f"{path}[{idx}]")


def test_independent_assertion_headless_contract() -> None:
    """Khẳng định độc lập trên base chứng minh hợp đồng kiểm thử headless tồn tại (API-EVL-0009).

    Bảo đảm bộ kiểm thử không bị bỏ qua toàn bộ khi thiếu các phụ thuộc tùy chọn.
    Xác minh sự hiện diện của các hàm và kiểu dữ liệu trọng yếu trong phân hệ đánh giá.
    """
    assert callable(render_charts), "Hàm render_charts phải tồn tại và có thể gọi."
    assert callable(evaluate_checkpoint), "Hàm evaluate_checkpoint phải tồn tại và có thể gọi."
    assert callable(run_cli), "Tiện ích run_cli phải tồn tại trong eval_fixtures."
    assert callable(make_run_dir), "Tiện ích make_run_dir phải tồn tại trong eval_fixtures."
    assert issubclass(ChartResult, object), "Lớp ChartResult phải tồn tại."
    assert issubclass(TrainingLog, object), "Lớp TrainingLog phải tồn tại."


def test_evaluate_with_display_unset_exit0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """004 US3, 004 AC-3, FR-010, FR-011, NFR-HEADLESS-001:
    DISPLAY và WAYLAND_DISPLAY bỏ đặt vẫn hoàn tất đánh giá với mã thoát 0 và đủ 3 tệp PNG.
    """
    _eval_deps()

    # Bảo đảm biến môi trường màn hình đồ hoạ bị gỡ bỏ triệt để
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # 1. Dựng thư mục lượt chạy mẫu hoàn chỉnh có đủ nhật ký huấn luyện
    run_dir = make_run_dir(tmp_path / "headless_run", status="done", with_log=True, seed=42)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # 2. Thực thi dòng lệnh đánh giá qua tiến trình con subprocess
    result = run_cli(
        ["--checkpoint", str(checkpoint_target), "--repeats", "1", "--eval-seed", "12345"]
    )

    # 3. Khẳng định mã thoát bằng 0 và không có lỗi nghiêm trọng
    assert result.exit_code == 0, (
        f"Lệnh đánh giá thất bại với mã {result.exit_code}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # 4. Kiểm tra thư mục kết quả đánh giá được xuất bản trong thư mục run
    eval_parent = run_dir / "eval"
    assert eval_parent.is_dir(), "Thư mục eval/ phải được tạo bên trong thư mục run."
    eval_subdirs = [p for p in eval_parent.iterdir() if p.is_dir()]
    assert len(eval_subdirs) == 1, (
        f"Kỳ vọng đúng 1 thư mục kết quả đánh giá duy nhất, nhận được: {eval_subdirs}"
    )
    published_dir = eval_subdirs[0]

    # 5. Kiểm tra tệp báo cáo report.json và trạng thái biểu đồ hoàn tất
    report_file = published_dir / "report.json"
    assert report_file.is_file(), "Tệp báo cáo report.json phải tồn tại trên đĩa."
    report_data = json.loads(report_file.read_text(encoding="utf-8"))

    assert report_data.get("status") == "done", "Trạng thái tổng thể của báo cáo phải là 'done'."
    charts_section = report_data.get("charts", {})
    assert charts_section.get("status") == "complete", "Trạng thái biểu đồ phải là 'complete'."
    assert charts_section.get("reason") is None, "Không được có lý do lỗi khi biểu đồ hoàn tất."
    assert charts_section.get("points_dropped") == 0, "Không có điểm dữ liệu nào bị loại bỏ."
    assert charts_section.get("log_source") == "jsonl", "Nguồn nhật ký huấn luyện phải là jsonl."

    # 6. Kiểm tra đủ 3 tệp ảnh PNG khác rỗng với chữ ký tệp PNG hợp lệ
    files_map = charts_section.get("files", {})
    for chart_type in ["loss", "reward", "activation"]:
        rel_path = files_map.get(chart_type)
        assert rel_path == f"charts/{chart_type}.png", (
            f"Đường dẫn tương đối của biểu đồ {chart_type} phải là 'charts/{chart_type}.png', "
            f"thực tế: {rel_path}"
        )
        img_file = published_dir / rel_path
        assert img_file.is_file(), f"Tệp ảnh {rel_path} phải tồn tại thực tế trên đĩa."
        assert img_file.stat().st_size > 0, f"Tệp ảnh {rel_path} không được rỗng (kích thước 0)."

        header = img_file.read_bytes()[: len(PNG_MAGIC_BYTES)]
        assert header == PNG_MAGIC_BYTES, (
            f"Tệp {rel_path} phải bắt đầu bằng chữ ký hợp lệ của định dạng PNG."
        )

    # 7. Kiểm tra tệp nhật ký tập phim episodes.csv tồn tại và có tiêu đề hợp lệ
    episodes_file = published_dir / "episodes.csv"
    assert episodes_file.is_file(), "Tệp episodes.csv phải được ghi nhận cùng báo cáo."
    csv_raw = episodes_file.read_text(encoding="utf-8")
    csv_lines = [line.strip() for line in csv_raw.splitlines() if line.strip()]
    assert len(csv_lines) >= 2, "Tệp episodes.csv phải có ít nhất dòng tiêu đề và 1 dòng dữ liệu."

    # 8. Xác thực độ tin cậy số học (NFR-REL-001)
    _assert_no_nonfinite(report_data)


def test_missing_activation_series_exit6_results_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """004 US3, 004 AC-3, FR-011:
    Nhật ký thiếu chuỗi activation thì thoát mã 6, report.json vẫn lưu kèm done_charts_incomplete,
    stderr nêu biểu đồ thiếu và nguyên nhân, tuyệt đối không tạo ảnh rỗng thay thế.
    """
    _eval_deps()

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # 1. Dựng thư mục lượt chạy mẫu cố ý loại bỏ chuỗi kích hoạt cơ (activation)
    run_dir = make_run_dir(
        tmp_path / "missing_act_run",
        status="done",
        with_log=True,
        drop_series=["activation"],
        seed=43,
    )
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # 2. Thực thi dòng lệnh đánh giá
    result = run_cli(
        ["--checkpoint", str(checkpoint_target), "--repeats", "1", "--eval-seed", "12345"]
    )

    # 3. Khẳng định mã thoát bắt buộc phải là 6 (thiếu biểu đồ nhưng đã lưu kết quả số)
    assert result.exit_code == 6, (
        f"Kỳ vọng mã thoát 6 khi thiếu chuỗi biểu đồ, thực tế {result.exit_code}.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # 4. Kiểm tra đầu ra lỗi tiêu chuẩn (stderr) nêu rõ biểu đồ thiếu và nguyên nhân
    stderr_lower = result.stderr.lower()
    assert "activation" in stderr_lower, (
        f"Đầu ra stderr phải nêu rõ biểu đồ 'activation' bị thiếu:\n{result.stderr}"
    )

    # 5. Kiểm tra kết quả số và báo cáo vẫn được lưu an toàn trong thư mục eval
    eval_parent = run_dir / "eval"
    assert eval_parent.is_dir(), "Thư mục eval/ vẫn phải tồn tại khi thoát mã 6."
    eval_subdirs = [p for p in eval_parent.iterdir() if p.is_dir()]
    assert len(eval_subdirs) == 1, "Phải xuất bản đúng một thư mục kết quả đánh giá."
    published_dir = eval_subdirs[0]

    report_file = published_dir / "report.json"
    assert report_file.is_file(), "Báo cáo report.json phải được lưu nguyên tử khi thiếu biểu đồ."
    report_data = json.loads(report_file.read_text(encoding="utf-8"))

    # 6. Kiểm tra trạng thái báo cáo phản ánh chuẩn done_charts_incomplete
    assert report_data.get("status") == "done_charts_incomplete", (
        f"Kỳ vọng status 'done_charts_incomplete', thực tế: {report_data.get('status')}"
    )
    charts_section = report_data.get("charts", {})
    assert charts_section.get("status") == "incomplete", (
        f"Kỳ vọng charts.status 'incomplete', thực tế: {charts_section.get('status')}"
    )
    reason_str = str(charts_section.get("reason") or "").lower()
    assert charts_section.get("reason") is not None, "Báo cáo phải nêu lý do tại charts.reason."
    reason_val = charts_section.get("reason")
    assert "activation" in reason_str, (
        f"charts.reason phải nêu rõ nguyên nhân activation: {reason_val}"
    )

    # 7. Tuyệt đối không tạo ảnh rỗng giả thay thế cho biểu đồ activation
    assert charts_section.get("files", {}).get("activation") is None, (
        "Trường charts.files.activation phải là null khi không tạo được biểu đồ."
    )
    fake_activation_img = published_dir / "charts" / "activation.png"
    assert not fake_activation_img.exists(), (
        "Tuyệt đối không được tạo tệp ảnh rỗng activation.png giả mạo trên đĩa."
    )

    # 8. Tuyệt đối không tạo ảnh rỗng giả thay thế trên đĩa
    fake_images = [
        img for img in (published_dir / "charts").glob("*.png") if img.stat().st_size == 0
    ]
    assert not fake_images, f"Không được tạo tệp ảnh rỗng giả mạo trên đĩa: {fake_images}"

    # 9. Kiểm tra các số liệu đánh giá cốt lõi vẫn được lưu đầy đủ
    assert "learned" in report_data.get("policies", {}), "Dữ liệu policy học được phải lưu."
    assert "random" in report_data.get("policies", {}), "Dữ liệu policy ngẫu nhiên phải lưu."
    assert "comparison" in report_data, "Khối so sánh thống kê phải được lưu."
    assert (published_dir / "episodes.csv").is_file(), "Tệp episodes.csv vẫn phải được lưu."

    _assert_no_nonfinite(report_data)


def test_nonfinite_loss_points_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """004 US3, 004 AC-3, FR-012, NFR-REL-001:
    Điểm không hữu hạn (NaN/Inf) bị loại trừ, số điểm bỏ và lý do nằm trong báo cáo.
    """
    _eval_deps()

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # =========================================================================
    # Kịch bản 1: Nhật ký chứa các điểm NaN và Inf xen kẽ với các điểm hợp lệ
    # =========================================================================
    run_dir_mixed = make_run_dir(
        tmp_path / "run_nonfinite_mixed", status="done", with_log=True, seed=44
    )
    metrics_file = run_dir_mixed / "metrics.jsonl"
    existing_lines = [
        json.loads(line)
        for line in metrics_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Chèn các bản ghi chứa NaN và Inf cho chuỗi mất mát policy_loss
    existing_lines.append(
        {
            "update": 4,
            "env_steps": 400,
            "step": 400,
            "loss/policy": float("nan"),
            "loss/value": 0.05,
            "loss/entropy": 0.02,
            "reward/mean_return": 40.0,
            **{f"activation/{m}": 0.4 for m in DEFAULT_MUSCLE_NAMES},
        }
    )
    existing_lines.append(
        {
            "update": 5,
            "env_steps": 500,
            "step": 500,
            "loss/policy": float("inf"),
            "loss/value": 0.04,
            "loss/entropy": 0.01,
            "reward/mean_return": 50.0,
            **{f"activation/{m}": 0.5 for m in DEFAULT_MUSCLE_NAMES},
        }
    )
    with metrics_file.open("w", encoding="utf-8") as f:
        for rec in existing_lines:
            f.write(json.dumps(rec) + "\n")

    checkpoint_target_mixed = run_dir_mixed / "checkpoints" / "latest.json"
    result_mixed = run_cli(
        ["--checkpoint", str(checkpoint_target_mixed), "--repeats", "1", "--eval-seed", "12345"]
    )

    # Do vẫn còn các điểm hợp lệ khác nên cả 3 biểu đồ vẫn vẽ được, thoát mã 0
    assert result_mixed.exit_code == 0, (
        f"Kỳ vọng mã thoát 0 khi còn điểm hợp lệ, thực tế {result_mixed.exit_code}.\n"
        f"STDERR:\n{result_mixed.stderr}"
    )

    eval_subdirs_mixed = [p for p in (run_dir_mixed / "eval").iterdir() if p.is_dir()]
    assert len(eval_subdirs_mixed) == 1
    report_mixed = json.loads((eval_subdirs_mixed[0] / "report.json").read_text(encoding="utf-8"))

    charts_mixed = report_mixed.get("charts", {})
    # Số điểm bị loại bỏ do không hữu hạn phải được ghi nhận trung thực (>= 2)
    assert charts_mixed.get("points_dropped", 0) >= 2, (
        f"Kỳ vọng points_dropped >= 2, thực tế: {charts_mixed.get('points_dropped')}"
    )
    assert charts_mixed.get("points_plotted", {}).get("loss", 0) > 0, (
        "Các điểm hợp lệ của chuỗi loss vẫn phải được vẽ vào biểu đồ."
    )
    _assert_no_nonfinite(report_mixed)

    # =========================================================================
    # Kịch bản 2: Toàn bộ chuỗi loss chứa giá trị không hữu hạn (run huấn luyện lỗi)
    # =========================================================================
    run_dir_all_nan = make_run_dir(
        tmp_path / "run_loss_all_nan", status="done", with_log=True, seed=45
    )
    all_nan_metrics = run_dir_all_nan / "metrics.jsonl"
    records_all_nan = [
        json.loads(line)
        for line in all_nan_metrics.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Đặt toàn bộ các giá trị của nhóm loss thành NaN
    for r in records_all_nan:
        for k in list(r.keys()):
            if k.startswith("loss/"):
                r[k] = float("nan")

    with all_nan_metrics.open("w", encoding="utf-8") as f:
        for rec in records_all_nan:
            f.write(json.dumps(rec) + "\n")

    checkpoint_target_nan = run_dir_all_nan / "checkpoints" / "latest.json"
    result_nan = run_cli(
        ["--checkpoint", str(checkpoint_target_nan), "--repeats", "1", "--eval-seed", "12345"]
    )

    # Khi không có bất kỳ điểm loss hợp lệ nào, biểu đồ loss không tạo được ⇒ thoát mã 6
    assert result_nan.exit_code == 6, (
        f"Kỳ vọng mã 6 khi loss không có điểm hợp lệ, thực tế: {result_nan.exit_code}"
    )

    eval_subdirs_nan = [p for p in (run_dir_all_nan / "eval").iterdir() if p.is_dir()]
    assert len(eval_subdirs_nan) == 1
    report_nan = json.loads((eval_subdirs_nan[0] / "report.json").read_text(encoding="utf-8"))

    charts_nan = report_nan.get("charts", {})
    assert charts_nan.get("status") == "incomplete", "Biểu đồ phải có trạng thái incomplete."
    assert charts_nan.get("files", {}).get("loss") is None, "Tệp loss phải là null trong báo cáo."
    assert not (eval_subdirs_nan[0] / "charts" / "loss.png").exists(), (
        "Tuyệt đối không được tạo tệp loss.png rỗng trên đĩa."
    )
    assert charts_nan.get("points_dropped", 0) > 0, "Phải ghi nhận số điểm không hữu hạn bị bỏ."
    reason_nan_str = str(charts_nan.get("reason") or "").lower()
    assert charts_nan.get("reason") is not None, "Báo cáo phải ghi nhận lý do tại charts.reason."
    assert "loss" in reason_nan_str, (
        f"Lý do trong báo cáo phải nêu rõ liên quan tới biểu đồ loss: {charts_nan.get('reason')}"
    )
    _assert_no_nonfinite(report_nan)


def test_running_or_error_run_reports_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """004 US3, 004 AC-3, FR-010, FR-013, Edge Cases:
    Phiên chạy đang chạy (running) hoặc lỗi (error/interrupted) vẫn vẽ phần đã có,
    báo cáo ghi nhận trung thực trạng thái run, không tự nhận là phiên chạy hoàn chỉnh.
    """
    _eval_deps()

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # 1. Kiểm tra đối với phiên chạy đang thực thi (running)
    run_dir_running = make_run_dir(
        tmp_path / "run_status_running", status="running", with_log=True, seed=46
    )
    res_running = run_cli(
        [
            "--checkpoint",
            str(run_dir_running / "checkpoints" / "latest.json"),
            "--repeats",
            "1",
            "--eval-seed",
            "12345",
        ]
    )

    assert res_running.exit_code == 0, (
        f"Phiên chạy running có nhật ký hợp lệ phải hoàn tất đánh giá thành công (mã 0), "
        f"thực tế {res_running.exit_code}.\nSTDERR:\n{res_running.stderr}"
    )

    eval_running = list((run_dir_running / "eval").glob("*"))[0]
    report_running = json.loads((eval_running / "report.json").read_text(encoding="utf-8"))

    # Báo cáo phải phản ánh đúng trạng thái của run là 'running', không được là 'done'
    actual_run_st = report_running.get("run", {}).get("run_status")
    assert actual_run_st == "running", (
        f"Kỳ vọng run.run_status là 'running', thực tế: {actual_run_st}"
    )
    assert actual_run_st != "done", (
        "Phiên chạy đang chạy tuyệt đối không được ghi nhận là 'done' (hoàn chỉnh)."
    )
    # Phần biểu đồ từ nhật ký hiện có vẫn được vẽ đầy đủ
    assert report_running.get("charts", {}).get("status") == "complete"
    for chart_type in ["loss", "reward", "activation"]:
        assert (eval_running / "charts" / f"{chart_type}.png").is_file()

    # 2. Kiểm tra đối với phiên chạy gặp lỗi gián đoạn (error)
    run_dir_error = make_run_dir(
        tmp_path / "run_status_error", status="error", with_log=True, seed=47
    )
    res_error = run_cli(
        [
            "--checkpoint",
            str(run_dir_error / "checkpoints" / "latest.json"),
            "--repeats",
            "1",
            "--eval-seed",
            "12345",
        ]
    )

    assert res_error.exit_code == 0, (
        f"Phiên chạy error có nhật ký hợp lệ vẫn kết xuất biểu đồ phần đã có (mã 0), "
        f"thực tế {res_error.exit_code}.\nSTDERR:\n{res_error.stderr}"
    )

    eval_error = list((run_dir_error / "eval").glob("*"))[0]
    report_error = json.loads((eval_error / "report.json").read_text(encoding="utf-8"))

    # Báo cáo phải phản ánh đúng trạng thái của run là 'error'
    actual_err_st = report_error.get("run", {}).get("run_status")
    assert actual_err_st == "error", (
        f"Kỳ vọng run.run_status là 'error', thực tế: {actual_err_st}"
    )
    assert actual_err_st != "done", "Phiên chạy lỗi tuyệt đối không được ghi nhận là 'done'."
    assert report_error.get("charts", {}).get("status") == "complete"
    for chart_type in ["loss", "reward", "activation"]:
        assert (eval_error / "charts" / f"{chart_type}.png").is_file()

    # 3. Kiểm tra đối với phiên chạy bị ngắt giữa chừng (interrupted)
    run_dir_interrupted = make_run_dir(
        tmp_path / "run_status_interrupted", status="interrupted", with_log=True, seed=48
    )
    res_interrupted = run_cli(
        [
            "--checkpoint",
            str(run_dir_interrupted / "checkpoints" / "latest.json"),
            "--repeats",
            "1",
            "--eval-seed",
            "12345",
        ]
    )

    assert res_interrupted.exit_code == 0, (
        "Phiên chạy interrupted vẫn kết xuất phần đã có (mã 0), "
        f"thực tế {res_interrupted.exit_code}."
    )

    eval_interrupted = list((run_dir_interrupted / "eval").glob("*"))[0]
    report_interrupted = json.loads((eval_interrupted / "report.json").read_text(encoding="utf-8"))

    actual_int_st = report_interrupted.get("run", {}).get("run_status")
    assert actual_int_st == "interrupted"
    assert actual_int_st != "done"
    assert report_interrupted.get("charts", {}).get("status") == "complete"

    _assert_no_nonfinite(report_running)
    _assert_no_nonfinite(report_error)
    _assert_no_nonfinite(report_interrupted)
