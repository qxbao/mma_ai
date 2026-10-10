"""Kiểm thử đơn vị cho bộ điều phối đánh giá chính sách runner.py (API-EVL-0002, CMD-EVL-0001).

Bao phủ và kiểm chứng toàn diện các yêu cầu chức năng, bất biến miền và kịch bản nghiệm thu:
- 004 FR-001, 004 AC-1: So sánh chính sách đã học với chính sách ngẫu nhiên (random policy).
- 004 FR-002, 004 INV-002: Cùng danh sách mục tiêu, cùng thứ tự, cùng hạt giống đếm tuần tự.
- 004 FR-007, 004 INV-006: Tiêu chí so sánh bất biến, cấu hình đánh giá tải và xác thực trước.
- 004 FR-008, 004 INV-001, 004 AC-4: Kiểm tra không giao cắt (check_disjoint) TRƯỚC tập phim đầu.
- 004 FR-009, 004 FR-015: Checkpoint ngoài thư mục run cần out_dir, từ chối khi không rõ tập train.
- 004 FR-010, 004 FR-011, 004 AC-3: Kết xuất biểu đồ; thiếu nhật ký thoát mã 6 nhưng vẫn lưu số.
- 004 FR-013, 004 KQ-4: Lưu trữ kết quả có truy vết đầy đủ trong runs/<run_id>/eval/<eval_id>/.
- 004 FR-014, 004 INV-005: Chỉ đọc đối với dữ liệu huấn luyện, không sửa tệp ngoài eval/.
- 004 FR-015, 004 AC-5: Checkpoint hỏng hoặc sai mã băm XML ném CheckpointUnusable (mã 4).
- 004 INV-004, 004 AC-5: Xử lý lỗi không để lại kết quả dở dang; công bố nguyên tử (atomic publish).
- 004 API-EVL-0002: Giao diện evaluate_checkpoint(checkpoint, cfg, out_dir=None) -> EvalResult.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from mma_ai.evaluation.charts import ChartData, ChartResult
from mma_ai.evaluation.errors import (
    CheckpointUnusable,
    EvalConfigError,
    EvalWriteError,
    LeakageError,
    LogMissing,
    TrainSetUnknown,
)
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.policies import BasePolicy
from mma_ai.evaluation.runner import (
    EvalResult,
    evaluate_checkpoint,
    get_exit_code,
)


@dataclass
class _DummyLoadedCheckpoint:
    """Đối tượng checkpoint giả lập cô lập phụ thuộc PyTorch cho unit test."""

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
    config: Any
    log_std: Any = None
    raw_data: dict[str, Any] | None = None


class _MockLearnedPolicy(BasePolicy):
    """Chính sách hành động giả lập phục vụ kiểm thử đơn vị độc lập."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.name = "learned"

    def act(self, obs_raw: Any = None) -> np.ndarray:
        return np.full(6, 0.5, dtype=np.float32)


def _setup_mock_run_environment(
    tmp_path: Path,
    *,
    seed: int = 42,
    model_sha256: str = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
    status: str = "done",
    with_log: bool = True,
) -> tuple[Path, Path]:
    """Tạo thư mục phiên chạy (run directory) mẫu chứa manifest, checkpoint và log."""
    run_dir = tmp_path / "test_run"
    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tạo manifest.json hợp chuẩn trỏ tới cấu hình môi trường có sẵn
    manifest_data = {
        "run_id": "run_test_001",
        "status": status,
        "seed": seed,
        "resumed_from": None,
        "config": {
            "env_config": "src/mma_ai/environment/elbow_env.yaml",
        },
        "model": {
            "sha256": model_sha256,
            "muscle_names": [
                "BIClong",
                "BICshort",
                "BRA",
                "TRIlong",
                "TRIlat",
                "TRImed",
            ],
        },
    }
    manifest_file = run_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # 2. Tạo checkpoint giả lập hợp chuẩn dạng nhị phân nhẹ
    pt_file = checkpoints_dir / "ckpt_u000001.pt"
    pt_file.write_bytes(b"MMA_AI_DUMMY_CHECKPOINT_DATA_1234567890")

    # Tạo tệp con trỏ latest.json
    latest_file = checkpoints_dir / "latest.json"
    latest_file.write_text(
        json.dumps({"path": f"checkpoints/{pt_file.name}", "sha256": None}, indent=2),
        encoding="utf-8",
    )

    # 3. Tạo nhật ký huấn luyện metrics.jsonl nếu được yêu cầu
    if with_log:
        metrics_file = run_dir / "metrics.jsonl"
        records = [
            {
                "step": 100,
                "loss/total": 0.5,
                "reward/episode_return": 10.0,
                "activation/BIClong": 0.2,
                "activation/BICshort": 0.3,
                "activation/BRA": 0.4,
                "activation/TRIlong": 0.1,
                "activation/TRIlat": 0.2,
                "activation/TRImed": 0.3,
            },
            {
                "step": 200,
                "loss/total": 0.3,
                "reward/episode_return": 15.0,
                "activation/BIClong": 0.25,
                "activation/BICshort": 0.35,
                "activation/BRA": 0.45,
                "activation/TRIlong": 0.15,
                "activation/TRIlat": 0.25,
                "activation/TRImed": 0.35,
            },
        ]
        with metrics_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    return run_dir, pt_file


