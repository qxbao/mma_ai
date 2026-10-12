"""Mô-đun dựng và công bố báo cáo đánh giá policy (API-EVL-0010).

Hiện thực kiến trúc functional core / imperative shell:
- Functional core: Dựng cấu trúc dữ liệu báo cáo (build_report), tạo định danh đánh giá
  (generate_eval_id), tổng hợp thông tin giới hạn (limits) và xác thực tính hợp lệ số học
  không chứa NaN/Infinity.
- Imperative shell: Ghi tệp nhật ký tập phim (episodes.csv), ghi báo cáo tạm thời và công bố
  nguyên tử (atomic publish) sang thư mục chính thức bằng thao tác đổi tên (publish_report).

Tuân thủ các yêu cầu và bất biến miền:
- FR-013, AC-1: Lưu bản ghi kết quả đầy đủ trong runs/<run_id>/eval/<eval_id>/ theo
  eval-report.schema.json.
- FR-014, INV-005: Chỉ đọc đối với hồ sơ run, checkpoint và nhật ký huấn luyện; không sửa dữ liệu.
- FR-017, NFR-REL-001: Độ tin cậy số học (numerical reliability), cấm tuyệt đối giá trị
  NaN/Infinity (allow_nan=False).
- FR-019, AC-2: Phân biệt số đo thực tế với giả định; nêu rõ độ rộng khoảng tin cậy và không
  khẳng định chất lượng ngoài đo đạc.
- INV-004, AC-5: Xử lý lỗi không để lại kết quả dở dang; publish_report là bước duy nhất làm
  xuất hiện kết quả.
- INV-006: Tiêu chí so sánh và quy tắc kết luận (better ⇔ ci_low > 0).
"""

from __future__ import annotations

import csv
import importlib.metadata
import json
import math
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from mma_ai.compat.fsio import write_text_atomic
from mma_ai.compat.pathrules import to_record_path
from mma_ai.evaluation.errors import EvalWriteError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import PolicyResult
from mma_ai.evaluation.rollout import EpisodeRecord
from mma_ai.evaluation.split_guard import DisjointnessReport
from mma_ai.evaluation.stats import Verdict


def generate_eval_id(
    episode_base: int,
    timestamp: datetime | None = None,
    existing_ids: Iterable[str] | None = None,
) -> str:
    """Tạo định danh lượt đánh giá (eval_id) duy nhất theo chuẩn UTC và seed đầu (FR-013).

    Mẫu định dạng: YYYYMMDDTHHMMSSZ_e<seed>[-n] (khớp biểu thức chính quy regex trong schema).
    Nếu đã tồn tại id trùng timestamp và seed, tự động thêm hậu tố -1, -2,... để tránh xung đột.

    Tham số:
        episode_base: Hạt giống (seed) cơ sở của tập episode đánh giá.
        timestamp: Thời điểm tạo báo cáo UTC, mặc định là thời gian hiện tại.
        existing_ids: Tập hợp các định danh eval_id đã tồn tại cần tránh trùng lặp.

    Trả về:
        eval_id: Chuỗi định danh lượt đánh giá không trùng lặp.
    """
    ts = timestamp or datetime.now(timezone.utc)
    time_str = ts.strftime("%Y%m%dT%H%M%SZ")
    base_id = f"{time_str}_e{int(episode_base)}"

    existing_set = set(existing_ids) if existing_ids is not None else set()
    if base_id not in existing_set:
        return base_id

    counter = 1
    while True:
        candidate = f"{base_id}-{counter}"
        if candidate not in existing_set:
            return candidate
        counter += 1


def get_library_versions(explicit: Mapping[str, str] | None = None) -> dict[str, str]:
    """Thu thập thông tin phiên bản các thư viện phụ thuộc bắt buộc theo schema JSON.

    Schema yêu cầu 7 thư viện: python, numpy, pandas, matplotlib, torch, gymnasium, mujoco.
    """
    required_libs = [
        "numpy",
        "pandas",
        "matplotlib",
        "torch",
        "gymnasium",
        "mujoco",
    ]
    versions: dict[str, str] = {
        "python": platform.python_version(),
    }

    for lib in required_libs:
        if explicit and lib in explicit:
            versions[lib] = str(explicit[lib])
            continue
        try:
            versions[lib] = importlib.metadata.version(lib)
        except Exception:
            mod = sys.modules.get(lib)
            if mod and hasattr(mod, "__version__"):
                versions[lib] = str(mod.__version__)
            else:
                versions[lib] = "not_installed"

    if explicit:
        for k, v in explicit.items():
            versions[k] = str(v)

    return versions


