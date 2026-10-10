"""Kiểm thử đơn vị cho mô-đun báo cáo đánh giá report.py (API-EVL-0010).

Hiện thực và kiểm chứng các yêu cầu nghiệp vụ và bất biến:
- FR-013, AC-1: Báo cáo kết quả đầy đủ lưu trong eval/<eval_id>/ kèm định danh, cấu hình và chỉ số.
- FR-014, INV-005: Đánh giá không sửa đổi dữ liệu huấn luyện của con 2; ghi nguyên tử.
- FR-017, NFR-REL-001: Độ tin cậy số học, từ chối giá trị không hữu hạn (NaN/Infinity),
  ghi null kèm lý do.
- FR-019, AC-2: Giới hạn kết luận (limits), phân biệt số đo với giả định, không khẳng định
  chất lượng ngoài đo đạc.
- INV-004, AC-5: Xử lý lỗi không để lại kết quả dở dang; publish_report là bước duy nhất
  làm xuất hiện kết quả.
- INV-006: Tiêu chí so sánh và quy tắc kết luận (better iff ci_low > 0).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from mma_ai.evaluation.errors import EvalWriteError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import MetricStat, PolicyResult
from mma_ai.evaluation.report import (
    build_report,
    generate_eval_id,
    publish_report,
    save_evaluation_result,
    write_episodes_csv,
)
from mma_ai.evaluation.rollout import EpisodeRecord
from mma_ai.evaluation.split_guard import DisjointnessReport
from mma_ai.evaluation.stats import Verdict


def _create_sample_policy_result(
    kind: str = "learned",
    success_rate_val: float = 0.6,
    ci_low: float = 0.462,
    ci_high: float = 0.724,
    n_episodes: int = 50,
) -> PolicyResult:
    """Tạo đối tượng PolicyResult mẫu phục vụ kiểm thử."""
    return PolicyResult(
        kind=kind,
        n_episodes=n_episodes,
        success_rate=MetricStat(
            value=success_rate_val,
            ci_low=ci_low,
            ci_high=ci_high,
            n=n_episodes,
            reason=None,
            k=int(success_rate_val * n_episodes),
        ),
        final_distance_m=MetricStat(
            value=0.031,
            ci_low=0.024,
            ci_high=0.040,
            n=n_episodes,
            reason=None,
        ),
        mean_return=MetricStat(
            value=12.5,
            ci_low=10.1,
            ci_high=14.9,
            n=n_episodes,
            reason=None,
        ),
        effort=MetricStat(
            value=0.41,
            ci_low=0.37,
            ci_high=0.45,
            n=n_episodes,
            reason=None,
        ),
        activation_per_muscle=[0.5, 0.4, 0.3, 0.45, 0.4, 0.41],
        abnormal_rate=MetricStat(
            value=0.0,
            ci_low=0.0,
            ci_high=0.071,
            n=n_episodes,
            reason=None,
        ),
        n_abnormal=0,
        nan_count=0,
        inf_count=0,
    )


def _create_sample_disjointness_report(n_eval_targets: int = 50) -> DisjointnessReport:
    """Tạo đối tượng DisjointnessReport mẫu hợp chuẩn."""
    return DisjointnessReport(
        checked=True,
        passed=True,
        train_target_provenance="rebuilt_from_config",
        target_fingerprint_sha256="c" * 64,
        n_train_targets=200,
        n_eval_targets=n_eval_targets,
        min_cross_distance_m=0.021,
        min_required_m=0.020,
        eval_seed_range=(12345, 12395),
        random_policy_seed=12345,
        train_seeds=(42,),
        n_checked=250,
    )


def _create_sample_charts_dict(status: str = "complete") -> dict[str, Any]:
    """Tạo từ điển biểu đồ mẫu hợp chuẩn."""
    if status == "complete":
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
    return {
        "status": "incomplete",
        "files": {
            "loss": "charts/loss.png",
            "reward": "charts/reward.png",
            "activation": None,
        },
        "points_plotted": {
            "loss": 20,
            "reward": 20,
            "activation": 0,
        },
        "points_dropped": 2,
        "reason": "thiếu chuỗi activation trong nhật ký",
        "log_source": "jsonl",
    }


def _get_eval_report_schema() -> dict[str, Any]:
    """Tải JSON schema chính thức của báo cáo đánh giá."""
    schema_path = (
        Path(__file__).parents[2]
        / "specs"
        / "004-eval-vs-random-plots"
        / "contracts"
        / "eval-report.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def test_eval_id_unique() -> None:
    """Kiểm tra tạo eval_id đúng định dạng regex và đảm bảo tính duy nhất (FR-013)."""
    ts = datetime(2026, 10, 10, 14, 0, 0, tzinfo=timezone.utc)
    id1 = generate_eval_id(episode_base=12345, timestamp=ts)
    assert id1 == "20261010T140000Z_e12345"

    # Khi đã tồn tại id1, bộ sinh tạo id mới với hậu tố chống trùng lặp
    existing = {id1}
    id2 = generate_eval_id(episode_base=12345, timestamp=ts, existing_ids=existing)
    assert id2 == "20261010T140000Z_e12345-1"
    assert id2 != id1

    existing.add(id2)
    id3 = generate_eval_id(episode_base=12345, timestamp=ts, existing_ids=existing)
    assert id3 == "20261010T140000Z_e12345-2"


def test_limits_present_and_no_quality_claim() -> None:
    """Kiểm tra limits hiện diện, nêu khoảng tin cậy và không khẳng định chất lượng (FR-019)."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned", success_rate_val=0.6)
    random = _create_sample_policy_result("random", success_rate_val=0.2)
    verdict = Verdict(better=True, difference=0.4, ci_low=0.21, ci_high=0.552)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=12.5,
    )

    limits = report["limits"]
    assert isinstance(limits, list)
    assert len(limits) >= 2

    # Phải nêu rõ số episode và độ rộng khoảng tin cậy
    joined_limits = " ".join(limits)
    assert "episode" in joined_limits
    assert "khoảng tin cậy" in joined_limits

    # Không khẳng định chất lượng policy ngoài kết quả đo
    assert "không khẳng định chất lượng policy ngoài" in joined_limits