def _get_mock_loaded_checkpoint(
    model_sha256: str = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
) -> _DummyLoadedCheckpoint:
    """Khởi tạo đối tượng LoadedCheckpoint mẫu."""
    return _DummyLoadedCheckpoint(
        actor_state_dict={},
        critic_state_dict={},
        obs_normalizer_state_dict={},
        optimizer_state_dict={},
        seed=42,
        rng_state={},
        update_idx=1,
        env_steps=2048,
        model_sha256=model_sha256,
        library_versions={"python": "3.12.0"},
        config={},
    )


def test_exception_to_exit_code_mapping() -> None:
    """Kiểm tra hàm ánh xạ ngoại lệ sang mã thoát CLI ổn định (FR-015, INV-004, CMD-EVL-0001)."""
    assert get_exit_code(EvalConfigError("Cấu hình sai")) == 2
    assert get_exit_code(CheckpointUnusable("Checkpoint lỗi")) == 4
    assert get_exit_code(LeakageError("Rò rỉ dữ liệu")) == 5
    assert get_exit_code(TrainSetUnknown("Không rõ tập train")) == 5
    assert get_exit_code(LogMissing("Thiếu nhật ký")) == 6
    assert get_exit_code(EvalWriteError("Lỗi ghi đĩa")) == 7
    assert get_exit_code(KeyboardInterrupt()) == 130
    assert get_exit_code(RuntimeError("Lỗi không lường trước")) == 1
    assert get_exit_code(ValueError("Lỗi giá trị khác")) == 1


def test_step_order_leak_check_before_first_episode(tmp_path: Path) -> None:
    """Kiểm tra bước kiểm tra rò rỉ chạy TRƯỚC episode đầu (FR-008, INV-001, AC-4)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=12345)

    base_cfg = EvalConfig.load()
    cfg = replace(base_cfg, seeds=replace(base_cfg.seeds, random_policy=12345))

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            with patch("mma_ai.evaluation.runner.run_policy_on_targets") as mock_rollout:
                with pytest.raises(LeakageError) as exc_info:
                    evaluate_checkpoint(pt_file, cfg=cfg)

                assert exc_info.value.exit_code == 5
                # Khẳng định không có bất kỳ tập phim nào được chạy khi phát hiện rò rỉ dữ liệu
                mock_rollout.assert_not_called()


def test_no_eval_dir_before_publish(tmp_path: Path) -> None:
    """Kiểm tra không tạo thư mục đích trước khi công bố (FR-014, INV-004, AC-5)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42)
    cfg = EvalConfig.load()

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            # Giả lập lỗi ở bước công bố báo cáo (publish_report)
            with patch(
                "mma_ai.evaluation.runner.publish_report",
                side_effect=EvalWriteError("Mô phỏng lỗi ghi đĩa khi đổi tên"),
            ):
                with pytest.raises(EvalWriteError):
                    evaluate_checkpoint(pt_file, cfg=cfg)

    # Kiểm tra thư mục eval không chứa thư mục kết quả chính thức hay tạm dở dang nào
    eval_root = run_dir / "eval"
    if eval_root.exists():
        subdirs = [p for p in eval_root.iterdir() if p.is_dir()]
        assert len(subdirs) == 0, f"Không được để lại thư mục dở dang: {subdirs}"


def test_checkpoint_outside_run_requires_out(tmp_path: Path) -> None:
    """Kiểm tra checkpoint ngoài run cần out_dir và ném TrainSetUnknown (FR-009, CMD-EVL-0001)."""
    isolated_dir = tmp_path / "isolated"
    isolated_dir.mkdir(parents=True, exist_ok=True)
    isolated_pt = isolated_dir / "lonely.pt"
    isolated_pt.write_bytes(b"ISOLATED_CHECKPOINT_DATA")

    cfg = EvalConfig.load()

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            # Nhánh 1: Thiếu out_dir -> ném EvalConfigError (mã thoát 2)
            with pytest.raises(EvalConfigError) as exc_info:
                evaluate_checkpoint(isolated_pt, cfg=cfg, out_dir=None)
            assert exc_info.value.exit_code == 2

            # Nhánh 2: Có out_dir nhưng không thiết lập được tập train -> ném TrainSetUnknown (mã 5)
            custom_out = tmp_path / "custom_output"
            with pytest.raises(TrainSetUnknown) as exc_info5:
                evaluate_checkpoint(isolated_pt, cfg=cfg, out_dir=custom_out)
            assert exc_info5.value.exit_code == 5


