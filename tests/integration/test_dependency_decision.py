"""Kiểm tra quyết định phụ thuộc cho AC-5 và NFR-INST-001."""

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _lock_packages() -> dict[str, dict[str, Any]]:
    with (PROJECT_ROOT / "uv.lock").open("rb") as lock_file:
        lock_data = tomllib.load(lock_file)
    return {package["name"]: package for package in lock_data["package"]}


def _project_data() -> dict[str, Any]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        return tomllib.load(project_file)


def test_ac_5_myosuite_absent_from_pyproject_and_lock() -> None:
    """AC-5 không được kéo MyoSuite vào phụ thuộc dự án hay lockfile."""
    project = _project_data()
    dependencies = project["project"]["dependencies"]

    assert all(not dependency.startswith("myosuite") for dependency in dependencies)
    assert "myosuite" not in _lock_packages()


def test_ac_5_gymnasium_locked_at_least_1_4() -> None:
    """AC-5 ghim Gymnasium ở dòng phiên bản 1.4."""
    version = tuple(
        int(part) for part in _lock_packages()["gymnasium"]["version"].split(".")
    )

    assert version >= (1, 4, 0)


def test_ac_5_myo_sim_locked_0_2_3() -> None:
    """AC-5 khoá đúng phiên bản myo-sim đã được quyết định."""
    assert _lock_packages()["myo-sim"]["version"] == "0.2.3"


def test_nfr_inst_001_lock_matches_pyproject_constraints() -> None:
    """NFR-INST-001 giữ các ràng buộc runtime trong metadata của lockfile."""
    project_dependencies = _project_data()["project"]["dependencies"]
    lock_metadata = _lock_packages()["mma-ai"]["metadata"]["requires-dist"]
    locked_constraints = {
        f'{dependency["name"]}{dependency.get("specifier", "")}'
        for dependency in lock_metadata
        if "marker" not in dependency
    }

    assert {"gymnasium>=1.4,<1.5", "myo-sim==0.2.3"}.issubset(project_dependencies)
    assert {"gymnasium>=1.4,<1.5", "myo-sim==0.2.3"}.issubset(locked_constraints)


def test_ac_5_decision_recorded_in_research_q1() -> None:
    """AC-5 ghi quyết định, phương án loại và bằng chứng cài đặt ở Q1."""
    research = (
        PROJECT_ROOT / "specs/002-elbow-muscle-env/research.md"
    ).read_text(encoding="utf-8")
    q1 = research.split("## Q1.", maxsplit=1)[1].split("## Q2.", maxsplit=1)[0]

    assert "**Quyết định**" in q1
    assert "**Phương án đã loại**" in q1
    assert "uv pip install --dry-run" in q1
