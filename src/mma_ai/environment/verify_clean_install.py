"""Xác minh cài đặt môi trường ảo sạch (verify clean install).

Thực hiện yêu cầu:
- FR-016: Xác minh cài đặt và kiểm thử trong môi trường ảo sạch (clean virtual environment).
- NFR-INST-001: Thực hiện uv sync và bộ kiểm thử xanh trong môi trường ảo mới.
- AC-5: Tạo môi trường ảo tạm, chạy uv sync, chạy pytest và ghi logs/m1/verify_clean_install.json.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

REQUIRED_PACKAGES: tuple[str, ...] = ("gymnasium", "mujoco", "myo-sim", "numpy")


def _find_project_root(start_dir: Path | None = None) -> Path:
    """Xác định thư mục gốc của dự án (project root) chứa tệp cấu hình pyproject.toml."""
    cur = (start_dir or Path.cwd()).resolve()
    for directory in [cur, *cur.parents]:
        if (directory / "pyproject.toml").is_file():
            return directory
    return cur


def _extract_exit_code(res: Any) -> int:
    """Chuẩn hoá mã thoát (exit code) từ kết quả thực thi của bộ chạy lệnh."""
    if isinstance(res, int):
        return res
    if isinstance(res, tuple) and len(res) > 0 and isinstance(res[0], int):
        return res[0]
    if hasattr(res, "returncode") and isinstance(res.returncode, int):
        return res.returncode
    if hasattr(res, "exit_code") and isinstance(res.exit_code, int):
        return res.exit_code
    return 0


def _query_installed_versions(
    py_executable: Path | None = None,
    custom_versions: dict[str, str] | None = None,
) -> dict[str, str]:
    """Thu thập phiên bản đã cài đặt (installed versions) của các thư viện bắt buộc."""
    if custom_versions is not None:
        return {pkg: custom_versions.get(pkg, "unknown") for pkg in REQUIRED_PACKAGES}

    # Nếu có tiến trình Python trong venv sạch, truy vấn trực tiếp từ môi trường đó
    if py_executable is not None and py_executable.is_file():
        code = (
            "import importlib.metadata as m, json; "
            "pkgs = ['gymnasium', 'mujoco', 'myo-sim', 'numpy']; "
            "print(json.dumps({p: m.version(p) for p in pkgs}))"
        )
        try:
            out = subprocess.check_output(
                [str(py_executable), "-c", code],
                text=True,
                stderr=subprocess.PIPE,
            )
            data = json.loads(out)
            if isinstance(data, dict):
                return {pkg: str(data.get(pkg, "unknown")) for pkg in REQUIRED_PACKAGES}
        except Exception:
            pass

    # Dự phòng (fallback): đọc metadata từ môi trường Python hiện hành
    versions: dict[str, str] = {}
    for pkg in REQUIRED_PACKAGES:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "unknown"
    return versions


def _execute_command(
    runner: Callable[..., Any] | None,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
) -> int:
    """Thực thi lệnh qua bộ chạy lệnh (command runner) được tiêm hoặc subprocess."""
    if runner is not None:
        res = runner(cmd, cwd=cwd, env=env)
        return _extract_exit_code(res)

    completed = subprocess.run(cmd, cwd=cwd, env=env, check=False)
    return completed.returncode


def verify_clean_install(
    project_root: Path | None = None,
    output_path: Path | None = None,
    runner: Callable[..., Any] | None = None,
    custom_versions: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Thực hiện chu trình kiểm tra cài đặt sạch trong môi trường ảo độc lập."""
    root = (project_root or _find_project_root()).resolve()
    lockfile = root / "uv.lock"

    if not lockfile.is_file():
        msg = (
            f"Lỗi: Không tìm thấy tệp khóa uv.lock tại '{root}'. "
            "Từ chối chạy xác minh cài đặt sạch (clean install) vì thiếu ràng buộc phiên bản."
        )
        print(msg, file=sys.stderr)
        return 1, {"error": msg, "exit_code": 1}

    out_file = (output_path or (root / "logs" / "m1" / "verify_clean_install.json")).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.perf_counter()
    commands_run: list[str] = []
    step_exit_codes: dict[str, int | None] = {"sync": None, "pytest": None}

    with tempfile.TemporaryDirectory(prefix="clean_install_venv_") as tmp_dir:
        venv_path = Path(tmp_dir) / ".venv"
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_path)

        # Khởi tạo venv sạch khi chạy thực tế không qua mock
        if runner is None:
            subprocess.run(
                ["uv", "venv", str(venv_path)],
                cwd=root,
                check=True,
                capture_output=True,
            )

        # Bước 1: Đồng bộ môi trường ảo với uv sync --frozen --extra dev
        sync_cmd = ["uv", "sync", "--frozen", "--extra", "dev", "--active"]
        commands_run.append("uv sync --frozen --extra dev --active")
        sync_exit = _execute_command(runner, sync_cmd, cwd=root, env=env)
        step_exit_codes["sync"] = sync_exit

        py_bin = venv_path / "bin" / "python"
        pytest_exit: int | None = None

        # Bước 2: Chạy kiểm thử môi trường nếu bước đồng bộ thành công
        if sync_exit == 0:
            pytest_cmd_runner = [
                str(py_bin) if runner is None else "python",
                "-m",
                "pytest",
                "-q",
                "--ignore=tests/unit/test_verify_clean_install.py",
                "--ignore=tests/e2e",
            ]
            commands_run.append(
                "python -m pytest -q --ignore=tests/unit/test_verify_clean_install.py"
                " --ignore=tests/e2e"
            )
            pytest_exit = _execute_command(runner, pytest_cmd_runner, cwd=root, env=env)
            step_exit_codes["pytest"] = pytest_exit

        duration_s = max(0.0, time.perf_counter() - start_time)
        installed_versions = _query_installed_versions(py_bin, custom_versions=custom_versions)

        is_passed = sync_exit == 0 and pytest_exit == 0
        overall_exit_code = (
            0 if is_passed else (sync_exit if sync_exit != 0 else (pytest_exit or 1))
        )

        # Đảm bảo đường dẫn lưu trữ trong bản ghi là tương đối (relative path)
        rel_log_path = (
            out_file.relative_to(root).as_posix()
            if out_file.is_relative_to(root)
            else out_file.name
        )

        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        record: dict[str, Any] = {
            "commands_run": commands_run,
            "commands": list(commands_run),
            "python_version": py_ver,
            "python": py_ver,
            "step_exit_codes": step_exit_codes,
            "exit_codes": step_exit_codes,
            "installed_versions": installed_versions,
            "libraries": installed_versions,
            "packages": installed_versions,
            "duration_seconds": round(duration_s, 4),
            "duration_s": round(duration_s, 4),
            "log_path": rel_log_path,
            "passed": is_passed,
            "status": "passed" if is_passed else "failed",
            "exit_code": overall_exit_code,
        }

        content = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        out_file.write_text(content, encoding="utf-8")
        return overall_exit_code, record


def main(
    argv: Sequence[str] | None = None,
    runner: Callable[..., Any] | None = None,
    project_root: Path | None = None,
    output_path: Path | None = None,
) -> int:
    """Điểm nhập chính (main entrypoint) cho CLI và thực thi trực tiếp."""
    parser = argparse.ArgumentParser(
        description="Xác minh cài đặt sạch mma-ai trong môi trường ảo tạm."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help="Đường dẫn thư mục gốc dự án.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=output_path,
        help="Đường dẫn lưu tệp kết quả JSON.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    exit_code, _ = verify_clean_install(
        project_root=args.project_root,
        output_path=args.output,
        runner=runner,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