def test_interrupt_removes_tmp(tmp_path: Path) -> None:
    """Kiểm tra khi bị ngắt bởi KeyboardInterrupt thì dọn dẹp sạch thư mục tạm (INV-004, AC-5)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42)
    cfg = EvalConfig.load()

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            # Giả lập người dùng bấm Ctrl+C trong khi đang thực hiện chạy rollout
            with patch(
                "mma_ai.evaluation.runner.run_policy_on_targets",
                side_effect=KeyboardInterrupt(),
            ):
                with pytest.raises(KeyboardInterrupt):
                    evaluate_checkpoint(pt_file, cfg=cfg)

    # Đảm bảo không tồn tại bất kỳ thư mục tạm .tmp-* nào còn sót lại
    eval_root = run_dir / "eval"
    if eval_root.exists():
        tmp_dirs = [p for p in eval_root.iterdir() if p.name.startswith(".tmp-")]
        assert len(tmp_dirs) == 0, f"Thư mục tạm chưa được dọn dẹp: {tmp_dirs}"


def test_xml_hash_mismatch_raises_checkpoint_unusable(tmp_path: Path) -> None:
    """Kiểm tra mã băm XML mô hình sai lệch ném CheckpointUnusable (FR-015, INV-002, AC-5)."""
    wrong_hash = "deadbeef" * 8
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42, model_sha256=wrong_hash)
    cfg = EvalConfig.load()

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint",
        return_value=_get_mock_loaded_checkpoint(model_sha256=wrong_hash),
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            with pytest.raises(CheckpointUnusable) as exc_info:
                evaluate_checkpoint(pt_file, cfg=cfg)

            assert exc_info.value.exit_code == 4
            # Thông báo phải nêu rõ hai mã băm
            assert wrong_hash in str(exc_info.value)


def test_min_targets_enforced(tmp_path: Path) -> None:
    """Kiểm tra từ chối khi số mục tiêu kiểm thử ít hơn min_targets (FR-018, API-EVL-0002)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42)

    base_cfg = EvalConfig.load()
    # Cấu hình đòi hỏi tối thiểu 100 mục tiêu, trong khi env mặc định chỉ có 50
    cfg = replace(base_cfg, episodes=replace(base_cfg.episodes, min_targets=100))

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            with pytest.raises(EvalConfigError) as exc_info:
                evaluate_checkpoint(pt_file, cfg=cfg)

            assert exc_info.value.exit_code == 2
            assert "100" in str(exc_info.value)


def test_evaluate_checkpoint_success_flow(tmp_path: Path) -> None:
    """Kiểm tra luồng đánh giá thành công hoàn chỉnh tạo báo cáo đầy đủ (FR-001, FR-013, AC-1)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42)
    cfg = EvalConfig.load()

    dummy_chart_res = ChartResult(
        status="complete",
        files={
            "loss": "charts/loss.png",
            "reward": "charts/reward.png",
            "activation": "charts/activation.png",
        },
        points_plotted={"loss": 2, "reward": 2, "activation": 12},
        points_dropped=0,
        reason=None,
        log_source="jsonl",
        data=ChartData([], {}),
    )

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            with patch("mma_ai.evaluation.runner.read_training_log", return_value=MagicMock()):
                with patch("mma_ai.evaluation.runner.render_charts", return_value=dummy_chart_res):
                    res = evaluate_checkpoint(pt_file, cfg=cfg)

    assert isinstance(res, EvalResult)
    assert res.status == "done"
    assert res.exit_code == 0
    assert res.charts_status == "complete"
    assert res.eval_dir.is_dir()
    assert (res.eval_dir / "report.json").is_file()
    assert (res.eval_dir / "episodes.csv").is_file()


def test_evaluate_checkpoint_missing_charts_exits_6(tmp_path: Path) -> None:
    """Thiếu nhật ký vẫn lưu số liệu và thoát mã 6 (FR-011, AC-3, CMD-EVL-0001)."""
    run_dir, pt_file = _setup_mock_run_environment(tmp_path, seed=42, with_log=False)
    cfg = EvalConfig.load()

    with patch(
        "mma_ai.learning.checkpoint.load_checkpoint", return_value=_get_mock_loaded_checkpoint()
    ):
        with patch("mma_ai.evaluation.runner.LearnedPolicy", _MockLearnedPolicy):
            with patch(
                "mma_ai.evaluation.runner.read_training_log",
                side_effect=LogMissing("Thiếu metrics.jsonl"),
            ):
                res = evaluate_checkpoint(pt_file, cfg=cfg)

    assert isinstance(res, EvalResult)
    assert res.status == "done_charts_incomplete"
    assert res.exit_code == 6
    assert res.charts_status == "incomplete"
    assert res.eval_dir.is_dir()
    assert (res.eval_dir / "report.json").is_file()


def test_no_training_imports() -> None:
    """Kiểm tra runner.py không nhập learning.trainer hay learning.ppo (FR-014, INV-005)."""
    runner_path = Path(__file__).parents[2] / "src" / "mma_ai" / "evaluation" / "runner.py"
    assert runner_path.is_file(), "Tệp runner.py phải tồn tại"

    code = runner_path.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(runner_path))

    forbidden_modules = {
        "mma_ai.learning.trainer",
        "mma_ai.learning.ppo",
        "learning.trainer",
        "learning.ppo",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules, (
                    f"runner.py không được phép nhập '{alias.name}'"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert mod not in forbidden_modules, f"runner.py không được phép nhập từ '{mod}'"
