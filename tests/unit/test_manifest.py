"""Kiểm thử đơn vị cho hồ sơ thí nghiệm run manifest.

Bao phủ các yêu cầu FR-011...FR-014, INV-001, NFR-RES-001, AC-3, AC-4.
"""

from __future__ import annotations

import json
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


def _dummy_config() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "stage": "elbow",
        "seed": 42,
        "reproducibility": {
            "rel_tolerance": 1e-6,
            "head_updates": 10,
            "torch_threads": 1,
            "deterministic_algorithms": True,
        },
        "ui": {
            "mode": "none",
            "url": None,
            "view3d": False,
        },
    }


def _dummy_model() -> dict[str, Any]:
    return {
        "sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
        "muscle_names": ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
    }


def test_build_fields_complete() -> None:
    """FR-011, FR-012, FR-013, NFR-RES-001, AC-3: đủ 20 trường bắt buộc trong hồ sơ run."""
    from mma_ai.learning.manifest import build_manifest

    manifest = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
    )

    required_keys = [
        "schema_version",
        "run_id",
        "stage",
        "status",
        "seed",
        "resumed_from",
        "started_utc",
        "finished_utc",
        "config",
        "library_versions",
        "model",
        "device",
        "checkpoints",
        "reward_metrics",
        "throughput",
        "resources",
        "numeric_health",
        "reproducibility",
        "ui",
        "error",
    ]
    for key in required_keys:
        assert key in manifest, f"Thiếu trường bắt buộc '{key}' trong hồ sơ run"

    assert manifest["schema_version"] == "1.0.0"
    assert manifest["stage"] == "elbow"
    assert manifest["status"] == "running"
    assert manifest["seed"] == 42
    assert manifest["finished_utc"] is None

    # Kiểm tra 7 thư viện bắt buộc
    req_libs = ["python", "torch", "numpy", "gymnasium", "mujoco", "myo-sim", "tensorboard"]
    for lib in req_libs:
        assert lib in manifest["library_versions"]
        assert isinstance(manifest["library_versions"][lib], str)

    # Kiểm tra 7 trường tài nguyên bắt buộc (NFR-RES-001)
    req_res = [
        "cpu_model",
        "cpu_logical_cores",
        "cpu_utilization_pct",
        "ram_peak_mb",
        "gpu_name",
        "gpu_utilization_pct",
        "vram_peak_mb",
    ]
    for res_key in req_res:
        assert res_key in manifest["resources"]

    # Kiểm tra reproducibility và device
    assert manifest["device"]["kind"] in ("cpu", "cuda")
    assert manifest["reproducibility"]["rel_tolerance"] == 1e-6
    assert manifest["reproducibility"]["head_updates"] == 10


def test_reject_nonfinite(tmp_path: Path) -> None:
    """FR-017, NFR-REL-001, AC-1: từ chối NaN và Inf trong hồ sơ run, ném NonFiniteError."""
    from mma_ai.learning.errors import NonFiniteError
    from mma_ai.learning.manifest import build_manifest, write_manifest

    # NaN trong reward_metrics
    with pytest.raises(NonFiniteError):
        build_manifest(
            run_id="20261010T080000Z_elbow_s42",
            config=_dummy_config(),
            seed=42,
            model=_dummy_model(),
            reward_metrics={
                "n_updates": 1,
                "n_episodes": 10,
                "head_updates": 1,
                "head_mean_return": [float("nan")],
                "first_mean_return": float("nan"),
                "last_mean_return": float("nan"),
                "success_rate": 0.5,
            },
        )

    # Inf trong throughput
    with pytest.raises(NonFiniteError):
        build_manifest(
            run_id="20261010T080000Z_elbow_s42",
            config=_dummy_config(),
            seed=42,
            model=_dummy_model(),
            throughput={
                "env_steps": 1000,
                "env_steps_per_second": float("inf"),
                "wall_clock_seconds": 10.0,
            },
        )

    # write_manifest trực tiếp quét từ điển chứa NaN
    bad_manifest = {
        "schema_version": "1.0.0",
        "bad_number": float("nan"),
    }
    with pytest.raises(NonFiniteError):
        write_manifest(tmp_path, bad_manifest)


def test_atomic_replace_status(tmp_path: Path) -> None:
    """FR-011, AC-3: ghi running lúc đầu rồi thay thế nguyên tử sang done lúc cuối."""
    from mma_ai.learning.manifest import build_manifest, read_manifest, write_manifest

    run_dir = tmp_path / "run_test"
    run_dir.mkdir()

    manifest_running = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="running",
    )
    written_path = write_manifest(run_dir, manifest_running)
    assert written_path.is_file()
    assert not (run_dir / "manifest.json.tmp").exists()

    loaded_1 = read_manifest(run_dir)
    assert loaded_1["status"] == "running"
    assert loaded_1["finished_utc"] is None

    # Cập nhật sang status="done"
    manifest_done = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="done",
        base_manifest=loaded_1,
        reward_metrics={
            "n_updates": 2,
            "n_episodes": 20,
            "head_updates": 2,
            "head_mean_return": [10.0, 15.0],
            "first_mean_return": 10.0,
            "last_mean_return": 15.0,
            "success_rate": 0.8,
        },
    )
    write_manifest(run_dir, manifest_done)
    assert not (run_dir / "manifest.json.tmp").exists()

    loaded_2 = read_manifest(run_dir)
    assert loaded_2["status"] == "done"
    assert loaded_2["finished_utc"] is not None


