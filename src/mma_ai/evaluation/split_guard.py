"""Mô-đun bảo vệ ranh giới phân tách dữ liệu huấn luyện và đánh giá (split guard).

Hiện thực API-EVL-0003 theo các yêu cầu miền và bất biến:
- FR-008: Kiểm tra tập đánh giá không giao tập huấn luyện (giao rỗng và khoảng cách).
- FR-009: Từ chối đánh giá khi không thiết lập được tập huấn luyện (TrainSetUnknown).
- INV-001: Bảo vệ bất biến tập đánh giá không bao giờ giao tập huấn luyện.
- AC-4: Đảm bảo kiểm tra rò rỉ (leakage) trước khi chạy bất kỳ episode đánh giá nào.
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.targets import TargetGenerator, TargetSetPair
from mma_ai.evaluation.errors import LeakageError, TrainSetUnknown
from mma_ai.evaluation.eval_config import EvalConfig


@dataclass(frozen=True)
class DisjointnessReport:
    """Báo cáo kiểm tra tính không giao cắt giữa tập đánh giá và tập train.

    Hiện thực các hợp đồng API-EVL-0003 và bất biến INV-001.
    """

    checked: bool
    passed: bool
    train_target_provenance: str
    target_fingerprint_sha256: str
    n_train_targets: int
    n_eval_targets: int
    min_cross_distance_m: float
    min_required_m: float
    eval_seed_range: tuple[int, int]
    random_policy_seed: int
    train_seeds: tuple[int, ...]
    n_checked: int

    @property
    def provenance(self) -> str:
        """Thuộc tính truy cập nguồn gốc tập mục tiêu (provenance) tương thích ngược."""
        return self.train_target_provenance

    def to_dict(self) -> dict[str, Any]:
        """Xuất từ điển hợp đồng theo eval-report.schema.json."""
        return {
            "checked": self.checked,
            "passed": self.passed,
            "train_target_provenance": self.train_target_provenance,
            "target_fingerprint_sha256": self.target_fingerprint_sha256,
            "n_train_targets": self.n_train_targets,
            "n_eval_targets": self.n_eval_targets,
            "min_cross_distance_m": round(float(self.min_cross_distance_m), 6),
            "min_required_m": round(float(self.min_required_m), 6),
            "eval_seed_range": [int(self.eval_seed_range[0]), int(self.eval_seed_range[1])],
            "random_policy_seed": self.random_policy_seed,
            "train_seeds": list(self.train_seeds),
        }


def _load_manifest_record(
    run: str | Path | Mapping[str, Any],
    runs_dir: str,
) -> tuple[dict[str, Any], Path | None]:
    """Đọc hồ sơ manifest.json từ tham số run theo cơ chế chỉ-đọc (INV-005, FR-009)."""
    if isinstance(run, Mapping):
        return dict(run), None

    run_path = Path(run)
    run_dir: Path | None = None
    manifest_file: Path | None = None

    if run_path.is_file():
        manifest_file = run_path
        run_dir = run_path.parent
    elif run_path.is_dir():
        manifest_file = run_path / "manifest.json"
        run_dir = run_path
    else:
        # Thử tìm kiếm tương đối trong thư mục runs_dir
        candidate = Path(runs_dir) / run_path
        if candidate.is_dir():
            manifest_file = candidate / "manifest.json"
            run_dir = candidate
        elif candidate.is_file():
            manifest_file = candidate
            run_dir = candidate.parent
        else:
            raise TrainSetUnknown(
                f"Không tìm thấy hồ sơ run tại '{run}': tệp manifest.json không tồn tại."
            )

    if not manifest_file.is_file():
        raise TrainSetUnknown(
            f"Không tìm thấy tệp manifest.json tại: {manifest_file}"
        )

    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as err:
        raise TrainSetUnknown(
            f"Không thể đọc hồ sơ manifest.json tại '{manifest_file}': {err}"
        ) from err

    if not isinstance(data, dict):
        raise TrainSetUnknown(
            f"Nội dung hồ sơ manifest.json tại '{manifest_file}' không hợp lệ (không phải mapping)."
        )

    return data, run_dir


def _collect_train_seeds(
    manifest_data: dict[str, Any],
    run_dir: Path | None,
    runs_dir: str,
) -> list[int]:
    """Thu thập toàn bộ hạt giống huấn luyện dọc theo chuỗi resumed_from (FR-008, INV-001)."""
    seed = manifest_data.get("seed")
    if seed is None or not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise TrainSetUnknown(f"Hồ sơ run thiếu seed huấn luyện hợp lệ: {seed}")

    train_seeds: list[int] = [seed]
    curr_manifest = manifest_data
    depth = 0

    while curr_manifest.get("resumed_from") is not None and depth < 100:
        depth += 1
        resumed = curr_manifest["resumed_from"]
        if not isinstance(resumed, dict):
            break

        parent_run_id = resumed.get("run_id")
        if not parent_run_id or not isinstance(parent_run_id, str):
            raise TrainSetUnknown("Hồ sơ resumed_from thiếu run_id của run cha.")

        candidates: list[Path] = []
        if run_dir is not None:
            candidates.append(run_dir.parent / parent_run_id / "manifest.json")
        candidates.append(Path(runs_dir) / parent_run_id / "manifest.json")
        candidates.append(Path(parent_run_id) / "manifest.json")

        parent_file: Path | None = None
        for c in candidates:
            if c.is_file():
                parent_file = c
                break

        if parent_file is None:
            raise TrainSetUnknown(
                f"Không tìm thấy hồ sơ run cha '{parent_run_id}' trong chuỗi resumed_from."
            )

        try:
            parent_manifest = json.loads(parent_file.read_text(encoding="utf-8"))
        except Exception as err:
            raise TrainSetUnknown(
                f"Không thể đọc hồ sơ run cha tại '{parent_file}': {err}"
            ) from err

        parent_seed = parent_manifest.get("seed")
        if (
            parent_seed is None
            or not isinstance(parent_seed, int)
            or isinstance(parent_seed, bool)
            or parent_seed < 0
        ):
            raise TrainSetUnknown(
                f"Hồ sơ run cha '{parent_run_id}' thiếu seed huấn luyện hợp lệ."
            )

        if parent_seed not in train_seeds:
            train_seeds.append(parent_seed)

        curr_manifest = parent_manifest

    return train_seeds


def _resolve_target_set_pair(
    manifest_data: dict[str, Any],
    cfg: EvalConfig,
    pair: TargetSetPair | None,
    run_dir: Path | None,
) -> tuple[TargetSetPair, float, str]:
    """Xác định hoặc tái dựng cặp tập mục tiêu TargetSetPair và nguồn gốc (FR-008, FR-009)."""
    if pair is not None:
        eval_pair = pair
        min_required_m = float(eval_pair.config.get("min_separation_m", 0.03))
    else:
        # Lấy đường dẫn cấu hình môi trường từ ghi đè hoặc hồ sơ run
        if cfg.paths.env_config_override:
            env_cfg_path_str = cfg.paths.env_config_override
        else:
            env_cfg_path_str = manifest_data.get("config", {}).get("env_config")
            if not env_cfg_path_str:
                raise TrainSetUnknown(
                    "Hồ sơ run thiếu cấu hình môi trường (config.env_config) và không có pair."
                )

        candidate_paths: list[Path] = [Path(env_cfg_path_str)]
        if run_dir is not None:
            candidate_paths.append(run_dir / env_cfg_path_str)

        resolved_path: Path | None = None
        for cand in candidate_paths:
            if cand.is_file():
                resolved_path = cand
                break

        if resolved_path is None:
            raise TrainSetUnknown(
                f"Không tìm thấy tệp cấu hình môi trường tại '{env_cfg_path_str}'."
            )

        try:
            loaded_env = ElbowEnvConfig.load(resolved_path)
        except Exception as err:
            raise TrainSetUnknown(
                f"Không thể nạp cấu hình môi trường từ '{resolved_path}': {err}"
            ) from err

        from mma_ai.physics.body_model import load_muscle_model

        try:
            loaded_body = load_muscle_model("myoelbow")
            model_obj = loaded_body.model
        except Exception as err:
            raise TrainSetUnknown(
                f"Không thể nạp mô hình cơ bắp myoelbow: {err}"
            ) from err

        model_sha256 = manifest_data.get("model", {}).get("sha256")
        if model_sha256 and model_sha256 != loaded_body.info.sha256:
            raise LeakageError(
                f"Mã băm XML của mô hình ({loaded_body.info.sha256}) không khớp "
                f"với hồ sơ run ({model_sha256}) (INV-002)."
            )

        gen = TargetGenerator(model=model_obj, cfg=loaded_env, model_sha256=model_sha256)
        eval_pair = gen.generate(seed=loaded_env.targets.default_seed)
        min_required_m = float(loaded_env.targets.min_separation_m)

    # Xác định nguồn gốc và đối chiếu mã băm fingerprint
    manifest_fp = (
        manifest_data.get("target_fingerprint_sha256")
        or manifest_data.get("env", {}).get("target_fingerprint_sha256")
    )
    if manifest_fp:
        if manifest_fp != eval_pair.fingerprint_sha256:
            raise LeakageError(
                f"Mã băm fingerprint của tập mục tiêu ({eval_pair.fingerprint_sha256}) "
                f"không khớp với fingerprint trong hồ sơ run ({manifest_fp})."
            )
        provenance = "manifest_fingerprint"
    else:
        provenance = "rebuilt_from_config"
        warnings.warn(
            "Hồ sơ run không chứa target_fingerprint_sha256; tập mục tiêu được dựng lại.",
            UserWarning,
            stacklevel=2,
        )

    # Kiểm tra ràng buộc ghim expect_fingerprint_sha256
    if cfg.paths.expect_fingerprint_sha256 is not None:
        if cfg.paths.expect_fingerprint_sha256 != eval_pair.fingerprint_sha256:
            raise LeakageError(
                f"Mã băm fingerprint của tập mục tiêu ({eval_pair.fingerprint_sha256}) "
                f"không khớp với expect_fingerprint_sha256 ({cfg.paths.expect_fingerprint_sha256})."
            )

    return eval_pair, min_required_m, provenance


def _check_target_disjointness(
    eval_pair: TargetSetPair,
    min_required_m: float,
) -> tuple[float, int]:
    """Kiểm tra giao rỗng và khoảng cách tối thiểu giữa tập train và tập test (FR-008, INV-001)."""
    train_targets = eval_pair.train
    test_targets = eval_pair.test

    min_dist = float("inf")
    n_checked = 0

    for t_eval in test_targets:
        pos_e = t_eval.position_m
        for t_train in train_targets:
            n_checked += 1
            pos_t = t_train.position_m
            dx = pos_e[0] - pos_t[0]
            dy = pos_e[1] - pos_t[1]
            dz = pos_e[2] - pos_t[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist < min_dist:
                min_dist = dist

            if dist < (min_required_m - 1e-9):
                raise LeakageError(
                    f"Mục tiêu kiểm thử vi phạm khoảng cách tối thiểu với tập train: "
                    f"test #{t_eval.index} và train #{t_train.index} cách nhau {dist:.6f}m "
                    f"< ngưỡng yêu cầu {min_required_m:.6f}m."
                )

    return min_dist, n_checked


def _check_seed_disjointness(
    cfg: EvalConfig,
    train_seeds: list[int],
    n_eval_targets: int,
) -> tuple[int, int]:
    """Kiểm tra tính không giao cắt giữa dải seed episode và train seeds (FR-008, INV-001)."""
    train_seed_set = set(train_seeds)

    # 1. Kiểm tra seed của random policy
    rand_seed = cfg.seeds.random_policy
    if rand_seed in train_seed_set:
        raise LeakageError(
            f"Seed của random policy ({rand_seed}) trùng với seed train ({train_seeds})."
        )

    # 2. Kiểm tra dải hạt giống episode
    ep_base = cfg.seeds.episode_base
    n_episodes = n_eval_targets * cfg.episodes.repeats
    ep_end = ep_base + n_episodes
    eval_seed_set = set(range(ep_base, ep_end))

    overlap = eval_seed_set & train_seed_set
    if overlap:
        sorted_overlap = sorted(overlap)
        raise LeakageError(
            f"Dải seed đánh giá [{ep_base}, {ep_end}) giao với seed huấn luyện của run "
            f"tại seed: {sorted_overlap}."
        )

    return ep_base, ep_end


def check_disjoint(
    run: str | Path | dict[str, Any],
    cfg: EvalConfig,
    pair: TargetSetPair | None = None,
) -> DisjointnessReport:
    """Kiểm tra tính không giao cắt giữa tập đánh giá và tập huấn luyện (API-EVL-0003).

    Bảo vệ các bất biến INV-001:
    - Hồ sơ run được đọc chỉ-đọc (INV-005).
    - Tập mục tiêu đánh giá và tập mục tiêu huấn luyện có giao rỗng và cách nhau >= min_required_m.
    - Hạt giống đánh giá (episode_base...episode_base + n) và random_policy không giao train seeds.
    - Không thiết lập được tập huấn luyện/seed thì từ chối (TrainSetUnknown, FR-009).
    """
    # 1. Đọc hồ sơ run (chỉ-đọc)
    manifest_data, run_dir = _load_manifest_record(run, cfg.paths.runs_dir)

    # 2. Thu thập toàn bộ hạt giống của run và các run cha (resumed_from)
    train_seeds = _collect_train_seeds(manifest_data, run_dir, cfg.paths.runs_dir)

    # 3. Tái dựng hoặc nhận cặp tập mục tiêu
    eval_pair, min_required_m, provenance = _resolve_target_set_pair(
        manifest_data, cfg, pair, run_dir
    )

    # 4. Kiểm tra giao rỗng mục tiêu và khoảng cách chéo tối thiểu
    min_cross_dist, n_checked = _check_target_disjointness(eval_pair, min_required_m)

    # 5. Kiểm tra phân tách hạt giống ngẫu nhiên (seeds)
    ep_base, ep_end = _check_seed_disjointness(cfg, train_seeds, len(eval_pair.test))

    return DisjointnessReport(
        checked=True,
        passed=True,
        train_target_provenance=provenance,
        target_fingerprint_sha256=eval_pair.fingerprint_sha256,
        n_train_targets=len(eval_pair.train),
        n_eval_targets=len(eval_pair.test),
        min_cross_distance_m=min_cross_dist,
        min_required_m=min_required_m,
        eval_seed_range=(ep_base, ep_end),
        random_policy_seed=cfg.seeds.random_policy,
        train_seeds=tuple(train_seeds),
        n_checked=n_checked,
    )


__all__: list[str] = [
    "DisjointnessReport",
    "check_disjoint",
]
