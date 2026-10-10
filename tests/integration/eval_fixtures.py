"""Fixture dùng chung cho kiểm thử tích hợp đánh giá (eval_fixtures.py).

Cung cấp các tiện ích phục vụ kiểm thử tích hợp (integration test) và kiểm thử chấp nhận
(acceptance test) cho quy trình đánh giá chính sách và so sánh đối chuẩn:
- make_run_dir: dựng thư mục lượt chạy mẫu (sample run directory) bằng giao diện lập trình
  ứng dụng (application programming interface - API) công khai của phân hệ huấn luyện 003.
- run_cli: thực thi giao diện dòng lệnh (command line interface - CLI) mma_ai.evaluation.cli
  qua tiến trình con (subprocess) ở chế độ không màn hình (headless mode).
- hash_tree: tính mã băm (hash digest) SHA-256 toàn bộ thư mục để kiểm tra tính bất biến
  (immutability).
- scripted_policy: tạo chính sách kịch bản mẫu (scripted policy) với giao diện act.

Hiện thực FR-020, FR-013; phục vụ INV-001, INV-003, INV-004, INV-005, NFR-HEADLESS-001.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from mma_ai.evaluation.policies import BasePolicy
from mma_ai.learning.manifest import build_manifest, write_manifest
from mma_ai.learning.metrics_log import build_metrics_record

# Mã băm SHA-256 chuẩn của mô hình khớp khuỷu tay 1 bậc tự do 6 cơ
_DEFAULT_MODEL_SHA256 = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"

# Danh sách 6 cơ bắp chuẩn của mô hình khuỷu tay
_DEFAULT_MUSCLE_NAMES: tuple[str, ...] = (
    "BIClong",
    "BICshort",
    "BRA",
    "TRIlong",
    "TRIlat",
    "TRImed",
)


class CliRunResult(tuple[int, str, str]):
    """Kết quả thực thi dòng lệnh đánh giá (CLI run result).

    Kế thừa bộ 3 phần tử (tuple) giúp hỗ trợ giải nén trực tiếp (unpacking)
    đồng thời cung cấp các thuộc tính truy cập returncode, exit_code, stdout, stderr.
    """

    def __new__(cls, returncode: int, stdout: str, stderr: str) -> CliRunResult:
        return super().__new__(cls, (returncode, stdout, stderr))

    @property
    def returncode(self) -> int:
        """Mã thoát của tiến trình con (returncode)."""
        return self[0]

    @property
    def exit_code(self) -> int:
        """Bí danh (alias) cho mã thoát returncode."""
        return self[0]

    @property
    def stdout(self) -> str:
        """Đầu ra tiêu chuẩn (standard output) của tiến trình."""
        return self[1]

    @property
    def stderr(self) -> str:
        """Đầu ra lỗi tiêu chuẩn (standard error) của tiến trình."""
        return self[2]


def _create_checkpoint(run_dir: Path, seed: int) -> Path:
    """Tạo tệp điểm kiểm tra (checkpoint) hợp chuẩn bằng API công khai hoặc cấu trúc tương đương."""
    try:
        import torch

        from mma_ai.learning.checkpoint import save_checkpoint
        from mma_ai.learning.networks import ActorCritic
        from mma_ai.learning.normalizer import RunningNorm
        from mma_ai.learning.train_config import TrainConfig

        class _DummyAgent:
            def __init__(self, cfg: TrainConfig) -> None:
                self.cfg = cfg
                self.model = ActorCritic(obs_dim=14, act_dim=6, cfg=cfg)
                self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

            def state_dict(self) -> dict[str, Any]:
                return {
                    "actor": self.model.actor.state_dict(),
                    "critic": self.model.critic.state_dict(),
                    "log_std": self.model.log_std.detach().clone(),
                    "optimizer": self.optimizer.state_dict(),
                }

        cfg = TrainConfig.load()
        agent = _DummyAgent(cfg)
        norm = RunningNorm()
        norm.update(np.ones((4, 14), dtype=np.float64))
        ctx = {
            "update_idx": 1,
            "env_steps": 2048,
            "model_sha256": _DEFAULT_MODEL_SHA256,
            "seed": seed,
            "obs_normalizer": norm,
        }
        meta = save_checkpoint(agent, run_dir, kind="periodic", ctx=ctx)
        return run_dir / meta.path
    except ImportError:
        # Cơ chế dự phòng (fallback) tạo cấu trúc checkpoint giả lập khi thiếu thư viện torch
        checkpoints_dir = run_dir / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        pt_file = checkpoints_dir / "ckpt_u000001.pt"
        pt_file.write_bytes(b"MMA_AI_DUMMY_CHECKPOINT_INITIALIZED_NETWORK_DATA")
        pt_sha256 = hashlib.sha256(pt_file.read_bytes()).hexdigest()
        now_utc = datetime.now(timezone.utc).isoformat()
        meta_dict = {
            "schema_version": "1.0.0",
            "path": f"checkpoints/{pt_file.name}",
            "kind": "periodic",
            "update_idx": 1,
            "env_steps": 2048,
            "sha256": pt_sha256,
            "created_utc": now_utc,
            "model_sha256": _DEFAULT_MODEL_SHA256,
            "components": ["actor", "critic", "obs_normalizer", "optimizer", "seed", "rng_state"],
            "library_versions": {},
            "finite": True,
        }
        (checkpoints_dir / f"{pt_file.stem}.meta.json").write_text(
            json.dumps(meta_dict, indent=2), encoding="utf-8"
        )
        (checkpoints_dir / "latest.json").write_text(
            json.dumps(meta_dict, indent=2), encoding="utf-8"
        )
        return pt_file


def make_run_dir(
    tmp_path: Path | str,
    *,
    status: str = "done",
    with_log: bool = True,
    drop_series: Sequence[str] = (),
    seed: int = 42,
    resumed_from: dict[str, Any] | None = None,
) -> Path:
    """Dựng thư mục run mẫu bằng API công khai của 003 (FR-020, FR-013).

    Bao gồm tệp điểm kiểm tra (checkpoint), hồ sơ thí nghiệm (manifest.json)
    và nhật ký huấn luyện (metrics.jsonl) chứa đầy đủ các nhóm chỉ số yêu cầu.

    Tham số:
        tmp_path: Thư mục tạm hoặc đường dẫn thư mục run cần tạo.
        status: Trạng thái của phiên chạy (mặc định 'done').
        with_log: Có tạo nhật ký metrics.jsonl hay không (mặc định True).
        drop_series: Danh sách tên chuỗi hoặc tiền tố thẻ cần loại bỏ khỏi nhật ký.
        seed: Hạt giống ngẫu nhiên của phiên huấn luyện (mặc định 42).
        resumed_from: Thông tin phiên chạy gốc khi huấn luyện tiếp nối (nếu có).

    Trả về:
        Path: Đường dẫn tới thư mục run vừa khởi tạo.
    """
    tmp = Path(tmp_path)
    run_id = f"20261011T000000Z_elbow_s{seed}"
    if tmp.name.startswith("2026") or tmp.name.startswith("run_"):
        run_dir = tmp
        run_id = tmp.name
    else:
        run_dir = tmp / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tạo tệp điểm kiểm tra checkpoint
    _create_checkpoint(run_dir, seed=seed)

    # 2. Tạo hồ sơ thí nghiệm manifest.json qua API công khai của 003
    manifest_payload = build_manifest(
        run_id=run_id,
        config={"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        seed=seed,
        status=status,
        resumed_from=resumed_from,
        model={
            "sha256": _DEFAULT_MODEL_SHA256,
            "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
            "muscle_names": list(_DEFAULT_MUSCLE_NAMES),
        },
    )
    write_manifest(run_dir, manifest_payload)

    # 3. Tạo nhật ký huấn luyện metrics.jsonl nếu được yêu cầu
    if with_log:
        records: list[dict[str, Any]] = []
        for i, step in enumerate([100, 200, 300], start=1):
            rec = build_metrics_record(
                update=i,
                env_steps=step,
                policy_loss=0.5 / i,
                value_loss=0.2 / i,
                entropy=0.1 / i,
                mean_return=10.0 * i,
                activations=[0.1 * i] * 6,
                env_steps_per_second=100.0,
                muscle_names=_DEFAULT_MUSCLE_NAMES,
            )
            # Thêm trường tương thích step cho các tầng đọc cũ
            rec["step"] = step

            # Lọc bỏ các chuỗi chỉ định trong drop_series
            if drop_series:
                filtered_rec: dict[str, Any] = {}
                for k, v in rec.items():
                    if k in ("update", "env_steps", "step"):
                        filtered_rec[k] = v
                        continue
                    should_drop = any(
                        k == ds or k.startswith(ds) or (ds in k) for ds in drop_series
                    )
                    if not should_drop:
                        filtered_rec[k] = v
                rec = filtered_rec
            records.append(rec)

        metrics_file = run_dir / "metrics.jsonl"
        with metrics_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return run_dir


def run_cli(
    args: Sequence[str] | str,
    env_overrides: Mapping[str, str] | None = None,
    timeout: float | None = 120.0,
) -> CliRunResult:
    """Chạy python -m mma_ai.evaluation.cli bằng subprocess không màn hình (headless mode).

    Thực hiện theo FR-020, NFR-HEADLESS-001: loại bỏ triệt để biến DISPLAY và WAYLAND_DISPLAY.

    Tham số:
        args: Chuỗi hoặc danh sách các đối số dòng lệnh truyền vào CLI.
        env_overrides: Từ điển biến môi trường bổ sung hoặc ghi đè (nếu có).
        timeout: Thời gian chờ tối đa bằng giây trước khi hết giờ (mặc định 120.0).

    Trả về:
        CliRunResult: Đối tượng chứa bộ ba (returncode, stdout, stderr).
    """
    if isinstance(args, str):
        cmd_args = shlex.split(args)
    else:
        cmd_args = list(args)

    run_env = os.environ.copy()
    if env_overrides is not None:
        run_env.update(env_overrides)
    run_env.pop("DISPLAY", None)
    run_env.pop("WAYLAND_DISPLAY", None)

    cmd = [sys.executable, "-m", "mma_ai.evaluation.cli", *cmd_args]
    proc = subprocess.run(
        cmd,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(Path.cwd()),
    )
    return CliRunResult(proc.returncode, proc.stdout, proc.stderr)


def hash_tree(path: Path | str) -> str:
    """Băm toàn bộ cấu trúc và nội dung thư mục bằng SHA-256 để so sánh tính bất biến (INV-005).

    Tham số:
        path: Đường dẫn thư mục hoặc tệp cần tính mã băm.

    Trả về:
        str: Chuỗi mã băm lục thập phân (hexadecimal digest) 64 ký tự.
    """
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


class ScriptedZeroPolicy(BasePolicy):
    """Chính sách kịch bản phát tín hiệu 0 cho toàn bộ các cơ (INV-003)."""

    def __init__(self, act_dim: int = 6) -> None:
        self.act_dim = act_dim

    def act(self, obs_raw: Any = None) -> np.ndarray:
        """Trả về mảng hành động toàn giá trị 0 kích thước (act_dim,)."""
        return np.zeros(self.act_dim, dtype=np.float32)


class ScriptedConstantPolicy(BasePolicy):
    """Chính sách kịch bản phát tín hiệu hằng số cho toàn bộ các cơ (INV-003)."""

    def __init__(self, value: float = 0.5, act_dim: int = 6) -> None:
        self.value = float(value)
        self.act_dim = act_dim

    def act(self, obs_raw: Any = None) -> np.ndarray:
        """Trả về mảng hành động toàn giá trị hằng số kích thước (act_dim,)."""
        return np.full(self.act_dim, self.value, dtype=np.float32)


def scripted_policy(kind: str = "zero", **kwargs: Any) -> BasePolicy:
    """Khởi tạo chính sách kịch bản mẫu (scripted policy) có giao diện act (FR-020, INV-003).

    Hỗ trợ kind:
    - 'zero': hành động kích thích cơ u = 0.0 cho mọi cơ.
    - 'constant': hành động kích thích cơ u = const (mặc định 0.5) cho mọi cơ.

    Tham số:
        kind: Loại chính sách ('zero' hoặc 'constant').
        **kwargs: Tham số bổ sung như value cho 'constant' hoặc act_dim.

    Trả về:
        BasePolicy: Đối tượng chính sách có phương thức act(obs_raw) -> np.ndarray.
    """
    kind_lower = kind.lower().strip()
    act_dim = int(kwargs.get("act_dim", 6))
    if kind_lower == "zero":
        return ScriptedZeroPolicy(act_dim=act_dim)
    if kind_lower == "constant":
        value = float(kwargs.get("value", 0.5))
        return ScriptedConstantPolicy(value=value, act_dim=act_dim)
    raise ValueError(
        f"Loại chính sách kịch bản không hợp lệ: '{kind}'. Kỳ vọng 'zero' hoặc 'constant'."
    )


__all__: list[str] = [
    "CliRunResult",
    "ScriptedConstantPolicy",
    "ScriptedZeroPolicy",
    "hash_tree",
    "make_run_dir",
    "run_cli",
    "scripted_policy",
]
