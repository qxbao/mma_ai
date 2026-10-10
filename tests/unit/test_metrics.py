"""Kiểm thử đơn vị cho mô-đun tính toán chỉ số đánh giá (API-EVL-0006).

Bao phủ các yêu cầu và bất biến theo hợp đồng phân hệ đánh giá:
- FR-004, AC-1: Tính đủ 7 nhóm chỉ số: tỷ lệ thành công (Wilson), khoảng cách cuối,
  reward trung bình, nỗ lực (kèm 6 cơ), tỷ lệ bất thường, số NaN và số Inf.
- FR-016, AC-1: Episode bị mất ổn định/bất thường tính là không tới mục tiêu, loại khỏi
  thống kê khoảng cách cuối, đếm vào tỷ lệ bất thường.
- FR-017, AC-1: Chỉ số không có dữ liệu hợp lệ ghi nhận giá trị None kèm lý do tường minh,
  không ghi nhận 0 hay NaN.
- NFR-REL-001: Độ tin cậy số học, 0 giá trị NaN/Inf trong báo cáo chỉ số, đếm số NaN/Inf riêng.
- API-EVL-0006: Giao diện hàm summarize(records, cfg) và aggregate_per_target(records).
"""

from __future__ import annotations

import math

import pytest

from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import (
    AggregatedTargets,
    MetricStat,
    PolicyResult,
    aggregate_per_target,
    summarize,
)
from mma_ai.evaluation.rollout import EpisodeRecord


def _create_record(
    *,
    policy: str = "learned",
    episode: int = 0,
    target_index: int = 0,
    seed: int = 12345,
    reached: bool = True,
    end_reason: str | None = "reached",
    abnormal: bool = False,
    final_distance_m: float | None = 0.02,
    return_: float = 10.0,
    effort: float = 0.4,
    act_m0: float = 0.1,
    act_m1: float = 0.2,
    act_m2: float = 0.3,
    act_m3: float = 0.4,
    act_m4: float = 0.5,
    act_m5: float = 0.6,
    n_steps: int = 50,
    nan_count: int = 0,
    inf_count: int = 0,
) -> EpisodeRecord:
    """Hàm trợ giúp tạo EpisodeRecord giả lập cho kiểm thử."""
    return EpisodeRecord(
        policy=policy,
        episode=episode,
        target_index=target_index,
        seed=seed,
        reached=reached,
        end_reason=end_reason,
        abnormal=abnormal,
        final_distance_m=final_distance_m,
        return_=return_,
        effort=effort,
        act_m0=act_m0,
        act_m1=act_m1,
        act_m2=act_m2,
        act_m3=act_m3,
        act_m4=act_m4,
        act_m5=act_m5,
        n_steps=n_steps,
        nan_count=nan_count,
        inf_count=inf_count,
    )


def test_independent_assertion_metrics_contract() -> None:
    """Assertion độc lập trên base chứng minh mô-đun và cấu trúc tồn tại (API-EVL-0006)."""
    assert callable(summarize)
    assert callable(aggregate_per_target)
    assert issubclass(MetricStat, object)
    assert issubclass(PolicyResult, object)
    assert issubclass(AggregatedTargets, object)


