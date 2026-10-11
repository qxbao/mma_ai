"""Kiểm thử phụ thuộc cài chung cho quá trình huấn luyện RL (US1, FR-002, FR-019).

Xác minh:
- test_gymnasium_torch_tensorboard_import_together:
  Nhập gymnasium, torch, tensorboard, mujoco cùng môi trường khuỷu tay
  trong cùng một tiến trình và ghi nhận phiên bản.
- test_no_forbidden_libs_imported:
  Không nhập stable_baselines3, psutil, pynvml, streamlit, flask, gradio
  từ các gói mma_ai.learning và mma_ai.monitoring.
- test_gymnasium_pin_matches_pyproject:
  Phiên bản gymnasium đang cài đặt khớp với ràng buộc ghim trong pyproject.toml.
"""

from __future__ import annotations

import ast
import importlib
import importlib.metadata
import tomllib
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version


def _get_project_root() -> Path:
    """Trả về đường dẫn gốc của dự án."""
    return Path(__file__).resolve().parents[2]


def _load_pyproject() -> dict[str, Any]:
    """Nạp cấu hình pyproject.toml dưới dạng từ điển."""
    pyproject_path = _get_project_root() / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        return tomllib.load(f)


def test_regress_tdd_rl_dependencies_configured_in_pyproject() -> None:
    """FR-002: Khẳng định độc lập extra rl được khai báo trong pyproject.toml."""
    pyproject = _load_pyproject()
    optional_deps = pyproject["project"]["optional-dependencies"]
    assert "rl" in optional_deps, "Thiếu extra 'rl' trong project.optional-dependencies"
    assert set(optional_deps["rl"]) >= {"torch", "tensorboard"}


def test_gymnasium_torch_tensorboard_import_together() -> None:
    """FR-002: Nhập gymnasium, torch, tensorboard, mujoco và môi trường khuỷu tay cùng lúc."""
    import pytest

    torch = pytest.importorskip("torch", reason="Cần extra rl (torch) để kiểm thử tương thích")
    tensorboard = pytest.importorskip(
        "tensorboard", reason="Cần extra rl (tensorboard) để kiểm thử tương thích"
    )
    import gymnasium
    import mujoco

    from mma_ai.environment.single_agent import make_env

    versions = {
        "gymnasium": gymnasium.__version__,
        "torch": torch.__version__,
        "tensorboard": tensorboard.__version__,
        "mujoco": mujoco.__version__,
    }

    # Xác nhận các phiên bản thư viện đều tồn tại và hợp lệ
    for name, ver in versions.items():
        assert ver, f"Phiên bản của {name} không hợp lệ hoặc rỗng: {ver}"

    # Khởi tạo môi trường khuỷu tay trên tập train trong cùng tiến trình
    env = make_env(split="train")
    try:
        assert env is not None, "Không thể tạo môi trường khuỷu tay với make_env(split='train')"
        obs, info = env.reset(seed=42)
        assert obs is not None, "Observation sau reset không được là None"
        assert info.get("target_split") == "train", "Môi trường phải chạy trên tập train"
    finally:
        env.close()


def test_no_forbidden_libs_imported() -> None:
    """FR-010, FR-019: Cấm nhập các thư viện không thuộc phạm vi vào learning và monitoring."""
    root = _get_project_root()
    forbidden_libs = {
        "stable_baselines3",
        "stable-baselines3",
        "psutil",
        "pynvml",
        "streamlit",
        "flask",
        "gradio",
    }

    # 1. Quét AST tĩnh toàn bộ module trong learning và monitoring
    target_dirs = [
        root / "src" / "mma_ai" / "learning",
        root / "src" / "mma_ai" / "monitoring",
    ]
    py_files: list[Path] = []
    for d in target_dirs:
        assert d.is_dir(), f"Thư mục không tồn tại: {d}"
        py_files.extend(sorted(d.glob("*.py")))

    assert len(py_files) > 0, "Không tìm thấy tệp Python nào trong learning hoặc monitoring"

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name_base = alias.name.split(".")[0].replace("-", "_")
                    assert name_base not in forbidden_libs, (
                        f"Vi phạm thư viện cấm: {py_file.name} chứa import '{alias.name}' "
                        f"tại dòng {node.lineno}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                mod_base = module.split(".")[0].replace("-", "_")
                assert mod_base not in forbidden_libs, (
                    f"Vi phạm thư viện cấm: {py_file.name} chứa from '{module}' import ... "
                    f"tại dòng {node.lineno}"
                )

    # 2. Nhập trực tiếp các module và kiểm tra sys.modules không xuất hiện thư viện cấm
    import sys

    import mma_ai.learning  # noqa: F401
    import mma_ai.monitoring  # noqa: F401

    for forbidden in ["stable_baselines3", "psutil", "pynvml", "streamlit", "flask", "gradio"]:
        assert forbidden not in sys.modules, (
            f"Thư viện cấm '{forbidden}' xuất hiện trong sys.modules sau khi nạp gói!"
        )


def test_gymnasium_pin_matches_pyproject() -> None:
    """FR-002: Phiên bản gymnasium đang cài đặt phải khớp với ghim trong pyproject.toml."""
    pyproject = _load_pyproject()
    dependencies: list[str] = pyproject["project"]["dependencies"]

    gym_constraint: str | None = None
    for dep in dependencies:
        if dep.startswith("gymnasium"):
            gym_constraint = dep[len("gymnasium"):]
            break

    assert gym_constraint is not None, "Không tìm thấy ràng buộc gymnasium trong pyproject.toml"

    installed_version_str = importlib.metadata.version("gymnasium")
    installed_version = Version(installed_version_str)
    specifier = SpecifierSet(gym_constraint)

    assert installed_version in specifier, (
        f"Phiên bản gymnasium cài đặt ({installed_version_str}) không thoả mãn ràng buộc "
        f"trong pyproject.toml: 'gymnasium{gym_constraint}'"
    )
