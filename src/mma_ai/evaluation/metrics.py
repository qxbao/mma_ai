"""Mô-đun tính toán chỉ số đánh giá và đọc nhật ký huấn luyện (API-EVL-0006, API-EVL-0008).

Hiện thực kiến trúc functional core / imperative shell:
- Functional core: Tính toán bảy nhóm chỉ số chính sách (summarize), gộp theo mục tiêu
  (aggregate_per_target) bằng thuật toán thuần túy giải tích, không thực hiện I/O.
- Imperative shell: Đọc nhật ký huấn luyện từ tệp JSONL hoặc tfevents TensorBoard
  (read_training_log) thành bảng dữ liệu dài (long-form table).

Tuân thủ các yêu cầu và bất biến:
- FR-004, AC-1: Bảy nhóm chỉ số: tỷ lệ thành công (success rate), khoảng cách cuối (final distance),
  reward trung bình (mean return), nỗ lực (effort) kèm 6 cơ, tỷ lệ bất thường (abnormal rate),
  số NaN và số Inf.
- FR-010, FR-011, AC-3: Đọc nhật ký huấn luyện theo tiền tố thẻ cấu hình được, ném LogMissing
  khi thiếu nhóm chỉ số kèm danh sách thẻ thực có.
- FR-016, FR-017: Loại trừ episode bất thường khỏi khoảng cách cuối, ghi nhận giá trị None kèm lý do
  tường minh khi không có dữ liệu hợp lệ, không ghi nhận 0 hay NaN.
- NFR-REL-001: Độ tin cậy số học (numerical reliability), không rò rỉ giá trị không hữu hạn.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from mma_ai.evaluation.errors import LogMissing
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.rollout import EpisodeRecord
from mma_ai.evaluation.stats import bootstrap_mean_ci, wilson_interval


@dataclass(frozen=True)
class MetricStat:
    """Thống kê của một đại lượng đo lường kèm khoảng tin cậy (confidence interval)."""

    value: float | None
    ci_low: float | None
    ci_high: float | None
    n: int
    reason: str | None = None
    k: float | int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin thống kê sang định dạng từ điển chuẩn schema JSON."""
        return {
            "value": self.value,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "n": self.n,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PolicyResult:
    """Kết quả đo lường và thống kê hoàn chỉnh của một chính sách (policy)."""

    kind: str
    n_episodes: int
    success_rate: MetricStat
    final_distance_m: MetricStat
    mean_return: MetricStat
    effort: MetricStat
    activation_per_muscle: list[float | None]
    abnormal_rate: MetricStat
    n_abnormal: int
    nan_count: int
    inf_count: int

    def to_dict(self) -> dict[str, Any]:
        """Xuất toàn bộ kết quả chính sách sang định dạng từ điển hợp chuẩn báo cáo."""
        return {
            "kind": self.kind,
            "n_episodes": self.n_episodes,
            "success_rate": self.success_rate.to_dict(),
            "final_distance_m": self.final_distance_m.to_dict(),
            "mean_return": self.mean_return.to_dict(),
            "effort": self.effort.to_dict(),
            "activation_per_muscle": list(self.activation_per_muscle),
            "abnormal_rate": self.abnormal_rate.to_dict(),
            "n_abnormal": self.n_abnormal,
            "nan_count": self.nan_count,
            "inf_count": self.inf_count,
        }


@dataclass(frozen=True)
class TargetAggregate:
    """Kết quả tổng hợp các lần lặp lại cho một mục tiêu kiểm thử duy nhất."""

    target_index: int
    n_repeats: int
    success_rate: float
    reached_count: int
    abnormal_count: int


@dataclass(frozen=True)
class AggregatedTargets:
    """Kết quả tổng hợp toàn bộ các mục tiêu khi số lần lặp repeats > 1."""

    targets: dict[int, TargetAggregate]
    k: float
    n: int
    approximate: bool = True

    def __len__(self) -> int:
        return len(self.targets)

    def __iter__(self) -> Any:
        return iter(self.targets)

    def __getitem__(self, key: int) -> TargetAggregate:
        return self.targets[key]


@dataclass(frozen=True)
class TrainingLog:
    """Nhật ký huấn luyện dạng bảng dài (series, step, value) đã thẩm định."""

    df: Any
    source: str
    available_tags: list[str]

    @property
    def dataframe(self) -> Any:
        """Thuộc tính truy cập bảng dữ liệu DataFrame."""
        return self.df


def _sanitize_finite(val: float | None) -> float | None:
    """Đảm bảo giá trị là số thực hữu hạn (finite number), chuyển NaN/Inf thành None."""
    if val is None or not math.isfinite(val):
        return None
    return float(val)


def summarize(
    records: Sequence[EpisodeRecord],
    cfg: EvalConfig,
    kind: str | None = None,
) -> PolicyResult:
    """Tính toán bảy nhóm chỉ số đánh giá cho một chính sách (API-EVL-0006).

    Args:
        records: Danh sách bản ghi episode thu thập từ rollout.
        cfg: Cấu hình đánh giá chứa mức tin cậy và tham số bootstrap.
        kind: Nhãn phân loại chính sách ('learned' hoặc 'random'), tự suy luận nếu None.

    Returns:
        PolicyResult: Kết quả đo lường và khoảng tin cậy của chính sách.
    """
    n_episodes = len(records)

    # 1. Xác định phân loại chính sách (policy kind)
    if kind is not None:
        resolved_kind = kind
    elif n_episodes > 0:
        pol_raw = records[0].policy.lower()
        resolved_kind = "random" if "random" in pol_raw else "learned"
    else:
        resolved_kind = "learned"

    # 2. Đếm số lượng giá trị không hữu hạn phát hiện (NFR-REL-001, FR-016)
    total_nan = int(sum(r.nan_count for r in records))
    total_inf = int(sum(r.inf_count for r in records))

    # 3. Thống kê tỷ lệ kết thúc bất thường (abnormal_rate) (FR-016)
    n_abnormal = int(sum(1 for r in records if r.abnormal))
    conf_level = cfg.criterion.confidence_level

    if n_episodes > 0:
        abn_val = float(n_abnormal / n_episodes)
        abn_low, abn_high = wilson_interval(n_abnormal, n_episodes, level=conf_level)
        abnormal_rate = MetricStat(
            value=_sanitize_finite(abn_val),
            ci_low=_sanitize_finite(abn_low),
            ci_high=_sanitize_finite(abn_high),
            n=n_episodes,
            reason=None,
            k=n_abnormal,
        )
    else:
        abnormal_rate = MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason="không có dữ liệu episode",
            k=0,
        )

    # 4. Thống kê tỷ lệ tới mục tiêu (success_rate) (FR-004, FR-016)
    # Episode bất thường luôn bị tính là không tới mục tiêu
    k_success = int(sum(1 for r in records if r.reached and not r.abnormal))
    if n_episodes > 0:
        succ_val = float(k_success / n_episodes)
        succ_low, succ_high = wilson_interval(k_success, n_episodes, level=conf_level)
        success_rate = MetricStat(
            value=_sanitize_finite(succ_val),
            ci_low=_sanitize_finite(succ_low),
            ci_high=_sanitize_finite(succ_high),
            n=n_episodes,
            reason=None,
            k=k_success,
        )
    else:
        success_rate = MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason="không có dữ liệu episode",
            k=0,
        )

    # 5. Thống kê khoảng cách cuối (final_distance_m) (FR-004, FR-016, FR-017)
    # Loại trừ toàn bộ episode bất thường và episode thiếu số đo khoảng cách
    valid_distances = [
        float(r.final_distance_m)
        for r in records
        if not r.abnormal and r.final_distance_m is not None and math.isfinite(r.final_distance_m)
    ]
    if valid_distances:
        dist_mean = float(np.mean(valid_distances))
        dist_low, dist_high = bootstrap_mean_ci(
            valid_distances,
            level=conf_level,
            resamples=cfg.stats.bootstrap_resamples,
            seed=cfg.stats.bootstrap_seed,
        )
        final_distance_m = MetricStat(
            value=_sanitize_finite(dist_mean),
            ci_low=_sanitize_finite(dist_low),
            ci_high=_sanitize_finite(dist_high),
            n=len(valid_distances),
            reason=None,
        )
    else:
        if n_episodes > 0 and n_abnormal == n_episodes:
            dist_reason = "mọi episode kết thúc bất thường"
        else:
            dist_reason = "không có dữ liệu khoảng cách hợp lệ"
        final_distance_m = MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason=dist_reason,
        )

    # 6. Thống kê phần thưởng trung bình (mean_return) (FR-004)
    valid_returns = [float(r.return_) for r in records if math.isfinite(r.return_)]
    if valid_returns:
        ret_mean = float(np.mean(valid_returns))
        ret_low, ret_high = bootstrap_mean_ci(
            valid_returns,
            level=conf_level,
            resamples=cfg.stats.bootstrap_resamples,
            seed=cfg.stats.bootstrap_seed,
        )
        mean_return = MetricStat(
            value=_sanitize_finite(ret_mean),
            ci_low=_sanitize_finite(ret_low),
            ci_high=_sanitize_finite(ret_high),
            n=len(valid_returns),
            reason=None,
        )
    else:
        mean_return = MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason="không có dữ liệu episode",
        )

    # 7. Thống kê nỗ lực cơ bắp (effort) (FR-004)
    valid_efforts = [float(r.effort) for r in records if math.isfinite(r.effort)]
    if valid_efforts:
        eff_mean = float(np.mean(valid_efforts))
        eff_low, eff_high = bootstrap_mean_ci(
            valid_efforts,
            level=conf_level,
            resamples=cfg.stats.bootstrap_resamples,
            seed=cfg.stats.bootstrap_seed,
        )
        effort_stat = MetricStat(
            value=_sanitize_finite(eff_mean),
            ci_low=_sanitize_finite(eff_low),
            ci_high=_sanitize_finite(eff_high),
            n=len(valid_efforts),
            reason=None,
        )
    else:
        effort_stat = MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason="không có dữ liệu episode",
        )

    # 8. Kích hoạt trung bình từng cơ trong 6 cơ (activation_per_muscle) (FR-004)
    activation_per_muscle: list[float | None] = []
    if n_episodes > 0:
        for m in range(6):
            muscle_acts = [
                float(getattr(r, f"act_m{m}"))
                for r in records
                if math.isfinite(getattr(r, f"act_m{m}"))
            ]
            if muscle_acts:
                activation_per_muscle.append(_sanitize_finite(float(np.mean(muscle_acts))))
            else:
                activation_per_muscle.append(None)
    else:
        activation_per_muscle = [None] * 6

    return PolicyResult(
        kind=resolved_kind,
        n_episodes=n_episodes,
        success_rate=success_rate,
        final_distance_m=final_distance_m,
        mean_return=mean_return,
        effort=effort_stat,
        activation_per_muscle=activation_per_muscle,
        abnormal_rate=abnormal_rate,
        n_abnormal=n_abnormal,
        nan_count=total_nan,
        inf_count=total_inf,
    )