def test_summarize_all_groups() -> None:
    """FR-004, AC-1, API-EVL-0006: Tính đầy đủ 7 nhóm chỉ số trên tập episode thông thường."""
    cfg = EvalConfig.load()
    records: list[EpisodeRecord] = [
        _create_record(
            episode=0,
            target_index=0,
            reached=True,
            final_distance_m=0.015,
            return_=12.0,
            effort=0.35,
            act_m0=0.1,
            act_m1=0.2,
            act_m2=0.3,
            act_m3=0.4,
            act_m4=0.5,
            act_m5=0.6,
        ),
        _create_record(
            episode=1,
            target_index=1,
            reached=False,
            final_distance_m=0.045,
            return_=8.0,
            effort=0.45,
            act_m0=0.2,
            act_m1=0.3,
            act_m2=0.4,
            act_m3=0.5,
            act_m4=0.6,
            act_m5=0.7,
        ),
    ]

    result: PolicyResult = summarize(records, cfg)

    # 1. Tỷ lệ thành công (Wilson score)
    assert result.kind == "learned"
    assert result.n_episodes == 2
    assert result.success_rate.value == pytest.approx(0.5)
    ci_low = result.success_rate.ci_low
    ci_high = result.success_rate.ci_high
    val = result.success_rate.value
    assert ci_low is not None and ci_high is not None and val is not None
    assert 0.0 <= ci_low <= val <= ci_high <= 1.0
    assert result.success_rate.reason is None

    # 2. Khoảng cách cuối (bootstrap CI)
    assert result.final_distance_m.value == pytest.approx(0.030)
    assert result.final_distance_m.n == 2
    assert result.final_distance_m.ci_low is not None
    assert result.final_distance_m.ci_high is not None
    assert result.final_distance_m.reason is None

    # 3. Reward trung bình (bootstrap CI)
    assert result.mean_return.value == pytest.approx(10.0)
    assert result.mean_return.n == 2
    assert result.mean_return.ci_low is not None
    assert result.mean_return.ci_high is not None
    assert result.mean_return.reason is None

    # 4. Nỗ lực (bootstrap CI) và kích hoạt 6 cơ
    assert result.effort.value == pytest.approx(0.40)
    assert len(result.activation_per_muscle) == 6
    assert result.activation_per_muscle[0] == pytest.approx(0.15)
    assert result.activation_per_muscle[5] == pytest.approx(0.65)

    # 5. Tỷ lệ bất thường
    assert result.abnormal_rate.value == pytest.approx(0.0)
    assert result.n_abnormal == 0
    assert result.abnormal_rate.reason is None

    # 6 & 7. Đếm NaN và Inf
    assert result.nan_count == 0
    assert result.inf_count == 0

    # Chuyển đổi từ điển hợp chuẩn báo cáo
    res_dict = result.to_dict()
    assert res_dict["kind"] == "learned"
    assert res_dict["n_episodes"] == 2
    assert res_dict["success_rate"]["value"] == pytest.approx(0.5)


def test_abnormal_excluded_from_distance() -> None:
    """FR-016, AC-1: Episode bất thường bị loại khỏi thống kê khoảng cách cuối."""
    cfg = EvalConfig.load()
    records: list[EpisodeRecord] = [
        _create_record(
            episode=0,
            target_index=0,
            reached=True,
            abnormal=False,
            final_distance_m=0.02,
        ),
        _create_record(
            episode=1,
            target_index=1,
            reached=True,  # Bị bất thường nên tính là không tới mục tiêu
            abnormal=True,
            end_reason="instability",
            final_distance_m=None,
        ),
    ]

    result = summarize(records, cfg)

    # Episode bất thường không được tính tới mục tiêu
    assert result.success_rate.value == pytest.approx(0.5)  # 1 / 2
    assert result.n_abnormal == 1
    assert result.abnormal_rate.value == pytest.approx(0.5)

    # Khoảng cách chỉ tính trên episode hợp lệ (n=1)
    assert result.final_distance_m.n == 1
    assert result.final_distance_m.value == pytest.approx(0.02)
    assert result.final_distance_m.reason is None


def test_all_abnormal_distance_is_null_with_reason() -> None:
    """FR-017, AC-1: Mọi episode kết thúc bất thường thì khoảng cách ghi None kèm lý do."""
    cfg = EvalConfig.load()
    records: list[EpisodeRecord] = [
        _create_record(
            episode=0,
            target_index=0,
            reached=False,
            abnormal=True,
            end_reason="instability",
            final_distance_m=None,
        ),
        _create_record(
            episode=1,
            target_index=1,
            reached=False,
            abnormal=True,
            end_reason="instability",
            final_distance_m=None,
        ),
    ]

    result = summarize(records, cfg)

    assert result.n_abnormal == 2
    assert result.abnormal_rate.value == pytest.approx(1.0)
    assert result.success_rate.value == pytest.approx(0.0)

    # final_distance_m phải có giá trị None kèm lý do tường minh
    assert result.final_distance_m.value is None
    assert result.final_distance_m.ci_low is None
    assert result.final_distance_m.ci_high is None
    assert result.final_distance_m.n == 0
    assert result.final_distance_m.reason is not None
    assert "bất thường" in result.final_distance_m.reason

    # Kiểm tra serialization to_dict giữ đúng None và reason
    d = result.to_dict()
    assert d["final_distance_m"]["value"] is None
    assert d["final_distance_m"]["reason"] is not None


