"""Kiểm tra metadata đóng gói cho feature huấn luyện."""

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_metadata() -> dict[str, Any]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject:
        return tomllib.load(pyproject)


def test_rl_extra_has_torch_and_tensorboard() -> None:
    """FR-002: extra rl phải cung cấp torch và tensorboard."""
    extras = _project_metadata()["project"]["optional-dependencies"]

    assert set(extras["rl"]) >= {"torch", "tensorboard"}


def test_forbidden_deps_absent() -> None:
    """FR-010: metadata không kéo các dependency ngoài phạm vi train."""
    metadata = _project_metadata()
    all_dependencies = [
        *metadata["project"]["dependencies"],
        *metadata["project"]["optional-dependencies"]["rl"],
        *metadata["project"]["optional-dependencies"]["dev"],
    ]
    forbidden = {"stable-baselines3", "psutil", "pynvml", "streamlit", "flask", "gradio"}

    dependency_names = {
        dependency.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0]
        for dependency in all_dependencies
    }

    assert not dependency_names & forbidden


def test_package_data_covers_learning_yaml() -> None:
    """FR-019: wheel phải chứa các YAML cạnh mã learning."""
    artifacts = _project_metadata()["tool"]["hatch"]["build"]["targets"]["wheel"]["artifacts"]

    assert "src/mma_ai/learning/*.yaml" in artifacts
