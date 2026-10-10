"""Kiểm thử tích hợp hợp đồng báo cáo cho phân hệ đánh giá policy (004-eval-vs-random-plots).

Hiện thực các bài kiểm thử hợp đồng dữ liệu (data contract test) cho báo cáo đánh giá
(evaluation report):
- 004 AC-1, 004 NFR-REL-001, FR-017, FR-019: report.json thật của một lượt đánh giá hợp
  eval-report.schema.json, quét đệ quy không chứa giá trị không hữu hạn (non-finite values)
  như NaN hay Infinity.
- 004 AC-1, 004 INV-002, FR-002: số lượng tập phim (episodes) bằng số mục tiêu nhân số lần lặp
  (repeats) cho cả hai chính sách; tệp episodes.csv có số dòng dữ liệu tương ứng.
- 004 AC-1, 004 INV-002: tính nhất quán mã băm (hash consistency) mô hình XML giữa báo cáo,
  điểm kiểm tra (checkpoint) và hồ sơ thí nghiệm (run manifest).
- 004 AC-1, 004 FR-017, 004 FR-019, 004 NFR-REL-001: mọi tệp ví dụ hợp đồng
  contracts/examples/eval-report.*.json hợp schema báo cáo; eval-config.default.json
  hợp schema cấu hình; report.config của một lượt thật hợp schema cấu hình.
- 004 AC-1, 004 FR-017, 004 NFR-REL-001: chỉ số khoảng cách null kèm lý do (reason) tường minh
  khi không có dữ liệu hợp lệ (ví dụ: eval-report.null-distance.json và một lượt chạy thật
  mà mọi episode kết thúc bất thường).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from eval_fixtures import make_run_dir
from jsonschema import Draft202012Validator

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.policies import BasePolicy
from mma_ai.evaluation.runner import evaluate_checkpoint

_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[2] / "specs" / "004-eval-vs-random-plots" / "contracts"
)
_DEFAULT_MODEL_SHA256 = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"


@dataclass
class _DummyLoadedCheckpoint:
    """Điểm kiểm tra giả lập cô lập phụ thuộc PyTorch khi chạy trong môi trường tối giản."""

    actor_state_dict: dict[str, Any]
    critic_state_dict: dict[str, Any]
    obs_normalizer_state_dict: dict[str, Any]
    optimizer_state_dict: dict[str, Any]
    seed: int
    rng_state: dict[str, Any]
    update_idx: int
    env_steps: int
    model_sha256: str
    library_versions: dict[str, str]
    config: Any = None
    log_std: Any = None
    raw_data: dict[str, Any] | None = None


class _MockLearnedPolicy(BasePolicy):
    """Chính sách học được giả lập trả về hành động hợp lệ trong [0, 1]^6."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.name = "learned"

    def act(self, obs_raw: Any = None) -> np.ndarray:
        return np.full(6, 0.5, dtype=np.float32)


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _ensure_checkpoint_loadable_when_torch_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tự động kích hoạt cơ chế nạp điểm kiểm tra giả lập khi thiếu thư viện PyTorch."""
    try:
        import torch  # noqa: F401
    except ImportError:
        def _mock_load_checkpoint(
            path: Path | str, for_training: bool = False, **kwargs: Any
        ) -> _DummyLoadedCheckpoint:
            return _DummyLoadedCheckpoint(
                actor_state_dict={},
                critic_state_dict={},
                obs_normalizer_state_dict={},
                optimizer_state_dict={},
                seed=42,
                rng_state={},
                update_idx=1,
                env_steps=2048,
                model_sha256=_DEFAULT_MODEL_SHA256,
                library_versions={"python": "3.12.0"},
            )

        monkeypatch.setattr("mma_ai.learning.checkpoint.load_checkpoint", _mock_load_checkpoint)
        monkeypatch.setattr("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy)


def _load_json(path: Path) -> dict[str, Any]:
    """Nạp một bản ghi JSON hợp đồng từ đĩa."""
    with path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _get_report_schema() -> dict[str, Any]:
    """Nạp lược đồ JSON Schema của báo cáo đánh giá eval-report.schema.json."""
    return _load_json(_CONTRACTS_DIR / "eval-report.schema.json")


def _get_config_schema() -> dict[str, Any]:
    """Nạp lược đồ JSON Schema của cấu hình đánh giá eval-config.schema.json."""
    return _load_json(_CONTRACTS_DIR / "eval-config.schema.json")


def _assert_no_nonfinite(obj: Any, path: str = "$") -> None:
    """Quét đệ quy toàn bộ cấu trúc dữ liệu không chứa NaN hay Infinity.

    Bảo đảm yêu cầu 004 NFR-REL-001 và 004 FR-017 về độ tin cậy số học.
    """
    if isinstance(obj, float):
        assert not math.isnan(obj), f"Phát hiện giá trị NaN tại đường dẫn {path}"
        assert not math.isinf(obj), f"Phát hiện giá trị Infinity tại đường dẫn {path}"
    elif isinstance(obj, str):
        lowered = obj.strip().lower()
        assert lowered not in {"nan", "infinity", "-infinity", "+infinity", "inf", "-inf"}, (
            f"Phát hiện chuỗi biểu diễn giá trị không hữu hạn '{obj}' tại đường dẫn {path}"
        )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_nonfinite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _assert_no_nonfinite(item, f"{path}[{idx}]")


def test_report_schema_and_no_nonfinite(tmp_path: Path) -> None:
    """004 AC-1, 004 NFR-REL-001, FR-017, FR-019: report.json hợp schema, quét không NaN/Inf."""
    run_dir = make_run_dir(tmp_path / "runs", seed=42)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001.pt"
    cfg = EvalConfig.load(overrides={"episodes": {"repeats": 1}})

    result = evaluate_checkpoint(ckpt_path, cfg)

    assert result.status in {"done", "done_charts_incomplete"}
    report_path = result.eval_dir / "report.json"
    assert report_path.is_file(), f"Tệp báo cáo không tồn tại: {report_path}"

    report_data = _load_json(report_path)

    # 1. Xác thực cấu trúc theo lược đồ JSON Schema chuẩn
    report_schema = _get_report_schema()
    validator = Draft202012Validator(report_schema)
    validator.validate(report_data)

    # 2. Quét đệ quy không chứa NaN hay Infinity
    _assert_no_nonfinite(report_data)

    # 3. Khẳng định cơ chế serialize JSON với allow_nan=False không ném ngoại lệ
    serialized = json.dumps(report_data, allow_nan=False)
    assert len(serialized) > 0


def test_n_episodes_equal_targets_times_repeats(tmp_path: Path) -> None:
    """004 AC-1, 004 INV-002, FR-002: số episode trong báo cáo và CSV bằng targets * repeats."""
    repeats = 2
    min_targets = 2
    run_dir = make_run_dir(tmp_path / "runs", seed=42)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001.pt"
    cfg = EvalConfig.load(overrides={"episodes": {"repeats": repeats}})

    result = evaluate_checkpoint(ckpt_path, cfg)
    report_data = result.report

    n_eval_targets = int(report_data["disjointness"]["n_eval_targets"])
    config_repeats = int(report_data["config"]["episodes"]["repeats"])
    assert config_repeats == repeats
    assert n_eval_targets >= min_targets

    expected_episodes = n_eval_targets * repeats

    # Kiểm tra số episode cho chính sách đã học (learned policy) và ngẫu nhiên (random policy)
    learned_episodes = report_data["policies"]["learned"]["n_episodes"]
    random_episodes = report_data["policies"]["random"]["n_episodes"]
    assert learned_episodes == expected_episodes
    assert random_episodes == expected_episodes

    # Kiểm tra tệp episodes.csv
    csv_path = result.eval_dir / "episodes.csv"
    assert csv_path.is_file(), f"Tệp nhật ký tập phim không tồn tại: {csv_path}"

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    learned_rows = [r for r in rows if r["policy"] == "learned"]
    random_rows = [r for r in rows if r["policy"] == "random"]

    assert len(learned_rows) == expected_episodes
    assert len(random_rows) == expected_episodes
    assert len(rows) == expected_episodes * 2

    # Mỗi mục tiêu phải xuất hiện đúng repeats lần cho mỗi chính sách
    for pol_rows in (learned_rows, random_rows):
        target_counts: dict[int, int] = {}
        for row in pol_rows:
            t_idx = int(row["target_index"])
            target_counts[t_idx] = target_counts.get(t_idx, 0) + 1
        assert len(target_counts) == n_eval_targets
        for t_idx, count in target_counts.items():
            assert count == repeats, f"Mục tiêu {t_idx} xuất hiện {count} lần, kỳ vọng {repeats}"


def test_hash_consistency(tmp_path: Path) -> None:
    """004 AC-1, 004 INV-002: tính nhất quán mã băm XML giữa báo cáo, checkpoint và hồ sơ run."""
    run_dir = make_run_dir(tmp_path / "runs", seed=42)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001.pt"
    cfg = EvalConfig.load(overrides={"episodes": {"repeats": 1}})

    result = evaluate_checkpoint(ckpt_path, cfg)
    report_data = result.report

    manifest_path = run_dir / "manifest.json"
    manifest_data = _load_json(manifest_path)

    report_model_sha256 = report_data["model"]["sha256"]
    ckpt_model_sha256 = report_data["checkpoint"]["model_sha256"]
    manifest_model_sha256 = manifest_data["model"]["sha256"]

    # Khẳng định bất biến INV-002: mã băm XML mô hình khớp tuyệt đối
    assert report_model_sha256 == ckpt_model_sha256
    assert report_model_sha256 == manifest_model_sha256

    # Khẳng định mã băm nội dung tệp checkpoint khớp mã băm thực tế trên đĩa
    expected_ckpt_sha256 = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
    assert report_data["checkpoint"]["sha256"] == expected_ckpt_sha256


def test_contract_examples_eval(tmp_path: Path) -> None:
    """004 AC-1, 004 FR-017, 004 FR-019, 004 NFR-REL-001: ví dụ hợp đồng hợp schema tương ứng."""
    report_schema = _get_report_schema()
    config_schema = _get_config_schema()
    report_validator = Draft202012Validator(report_schema)
    config_validator = Draft202012Validator(config_schema)

    # 1. Kiểm tra tất cả tệp ví dụ báo cáo hợp đồng
    report_example_names = [
        "eval-report.charts-incomplete.json",
        "eval-report.done-better.json",
        "eval-report.done-not-better.json",
        "eval-report.null-distance.json",
    ]

    for name in report_example_names:
        example_path = _CONTRACTS_DIR / "examples" / name
        assert example_path.is_file(), f"Tệp ví dụ báo cáo không tồn tại: {example_path}"
        data = _load_json(example_path)
        report_validator.validate(data)
        _assert_no_nonfinite(data)

    # 2. Kiểm tra tệp ví dụ cấu hình mặc định
    config_example_path = _CONTRACTS_DIR / "examples" / "eval-config.default.json"
    assert config_example_path.is_file(), f"Tệp ví dụ cấu hình không tồn tại: {config_example_path}"
    config_data = _load_json(config_example_path)
    config_validator.validate(config_data)
    _assert_no_nonfinite(config_data)

    # 3. Đảm bảo toàn bộ tệp .json trong thư mục examples đều được kiểm tra
    actual_example_files = {p.name for p in (_CONTRACTS_DIR / "examples").glob("*.json")}
    expected_example_files = set(report_example_names) | {"eval-config.default.json"}
    diff_examples = actual_example_files ^ expected_example_files
    assert actual_example_files == expected_example_files, (
        f"Danh sách tệp ví dụ không khớp: thừa/thiếu {diff_examples}"
    )

    # 4. Kiểm tra report.config của một lượt đánh giá thật hợp schema cấu hình
    run_dir = make_run_dir(tmp_path / "runs", seed=42)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001.pt"
    cfg = EvalConfig.load(overrides={"episodes": {"repeats": 1}})
    result = evaluate_checkpoint(ckpt_path, cfg)

    actual_config_in_report = result.report["config"]
    config_validator.validate(actual_config_in_report)
    _assert_no_nonfinite(actual_config_in_report)


def test_null_with_reason_when_no_valid_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """004 AC-1, 004 FR-017, 004 NFR-REL-001: khoảng cách null kèm lý do khi không có dữ liệu."""
    # 1. Kiểm chứng trên tệp ví dụ hợp đồng eval-report.null-distance.json
    null_dist_example = _load_json(_CONTRACTS_DIR / "examples" / "eval-report.null-distance.json")
    rand_dist = null_dist_example["policies"]["random"]["final_distance_m"]
    assert rand_dist["value"] is None
    assert rand_dist["ci_low"] is None
    assert rand_dist["ci_high"] is None
    assert rand_dist["n"] == 0
    assert rand_dist["reason"] == "mọi episode kết thúc bất thường"

    # 2. Kiểm chứng trên một lượt đánh giá thật khi mọi episode đều kết thúc bất thường
    def _mock_step_instability(self: ElbowReachEnv, action: Any) -> Any:
        raise PhysicsInstabilityError("Mô phỏng mất ổn định động học trong kiểm thử")

    monkeypatch.setattr(ElbowReachEnv, "step", _mock_step_instability)

    run_dir = make_run_dir(tmp_path / "runs", seed=42)
    ckpt_path = run_dir / "checkpoints" / "ckpt_u000001.pt"
    cfg = EvalConfig.load(overrides={"episodes": {"repeats": 1}})

    result = evaluate_checkpoint(ckpt_path, cfg)
    report_data = result.report

    # Xác thực báo cáo vẫn hợp lệ theo schema ngay cả khi toàn bộ episode bất thường
    report_schema = _get_report_schema()
    validator = Draft202012Validator(report_schema)
    validator.validate(report_data)

    for pol_key in ("learned", "random"):
        pol_result = report_data["policies"][pol_key]
        dist_stat = pol_result["final_distance_m"]

        # Khoảng cách cuối phải là null kèm lý do rõ ràng, không được là 0 hay NaN
        assert dist_stat["value"] is None
        assert dist_stat["ci_low"] is None
        assert dist_stat["ci_high"] is None
        assert dist_stat["n"] == 0
        assert dist_stat["reason"] == "mọi episode kết thúc bất thường"

        # Tỷ lệ bất thường phải là 1.0 (toàn bộ)
        assert pol_result["abnormal_rate"]["value"] == 1.0
        assert pol_result["n_abnormal"] == pol_result["n_episodes"]

    # Quét đệ quy không chứa NaN hay Infinity
    _assert_no_nonfinite(report_data)
