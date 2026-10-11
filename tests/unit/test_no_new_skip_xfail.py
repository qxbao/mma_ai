"""Bảo vệ số lượng dấu bỏ qua trong bộ kiểm thử của dự án."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE_TEST_FILES = (
    "tests/unit/test_compat_platform.py",
    "tests/unit/test_compat_memory.py",
    "tests/unit/test_compat_display.py",
    "tests/unit/test_compat_capabilities.py",
    "tests/unit/test_compat_stdio.py",
    "tests/unit/test_capability_gate.py",
    "tests/unit/test_compat_pathrules.py",
    "tests/unit/test_compat_fsio.py",
    "tests/unit/test_env_report.py",
    "tests/integration/test_contract_examples_platform.py",
    "tests/integration/test_check_env_cli.py",
    "tests/integration/test_atomic_replace_locked_windows.py",
)
OCCURRENCE = re.compile(
    r"pytest\.skip|skipif|xfail|importorskip|pytest\.mark\.skip"
)
BASELINE_COUNTS = {
    "tests/challenge/test_env_invariants.py": 8,
    "tests/challenge/test_evaluate_invariants.py": 5,
    "tests/challenge/test_replay_invariants.py": 5,
    "tests/challenge/test_train_invariants.py": 4,
    "tests/e2e/test_007_viewer_entrypoint.py": 1,
    "tests/e2e/test_008_docs_entrypoints.py": 2,
    "tests/integration/test_benchmark_train.py": 2,
    "tests/integration/test_contract_examples_m1.py": 1,
    "tests/integration/test_contract_examples_replay.py": 1,
    "tests/integration/test_contract_examples_train.py": 1,
    "tests/integration/test_dashboard_resilience.py": 4,
    "tests/integration/test_demo_cli.py": 1,
    "tests/integration/test_dependency_train.py": 2,
    "tests/integration/test_env_episode_end.py": 1,
    "tests/integration/test_eval_determinism.py": 6,
    "tests/integration/test_evaluate_bad_checkpoint.py": 1,
    "tests/integration/test_evaluate_cli.py": 9,
    "tests/integration/test_evaluate_headless.py": 3,
    "tests/integration/test_evaluate_leakage.py": 3,
    "tests/integration/test_evaluate_storage.py": 3,
    "tests/integration/test_manifest_contract.py": 6,
    "tests/integration/test_network_config.py": 1,
    "tests/integration/test_replay_viewer_real.py": 5,
    "tests/integration/test_resume.py": 2,
    "tests/integration/test_train_cli.py": 2,
    "tests/integration/test_train_determinism.py": 1,
    "tests/integration/test_train_headless.py": 1,
    "tests/integration/test_train_nan_guard.py": 4,
    "tests/integration/test_train_split.py": 1,
    "tests/integration/test_viewer3d_train.py": 1,
    "tests/property/test_networks_properties.py": 1,
    "tests/property/test_ppo_properties.py": 1,
    "tests/unit/test_charts.py": 2,
    "tests/unit/test_checkpoint.py": 1,
    "tests/unit/test_metrics_log.py": 1,
    "tests/unit/test_networks.py": 1,
    "tests/unit/test_policies.py": 1,
    "tests/unit/test_ppo.py": 1,
    "tests/unit/test_repro.py": 1,
    "tests/unit/test_run_replay.py": 1,
    "tests/unit/test_trainer.py": 1,
    "tests/unit/test_training_log.py": 3,
}


def _count_occurrences(path: Path) -> int:
    return len(OCCURRENCE.findall(path.read_text(encoding="utf-8")))


def test_inv_006_ac_6_feature_tests_have_no_skip_or_xfail() -> None:
    """INV-006 AC-6: các test của feature không che lỗi bằng dấu bỏ qua."""
    violations = {
        name: _count_occurrences(ROOT / name)
        for name in FEATURE_TEST_FILES
        if _count_occurrences(ROOT / name)
    }

    assert violations == {}


def test_inv_006_baseline_occurrences_not_increased() -> None:
    """INV-006: số dấu bỏ qua không tăng ở bất kỳ tệp test nào."""
    current_counts = {
        path.relative_to(ROOT).as_posix(): _count_occurrences(path)
        for path in (ROOT / "tests").rglob("*.py")
        if path.is_file() and path.resolve() != Path(__file__).resolve()
    }
    increased = {
        name: (BASELINE_COUNTS.get(name, 0), count)
        for name, count in current_counts.items()
        if count > BASELINE_COUNTS.get(name, 0)
    }

    assert increased == {}
