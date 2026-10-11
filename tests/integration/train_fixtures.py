"""Fixture dùng chung cho kiểm thử tích hợp (train_fixtures.py).

Cung cấp các tiện ích phục vụ kiểm thử tích hợp (integration test) và kiểm thử hồi quy
cho quy trình huấn luyện học tăng cường (reinforcement learning - RL) PPO:
- smoke_config: ghi cấu hình chạy khói (smoke config) vào thư mục tạm.
- run_train_cli: thực thi CLI huấn luyện qua tiến trình con ở chế độ headless.
- load_manifest: nạp hồ sơ thí nghiệm (run manifest) từ thư mục lượt chạy.
- list_runs: liệt kê danh sách các thư mục lượt chạy.
- hash_tree: tính mã băm (hash digest) toàn bộ thư mục để kiểm tra tính bất biến (immutability).
- sample_observations: sinh lô quan sát mẫu cố định (fixed observation batch) tất định.
- load_schema_registry: nạp toàn bộ lược đồ hợp đồng (contract schemas) vào registry của jsonschema.

Hiện thực FR-019, phục vụ INV-001, INV-002, INV-005.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.resources
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import referencing
import yaml


class CliRunResult(subprocess.CompletedProcess[str]):
    """Kết quả thực thi dòng lệnh huấn luyện (CLI run result)."""

    @property
    def exit_code(self) -> int:
        """Bí danh (alias) cho mã thoát returncode."""
        return self.returncode


def smoke_config(tmp_path: Path | str, **overrides: Any) -> Path:
    """Ghi cấu hình smoke vào thư mục tạm.

    Mặc định: 4096 bước, every_updates 1, ui.mode none, runs_dir trỏ vào thư mục tạm.

    Tham số:
        tmp_path: Thư mục tạm (Path hoặc chuỗi đường dẫn).
        **overrides: Các tham số ghi đè (overrides) bổ sung.

    Trả về:
        Đường dẫn Path tới tệp cấu hình YAML vừa ghi.
    """
    tmp_dir = Path(tmp_path)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Nạp nội dung cấu hình smoke mẫu đóng gói sẵn
    resource = importlib.resources.files("mma_ai.learning").joinpath("train_elbow_smoke.yaml")
    data: dict[str, Any] = yaml.safe_load(resource.read_text(encoding="utf-8"))

    # Đảm bảo các giá trị mặc định của lượt chạy smoke
    data["schedule"]["total_timesteps"] = 4096
    data["checkpoint"]["every_updates"] = 1
    data["ui"]["mode"] = "none"

    # Chuẩn bị thư mục con runs_dir trong thư mục tạm
    runs_dir = tmp_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    try:
        rel_runs_dir = runs_dir.relative_to(Path.cwd()).as_posix()
    except ValueError:
        rel_runs_dir = os.path.relpath(runs_dir, Path.cwd())

    data["paths"]["runs_dir"] = rel_runs_dir

    # Bản đồ bí danh ngắn gọn cho các tham số ghi đè phổ biến
    alias_map: dict[str, tuple[str, str]] = {
        "total_timesteps": ("schedule", "total_timesteps"),
        "n_steps": ("schedule", "n_steps"),
        "batch_size": ("schedule", "batch_size"),
        "every_updates": ("checkpoint", "every_updates"),
        "runs_dir": ("paths", "runs_dir"),
        "mode": ("ui", "mode"),
    }

    # Áp dụng các giá trị ghi đè
    for key, value in overrides.items():
        if key in alias_map:
            group, subkey = alias_map[key]
            data[group][subkey] = value
        elif "." in key:
            parts = key.split(".")
            target = data
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
        elif key in data and isinstance(data[key], dict) and isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value

    config_path = tmp_dir / "train_smoke.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return config_path


def run_train_cli(
    args: Sequence[str] | str,
    env: Mapping[str, str] | None = None,
    timeout: float | None = 120.0,
) -> CliRunResult:
    """Chạy python -m mma_ai.learning.cli bằng subprocess thật.

    Loại bỏ biến môi trường DISPLAY và WAYLAND_DISPLAY để chạy ở chế độ headless.
    Trả về đối tượng CliRunResult chứa returncode, stdout, stderr và alias exit_code.
    """
    if isinstance(args, str):
        cmd_args = shlex.split(args)
    else:
        cmd_args = list(args)

    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    run_env.pop("DISPLAY", None)
    run_env.pop("WAYLAND_DISPLAY", None)

    cmd = [sys.executable, "-m", "mma_ai.learning.cli", *cmd_args]
    proc = subprocess.run(
        cmd,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(Path.cwd()),
    )
    return CliRunResult(
        args=proc.args,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def load_manifest(run_dir: Path | str) -> dict[str, Any]:
    """Nạp hồ sơ thí nghiệm manifest.json từ thư mục lượt chạy."""
    path = Path(run_dir)
    target_file = path if path.is_file() else path / "manifest.json"
    if not target_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy manifest tại: {target_file}")
    loaded = json.loads(target_file.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Dữ liệu manifest không phải từ điển hợp lệ: {target_file}")
    return copy.deepcopy(loaded)


def list_runs(runs_dir: Path | str) -> list[Path]:
    """Liệt kê các thư mục lượt chạy bên trong runs_dir, sắp xếp theo tên."""
    root = Path(runs_dir)
    if not root.exists() or not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def hash_tree(path: Path | str) -> str:
    """Băm toàn bộ cấu trúc và nội dung thư mục (SHA-256) để so sánh tính bất biến."""
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"Đường dẫn không tồn tại: {path}")
    if root.is_file():
        hasher = hashlib.sha256()
        hasher.update(root.read_bytes())
        return hasher.hexdigest()

    hasher = hashlib.sha256()
    all_files = sorted(p for p in root.rglob("*") if p.is_file())
    for file_path in all_files:
        rel_path = file_path.relative_to(root).as_posix()
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def sample_observations(n: int = 64) -> np.ndarray:
    """Tạo lô quan sát mẫu cố định (n, 14) tất định bằng seed cố định."""
    rng = np.random.default_rng(seed=42)
    return rng.normal(loc=0.0, scale=1.0, size=(n, 14)).astype(np.float64)


def load_schema_registry() -> referencing.Registry:
    """Nạp mọi schema trong specs/003-ppo-train-repro/contracts/ vào một registry jsonschema."""
    candidate_paths = [
        Path.cwd() / "specs/003-ppo-train-repro/contracts",
        Path(__file__).resolve().parents[2] / "specs/003-ppo-train-repro/contracts",
    ]
    contracts_dir: Path | None = None
    for cand in candidate_paths:
        if cand.is_dir():
            contracts_dir = cand
            break

    if contracts_dir is None:
        err_msg = "Không tìm thấy thư mục hợp đồng specs/003-ppo-train-repro/contracts"
        raise FileNotFoundError(err_msg)

    registry: referencing.Registry = referencing.Registry()
    for schema_file in sorted(contracts_dir.glob("*.schema.json")):
        content = json.loads(schema_file.read_text(encoding="utf-8"))
        resource = referencing.Resource.from_contents(content)
        registry = registry.with_resource(schema_file.name, resource)
        if isinstance(content, dict) and "$id" in content and isinstance(content["$id"], str):
            registry = registry.with_resource(content["$id"], resource)

    return registry


__all__ = [
    "CliRunResult",
    "hash_tree",
    "list_runs",
    "load_manifest",
    "load_schema_registry",
    "run_train_cli",
    "sample_observations",
    "smoke_config",
]
