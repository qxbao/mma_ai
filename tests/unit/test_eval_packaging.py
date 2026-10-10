"""Kiểm thử cấu hình đóng gói (packaging) cho phân hệ đánh giá policy.

Chứng minh các yêu cầu:
- FR-010: Extra eval cung cấp pandas và matplotlib để đọc nhật ký và vẽ biểu đồ.
- FR-005: Giữ thuật toán thống kê gọn nhẹ, không phụ thuộc scipy.
- NFR-HEADLESS-001: Môi trường đánh giá và tạo biểu đồ độc lập không đồ hoạ (headless).
"""

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_metadata() -> dict[str, Any]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)


def test_eval_extra_has_pandas_and_matplotlib() -> None:
    """FR-010, FR-005: Extra eval phải cung cấp pandas và matplotlib."""
    metadata = _project_metadata()
    optional_deps = metadata["project"]["optional-dependencies"]

    assert "eval" in optional_deps, "Thiếu nhóm phụ thuộc tùy chọn (optional dependency) 'eval'"
    eval_deps = {
        dep.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].strip()
        for dep in optional_deps["eval"]
    }
    assert {"pandas", "matplotlib"}.issubset(eval_deps), (
        f"Extra 'eval' phải chứa cả 'pandas' và 'matplotlib', thực tế: {eval_deps}"
    )


def test_eval_forbidden_dependencies_absent() -> None:
    """FR-005, NFR-HEADLESS-001: Không kéo scipy, seaborn, statsmodels vào extra eval."""
    metadata = _project_metadata()
    optional_deps = metadata["project"].get("optional-dependencies", {})
    eval_list = optional_deps.get("eval", [])

    eval_deps = {
        dep.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].strip()
        for dep in eval_list
    }
    forbidden = {"scipy", "seaborn", "statsmodels"}
    found_forbidden = eval_deps & forbidden
    assert not found_forbidden, (
        f"Extra 'eval' không được chứa các thư viện nặng ngoài phạm vi: {found_forbidden}"
    )


def test_package_data_covers_evaluation_yaml() -> None:
    """FR-010: Khai báo dữ liệu gói (package data) phải phủ evaluation/*.yaml."""
    artifacts = _project_metadata()["tool"]["hatch"]["build"]["targets"]["wheel"]["artifacts"]

    assert "src/mma_ai/evaluation/*.yaml" in artifacts, (
        f"Wheel artifacts phải chứa 'src/mma_ai/evaluation/*.yaml', thực tế: {artifacts}"
    )
