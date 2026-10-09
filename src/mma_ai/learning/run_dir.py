"""Tạo thư mục cô lập cho một lần chạy huấn luyện."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
        try:
            (path / "checkpoints").mkdir()
            (path / "tb").mkdir()
        except OSError as exc:
            raise RunDirError(f"Không thể tạo cấu trúc thư mục lần chạy {run_id}: {exc}") from exc
        return RunDir(run_id, path, path.relative_to(root))
    raise RunDirError(f"Không thể tạo thư mục lần chạy sau 100 lần va chạm: {base}")