def test_report_validates_schema_and_no_nonfinite() -> None:
    """Kiểm tra báo cáo hợp chuẩn JSON schema và không chứa NaN/Infinity (FR-013, NFR-REL-001)."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned", success_rate_val=0.6)
    random = _create_sample_policy_result("random", success_rate_val=0.2)
    verdict = Verdict(better=True, difference=0.4, ci_low=0.21, ci_high=0.552)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=10.0,
    )

    # 1. Kiểm tra không có NaN / Infinity khi serialize
    serialized = json.dumps(report, allow_nan=False)
    assert serialized is not None

    # 2. Xác thực cấu trúc chặt chẽ theo json schema
    schema = _get_eval_report_schema()
    jsonschema.validate(instance=report, schema=schema)


def test_difference_equals_rates_minus() -> None:
    """Kiểm tra difference trong comparison bằng đúng hiệu tỷ lệ hai policy (FR-006, INV-006)."""
    cfg = EvalConfig.load()
    learned_sr = 0.55
    random_sr = 0.15
    learned = _create_sample_policy_result("learned", success_rate_val=learned_sr)
    random = _create_sample_policy_result("random", success_rate_val=random_sr)
    verdict = Verdict(better=True, difference=0.40, ci_low=0.15, ci_high=0.58)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=8.0,
    )

    comparison = report["comparison"]
    expected_diff = learned_sr - random_sr
    assert abs(comparison["difference"] - expected_diff) <= 1e-9
    assert comparison["better"] is True
    assert comparison["ci_low"] > 0


def test_publish_is_atomic_rename(tmp_path: Path) -> None:
    """Kiểm tra publish_report đổi tên nguyên tử từ thư mục tạm sang đích (INV-004, FR-013)."""
    run_dir = tmp_path / "run_test"
    eval_root = run_dir / "eval"
    eval_root.mkdir(parents=True)

    eval_id = "20261010T140000Z_e12345"
    tmp_dir = eval_root / f".tmp-{eval_id}"
    final_dir = eval_root / eval_id

    tmp_dir.mkdir(parents=True)
    report_file = tmp_dir / "report.json"
    report_file.write_text('{"status": "done"}', encoding="utf-8")

    # Trước khi publish: thư mục đích chưa tồn tại, thư mục tạm có tồn tại
    assert tmp_dir.exists()
    assert not final_dir.exists()

    result_path = publish_report(tmp_dir, final_dir)

    # Sau khi publish: thư mục tạm biến mất, thư mục đích xuất hiện
    assert result_path == final_dir
    assert not tmp_dir.exists()
    assert final_dir.exists()
    assert (final_dir / "report.json").exists()


def test_failure_removes_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra khi xảy ra lỗi, thư mục tạm bị dọn dẹp và ném EvalWriteError (INV-004, FR-015)."""
    eval_root = tmp_path / "eval"
    eval_root.mkdir(parents=True)
    eval_id = "20261010T140000Z_e12345"
    tmp_dir = eval_root / f".tmp-{eval_id}"
    final_dir = eval_root / eval_id

    tmp_dir.mkdir(parents=True)
    (tmp_dir / "dummy.txt").write_text("tam thoi", encoding="utf-8")

    # Giả lập lỗi I/O trong thao tác đổi tên
    def mock_rename(src: Any, dst: Any) -> None:
        raise OSError("Không thể ghi đĩa hoặc thiếu quyền truy cập.")

    monkeypatch.setattr("os.rename", mock_rename)

    with pytest.raises(EvalWriteError) as exc_info:
        publish_report(tmp_dir, final_dir)

    assert exc_info.value.exit_code == 7
    # Thư mục tạm phải bị dọn dẹp sạch sẽ
    assert not tmp_dir.exists()
    assert not final_dir.exists()


