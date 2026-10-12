"""Tạo thư mục cô lập cho một lần chạy huấn luyện."""

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mma_ai.compat.capabilities import long_paths_enabled

from .errors import RunDirError


@dataclass(frozen=True)
class RunDir:
    """Định danh và đường dẫn tương đối của một lần chạy."""

    run_id: str
    path: Path
    relative_path: Path


def create_run_dir(runs_dir: str | Path, stage: str, seed: int) -> RunDir:
    """Tạo thư mục lần chạy bằng thao tác mkdir loại trừ, không ghi đè."""
    root = Path(runs_dir)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"{stamp}_{stage}_s{seed}"
    for attempt in range(101):
        run_id = base if attempt == 0 else f"{base}-{attempt + 1}"
        path = root / run_id
        try:
            path.mkdir()
        except FileExistsError:
            continue
        except OSError as exc:
            raise _run_dir_error(path, exc) from exc
        try:
            (path / "checkpoints").mkdir()
            (path / "tb").mkdir()
        except OSError as exc:
            shutil.rmtree(path, ignore_errors=True)
            raise _run_dir_error(path, exc) from exc
        return RunDir(run_id, path, path.relative_to(root))
    raise RunDirError(f"Không thể tạo thư mục lần chạy sau 100 lần va chạm: {base}")


def _run_dir_error(path: Path, error: OSError) -> RunDirError:
    shutil.rmtree(path, ignore_errors=True)
    length = len(str(path))
    hint = ""
    if length >= 260 and not long_paths_enabled().available:
        hint = " Hãy bật hỗ trợ đường dẫn dài của Windows hoặc rút ngắn thư mục gốc."
    return RunDirError(
        f"Không thể tạo thư mục lần chạy (đường dẫn dài {length} ký tự): {error}.{hint}"
    )
