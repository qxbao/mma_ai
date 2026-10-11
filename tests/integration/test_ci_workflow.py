"""Kiểm tra hợp đồng của workflow đa nền tảng: 006 FR-020, NFR-CI-001, AC-6."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def _load_workflow() -> tuple[dict[str, Any], str]:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)
    assert isinstance(workflow, dict)
    return workflow, source


def test_matrix_has_six_cells() -> None:
    """006 FR-020, NFR-CI-001, AC-6: chạy đủ sáu tổ hợp nền tảng và Python."""
    workflow, _ = _load_workflow()
    job = workflow["jobs"]["test"]
    strategy = job["strategy"]
    matrix = strategy["matrix"]

    cells = {
        (os_name, python_version)
        for os_name in matrix["os"]
        for python_version in matrix["python"]
    }

    assert cells == {
        (os_name, python_version)
        for os_name in ("ubuntu-latest", "macos-latest", "windows-latest")
        for python_version in ("3.11", "3.12")
    }
    assert strategy["fail-fast"] is False


def test_each_cell_runs_check_env_then_tests() -> None:
    """006 FR-020, NFR-CI-001, AC-6: kiểm tra môi trường trước pytest ở mỗi ô ma trận."""
    workflow, _ = _load_workflow()
    steps = workflow["jobs"]["test"]["steps"]
    runs = [str(step.get("run", "")) for step in steps]
    env_checks = [
        index
        for index, command in enumerate(runs)
        if "python -m mma_ai.compat.env_report" in command
        or "scripts/check_env.py" in command
    ]
    test_runs = [index for index, command in enumerate(runs) if "pytest" in command]

    assert env_checks, "workflow cần có bước kiểm tra môi trường"
    assert test_runs, "workflow cần có bước pytest"
    assert min(env_checks) < min(test_runs)


def test_lockfile_is_checked_and_locked_sync() -> None:
    """006 FR-020, NFR-CI-001, AC-6: kiểm tra lockfile và đồng bộ chế độ khóa."""
    workflow, _ = _load_workflow()
    commands = "\n".join(
        str(step.get("run", ""))
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
    )

    assert "uv lock --check" in commands
    assert "uv sync --locked" in commands


def test_no_failure_masking_in_workflow() -> None:
    """006 FR-020, NFR-CI-001, AC-6: workflow không che mã lỗi bằng cấu hình hay shell."""
    _, source = _load_workflow()
    assert "continue-on-error" not in source
    assert "|| true" not in source
    forbidden_tokens = ("sk" + "ip", "xf" + "ail")
    assert all(token not in source.lower() for token in forbidden_tokens)
