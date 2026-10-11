"""Kiểm thử tích hợp kết luận đánh giá bằng chính sách có chất lượng đã biết (API-EVL-0007).

Hiện thực các kịch bản kiểm thử tích hợp (integration test) và chấp nhận (acceptance test):
- 004 AC-2, 004 FR-006, 004 INV-006: Chính sách kích thích cơ bằng 0 (always-zero policy) trên
  môi trường thực tế không bao giờ tốt hơn chính sách ngẫu nhiên (random policy).
- 004 AC-2, 004 FR-006, 004 INV-006: Hai chính sách giống hệt nhau (identical policies) cho
  hiệu số bằng 0 và khoảng tin cậy (confidence interval) chứa 0, kết luận không tốt hơn.
- 004 AC-2, 004 KQ-2, 004 SC-002, 004 FR-005, 004 FR-006, 004 FR-007, 004 INV-006: Chính sách
  kịch bản chắc chắn tới mục tiêu (reaching policy) cho kết luận tốt hơn có ý nghĩa thống kê;
  kiểm chứng bằng dữ liệu tổng hợp có đáp án tính tay theo quy tắc tự chốt.
- 004 AC-2, 004 FR-005, 004 FR-019, 004 INV-006: Khoảng tin cậy rộng khi số lượng mục tiêu ít
  được báo cáo trung thực trong phần giới hạn (limits) đúng như kết quả tính toán.
- 004 AC-2, 004 FR-005, 004 FR-006, 004 NFR-STAT-001, 004 INV-006: Các trường hợp biên (edge case)
  tỷ lệ 0% và 100% bảo đảm giá trị số hữu hạn (finite numbers), kết luận không tốt hơn và nêu rõ
  nguyên nhân.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from eval_fixtures import scripted_policy
from jsonschema import Draft202012Validator

from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import summarize
from mma_ai.evaluation.policies import RandomPolicy
from mma_ai.evaluation.report import build_report, generate_eval_id
from mma_ai.evaluation.rollout import EpisodeRecord, run_policy_on_targets
from mma_ai.evaluation.split_guard import DisjointnessReport
from mma_ai.evaluation.stats import decide

_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[2] / "specs" / "004-eval-vs-random-plots" / "contracts"
)
_DEFAULT_MODEL_SHA256 = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"
_DEFAULT_MUSCLE_NAMES = (
    "BIClong",
    "BICshort",
    "BRA",
    "TRIlong",
    "TRIlat",
    "TRImed",
)


def _assert_no_nonfinite(obj: Any, path: str = "$") -> None:
    """Quét đệ quy cấu trúc dữ liệu bảo đảm không chứa NaN hoặc Infinity (NFR-STAT-001, FR-017)."""
    if isinstance(obj, float):
        assert not math.isnan(obj), f"Phát hiện NaN tại {path}"
        assert not math.isinf(obj), f"Phát hiện Infinity tại {path}"
    elif isinstance(obj, str):
        lowered = obj.strip().lower()
        assert lowered not in {"nan", "infinity", "-infinity", "+infinity", "inf", "-inf"}, (
            f"Phát hiện chuỗi số không hữu hạn '{obj}' tại {path}"
        )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_nonfinite(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _assert_no_nonfinite(item, f"{path}[{idx}]")


def _get_report_schema() -> dict[str, Any]:
    """Tải lược đồ JSON Schema của báo cáo đánh giá eval-report.schema.json."""
    schema_path = _CONTRACTS_DIR / "eval-report.schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _create_sample_disjointness_report(n_eval_targets: int = 50) -> DisjointnessReport:
    """Tạo báo cáo kiểm tra không giao cắt mẫu hợp chuẩn."""
    return DisjointnessReport(
        checked=True,
        passed=True,
        train_target_provenance="rebuilt_from_config",
        target_fingerprint_sha256="c" * 64,
        n_train_targets=200,
        n_eval_targets=n_eval_targets,
        min_cross_distance_m=0.025,
        min_required_m=0.020,
        eval_seed_range=(12345, 12345 + n_eval_targets),
        random_policy_seed=12345,
        train_seeds=(42,),
        n_checked=200 + n_eval_targets,
    )


def _create_sample_charts_dict() -> dict[str, Any]:
    """Tạo từ điển biểu đồ mẫu hợp chuẩn."""
    return {
        "status": "complete",
        "files": {
            "loss": "charts/loss.png",
            "reward": "charts/reward.png",
            "activation": "charts/activation.png",
        },
        "points_plotted": {
            "loss": 20,
            "reward": 20,
            "activation": 120,
        },
        "points_dropped": 0,
        "reason": None,
        "log_source": "jsonl",
    }


def _create_synthetic_episode_record(
    policy: str,
    episode: int,
    target_index: int,
    reached: bool,
    final_distance_m: float | None = 0.015,
    abnormal: bool = False,
    return_: float = 10.0,
    effort: float = 0.40,
) -> EpisodeRecord:
    """Dựng bản ghi tập phim tổng hợp phục vụ kiểm thử đơn vị với đáp án đã biết."""
    return EpisodeRecord(
        policy=policy,
        episode=episode,
        target_index=target_index,
        seed=12345 + episode,
        reached=reached,
        end_reason="reached" if reached else "max_actions",
        abnormal=abnormal,
        final_distance_m=final_distance_m,
        return_=return_,
        effort=effort,
        act_m0=effort,
        act_m1=effort,
        act_m2=effort,
        act_m3=effort,
        act_m4=effort,
        act_m5=effort,
        n_steps=25,
        nan_count=0,
        inf_count=0,
    )


def test_always_zero_policy_is_not_better() -> None:
    """Chính sách 0 trên môi trường thật so với random cho kết luận không tốt hơn.

    Truy vết: AC-2, FR-006, INV-006.
    """
    env = ElbowReachEnv()
    zero_policy = scripted_policy("zero")
    random_policy = RandomPolicy(seed=12345)
    cfg = EvalConfig.load()

    records_zero = run_policy_on_targets(
        env, zero_policy, n_targets=3, repeats=1, seed_base=12345, policy_name="zero"
    )
    records_rand = run_policy_on_targets(
        env, random_policy, n_targets=3, repeats=1, seed_base=12345, policy_name="random"
    )

    res_zero = summarize(records_zero, cfg, kind="learned")
    res_rand = summarize(records_rand, cfg, kind="random")
    verdict = decide(res_zero, res_rand, level=cfg.criterion.confidence_level)

    assert verdict.better is False, (
        "Chính sách kích thích 0 không thể tốt hơn chính sách ngẫu nhiên"
    )
    assert verdict.ci_low <= 0.0, "Cận dưới khoảng tin cậy của hiệu số phải <= 0"
    assert -1.0 <= verdict.ci_low <= verdict.difference <= verdict.ci_high <= 1.0
    assert math.isfinite(verdict.difference)
    assert math.isfinite(verdict.ci_low)
    assert math.isfinite(verdict.ci_high)
    assert verdict.method == "newcombe_wilson_hybrid"


def test_identical_policies_not_better() -> None:
    """Hai chính sách giống hệt nhau cho hiệu số bằng 0 và khoảng tin cậy chứa 0.

    Truy vết: AC-2, FR-006, INV-006.
    """
    env = ElbowReachEnv()
    policy1 = scripted_policy("zero")
    policy2 = scripted_policy("zero")
    cfg = EvalConfig.load()

    records1 = run_policy_on_targets(
        env, policy1, n_targets=3, repeats=1, seed_base=12345, policy_name="learned"
    )
    records2 = run_policy_on_targets(
        env, policy2, n_targets=3, repeats=1, seed_base=12345, policy_name="random"
    )

    res1 = summarize(records1, cfg, kind="learned")
    res2 = summarize(records2, cfg, kind="random")
    verdict = decide(res1, res2, level=cfg.criterion.confidence_level)

    assert math.isclose(verdict.difference, 0.0, abs_tol=1e-9), "Hiệu số đồng nhất phải bằng 0"
    assert verdict.ci_low <= 0.0 <= verdict.ci_high, (
        "Khoảng tin cậy của hiệu số phải chứa giá trị 0"
    )
    assert math.isclose(verdict.ci_low, -verdict.ci_high, abs_tol=1e-9), "Đối xứng qua 0"
    assert verdict.better is False, "Quy tắc ci_low > 0 phải kết luận không tốt hơn"


def test_scripted_reaching_policy_is_better() -> None:
    """Chính sách kịch bản chắc chắn tới cho kết luận tốt hơn có ý nghĩa thống kê.

    Tự chốt: vì chưa đo được một policy kịch bản tới MỌI mục tiêu thật, ca 'chắc chắn tới'
    dựng danh sách EpisodeRecord tổng hợp có đáp án tay — tới 50/50 so với 0/50 ⇒ better,
    ci_low ≈ 0,899 — đi qua summarize + decide + build_report; ca môi trường thật chỉ dùng
    cho hai ca còn lại.

    Truy vết: AC-2, KQ-2, SC-002, FR-005, FR-006, FR-007, INV-006.
    """
    n_targets = 50
    learned_records = [
        _create_synthetic_episode_record(
            policy="learned",
            episode=i,
            target_index=i,
            reached=True,
            final_distance_m=0.012,
            return_=16.0,
            effort=0.38,
        )
        for i in range(n_targets)
    ]
    random_records = [
        _create_synthetic_episode_record(
            policy="random",
            episode=i,
            target_index=i,
            reached=False,
            final_distance_m=0.185,
            return_=0.5,
            effort=0.50,
        )
        for i in range(n_targets)
    ]

    cfg = EvalConfig.load()
    learned_res = summarize(learned_records, cfg, kind="learned")
    random_res = summarize(random_records, cfg, kind="random")
    verdict = decide(learned_res, random_res, level=cfg.criterion.confidence_level)

    # Đối chiếu nghiệm giải tích 50 vs 0 theo nghiên cứu Q1
    assert verdict.better is True, "Chính sách đạt 50/50 so với 0/50 phải kết luận tốt hơn"
    assert math.isclose(verdict.difference, 1.000, abs_tol=1e-3)
    assert math.isclose(verdict.ci_low, 0.899, abs_tol=1e-3)
    assert math.isclose(verdict.ci_high, 1.000, abs_tol=1e-3)
    assert verdict.ci_low > 0.0

    eval_id = generate_eval_id(episode_base=cfg.seeds.episode_base)
    disjointness = _create_sample_disjointness_report(n_eval_targets=n_targets)
    charts = _create_sample_charts_dict()

    report = build_report(
        eval_id=eval_id,
        run_id="run-sample-001",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_u000001.pt",
        checkpoint_sha256="a" * 64,
        update_idx=10,
        env_steps=20480,
        model_sha256=_DEFAULT_MODEL_SHA256,
        muscle_names=_DEFAULT_MUSCLE_NAMES,
        cfg=cfg,
        disjointness=disjointness,
        learned=learned_res,
        random=random_res,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=5.25,
    )

    comp = report["comparison"]
    assert comp["better"] is True
    assert math.isclose(float(comp["difference"]), 1.000, abs_tol=1e-3)
    assert math.isclose(float(comp["ci_low"]), 0.899, abs_tol=1e-3)
    assert math.isclose(float(comp["ci_high"]), 1.000, abs_tol=1e-3)
    assert comp["confidence_level"] == cfg.criterion.confidence_level
    assert comp["ci_method"] == "newcombe_wilson_hybrid"

    crit = report["criterion"]
    assert crit["declared_before_run"] is True
    assert crit["primary_metric"] == "success_rate"
    assert crit["rule"] == "better_iff_ci_lower_bound_of_difference_gt_0"
    assert crit["confidence_level"] == cfg.criterion.confidence_level

    # Xác thực lược đồ JSON schema chính thức và kiểm tra không rò rỉ giá trị vô hạn
    schema = _get_report_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(report))
    assert not errors, f"Báo cáo không khớp schema: {[e.message for e in errors]}"
    _assert_no_nonfinite(report)


def test_wide_ci_few_targets_reported_as_computed() -> None:
    """Ít mục tiêu dẫn tới khoảng tin cậy rộng và được báo cáo trung thực trong limits.

    Truy vết: AC-2, FR-005, FR-019, INV-006.
    """
    n_targets = 2
    learned_records = [
        _create_synthetic_episode_record("learned", 0, 0, reached=True, final_distance_m=0.015),
        _create_synthetic_episode_record("learned", 1, 1, reached=False, final_distance_m=0.090),
    ]
    random_records = [
        _create_synthetic_episode_record("random", 0, 0, reached=False, final_distance_m=0.150),
        _create_synthetic_episode_record("random", 1, 1, reached=False, final_distance_m=0.170),
    ]

    cfg = EvalConfig.load()
    learned_res = summarize(learned_records, cfg, kind="learned")
    random_res = summarize(random_records, cfg, kind="random")
    verdict = decide(learned_res, random_res, level=cfg.criterion.confidence_level)

    ci_width = round(verdict.ci_high - verdict.ci_low, 3)
    assert ci_width >= 0.80, f"Khoảng tin cậy với n=2 phải rất rộng, nhận được: {ci_width}"
    assert verdict.better is False, "Với n=2 và ci_low <= 0 thì không thể kết luận tốt hơn"

    eval_id = generate_eval_id(episode_base=cfg.seeds.episode_base)
    disjointness = _create_sample_disjointness_report(n_eval_targets=n_targets)
    charts = _create_sample_charts_dict()

    report = build_report(
        eval_id=eval_id,
        run_id="run-few-targets-002",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_u000001.pt",
        checkpoint_sha256="b" * 64,
        update_idx=1,
        env_steps=2048,
        model_sha256=_DEFAULT_MODEL_SHA256,
        muscle_names=_DEFAULT_MUSCLE_NAMES,
        cfg=cfg,
        disjointness=disjointness,
        learned=learned_res,
        random=random_res,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=1.12,
    )

    limits = report["limits"]
    assert len(limits) == 2
    assert f"khoảng tin cậy của hiệu rộng ≈ {ci_width:.2f}" in limits[0]
    assert "2 episode mỗi policy" in limits[0]
    assert "chênh lệch nhỏ hơn mức này không phát hiện được" in limits[0]
    assert "không khẳng định chất lượng policy ngoài số đo này" in limits[1]
    assert "Kết luận chỉ áp cho checkpoint" in limits[1]

    _assert_no_nonfinite(report)


def test_both_rates_zero_or_one_finite() -> None:
    """Các ca biên 0% và 100% không chứa NaN, kết luận không tốt hơn và nêu rõ nguyên nhân.

    Truy vết: AC-2, FR-005, FR-006, NFR-STAT-001, INV-006.
    """
    n_targets = 50
    cfg = EvalConfig.load()

    # 1. Ca biên tỷ lệ 0% cho cả hai chính sách (0/50 vs 0/50)
    records_0_learned = [
        _create_synthetic_episode_record("learned", i, i, reached=False, final_distance_m=0.15)
        for i in range(n_targets)
    ]
    records_0_random = [
        _create_synthetic_episode_record("random", i, i, reached=False, final_distance_m=0.16)
        for i in range(n_targets)
    ]

    res_0_learned = summarize(records_0_learned, cfg, kind="learned")
    res_0_random = summarize(records_0_random, cfg, kind="random")
    v_0 = decide(res_0_learned, res_0_random, level=cfg.criterion.confidence_level)

    assert math.isfinite(v_0.difference)
    assert math.isfinite(v_0.ci_low)
    assert math.isfinite(v_0.ci_high)
    assert not math.isnan(v_0.difference)
    assert not math.isnan(v_0.ci_low)
    assert not math.isnan(v_0.ci_high)
    assert math.isclose(v_0.difference, 0.0, abs_tol=1e-9)
    assert math.isclose(v_0.ci_low, -0.071, abs_tol=1e-3)
    assert math.isclose(v_0.ci_high, 0.071, abs_tol=1e-3)
    assert v_0.better is False
    # Lý do: Cả hai tỷ lệ đều bằng 0, hiệu số bằng 0 và cận dưới khoảng tin cậy không lớn hơn 0
    assert v_0.ci_low <= 0.0

    # 2. Ca biên tỷ lệ 100% cho cả hai chính sách (50/50 vs 50/50)
    records_1_learned = [
        _create_synthetic_episode_record("learned", i, i, reached=True, final_distance_m=0.01)
        for i in range(n_targets)
    ]
    records_1_random = [
        _create_synthetic_episode_record("random", i, i, reached=True, final_distance_m=0.01)
        for i in range(n_targets)
    ]

    res_1_learned = summarize(records_1_learned, cfg, kind="learned")
    res_1_random = summarize(records_1_random, cfg, kind="random")
    v_1 = decide(res_1_learned, res_1_random, level=cfg.criterion.confidence_level)

    assert math.isfinite(v_1.difference)
    assert math.isfinite(v_1.ci_low)
    assert math.isfinite(v_1.ci_high)
    assert not math.isnan(v_1.difference)
    assert not math.isnan(v_1.ci_low)
    assert not math.isnan(v_1.ci_high)
    assert math.isclose(v_1.difference, 0.0, abs_tol=1e-9)
    assert math.isclose(v_1.ci_low, -0.071, abs_tol=1e-3)
    assert math.isclose(v_1.ci_high, 0.071, abs_tol=1e-3)
    assert v_1.better is False
    # Lý do: Cả hai tỷ lệ đều bằng 100%, hiệu số bằng 0 và cận dưới khoảng tin cậy không lớn hơn 0
    assert v_1.ci_low <= 0.0

    # Xác thực báo cáo cho cả hai ca biên không chứa NaN/Infinity
    disjointness = _create_sample_disjointness_report(n_eval_targets=n_targets)
    charts = _create_sample_charts_dict()

    report_0 = build_report(
        eval_id=generate_eval_id(episode_base=cfg.seeds.episode_base),
        run_id="run-zero-edge-003",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_u000001.pt",
        checkpoint_sha256="c" * 64,
        update_idx=1,
        env_steps=2048,
        model_sha256=_DEFAULT_MODEL_SHA256,
        muscle_names=_DEFAULT_MUSCLE_NAMES,
        cfg=cfg,
        disjointness=disjointness,
        learned=res_0_learned,
        random=res_0_random,
        verdict=v_0,
        charts=charts,
        wall_clock_seconds=2.0,
    )
    _assert_no_nonfinite(report_0)

    report_1 = build_report(
        eval_id=generate_eval_id(episode_base=cfg.seeds.episode_base + 1),
        run_id="run-one-edge-004",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_u000001.pt",
        checkpoint_sha256="d" * 64,
        update_idx=1,
        env_steps=2048,
        model_sha256=_DEFAULT_MODEL_SHA256,
        muscle_names=_DEFAULT_MUSCLE_NAMES,
        cfg=cfg,
        disjointness=disjointness,
        learned=res_1_learned,
        random=res_1_random,
        verdict=v_1,
        charts=charts,
        wall_clock_seconds=2.0,
    )
    _assert_no_nonfinite(report_1)