def aggregate_per_target(records: Sequence[EpisodeRecord]) -> AggregatedTargets:
    """Gộp các episode theo từng mục tiêu kiểm thử khi repeats > 1 (API-EVL-0006).

    Args:
        records: Danh sách bản ghi episode thu thập từ rollout.

    Returns:
        AggregatedTargets: Đối tượng chứa thống kê gộp theo mục tiêu kèm tổng k và n.
    """
    grouped: dict[int, list[EpisodeRecord]] = {}
    for r in records:
        grouped.setdefault(r.target_index, []).append(r)

    targets: dict[int, TargetAggregate] = {}
    total_k = 0.0

    for target_idx, recs in grouped.items():
        n_rep = len(recs)
        reached_cnt = sum(1 for r in recs if r.reached and not r.abnormal)
        abn_cnt = sum(1 for r in recs if r.abnormal)
        succ_rate = float(reached_cnt / n_rep) if n_rep > 0 else 0.0
        total_k += succ_rate
        targets[target_idx] = TargetAggregate(
            target_index=target_idx,
            n_repeats=n_rep,
            success_rate=succ_rate,
            reached_count=reached_cnt,
            abnormal_count=abn_cnt,
        )

    n_targets = len(targets)
    return AggregatedTargets(
        targets=targets,
        k=total_k,
        n=n_targets,
        approximate=True,
    )