def test_nan_inf_counted_not_averaged() -> None:
    """NFR-REL-001, FR-016: NaN/Inf được đếm riêng, không đưa vào trung bình các chỉ số."""
    cfg = EvalConfig.load()
    records: list[EpisodeRecord] = [
        _create_record(
            episode=0,
            reached=True,
            abnormal=False,
            final_distance_m=0.03,
            nan_count=3,
            inf_count=1,
        ),
        _create_record(
            episode=1,
            reached=False,
            abnormal=False,
            final_distance_m=0.05,
            nan_count=2,
            inf_count=0,
        ),
    ]

    result = summarize(records, cfg)

    assert result.nan_count == 5
    assert result.inf_count == 1
    # Giá trị trung bình không bị ô nhiễm bởi nan_count hay inf_count
    assert math.isfinite(result.final_distance_m.value or 0.0)
    assert math.isfinite(result.mean_return.value or 0.0)
    assert math.isfinite(result.effort.value or 0.0)


def test_aggregate_per_target_repeats_gt_1() -> None:
    """API-EVL-0006: Gộp các lần lặp theo mục tiêu khi repeats > 1."""
    # 2 mục tiêu, mỗi mục tiêu lặp 2 lần (tổng 4 episode)
    records: list[EpisodeRecord] = [
        _create_record(episode=0, target_index=0, reached=True, abnormal=False),
        _create_record(episode=1, target_index=1, reached=True, abnormal=False),
        _create_record(episode=2, target_index=0, reached=False, abnormal=False),
        _create_record(episode=3, target_index=1, reached=True, abnormal=False),
    ]

    agg: AggregatedTargets = aggregate_per_target(records)

    # Mục tiêu 0: 1/2 thành công -> 0.5
    # Mục tiêu 1: 2/2 thành công -> 1.0
    # Tổng k = 0.5 + 1.0 = 1.5; n = 2 mục tiêu
    assert agg.n == 2
    assert agg.k == pytest.approx(1.5)
    assert agg.approximate is True
    assert len(agg) == 2
    assert agg.targets[0].success_rate == pytest.approx(0.5)
    assert agg.targets[1].success_rate == pytest.approx(1.0)


def test_empty_records_summarize_all_null_with_reasons() -> None:
    """FR-017, AC-1: Danh sách records rỗng thì mọi chỉ số ghi nhận None kèm lý do."""
    cfg = EvalConfig.load()
    result = summarize([], cfg)

    assert result.n_episodes == 0
    assert result.n_abnormal == 0
    assert result.nan_count == 0
    assert result.inf_count == 0
    assert result.success_rate.value is None
    assert result.success_rate.reason is not None
    assert result.final_distance_m.value is None
    assert result.final_distance_m.reason is not None
    assert result.mean_return.value is None
    assert result.effort.value is None
    assert result.activation_per_muscle == [None] * 6


def test_summarize_compatible_with_stats_decide() -> None:
    """API-EVL-0006, FR-006: Kết quả summarize tương thích hoàn toàn với stats.decide."""
    from mma_ai.evaluation.stats import decide

    cfg = EvalConfig.load()
    # 10 episode, policy học được thành công 9, random thành công 1
    recs_learned = [
        _create_record(policy="learned", episode=i, reached=(i < 9), abnormal=False)
        for i in range(10)
    ]
    recs_random = [
        _create_record(policy="random", episode=i, reached=(i < 1), abnormal=False)
        for i in range(10)
    ]

    res_learned = summarize(recs_learned, cfg)
    res_random = summarize(recs_random, cfg)

    verdict = decide(res_learned, res_random, level=cfg.criterion.confidence_level)
    assert verdict.difference == pytest.approx(0.8)
    assert verdict.better is True
    assert verdict.ci_low > 0.0


def test_policy_kind_explicit_and_inferred() -> None:
    """API-EVL-0006: Phân loại chính sách theo tham số explicit hoặc tự suy luận."""
    cfg = EvalConfig.load()
    rec_rand = [_create_record(policy="random_policy_v1", episode=0)]
    rec_learn = [_create_record(policy="learned_checkpoint_step_100", episode=0)]

    assert summarize(rec_rand, cfg).kind == "random"
    assert summarize(rec_learn, cfg).kind == "learned"
    assert summarize(rec_rand, cfg, kind="learned").kind == "learned"