def test_paths_relative() -> None:
    """Kiểm tra các đường dẫn trong báo cáo luôn là đường dẫn tương đối (FR-013)."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned")
    random = _create_sample_policy_result("random")
    verdict = Verdict(better=True, difference=0.4, ci_low=0.2, ci_high=0.5)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=10.0,
    )

    ckpt_path = report["checkpoint"]["path"]
    assert not ckpt_path.startswith("/")
    assert ckpt_path.endswith(".pt")

    for chart_key, c_path in report["charts"]["files"].items():
        if c_path is not None:
            assert not c_path.startswith("/")
            assert c_path.endswith(".png")


def test_write_episodes_csv(tmp_path: Path) -> None:
    """Kiểm tra xuất tệp episodes.csv đúng định dạng tiêu đề và các trường (FR-013, AC-1)."""
    records = [
        EpisodeRecord(
            policy="learned",
            episode=0,
            target_index=0,
            seed=12345,
            reached=True,
            end_reason="reached",
            abnormal=False,
            final_distance_m=0.012,
            return_=15.2,
            effort=0.35,
            act_m0=0.4,
            act_m1=0.3,
            act_m2=0.2,
            act_m3=0.5,
            act_m4=0.4,
            act_m5=0.3,
            n_steps=45,
            nan_count=0,
            inf_count=0,
        )
    ]

    csv_path = tmp_path / "episodes.csv"
    write_episodes_csv(records, csv_path)

    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert len(lines) == 2
    header = lines[0].split(",")
    assert header == [
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
    row = lines[1].split(",")
    assert row[0] == "learned"
    assert row[1] == "0"
    assert row[4] == "True"
    assert row[8] == "15.2"


def test_save_evaluation_result_rejects_nonfinite(tmp_path: Path) -> None:
    """Kiểm tra lưu kết quả từ chối NaN/Infinity và ném lỗi EvalWriteError (FR-017, NFR-REL-001)."""
    bad_report = {"invalid_nan": float("nan")}
    with pytest.raises(EvalWriteError):
        save_evaluation_result(tmp_path, bad_report)


def test_done_charts_incomplete_status() -> None:
    """Kiểm tra biểu đồ chưa hoàn tất thì trạng thái là done_charts_incomplete (AC-3, INV-004)."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned")
    random = _create_sample_policy_result("random")
    verdict = Verdict(better=True, difference=0.4, ci_low=0.2, ci_high=0.5)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("incomplete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=10.0,
    )

    assert report["status"] == "done_charts_incomplete"
    assert report["charts"]["status"] == "incomplete"
    schema = _get_eval_report_schema()
    jsonschema.validate(instance=report, schema=schema)