def _validate_finite_numbers(obj: Any) -> None:
    """Kiểm tra đệ quy để đảm bảo không có giá trị NaN hay vô cực (Infinity) (NFR-REL-001)."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Phát hiện giá trị số học không hữu hạn (NaN hoặc Inf): {obj}")
    elif isinstance(obj, dict):
        for v in obj.values():
            _validate_finite_numbers(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _validate_finite_numbers(item)


def build_report(
    eval_id: str,
    run_id: str,
    run_status: str,
    run_seed: int,
    train_seeds: Sequence[int],
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    update_idx: int | None,
    env_steps: int | None,
    model_sha256: str,
    muscle_names: Sequence[str],
    cfg: EvalConfig,
    disjointness: DisjointnessReport | Mapping[str, Any],
    learned: PolicyResult | Mapping[str, Any],
    random: PolicyResult | Mapping[str, Any],
    verdict: Verdict | Mapping[str, Any],
    charts: Any,
    wall_clock_seconds: float,
    created_utc: datetime | str | None = None,
    device_kind: str = "cpu",
    device_name: str | None = None,
    checkpoint_saved_with: Mapping[str, str] | None = None,
    library_versions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Dựng từ điển báo cáo hoàn chỉnh theo hợp đồng JSON schema (API-EVL-0010).

    Tham số:
        eval_id: Định danh lượt đánh giá chuẩn.
        run_id: Định danh phiên huấn luyện được đánh giá.
        run_status: Trạng thái phiên huấn luyện ('running', 'done', 'error', 'interrupted').
        run_seed: Hạt giống huấn luyện của run.
        train_seeds: Danh sách các hạt giống huấn luyện (gồm run hiện tại và các run cha).
        checkpoint_path: Đường dẫn tương đối của tệp checkpoint so với thư mục run.
        checkpoint_sha256: Mã băm SHA-256 nội dung tệp checkpoint.
        update_idx: Chỉ số cập nhật mô hình (có thể là None).
        env_steps: Số bước môi trường đã huấn luyện (có thể là None).
        model_sha256: Mã băm XML mô hình môi trường.
        muscle_names: Danh sách đúng 6 tên cơ bắp.
        cfg: Cấu hình đánh giá bất biến EvalConfig.
        disjointness: Báo cáo kiểm tra không giao cắt DisjointnessReport hoặc từ điển tương đương.
        learned: Kết quả đo lường của chính sách đã học PolicyResult.
        random: Kết quả đo lường của chính sách ngẫu nhiên PolicyResult.
        verdict: Kết luận so sánh thống kê Verdict.
        charts: Kết quả biểu đồ ChartResult hoặc từ điển biểu đồ.
        wall_clock_seconds: Thời gian chạy thực tế tính bằng giây.
        created_utc: Thời điểm tạo báo cáo UTC.
        device_kind: Loại thiết bị tính toán ('cpu' hoặc 'cuda').
        device_name: Tên chi tiết của thiết bị nếu có.
        checkpoint_saved_with: Phiên bản thư viện lúc lưu checkpoint nếu khác biệt.
        library_versions: Bản đồ phiên bản thư viện ghi đè nếu có.

    Trả về:
        report: Từ điển dữ liệu hợp chuẩn schema eval-report.schema.json.
    """
    if run_status not in {"running", "done", "error", "interrupted"}:
        raise ValueError(f"Trạng thái run_status không hợp lệ: '{run_status}'")

    if len(muscle_names) != 6:
        raise ValueError(f"Danh sách cơ bắp phải có đúng 6 phần tử, nhận được: {len(muscle_names)}")

    # 1. Trạng thái công bố chỉ gồm done hoặc done_charts_incomplete (INV-004)
    charts_dict: dict[str, Any]
    if hasattr(charts, "to_dict"):
        charts_dict = charts.to_dict()
    elif isinstance(charts, Mapping):
        charts_dict = dict(charts)
    else:
        raise ValueError(f"charts phải là ChartResult hoặc từ điển, nhận được: {type(charts)}")

    charts_status = str(charts_dict.get("status", "incomplete"))
    status = "done" if charts_status == "complete" else "done_charts_incomplete"

    # 2. Định dạng thời gian created_utc
    if created_utc is None:
        created_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(created_utc, datetime):
        utc_dt = created_utc.astimezone(timezone.utc)
        created_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        created_str = str(created_utc)

    # 3. Chuẩn hoá đường dẫn checkpoint và charts đảm bảo tương đối
    ckpt_path_str = to_record_path(checkpoint_path)
    if not ckpt_path_str.endswith(".pt"):
        raise ValueError(
            f"Đường dẫn checkpoint phải kết thúc bằng .pt, nhận được: '{ckpt_path_str}'"
        )

    cleaned_charts_files: dict[str, str | None] = {}
    for ch_name in ["loss", "reward", "activation"]:
        raw_val = charts_dict.get("files", {}).get(ch_name)
        if raw_val is not None:
            cleaned_charts_files[ch_name] = to_record_path(raw_val)
        else:
            cleaned_charts_files[ch_name] = None

    # 4. Trích xuất policies và disjointness
    learned_dict = learned.to_dict() if hasattr(learned, "to_dict") else dict(learned)
    random_dict = random.to_dict() if hasattr(random, "to_dict") else dict(random)
    disjoint_dict = (
        disjointness.to_dict() if hasattr(disjointness, "to_dict") else dict(disjointness)
    )

    # 5. Khối so sánh comparison
    learned_sr = float(learned_dict["success_rate"]["value"])
    random_sr = float(random_dict["success_rate"]["value"])
    difference = round(learned_sr - random_sr, 9)

    ci_low = float(verdict.ci_low if hasattr(verdict, "ci_low") else verdict["ci_low"])
    ci_high = float(verdict.ci_high if hasattr(verdict, "ci_high") else verdict["ci_high"])
    better = bool(ci_low > 0.0)  # Bất biến INV-006: better ⇔ ci_low > 0

    n_eval_targets = int(disjoint_dict["n_eval_targets"])
    approximate = bool(cfg.episodes.repeats > 1)

    comparison_dict = {
        "metric": "success_rate",
        "difference": difference,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "confidence_level": float(cfg.criterion.confidence_level),
        "better": better,
        "ci_method": "newcombe_wilson_hybrid",
        "approximate": approximate,
        "n_units_each": n_eval_targets,
        "note": "Xấp xỉ do số lần lặp repeats > 1 (đơn vị phân tích là mục tiêu)"
        if approximate
        else None,
    }

    # 6. Khối thời gian timing
    total_episodes = int(learned_dict["n_episodes"]) + int(random_dict["n_episodes"])
    eps = (
        round(float(total_episodes) / float(wall_clock_seconds), 4)
        if wall_clock_seconds > 0.0
        else None
    )
    timing_dict = {
        "wall_clock_seconds": round(float(wall_clock_seconds), 4),
        "episodes_per_second": eps,
    }

    # 7. Khối giới hạn limits (FR-019)
    ci_width = round(ci_high - ci_low, 3)
    n_ep_each = int(learned_dict["n_episodes"])
    limits = [
        (
            f"{n_ep_each} episode mỗi policy: khoảng tin cậy của hiệu rộng ≈ {ci_width:.2f}; "
            "chênh lệch nhỏ hơn mức này không phát hiện được."
        ),
        (
            "Kết luận chỉ áp cho checkpoint, tập mục tiêu kiểm thử và cấu hình ghi ở trên; "
            "không khẳng định chất lượng policy ngoài số đo này."
        ),
    ]

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "eval_id": eval_id,
        "status": status,
        "created_utc": created_str,
        "run": {
            "run_id": str(run_id),
            "run_status": run_status,
            "seed": int(run_seed),
            "train_seeds": [int(s) for s in train_seeds],
        },
        "checkpoint": {
            "path": ckpt_path_str,
            "sha256": str(checkpoint_sha256),
            "update_idx": int(update_idx) if update_idx is not None else None,
            "env_steps": int(env_steps) if env_steps is not None else None,
            "model_sha256": str(model_sha256),
        },
        "model": {
            "sha256": str(model_sha256),
            "muscle_names": [str(m) for m in muscle_names],
        },
        "library_versions": get_library_versions(library_versions),
        "device": {
            "kind": device_kind,
            "name": str(device_name) if device_name is not None else None,
            "checkpoint_saved_with": dict(checkpoint_saved_with)
            if checkpoint_saved_with
            else None,
        },
        "criterion": {
            "primary_metric": "success_rate",
            "confidence_level": float(cfg.criterion.confidence_level),
            "rule": "better_iff_ci_lower_bound_of_difference_gt_0",
            "declared_before_run": True,
        },
        "config": cfg.as_dict(),
        "disjointness": disjoint_dict,
        "policies": {
            "learned": learned_dict,
            "random": random_dict,
        },
        "comparison": comparison_dict,
        "charts": {
            "status": charts_status,
            "files": cleaned_charts_files,
            "points_plotted": {
                "loss": int(charts_dict.get("points_plotted", {}).get("loss", 0)),
                "reward": int(charts_dict.get("points_plotted", {}).get("reward", 0)),
                "activation": int(charts_dict.get("points_plotted", {}).get("activation", 0)),
            },
            "points_dropped": int(charts_dict.get("points_dropped", 0)),
            "reason": charts_dict.get("reason"),
            "log_source": charts_dict.get("log_source"),
        },
        "timing": timing_dict,
        "limits": limits,
    }

    # Xác thực số học chặt chẽ (NFR-REL-001)
    _validate_finite_numbers(report)

    return report


