"""Kiểm thử tích hợp các ràng buộc nhập và ghi tệp cho phân hệ đánh giá (US5/FR-014/INV-005).

Mô-đun này chứng minh và bảo vệ các yêu cầu miền:
- FR-014, INV-005: Phân hệ đánh giá (mma_ai.evaluation) hoạt động ở chế độ chỉ đọc
  đối với dữ liệu huấn luyện (run profile, checkpoint, training log); TUYỆT ĐỐI KHÔNG nhập
  các mô-đun huấn luyện (learning.trainer, learning.ppo); mọi dữ liệu xuất ra chỉ được
  phép ghi vào thư mục eval/ và thư mục tạm .tmp-*.
- NFR-HEADLESS-001: Môi trường không đầu (headless environment) cho phép kết xuất biểu đồ
  mà không cần màn hình; việc nhập mô-đun charts không phụ thuộc vào biến môi trường DISPLAY
  và backend matplotlib được cố định là 'Agg'.
- AC-1, AC-3: Bảo vệ ranh giới kiến trúc độc lập giữa phân hệ đánh giá và phân hệ huấn luyện.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from mma_ai.evaluation.report import (
    prepare_eval_dirs,
    publish_report,
    save_evaluation_result,
)


def _get_project_root() -> Path:
    """Trả về thư mục gốc của dự án (project root)."""
    return Path(__file__).resolve().parents[2]


def _compute_sha256(file_path: Path) -> str:
    """Tính mã băm SHA-256 của tệp để kiểm tra tính bất biến (immutability)."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_evaluation_has_no_training_imports() -> None:
    """FR-014, INV-005, US5: Quét AST phân hệ evaluation đảm bảo không nhập mô-đun huấn luyện."""
    root = _get_project_root()
    eval_dir = root / "src" / "mma_ai" / "evaluation"
    assert eval_dir.is_dir(), f"Thư mục evaluation không tồn tại: {eval_dir}"

    py_files = sorted(eval_dir.glob("*.py"))
    assert len(py_files) > 0, "Không tìm thấy tệp mã Python nào trong src/mma_ai/evaluation"

    # Danh sách các mô-đun huấn luyện bị cấm tuyệt đối theo FR-014 và INV-005
    forbidden_modules = (
        "learning.trainer",
        "learning.ppo",
        "mma_ai.learning.trainer",
        "mma_ai.learning.ppo",
    )

    # 1. Quét cây cú pháp trừu tượng (abstract syntax tree - AST) trên toàn bộ tệp mã nguồn
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert forbidden not in alias.name, (
                            f"INV-005 vi phạm: {py_file.name} chứa lệnh import '{alias.name}' "
                            f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for forbidden in forbidden_modules:
                    assert forbidden not in module, (
                        f"INV-005 vi phạm: {py_file.name} chứa lệnh from {module} import ... "
                        f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                    )
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    for forbidden in forbidden_modules:
                        assert forbidden not in full_name, (
                            f"INV-005 vi phạm: {py_file.name} nhập '{alias.name}' từ '{module}' "
                            f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                        )

    # 2. Kiểm tra động trong tiến trình con cô lập (isolated subprocess)
    modules_to_test = [
        "mma_ai.evaluation",
        "mma_ai.evaluation.errors",
        "mma_ai.evaluation.eval_config",
        "mma_ai.evaluation.policies",
        "mma_ai.evaluation.rollout",
        "mma_ai.evaluation.stats",
        "mma_ai.evaluation.split_guard",
        "mma_ai.evaluation.report",
        "mma_ai.evaluation.runner",
        "mma_ai.evaluation.cli",
    ]
    import_statements = "\n".join(f"import {mod}" for mod in modules_to_test)
    check_code = (
        f"{import_statements}\n"
        "import sys\n"
        "forbidden = ('mma_ai.learning.trainer', 'mma_ai.learning.ppo')\n"
        "for mod in forbidden:\n"
        "    assert mod not in sys.modules, f'{mod} đã bị nạp vào sys.modules'\n"
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Kiểm tra động nạp mô-đun huấn luyện thất bại: {result.stderr}"
    )


def test_charts_import_does_not_require_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-HEADLESS-001, FR-010, FR-011, AC-3:
    Nhập charts với DISPLAY bỏ đặt không lỗi, backend Agg.
    """
    root = _get_project_root()
    charts_file = root / "src" / "mma_ai" / "evaluation" / "charts.py"
    assert charts_file.is_file(), f"Tệp charts.py không tồn tại: {charts_file}"

    # 1. Quét AST tĩnh của charts.py để xác nhận matplotlib.use('Agg') được cấu hình
    tree = ast.parse(charts_file.read_text(encoding="utf-8"), filename=str(charts_file))
    has_use_agg = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "use"
                and len(node.args) >= 1
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "Agg"
            ):
                has_use_agg = True
                break
    assert has_use_agg, "charts.py phải chứa lời gọi cấu hình matplotlib.use('Agg')"

    # 2. Thử nghiệm nhập cục bộ với biến DISPLAY và WAYLAND_DISPLAY bị xóa bỏ
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # Đảm bảo import mma_ai.evaluation.charts thành công trong môi trường headless
    import mma_ai.evaluation.charts as charts_mod

    assert hasattr(charts_mod, "render_charts"), "Module charts phải chứa hàm render_charts"
    assert hasattr(charts_mod, "ChartResult"), "Module charts phải chứa lớp ChartResult"

    # 3. Kiểm tra động trong tiến trình con cô lập khi DISPLAY không tồn tại
    check_code = (
        "import os\n"
        "import sys\n"
        "os.environ.pop('DISPLAY', None)\n"
        "os.environ.pop('WAYLAND_DISPLAY', None)\n"
        "import mma_ai.evaluation.charts as charts\n"
        "try:\n"
        "    import matplotlib\n"
        "    matplotlib.use('Agg')\n"
        "    backend = matplotlib.get_backend().lower()\n"
        "    assert 'agg' in backend, f'Backend không phải Agg: {backend}'\n"
        "except ImportError:\n"
        "    pass\n"
    )

    env = dict(os.environ)
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["PYTHONPATH"] = str(root / "src")

    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Lỗi khi kiểm tra nạp charts trong môi trường không có DISPLAY: {result.stderr}"
    )


def test_no_writes_outside_eval_dir(tmp_path: Path) -> None:
    """FR-014, INV-005, US5:
    Lời gọi ghi tệp trong runner/report chỉ nhắm thư mục eval/ và .tmp-*.
    """
    root = _get_project_root()
    eval_dir = root / "src" / "mma_ai" / "evaluation"

    runner_file = eval_dir / "runner.py"
    report_file = eval_dir / "report.py"
    assert runner_file.is_file(), f"Tệp runner.py không tồn tại: {runner_file}"
    assert report_file.is_file(), f"Tệp report.py không tồn tại: {report_file}"

    # 1. Phân tích AST tĩnh: Kiểm tra mọi thao tác ghi đĩa trong runner.py và report.py
    for py_file in (runner_file, report_file):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func

                # Kiểm tra open(..., mode)
                if isinstance(func, ast.Name) and func.id == "open":
                    mode_val: object = "r"
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                        mode_val = node.args[1].value
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            mode_val = kw.value.value

                    is_write_mode = (
                        isinstance(mode_val, str)
                        and any(m in mode_val for m in ("w", "a", "x", "+"))
                    )
                    if is_write_mode:
                        # Chỉ cho phép mở ghi trong report.py tại hàm write_episodes_csv
                        assert py_file.name == "report.py", (
                            f"FR-014 vi phạm: {py_file.name} mở tệp chế độ ghi '{mode_val}' "
                            f"tại dòng {node.lineno}"
                        )

                # Kiểm tra write_text hoặc write_bytes của Path
                elif isinstance(func, ast.Attribute) and func.attr in ("write_text", "write_bytes"):
                    assert py_file.name == "report.py", (
                        f"FR-014 vi phạm: {func.attr} xuất hiện ngoài report.py "
                        f"tại {py_file.name}:{node.lineno}"
                    )
                    # Trong report.py, chỉ biến report_file (thuộc tmp_path) được ghi
                    if isinstance(func.value, ast.Name):
                        assert func.value.id in ("report_file", "path"), (
                            f"FR-014 vi phạm: {func.attr} gọi trên đối tượng không hợp lệ "
                            f"'{func.value.id}' tại dòng {node.lineno}"
                        )

    # 2. Kiểm tra hợp đồng phân định đường dẫn của prepare_eval_dirs
    run_dir = tmp_path / "sample_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    eval_id = "20261011T000000Z_e12345"

    tmp_eval_dir, target_eval_dir = prepare_eval_dirs(run_dir, eval_id)
    eval_root = run_dir / "eval"

    assert tmp_eval_dir.parent == eval_root, (
        f"Thư mục tạm '{tmp_eval_dir}' phải nằm trực tiếp dưới '{eval_root}'"
    )
    assert tmp_eval_dir.name.startswith(".tmp-"), (
        f"Thư mục tạm '{tmp_eval_dir.name}' phải bắt đầu bằng tiền tố '.tmp-'"
    )
    assert target_eval_dir.parent == eval_root, (
        f"Thư mục đích '{target_eval_dir}' phải nằm trực tiếp dưới '{eval_root}'"
    )
    assert target_eval_dir.name == eval_id, (
        f"Thư mục đích '{target_eval_dir.name}' phải trùng khớp định danh eval_id"
    )

    # 3. Kiểm chứng thực nghiệm động: Đảm bảo không ghi đè bất kỳ tệp gốc nào của run
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"run_id": "sample_run", "seed": 42}), encoding="utf-8")

    metrics_path = run_dir / "metrics.jsonl"
    metrics_path.write_text('{"step": 1, "reward": 0.5}\n', encoding="utf-8")

    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    ckpt_file = checkpoints_dir / "latest.json"
    ckpt_file.write_text(json.dumps({"step": 1}), encoding="utf-8")

    # Lưu lại mã băm ban đầu của các tệp thuộc run
    initial_hashes = {
        manifest_path: _compute_sha256(manifest_path),
        metrics_path: _compute_sha256(metrics_path),
        ckpt_file: _compute_sha256(ckpt_file),
    }

    # Thực hiện lưu kết quả đánh giá vào thư mục tạm và công bố nguyên tử (atomic rename)
    sample_report: dict[str, Any] = {
        "eval_id": eval_id,
        "run": {"seed": 42},
        "status": "done",
    }
    saved_tmp = save_evaluation_result(tmp_eval_dir, sample_report, records=[])
    assert saved_tmp.is_dir(), "Thư mục tạm phải tồn tại sau khi save_evaluation_result"
    assert (saved_tmp / "report.json").is_file(), "Tệp report.json phải nằm trong thư mục tạm"
    assert (saved_tmp / "episodes.csv").is_file(), "Tệp episodes.csv phải nằm trong thư mục tạm"

    # Công bố kết quả đánh giá sang thư mục chính thức
    final_dir = publish_report(saved_tmp, target_eval_dir)
    assert final_dir == target_eval_dir, "publish_report phải trả về đường dẫn thư mục đích"
    assert final_dir.is_dir(), "Thư mục kết quả chính thức phải tồn tại"
    assert (final_dir / "report.json").is_file(), "report.json phải nằm trong thư mục eval"
    assert not saved_tmp.exists(), "Thư mục tạm .tmp-* phải được dọn sạch sau khi đổi tên nguyên tử"

    # Kiểm tra tính toàn vẹn của các tệp ban đầu của run
    for file_path, original_hash in initial_hashes.items():
        assert _compute_sha256(file_path) == original_hash, (
            f"INV-005 vi phạm: Tệp của run '{file_path.name}' đã bị thay đổi sau khi đánh giá"
        )

    # Quét toàn bộ thư mục run: Đảm bảo mọi tệp mới CHỈ xuất hiện trong run_dir / "eval"
    for item in run_dir.rglob("*"):
        if item.is_file():
            is_original = item in initial_hashes
            is_in_eval = eval_root in item.parents
            assert is_original or is_in_eval, (
                f"FR-014 / INV-005 vi phạm: Phát hiện tệp mới '{item.relative_to(run_dir)}' "
                f"nằm ngoài thư mục 'eval/'"
            )