def _validate_log_groups(
    available_tags: list[str],
    loss_pfx: str,
    reward_pfx: str,
    activation_pfx: str,
    run_path: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Kiểm tra sự hiện diện của ba nhóm chỉ số trong danh sách thẻ nhật ký (FR-011)."""
    loss_tags = [t for t in available_tags if t.startswith(loss_pfx)]
    reward_tags = [t for t in available_tags if t.startswith(reward_pfx)]
    activation_tags = [t for t in available_tags if t.startswith(activation_pfx)]

    missing_groups: list[str] = []
    if not loss_tags:
        missing_groups.append(f"loss (tiền tố '{loss_pfx}')")
    if not reward_tags:
        missing_groups.append(f"reward (tiền tố '{reward_pfx}')")
    if not activation_tags:
        missing_groups.append(f"activation (tiền tố '{activation_pfx}')")

    if missing_groups:
        tags_str = ", ".join(f"'{t}'" for t in available_tags) if available_tags else "trống"
        raise LogMissing(
            f"Nhật ký huấn luyện tại '{run_path}' bị thiếu các nhóm chỉ số bắt buộc: "
            f"{', '.join(missing_groups)}. "
            f"Danh sách các thẻ (tags) thực có: [{tags_str}]."
        )

    return loss_tags, reward_tags, activation_tags


def read_training_log(run_dir: str | Path, cfg: EvalConfig) -> TrainingLog:
    """Đọc nhật ký huấn luyện từ metrics.jsonl hoặc tfevents TensorBoard (API-EVL-0008).

    Args:
        run_dir: Thư mục chứa nhật ký huấn luyện của run.
        cfg: Cấu hình đánh giá chỉ định nguồn dữ liệu (logs.source) và tiền tố thẻ.

    Returns:
        TrainingLog: Đối tượng chứa bảng dài DataFrame (series, step, value) và nguồn dữ liệu.

    Raises:
        LogMissing: Khi không tìm thấy nhật ký hoặc thiếu bất kỳ nhóm nào trong 3 nhóm.
        ImportError: Khi thiếu thư viện bổ trợ pandas hoặc tensorboard.
    """
    try:
        import pandas as pd
    except ImportError as err:
        raise ImportError(
            "Cần cài đặt thư viện 'pandas' (nhóm phụ thuộc tùy chọn 'eval') để đọc nhật ký."
        ) from err

    path = Path(run_dir)
    source_cfg = cfg.logs.source.lower()
    tags_cfg = cfg.logs.tags
    loss_pfx = tags_cfg.loss_prefix
    reward_pfx = tags_cfg.reward_prefix
    activation_pfx = tags_cfg.activation_prefix

    # Nhánh 1: Đọc tệp metrics.jsonl nếu được cấu hình hoặc ở chế độ tự động (auto)
    metrics_file = path / "metrics.jsonl"
    if source_cfg in ("jsonl", "auto") and metrics_file.is_file():
        parsed_records: list[dict[str, Any]] = []
        with metrics_file.open("r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    parsed_records.append(json.loads(line_str))
                except Exception:
                    # Bỏ qua dòng dở dang do tiến trình huấn luyện chưa hoàn tất (FR-010)
                    continue

        if parsed_records:
            all_tags_set: set[str] = set()
            for r in parsed_records:
                for k in r:
                    if k not in ("update", "env_steps", "step"):
                        all_tags_set.add(k)
            available_tags = sorted(all_tags_set)

            loss_tags, reward_tags, activation_tags = _validate_log_groups(
                available_tags, loss_pfx, reward_pfx, activation_pfx, path
            )
            target_tags = set(loss_tags + reward_tags + activation_tags)

            rows: list[dict[str, Any]] = []
            for idx, r in enumerate(parsed_records):
                step_val = r.get("update", r.get("step", r.get("env_steps", idx + 1)))
                for tag in target_tags:
                    if tag in r:
                        raw_val = r[tag]
                        try:
                            num_val = float(raw_val)
                        except (ValueError, TypeError):
                            continue
                        rows.append(
                            {
                                "series": tag,
                                "step": int(step_val),
                                "value": num_val,
                            }
                        )

            df = pd.DataFrame(rows, columns=["series", "step", "value"])
            return TrainingLog(df=df, source="jsonl", available_tags=available_tags)

        if source_cfg == "jsonl":
            raise LogMissing(
                f"Tệp nhật ký JSONL tại '{metrics_file}' rỗng hoặc không có bản ghi hợp lệ."
            )

    # Nhánh 2: Đọc sự kiện TensorBoard (tfevents) nếu được cấu hình hoặc chế độ auto
    tb_candidates = [path / "tb", path]
    tb_dir: Path | None = None
    for cand in tb_candidates:
        if cand.is_dir() and any(cand.glob("events.out.tfevents.*")):
            tb_dir = cand
            break

    if source_cfg in ("tensorboard", "tfevents", "auto") and tb_dir is not None:
        try:
            from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
        except ImportError as err:
            raise ImportError(
                "Cần cài đặt thư viện 'tensorboard' (nhóm phụ thuộc tùy chọn 'rl') "
                "để đọc tệp sự kiện TensorBoard."
            ) from err

        ea = EventAccumulator(str(tb_dir), size_guidance={"scalars": 0})
        ea.Reload()
        tags_dict = ea.Tags()
        scalar_tags = sorted(tags_dict.get("scalars", []))

        loss_tags, reward_tags, activation_tags = _validate_log_groups(
            scalar_tags, loss_pfx, reward_pfx, activation_pfx, path
        )
        target_tags = set(loss_tags + reward_tags + activation_tags)

        rows = []
        for tag in target_tags:
            events = ea.Scalars(tag)
            for ev in events:
                rows.append(
                    {
                        "series": tag,
                        "step": int(ev.step),
                        "value": float(ev.value),
                    }
                )

        # Sắp xếp theo thứ tự bước huấn luyện
        rows.sort(key=lambda item: (item["series"], item["step"]))
        df = pd.DataFrame(rows, columns=["series", "step", "value"])
        return TrainingLog(df=df, source="tensorboard", available_tags=scalar_tags)

    # Không tìm thấy bất kỳ nguồn nhật ký hợp lệ nào
    raise LogMissing(
        f"Không tìm thấy nhật ký huấn luyện (metrics.jsonl hoặc tfevents) tại '{path}'."
    )


__all__: list[str] = [
    "AggregatedTargets",
    "MetricStat",
    "PolicyResult",
    "TargetAggregate",
    "TrainingLog",
    "aggregate_per_target",
    "read_training_log",
    "summarize",
]
