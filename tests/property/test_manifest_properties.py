"""Kiểm thử thuộc tính và bất biến cho hồ sơ run manifest (INV-001, FR-011...FR-014)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, cast

import pytest
import referencing
from jsonschema import Draft202012Validator, FormatChecker


def _load_schema(name: str) -> dict[str, Any]:
    path = (
        Path(__file__).parents[2]
        / f"specs/003-ppo-train-repro/contracts/{name}"
    )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _get_validator() -> Draft202012Validator:
    manifest_schema = _load_schema("run-manifest.schema.json")
    checkpoint_schema = _load_schema("checkpoint-meta.schema.json")

    resource = referencing.Resource.from_contents(checkpoint_schema)
    registry = referencing.Registry().with_resource("checkpoint-meta.schema.json", resource)

    return Draft202012Validator(
        manifest_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def setup_module() -> None:
    """Dọn dẹp triệt để không gian tên mma_ai.learning trước khi kiểm thử."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)



def _base_config(seed: int, head_updates: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "elbow",
        "seed": seed,
        "reproducibility": {
            "rel_tolerance": 1e-6,
            "head_updates": head_updates,
            "torch_threads": 1,
            "deterministic_algorithms": True,
        },
        "ui": {
            "mode": "none",
            "url": None,
            "view3d": False,
        },
    }


def _model() -> dict[str, Any]:
    return {
        "sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
        "muscle_names": ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
    }


def test_inv_001_finished_run_cannot_be_overwritten_property(tmp_path: Path) -> None:
    """INV-001: 50 lần thử ngẫu nhiên xác nhận run đã kết thúc không bao giờ bị ghi đè."""
    from mma_ai.learning.errors import RunDirError
    from mma_ai.learning.manifest import build_manifest, write_manifest

    rng = random.Random(20261010)
    finished_statuses = ["done", "error", "interrupted"]

    for i in range(50):
        run_dir = tmp_path / f"run_prop_{i}"
        run_dir.mkdir()
        status = rng.choice(finished_statuses)
        seed = rng.randint(0, 10000)
        run_id = f"20261010T080000Z_elbow_s{seed}-{i}"

        error_payload = (
            {"kind": "other", "message": "lỗi thử nghiệm", "update_idx": 1}
            if status == "error"
            else None
        )

        manifest = build_manifest(
            run_id=run_id,
            config=_base_config(seed, 10),
            seed=seed,
            model=_model(),
            status=status,
            error=error_payload,
        )
        write_manifest(run_dir, manifest)

        # Cố gắng ghi đè lại bất kỳ trạng thái nào đều phải thất bại với RunDirError
        overwrite_manifest = build_manifest(
            run_id=run_id,
            config=_base_config(seed, 10),
            seed=seed,
            model=_model(),
            status=rng.choice(["running", "done", "error", "interrupted"]),
        )
        with pytest.raises(RunDirError, match="INV-001"):
            write_manifest(run_dir, overwrite_manifest)


def test_inv_004_nonfinite_rejected_property(tmp_path: Path) -> None:
    """INV-004, NFR-REL-001: 50 giá trị không hữu hạn ngẫu nhiên luôn bị từ chối."""
    from mma_ai.learning.errors import NonFiniteError
    from mma_ai.learning.manifest import build_manifest

    rng = random.Random(20261011)
    nonfinite_values = [float("nan"), float("inf"), float("-inf")]

    for i in range(50):
        val = rng.choice(nonfinite_values)
        field_choice = rng.randint(0, 2)

        reward_metrics = {
            "n_updates": 1,
            "n_episodes": 1,
            "head_updates": 1,
            "head_mean_return": [val] if field_choice == 0 else [1.0],
            "first_mean_return": val if field_choice == 1 else 1.0,
            "last_mean_return": val if field_choice == 2 else 1.0,
            "success_rate": 0.5,
        }

        with pytest.raises(NonFiniteError):
            build_manifest(
                run_id="20261010T080000Z_elbow_s42",
                config=_base_config(42, 10),
                seed=42,
                model=_model(),
                reward_metrics=reward_metrics,
            )


def test_manifest_schema_property() -> None:
    """FR-011...FR-014: 50 cấu hình ngẫu nhiên sinh hồ sơ luôn hợp lệ schema."""
    from mma_ai.learning.manifest import build_manifest

    validator = _get_validator()
    rng = random.Random(20261012)

    for i in range(50):
        seed = rng.randint(0, 100000)
        n_updates = rng.randint(0, 30)
        head_updates = rng.randint(1, 15)
        k = min(head_updates, n_updates)

        returns = [rng.uniform(-100.0, 100.0) for _ in range(n_updates)]

        manifest = build_manifest(
            run_id=f"20261010T080000Z_elbow_s{seed}",
            config=_base_config(seed, head_updates),
            seed=seed,
            model=_model(),
            status="done",
            reward_metrics={
                "n_updates": n_updates,
                "n_episodes": n_updates * 10,
                "head_mean_return": returns,
                "success_rate": rng.uniform(0.0, 1.0) if n_updates > 0 else None,
            },
            throughput={
                "env_steps": n_updates * 2048,
                "env_steps_per_second": rng.uniform(100.0, 5000.0) if n_updates > 0 else None,
                "wall_clock_seconds": rng.uniform(1.0, 100.0) if n_updates > 0 else None,
            },
        )

        assert manifest["reward_metrics"]["head_updates"] == k
        assert len(manifest["reward_metrics"]["head_mean_return"]) == k
        validator.validate(manifest)


def teardown_module() -> None:
    """Dọn module trì hoãn."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)