def test_null_distance_when_all_abnormal() -> None:
    """Kiểm tra khi mọi episode bất thường thì khoảng cách là null kèm lý do (FR-017)."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned")
    # Random policy có mọi episode abnormal
    random = PolicyResult(
        kind="random",
        n_episodes=50,
        success_rate=MetricStat(value=0.0, ci_low=0.0, ci_high=0.071, n=50, reason=None, k=0),
        final_distance_m=MetricStat(
            value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            reason="mọi episode kết thúc bất thường",
        ),
        mean_return=MetricStat(value=3.2, ci_low=2.4, ci_high=4.0, n=50, reason=None),
        effort=MetricStat(value=0.5, ci_low=0.49, ci_high=0.51, n=50, reason=None),
        activation_per_muscle=[0.5] * 6,
        abnormal_rate=MetricStat(value=1.0, ci_low=0.929, ci_high=1.0, n=50, reason=None, k=50),
        n_abnormal=50,
        nan_count=0,
        inf_count=0,
    )
    verdict = Verdict(better=True, difference=0.6, ci_low=0.4, ci_high=0.7)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    report = build_report(
        eval_id="20261010T140000Z_e12345",
        run_id="20261010T130000Z_elbow_s42",
        run_status="done",
        run_seed=42,
        train_seeds=[42],
        checkpoint_path="checkpoints/ckpt_final.pt",
        checkpoint_sha256="a" * 64,
        update_idx=20,
        env_steps=40960,
        model_sha256="b" * 64,
        muscle_names=["m0", "m1", "m2", "m3", "m4", "m5"],
        cfg=cfg,
        disjointness=disjointness,
        learned=learned,
        random=random,
        verdict=verdict,
        charts=charts,
        wall_clock_seconds=10.0,
    )

    rand_stat = report["policies"]["random"]["final_distance_m"]
    assert rand_stat["value"] is None
    assert rand_stat["reason"] == "mọi episode kết thúc bất thường"
    schema = _get_eval_report_schema()
    jsonschema.validate(instance=report, schema=schema)


def test_invalid_parameters_raise() -> None:
    """Kiểm tra các tham số đầu vào không hợp lệ bị từ chối với ValueError."""
    cfg = EvalConfig.load()
    learned = _create_sample_policy_result("learned")
    random = _create_sample_policy_result("random")
    verdict = Verdict(better=True, difference=0.4, ci_low=0.2, ci_high=0.5)
    disjointness = _create_sample_disjointness_report(50)
    charts = _create_sample_charts_dict("complete")

    # Sai run_status
    with pytest.raises(ValueError, match="run_status"):
        build_report(
            eval_id="20261010T140000Z_e12345",
            run_id="r1",
            run_status="invalid_status",
            run_seed=42,
            train_seeds=[42],
            checkpoint_path="checkpoints/ckpt.pt",
            checkpoint_sha256="a" * 64,
            update_idx=0,
            env_steps=0,
            model_sha256="b" * 64,
            muscle_names=["m0"] * 6,
            cfg=cfg,
            disjointness=disjointness,
            learned=learned,
            random=random,
            verdict=verdict,
            charts=charts,
            wall_clock_seconds=5.0,
        )

    # Sai số lượng cơ bắp
    with pytest.raises(ValueError, match="cơ bắp"):
        build_report(
            eval_id="20261010T140000Z_e12345",
            run_id="r1",
            run_status="done",
            run_seed=42,
            train_seeds=[42],
            checkpoint_path="checkpoints/ckpt.pt",
            checkpoint_sha256="a" * 64,
            update_idx=0,
            env_steps=0,
            model_sha256="b" * 64,
            muscle_names=["m0"] * 5,
            cfg=cfg,
            disjointness=disjointness,
            learned=learned,
            random=random,
            verdict=verdict,
            charts=charts,
            wall_clock_seconds=5.0,
        )

    # Sai phần mở rộng checkpoint
    with pytest.raises(ValueError, match=r"\.pt"):
        build_report(
            eval_id="20261010T140000Z_e12345",
            run_id="r1",
            run_status="done",
            run_seed=42,
            train_seeds=[42],
            checkpoint_path="checkpoints/ckpt.pth",
            checkpoint_sha256="a" * 64,
            update_idx=0,
            env_steps=0,
            model_sha256="b" * 64,
            muscle_names=["m0"] * 6,
            cfg=cfg,
            disjointness=disjointness,
            learned=learned,
            random=random,
            verdict=verdict,
            charts=charts,
            wall_clock_seconds=5.0,
        )

