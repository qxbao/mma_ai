"""Kiểm thử đầu-cuối (end-to-end, E2E) tài liệu qua entrypoint CLI thật.

Truy vết: AC-1, AC-2, AC-3, AC-4, AC-5, INV-001, INV-004,
NFR-DOC-001, NFR-DOC-003, NFR-DOC-004.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from functools import cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUIDES = {"training.md": "train", "evaluation.md": "evaluate", "replay-demo.md": "replay"}
DOCUMENTS = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CONTRIBUTING.md",
    PROJECT_ROOT / "CHANGELOG.md",
    *(PROJECT_ROOT / "docs/guides" / name for name in GUIDES),
)
COMMANDS = {
    "train": [sys.executable, "scripts/train.py"],
    "evaluate": [sys.executable, "-m", "mma_ai.evaluation.cli"],
    "replay": [sys.executable, "-m", "mma_ai.visualization.cli"],
    "benchmark": [sys.executable, "-m", "mma_ai.learning.benchmark"],
    "uv-run": ["uv", "run"],
    "uv-sync": ["uv", "sync"],
    "mypy": ["uv", "run", "--isolated", "--with", "mypy", "mypy"],
}
FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
SHELL_BLOCK_RE = re.compile(r"^[ \t]*```(?:sh|bash)\s*\n(.*?)^[ \t]*```", re.MULTILINE | re.DOTALL)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _read(path: Path) -> str:
    """Đọc tài liệu bằng UTF-8 để phát hiện lỗi mã hóa."""
    return path.read_text(encoding="utf-8")


@cache
def _help(command: str) -> str:
    """Gọi trợ giúp của entrypoint thật bằng tiến trình con."""
    result = subprocess.run(
        [*COMMANDS[command], "--help"], cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=45, check=False,
    )
    if (command in {"train", "evaluate"} and result.returncode != 0
            and ("ModuleNotFoundError" in result.stderr or "ImportError" in result.stderr)):
        pytest.skip(f"Thiếu phụ thuộc nhóm rl/eval: {result.stderr.strip()}")
    assert result.returncode == 0, (
        f"Lệnh {command} --help trả mã {result.returncode}: "
        f"{result.stdout}\n{result.stderr}"
    )
    assert "usage:" in result.stdout.lower(), f"Lệnh {command} không in trợ giúp"
    return result.stdout


def _flags(text: str) -> set[str]:
    """Trích cờ dài (long options) để so khớp nguyên cờ."""
    return set(FLAG_RE.findall(text))


def _documented_commands(text: str) -> list[str]:
    """Lấy từng dòng lệnh trong khối shell của tài liệu."""
    return [
        line.strip()
        for block in SHELL_BLOCK_RE.findall(text)
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _command_for_line(line: str) -> str:
    """Ánh xạ lệnh tài liệu tới trợ giúp tương ứng."""
    if line.startswith("python scripts/train.py "):
        return "train"
    for module, command in (
        ("mma_ai.evaluation.cli", "evaluate"),
        ("mma_ai.visualization.cli", "replay"),
        ("mma_ai.learning.benchmark", "benchmark"),
    ):
        if line.startswith(f"python -m {module} "):
            return command
    if line.startswith("uv sync"):
        return "uv-sync"
    if line.startswith("uv run"):
        return "uv-run"
    pytest.fail(f"Lệnh tài liệu chưa ánh xạ tới --help: {line}")
    raise AssertionError("pytest.fail phải dừng kiểm thử")


@pytest.mark.parametrize("command", ("train", "evaluate", "replay", "benchmark"))
def test_ac2_ac5_inv001_cli_help(command: str) -> None:
    """AC-2, AC-5, INV-001: bốn lệnh thật trả trợ giúp và mã thoát 0."""
    assert _flags(_help(command)), f"Trợ giúp {command} không có cờ"


def test_ac2_inv004_readme_quickstart() -> None:
    """AC-2, INV-004: README có đúng bốn lệnh nhanh đã chốt."""
    readme = _read(PROJECT_ROOT / "README.md")
    quickstart = readme.split("## Bắt đầu nhanh\n", 1)[1].split("\n## ", 1)[0]
    assert _documented_commands(quickstart) == [
        "python scripts/train.py --stage elbow --seed 42",
        "python -m mma_ai.evaluation.cli --checkpoint <ckpt>",
        "python -m mma_ai.visualization.cli --episode <tệp>",
        "python -m mma_ai.learning.benchmark --seed 42 --repeats 5",
    ]


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda path: path.name)
def test_ac2_ac3_ac5_inv001_documented_flags(path: Path) -> None:
    """AC-2, AC-3, AC-5, INV-001: mọi cờ trong khối lệnh có ở --help thật."""
    lines = _documented_commands(_read(path))
    if path.name == "CHANGELOG.md":
        assert not lines
        return
    assert lines, f"{path.name} không có khối lệnh để đối chiếu"
    for line in lines:
        command = _command_for_line(line)
        documented = _flags(line)
        if command == "uv-run":
            uv_flags = documented & {"--isolated", "--with"}
            assert uv_flags <= _flags(_help("uv-run")), f"Cờ uv sai trong {path}: {line}"
            documented -= uv_flags
            if "mypy --strict" in line:
                assert documented <= _flags(_help("mypy")), f"Cờ mypy sai trong {path}: {line}"
            else:
                assert not documented, f"Cờ lệnh chưa đối chiếu trong {path}: {line}"
        else:
            missing = documented - _flags(_help(command))
            assert not missing, f"Cờ sai trong {path.name}, lệnh {command}: {sorted(missing)}"


@pytest.mark.parametrize("name,command", GUIDES.items())
def test_ac5_inv001_guide_options(name: str, command: str) -> None:
    """AC-5, INV-001: cờ mô tả bằng văn xuôi có ở CLI thật."""
    guide_flags = _flags(_read(PROJECT_ROOT / "docs/guides" / name))
    assert guide_flags
    if name == "training.md":
        assert "--repeats" in _flags(_help("benchmark"))
        guide_flags.remove("--repeats")
    missing = guide_flags - _flags(_help(command))
    assert not missing, f"{name} ghi cờ sai: {sorted(missing)}"


def test_ac1_ac2_ac3_ac4_ac5_document_structure() -> None:
    """AC-1…AC-5: kiểm tra cấu trúc, phiên bản và độ dài tài liệu."""
    license_text = _read(PROJECT_ROOT / "LICENSE")
    assert license_text.startswith("MIT License\n")
    assert license_text.count("Copyright (c) 2026 Dương Quan Bao") == 1
    assert "Permission is hereby granted, free of charge" in license_text

    readme = _read(PROJECT_ROOT / "README.md")
    assert re.findall(r"^## (.+)$", readme, re.MULTILINE) == [
        "Tính năng", "Yêu cầu hệ thống", "Cài đặt bằng uv", "Bắt đầu nhanh",
        "Cấu trúc thư mục", "Chạy kiểm thử", "Tình trạng nền tảng",
        "Tài liệu", "Đóng góp", "Giấy phép",
    ]
    assert "Python-3.11--3.12" in readme and "license-MIT" in readme
    assert "uv sync" in readme
    metadata = tomllib.loads(_read(PROJECT_ROOT / "pyproject.toml"))
    assert set(metadata["project"]["optional-dependencies"]) == {"rl", "eval", "dev"}
    for group in ("rl", "eval", "dev"):
        assert f"--extra {group}" in readme

    contributing = _read(PROJECT_ROOT / "CONTRIBUTING.md")
    assert len(contributing.splitlines()) <= 100
    for tool in ("pytest", "ruff", "mypy"):
        assert tool in contributing
    assert "docs/MAP.md" in contributing and "specs/*/tasks.md" in contributing

    changelog = _read(PROJECT_ROOT / "CHANGELOG.md")
    version = metadata["project"]["version"]
    assert "## [Unreleased]" in changelog
    assert re.search(
        rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
        changelog, re.MULTILINE,
    )
    assert "Keep a Changelog" in changelog

    guides_dir = PROJECT_ROOT / "docs/guides"
    assert {p.name for p in guides_dir.iterdir() if p.is_file()} == set(GUIDES)
    for name in GUIDES:
        guide = _read(guides_dir / name)
        assert len(guide.splitlines()) <= 120, f"{name} dài quá 120 dòng"
        assert "../../README.md" in guide


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda path: path.name)
def test_ac2_ac3_ac4_ac5_inv004_relative_links(path: Path) -> None:
    """AC-2…AC-5, INV-004: mọi liên kết tương đối có đích thật."""
    links = LINK_RE.findall(_read(path))
    assert links, f"{path.name} không có liên kết để kiểm tra"
    for raw_target in links:
        target = raw_target.split(maxsplit=1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith("#"):
            continue
        destination = path.parent / unquote(parsed.path)
        assert destination.exists(), f"Liên kết gãy tại {path.name}: {raw_target}"