def write_episodes_csv(records: Sequence[EpisodeRecord], csv_path: Path | str) -> Path:
    """Ghi dữ liệu chi tiết từng tập phim (episode) ra tệp CSV (FR-013, AC-1).

    Các cột: policy, episode, target_index, seed, reached, end_reason, abnormal,
             final_distance_m, return, effort, act_m0..act_m5, n_steps, nan_count, inf_count.
    """
    path = Path(csv_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = [
                "policy",
                "episode",
                "target_index",
                "seed",
                "reached",
                "end_reason",
                "abnormal",
                "final_distance_m",
                "return",
                "effort",
                "act_m0",
                "act_m1",
                "act_m2",
                "act_m3",
                "act_m4",
                "act_m5",
                "n_steps",
                "nan_count",
                "inf_count",
            ]
            writer.writerow(header)

            for r in records:
                ret_val = getattr(r, "return_", getattr(r, "return_val", getattr(r, "return", 0.0)))
                dist_str = (
                    f"{r.final_distance_m:.6f}" if r.final_distance_m is not None else ""
                )
                row = [
                    r.policy,
                    r.episode,
                    r.target_index,
                    r.seed,
                    r.reached,
                    r.end_reason or "",
                    r.abnormal,
                    dist_str,
                    round(float(ret_val), 6),
                    round(float(r.effort), 6),
                    round(float(r.act_m0), 6),
                    round(float(r.act_m1), 6),
                    round(float(r.act_m2), 6),
                    round(float(r.act_m3), 6),
                    round(float(r.act_m4), 6),
                    round(float(r.act_m5), 6),
                    r.n_steps,
                    r.nan_count,
                    r.inf_count,
                ]
                writer.writerow(row)
        return path
    except Exception as err:
        raise EvalWriteError(f"Lỗi khi ghi tệp CSV chi tiết tập phim '{path}': {err}") from err


def save_evaluation_result(
    tmp_dir: Path | str,
    report: dict[str, Any],
    records: Sequence[EpisodeRecord] | None = None,
) -> Path:
    """Ghi cấu trúc báo cáo và dữ liệu tập phim vào thư mục tạm (INV-004, FR-017).

    Từ chối các giá trị không hữu hạn bằng cờ allow_nan=False của json.dumps.
    Nếu ghi thất bại, dọn dẹp thư mục tạm và ném EvalWriteError.
    """
    tmp_path = Path(tmp_dir)
    try:
        tmp_path.mkdir(parents=True, exist_ok=True)
        # Bắt buộc cấm NaN/Infinity theo hợp đồng NFR-REL-001
        payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
        report_file = tmp_path / "report.json"
        write_text_atomic(report_file, payload)

        if records is not None:
            write_episodes_csv(records, tmp_path / "episodes.csv")

        return tmp_path
    except Exception as err:
        shutil.rmtree(tmp_path, ignore_errors=True)
        raise EvalWriteError(
            f"Không thể lưu kết quả đánh giá tạm thời tại '{tmp_path}': {err}"
        ) from err


def publish_report(tmp_dir: Path | str, eval_dir: Path | str) -> Path:
    """Công bố kết quả đánh giá bằng thao tác đổi tên nguyên tử (API-EVL-0010, INV-004).

    Đây là bước DUY NHẤT làm kết quả xuất hiện trên hệ thống tệp.
    Nếu xảy ra lỗi, thư mục tạm bị dọn dẹp ngay lập tức và ném EvalWriteError (mã thoát 7).
    """
    tmp_path = Path(tmp_dir)
    eval_path = Path(eval_dir)

    try:
        eval_path.parent.mkdir(parents=True, exist_ok=True)
        # Sử dụng os.rename để đảm bảo tính nguyên tử (atomic rename)
        os.rename(tmp_path, eval_path)
        return eval_path
    except Exception as err:
        shutil.rmtree(tmp_path, ignore_errors=True)
        raise EvalWriteError(
            f"Không thể công bố kết quả đánh giá từ '{tmp_path}' tới '{eval_path}': {err}"
        ) from err


def prepare_eval_dirs(run_dir: Path | str, eval_id: str) -> tuple[Path, Path]:
    """Tạo đường dẫn thư mục tạm và thư mục đích cho lượt đánh giá (INV-004).

    Cấu trúc:
        eval_dir: runs/<run_id>/eval/<eval_id>/
        tmp_dir: runs/<run_id>/eval/.tmp-<eval_id>/
    """
    eval_root = Path(run_dir) / "eval"
    eval_dir = eval_root / eval_id
    tmp_dir = eval_root / f".tmp-{eval_id}"
    return tmp_dir, eval_dir


__all__: list[str] = [
    "build_report",
    "generate_eval_id",
    "get_library_versions",
    "prepare_eval_dirs",
    "publish_report",
    "save_evaluation_result",
    "write_episodes_csv",
]
