"""Kiểm thử đầu-cuối (end-to-end, E2E) tài liệu qua entrypoint CLI thật.

Truy vết: AC-1, AC-2, AC-3, AC-4, AC-5, INV-001, INV-002,
INV-003, INV-004, NFR-DOC-001, NFR-DOC-002, NFR-DOC-003, NFR-DOC-004,
NFR-GATE-001, NFR-QUAL-001.
Truy vết đồng bộ: 010/AC-1, 010/AC-2, 010/AC-3, 010/FR-010,
010/FR-011, 010/INV-001, 010/INV-003, 010/INV-004, 010/INV-005,
010/NFR-DOC-001, 010/NFR-DOC-002, 010/NFR-GATE-001, 010/NFR-QUAL-001.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import tomllib
from functools import cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUIDES = {"training.md": "train", "evaluation.md": "evaluate", "replay-demo.md": "replay"}
PLATFORM_GUIDE = "platforms.md"
ALL_GUIDES = (*GUIDES, PLATFORM_GUIDE)
CAPABILITY_MARKERS = (
    "requires_display", "requires_cuda", "requires_symlink",
    "windows_only", "requires_xdist", "requires_git_history",
)
DOCUMENTS = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CONTRIBUTING.md",
    PROJECT_ROOT / "CHANGELOG.md",
    *(PROJECT_ROOT / "docs/guides" / name for name in ALL_GUIDES),
)
COMMANDS = {
    "train": [sys.executable, "scripts/train.py"],
    "evaluate": [sys.executable, "-m", "mma_ai.evaluation.cli"],
    "replay": [sys.executable, "-m", "mma_ai.visualization.cli"],
    "benchmark": [sys.executable, "-m", "mma_ai.learning.benchmark"],
    "env-report": [sys.executable, "-m", "mma_ai.compat.env_report"],
    "pytest": [sys.executable, "-m", "pytest"],
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
    assert result.returncode == 0, (
        f"Lệnh {command} --help trả mã {result.returncode}: "
        f"{result.stdout}\n{result.stderr}"
    )
    assert "usage:" in result.stdout.lower(), f"Lệnh {command} không in trợ giúp"
    return result.stdout


def _flags(text: str) -> set[str]:
    """Trích cờ dài (long options) để so khớp nguyên cờ."""
    return set(FLAG_RE.findall(text))


def _supported_flags(command: str) -> set[str]:
    """Đối chiếu nguồn CLI tối giản không có --help; CLI khác dùng trợ giúp thật."""
    if command == "env-report":
        return _flags(_read(PROJECT_ROOT / "src/mma_ai/compat/env_report.py"))
    return _flags(_help(command))


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
        ("mma_ai.compat.env_report", "env-report"),
        ("pytest", "pytest"),
    ):
        if line.startswith(f"python -m {module} ") or (
            command == "env-report" and line == f"python -m {module}"
        ):
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


@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")
def test_inv002_document_commits_keep_product_code_untouched() -> None:
    """INV-002, NFR-GATE-001, NFR-QUAL-001: các commit tạo tài liệu không sửa mã sản phẩm hay CI."""
    allowed = {
        "README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md",
        *(f"docs/guides/{name}" for name in GUIDES),
    }
    changed: set[str] = set()
    for document in ("README.md", "CHANGELOG.md"):
        history = subprocess.run(
            ["git", "log", "--diff-filter=A", "-1", "--format=%H", "--", document],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
        commit = history.stdout.strip()
        assert commit, f"Không tìm được commit tạo {document}"
        files = subprocess.run(
            ["git", "show", "--format=", "--name-only", commit],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
        changed.update(files.stdout.splitlines())
    assert changed == allowed, f"Commit tài liệu đổi sai phạm vi: {sorted(changed ^ allowed)}"


def test_ac2_inv003_platform_claims_match_draft_support() -> None:
    """AC-2, INV-003: README nêu giới hạn nền tảng khi spec 006 còn draft."""
    platform = _read(PROJECT_ROOT / "README.md").split(
        "## Tình trạng nền tảng\n", 1
    )[1].split("\n## ", 1)[0]
    support_spec = _read(PROJECT_ROOT / "specs/006-cross-platform-support/spec.md")
    assert re.search(r"^status: draft$", support_spec, re.MULTILINE)
    assert "specs/006-cross-platform-support/" in platform
    rows = dict(re.findall(r"^- \*\*(.+?)\*\*: (.+)$", platform, re.MULTILINE))
    assert "đã kiểm" in rows["Linux"] and "chưa kiểm" not in rows["Linux"]
    for label in ("Windows 11", "WSL2", "macOS", "CUDA", "Ô CI chạy thật trên GitHub Actions"):
        assert "chưa kiểm" in rows[label], f"{label} thiếu giới hạn kiểm chứng"
        assert "đã kiểm" not in rows[label], f"{label} khẳng định vượt bằng chứng"
    for claim in ("hỗ trợ đầy đủ", "đã xác nhận khả năng chạy", "chạy được trên mọi nền tảng"):
        assert claim not in platform.lower(), f"Khẳng định vượt bằng chứng: {claim}"


def test_ac2_nfr_doc002_first_step_is_executable() -> None:
    """AC-2, NFR-DOC-002: kiểm tiền đề tự động; thời gian đọc do reviewer đo."""
    readme = _read(PROJECT_ROOT / "README.md")
    install = readme.split("## Cài đặt bằng uv\n", 1)[1].split("\n## ", 1)[0]
    quickstart = readme.split("## Bắt đầu nhanh\n", 1)[1].split("\n## ", 1)[0]
    assert "uv sync" in install
    assert ".venv" in quickstart and "uv run" in quickstart
    assert _documented_commands(quickstart)[0] == "python scripts/train.py --stage elbow --seed 42"
    start = time.monotonic()
    result = subprocess.run(
        [*COMMANDS["train"], "--help"], cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=600, check=False,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert elapsed <= 600, f"Entrypoint đầu tiên mất {elapsed:.2f} giây"


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
            missing = documented - _supported_flags(command)
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
    assert {p.name for p in guides_dir.iterdir() if p.is_file()} == set(ALL_GUIDES)
    assert f"docs/guides/{PLATFORM_GUIDE}" in readme
    for name in ALL_GUIDES:
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


def _capture_cli(name: str, result: subprocess.CompletedProcess[str]) -> None:
    """Lưu đầu ra CLI theo kịch bản (scenario) khi cổng cấp thư mục capture."""
    record = f"exit={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    print(f"{name}\n{record}")
    capture_dir = os.environ.get("AI_SDLC_CAPTURE_DIR")
    if capture_dir:
        destination = Path(capture_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f"{name}.txt").write_text(record, encoding="utf-8")


@pytest.mark.parametrize("argument", ("--json", "--unknown-platform-option"))
def test_010_ac1_inv004_env_report_entrypoint(argument: str) -> None:
    """010/AC-1, 010/INV-004: JSON và cờ lạ đi qua điểm vào (entrypoint) thật."""
    result = subprocess.run(
        [*COMMANDS["env-report"], argument], cwd=PROJECT_ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=45, check=False,
    )
    name = "json" if argument == "--json" else "unknown-option"
    _capture_cli(f"010-AC-1-env-report-{name}", result)
    if argument == "--json":
        assert result.returncode in {0, 1}, result.stderr
        report = json.loads(result.stdout)
        assert isinstance(report, dict) and report.get("schema_version")
    else:
        assert result.returncode == 2, result.stderr


def test_010_ac1_inv004_platform_guide_commands_and_markers() -> None:
    """010/AC-1, 010/INV-004: ba lệnh và sáu dấu năng lực khớp nguồn thật."""
    guide = _read(PROJECT_ROOT / "docs/guides" / PLATFORM_GUIDE)
    lines = _documented_commands(guide)
    assert lines == [
        "python -m mma_ai.compat.env_report",
        "python -m mma_ai.compat.env_report --json",
        "python -m pytest -q --capability-report capability.json",
    ]
    assert [_command_for_line(line) for line in lines] == ["env-report", "env-report", "pytest"]
    result = subprocess.run(
        [*COMMANDS["pytest"], "--help"], cwd=PROJECT_ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=45, check=False,
    )
    _capture_cli("010-AC-1-pytest-help", result)
    assert result.returncode == 0, result.stderr
    assert {"--capability-report", "--capability-max-ratio"} <= _flags(result.stdout)
    assert _flags(guide) <= _supported_flags("env-report") | _flags(result.stdout)
    source = _read(PROJECT_ROOT / "tests/unit/capability_gate.py")
    for marker in CAPABILITY_MARKERS:
        assert f"`{marker}`" in guide
        assert re.search(rf'^\s*"{marker}":', source, re.MULTILINE), marker
    assert "check_env.py" not in guide


def test_010_ac1_ac2_inv001_unreleased_platform_changes() -> None:
    """010/AC-1, 010/AC-2, 010/INV-001: thay đổi có truy vết và giới hạn kiểm chứng."""
    unreleased = _read(PROJECT_ROOT / "CHANGELOG.md").split(
        "## [Unreleased]\n", 1
    )[1].split("\n## ", 1)[0]
    assert "### Added" in unreleased and "### Changed" in unreleased
    for feature in (
        "006-cross-platform-support", "007-stabilize-viewer-tests",
        "008-project-docs", "009-git-history-capability",
    ):
        assert f"specs/{feature}/" in LINK_RE.findall(unreleased)
    source = _read(PROJECT_ROOT / "tests/unit/capability_gate.py")
    for marker in CAPABILITY_MARKERS:
        assert f"`{marker}`" in unreleased
        assert re.search(rf'^\s*"{marker}":', source, re.MULTILINE), marker
    assert not _documented_commands(unreleased)
    assert not re.search(r"^\s*```(?:sh|bash)\b", unreleased, re.MULTILINE)
    limits = [line for line in unreleased.splitlines() if "Windows" in line and "macOS" in line]
    assert any("CI" in line and re.search(r"chưa (?:được )?kiểm", line) for line in limits)


def test_010_ac2_inv001_platform_guide_verification_limits() -> None:
    """010/AC-2, 010/INV-001: hướng dẫn không suy ra nền tảng đã kiểm từ cấu hình."""
    guide = _read(PROJECT_ROOT / "docs/guides" / PLATFORM_GUIDE)
    limits = guide.split("## Giới hạn kiểm chứng", 1)[1]
    rows = dict(re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", limits, re.MULTILINE))
    assert "Đã kiểm" in rows["Linux"]
    for label in ("Windows 11", "WSL2", "macOS", "CUDA", "GitHub Actions"):
        matching = [value for key, value in rows.items() if label in key]
        assert len(matching) == 1, f"Thiếu dòng giới hạn {label}"
        assert "Chưa kiểm" in matching[0] and "Đã kiểm" not in matching[0]