def test_validates_schema() -> None:
    """FR-011, FR-012, FR-014, AC-3: hồ sơ tạo ra hợp lệ tuyệt đối theo run-manifest.schema.json."""
    from mma_ai.learning.manifest import build_manifest

    validator = _get_validator()

    # Trường hợp 1: status="running"
    manifest_running = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="running",
    )
    validator.validate(manifest_running)

    # Trường hợp 2: status="done" kèm checkpoints
    dummy_checkpoint = {
        "schema_version": "1.0.0",
        "path": "checkpoints/ckpt_u000010.pt",
        "kind": "periodic",
        "update_idx": 10,
        "env_steps": 20480,
        "sha256": "a" * 64,
        "created_utc": "2026-10-10T08:10:00Z",
        "model_sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "components": ["actor", "critic", "obs_normalizer", "optimizer", "seed", "rng_state"],
        "library_versions": {"torch": "2.14.1", "numpy": "2.4.6"},
        "finite": True,
    }
    manifest_done = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="done",
        checkpoints=[dummy_checkpoint],
        reward_metrics={
            "n_updates": 10,
            "n_episodes": 100,
            "head_updates": 10,
            "head_mean_return": [float(i) for i in range(10)],
            "first_mean_return": 0.0,
            "last_mean_return": 9.0,
            "success_rate": 0.95,
        },
        throughput={
            "env_steps": 20480,
            "env_steps_per_second": 1250.5,
            "wall_clock_seconds": 16.37,
        },
    )
    validator.validate(manifest_done)

    # Trường hợp 3: status="error"
    manifest_error = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="error",
        error={
            "kind": "non_finite",
            "message": "Phát hiện NaN trong loss chính sách tại lượt 3",
            "update_idx": 3,
        },
    )
    validator.validate(manifest_error)


def test_head_mean_return_has_k_points() -> None:
    """FR-014, AC-4: head_mean_return có đúng K = min(head_updates, n_updates) phần tử."""
    from mma_ai.learning.manifest import build_manifest

    cfg = _dummy_config()
    cfg["reproducibility"]["head_updates"] = 5

    # n_updates = 0 => K = 0
    m0 = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=cfg,
        seed=42,
        model=_dummy_model(),
        reward_metrics={
            "n_updates": 0,
            "n_episodes": 0,
            "head_mean_return": [],
        },
    )
    assert m0["reward_metrics"]["head_updates"] == 0
    assert len(m0["reward_metrics"]["head_mean_return"]) == 0

    # n_updates = 2, head_updates = 5 => K = 2
    m2 = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=cfg,
        seed=42,
        model=_dummy_model(),
        reward_metrics={
            "n_updates": 2,
            "n_episodes": 20,
            "head_mean_return": [1.0, 2.0, 3.0, 4.0],
        },
    )
    assert m2["reward_metrics"]["head_updates"] == 2
    assert m2["reward_metrics"]["head_mean_return"] == [1.0, 2.0]

    # n_updates = 10, head_updates = 5 => K = 5
    m10 = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=cfg,
        seed=42,
        model=_dummy_model(),
        reward_metrics={
            "n_updates": 10,
            "n_episodes": 100,
            "head_mean_return": [float(i) for i in range(10)],
        },
    )
    assert m10["reward_metrics"]["head_updates"] == 5
    assert len(m10["reward_metrics"]["head_mean_return"]) == 5
    assert m10["reward_metrics"]["head_mean_return"] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_finished_run_not_rewritten(tmp_path: Path) -> None:
    """INV-001, AC-3: run đã done/error/interrupted không bị sửa hoặc ghi đè."""
    from mma_ai.learning.errors import RunDirError
    from mma_ai.learning.manifest import build_manifest, write_manifest

    run_dir = tmp_path / "finished_run"
    run_dir.mkdir()

    # Ghi run đã done
    manifest_done = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="done",
    )
    write_manifest(run_dir, manifest_done)

    # Thử sửa lại hoặc ghi đè run đã done => phải ném RunDirError
    manifest_rewrite = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="done",
    )
    with pytest.raises(RunDirError, match="INV-001"):
        write_manifest(run_dir, manifest_rewrite)


def test_inv_001_interrupted_run_not_rewritten(tmp_path: Path) -> None:
    """INV-001, AC-3: run đã interrupted không bị sửa lại."""
    from mma_ai.learning.errors import RunDirError
    from mma_ai.learning.manifest import build_manifest, write_manifest

    run_dir = tmp_path / "interrupted_run"
    run_dir.mkdir()

    manifest_interrupted = build_manifest(
        run_id="20261010T080000Z_elbow_s42",
        config=_dummy_config(),
        seed=42,
        model=_dummy_model(),
        status="interrupted",
    )
    write_manifest(run_dir, manifest_interrupted)

    with pytest.raises(RunDirError, match="INV-001"):
        write_manifest(run_dir, manifest_interrupted)


def teardown_module() -> None:
    """Dọn dẹp các mô-đun trì hoãn để bảo vệ ranh giới kiểm thử."""
    import sys

    sys.modules.pop("mma_ai.learning.manifest", None)
    sys.modules.pop("mma_ai.learning", None)
