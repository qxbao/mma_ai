"""Kiểm thử ràng buộc nhập và ghi tệp cho giao diện quan sát và checkpoint (US5/INV-005).

Hiện thực và bảo vệ các yêu cầu:
- FR-021: Giao diện quan sát (monitoring) chỉ đọc dữ liệu huấn luyện, không can thiệp.
- INV-005: Mô-đun quan sát chỉ-đọc, không nhập learning.trainer, learning.ppo hay torch.
- INV-004 / INV-005: learning/checkpoint.py chỉ nhập networks, normalizer;
  không nhập ppo hay trainer.
- Ràng buộc ghi tệp: Ngoại trừ ui.json (và tệp tạm .tmp của nó),
  mô-đun quan sát tuyệt đối không ghi tệp.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _get_project_root() -> Path:
    """Trả về thư mục gốc của dự án."""
    return Path(__file__).resolve().parents[2]


def test_monitoring_has_no_training_imports() -> None:
    """FR-021, INV-005: Quét AST tệp src/mma_ai/monitoring/*.py: cấm trainer, ppo, torch."""
    root = _get_project_root()
    monitoring_dir = root / "src" / "mma_ai" / "monitoring"
    assert monitoring_dir.is_dir(), f"Thư mục quan sát không tồn tại: {monitoring_dir}"

    py_files = sorted(monitoring_dir.glob("*.py"))
    assert len(py_files) > 0, "Không tìm thấy tệp mã Python nào trong src/mma_ai/monitoring"

    forbidden_modules = ("learning.trainer", "learning.ppo", "torch")

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


def test_checkpoint_does_not_import_ppo_or_trainer() -> None:
    """INV-004, INV-005: learning/checkpoint.py cấm nhập ppo hay trainer."""
    root = _get_project_root()
    checkpoint_file = root / "src" / "mma_ai" / "learning" / "checkpoint.py"
    assert checkpoint_file.is_file(), f"Tệp checkpoint.py không tồn tại: {checkpoint_file}"

    forbidden_patterns = ("learning.trainer", "learning.ppo", "trainer", "ppo")
    tree = ast.parse(checkpoint_file.read_text(encoding="utf-8"), filename=str(checkpoint_file))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_patterns:
                    assert forbidden not in alias.name, (
                        f"INV-005 vi phạm: checkpoint.py chứa import '{alias.name}' "
                        f"(bị cấm '{forbidden}') tại dòng {node.lineno}"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for forbidden in forbidden_patterns:
                assert forbidden not in module, (
                    f"INV-005 vi phạm: checkpoint.py chứa from {module} import ... "
                    f"(bị cấm '{forbidden}') tại dòng {node.lineno}"
                )
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                for forbidden in forbidden_patterns:
                    assert forbidden not in full_name, (
                        f"INV-005 vi phạm: checkpoint.py nhập '{alias.name}' từ '{module}' "
                        f"(bị cấm '{forbidden}') tại dòng {node.lineno}"
                    )


def test_monitoring_no_file_writes_except_ui_json() -> None:
    """FR-021, INV-005: Quét AST tĩnh đảm bảo monitoring không ghi tệp ngoài ui.json."""
    root = _get_project_root()
    monitoring_dir = root / "src" / "mma_ai" / "monitoring"

    py_files = sorted(monitoring_dir.glob("*.py"))
    assert len(py_files) > 0, "Không tìm thấy tệp mã Python nào trong src/mma_ai/monitoring"

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # 1. Kiểm tra open(..., mode) với mode có 'w', 'a', 'x', '+'
                if isinstance(func, ast.Name) and func.id == "open":
                    # Mặc định open không ghi nếu chỉ đọc, kiểm tra các đối số
                    args = node.args
                    keywords = {kw.arg: kw.value for kw in node.keywords}
                    mode_val = None
                    if len(args) >= 2 and isinstance(args[1], ast.Constant):
                        mode_val = args[1].value
                    elif "mode" in keywords and isinstance(keywords["mode"], ast.Constant):
                        mode_val = keywords["mode"].value

                    is_write_mode = (
                        isinstance(mode_val, str)
                        and any(m in mode_val for m in ("w", "a", "x", "+"))
                    )
                    if is_write_mode and isinstance(mode_val, str):
                        # Nếu mở ghi, chỉ cho phép trong ngữ cảnh cli.py và tệp ui.json
                        assert py_file.name == "cli.py", (
                            f"FR-021 vi phạm: open() ở chế độ ghi '{mode_val}' xuất hiện tại "
                            f"{py_file.name}:{node.lineno}"
                        )

                # 2. Kiểm tra phương thức write_text hoặc write_bytes của Path
                elif isinstance(func, ast.Attribute) and func.attr in ("write_text", "write_bytes"):
                    assert py_file.name == "cli.py", (
                        f"FR-021 vi phạm: {func.attr} xuất hiện tại {py_file.name}:{node.lineno}"
                    )
                    # Trong cli.py, chỉ tmp_path ghi dữ liệu cho ui.json
                    if isinstance(func.value, ast.Name):
                        assert func.value.id in ("tmp_path", "ui_path"), (
                            f"FR-021 vi phạm: {func.attr} được gọi trên biến không hợp lệ "
                            f"'{func.value.id}' tại {py_file.name}:{node.lineno}"
                        )
