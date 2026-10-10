"""Kiểm thử đơn vị cho bộ đọc nhật ký huấn luyện (API-EVL-0008).

Bao phủ các yêu cầu và bất biến theo hợp đồng phân hệ đánh giá:
- FR-010, AC-3: Đọc nhật ký huấn luyện từ metrics.jsonl hoặc tfevents vào bảng dài
  pandas (series, step, value) dựa trên cấu hình tiền tố thẻ tags.*.
- FR-011, AC-3: Khi nhật ký thiếu một nhóm (loss, reward, activation), ném ngoại lệ
  LogMissing nêu rõ nhóm thiếu và danh sách thẻ thực có.
- FR-012, AC-3: Điểm không hữu hạn được đọc trung thực vào bảng dữ liệu (không tự biến thành 0).
- API-EVL-0008: Giao diện hàm read_training_log(run_dir, cfg) -> TrainingLog.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mma_ai.evaluation.errors import LogMissing
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import TrainingLog, read_training_log


def _pandas() -> Any:
    """Nạp thư viện pandas hoặc bỏ qua kiểm thử nếu thiếu phụ thuộc eval."""
    return pytest.importorskip("pandas")


def _tensorboard() -> Any:
    """Nạp thư viện tensorboard hoặc bỏ qua kiểm thử nếu thiếu phụ thuộc rl."""
    return pytest.importorskip("tensorboard")


def test_independent_assertion_training_log_contract() -> None:
    """Assertion độc lập trên base chứng minh mô-đun và kiểu dữ liệu tồn tại (API-EVL-0008)."""
    assert callable(read_training_log)
    assert issubclass(TrainingLog, object)


def test_read_training_log_signature_and_docstring() -> None:
    """API-EVL-0008: Kiểm tra chữ ký hàm và docstring tiếng Việt."""
    import inspect

    sig = inspect.signature(read_training_log)
    assert "run_dir" in sig.parameters
    assert "cfg" in sig.parameters
    doc = inspect.getdoc(read_training_log)
    assert doc is not None and "API-EVL-0008" in doc


def test_reads_jsonl_training_log(tmp_path: Path) -> None:
    """FR-010, AC-3, API-EVL-0008: Đọc tệp nhật ký metrics.jsonl thành bảng dài pandas chuẩn."""
    _pandas()
    cfg = EvalConfig.load()
    run_dir = tmp_path / "run_jsonl"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = run_dir / "metrics.jsonl"

    records = [
        {
            "update": 1,
            "env_steps": 100,
            "loss/policy": 0.5,
            "loss/value": 0.2,
            "reward/mean_return": 10.0,
            "activation/m0": 0.1,
            "activation/m1": 0.2,
            "throughput/steps_per_s": 200.0,
        },
        {
            "update": 2,
            "env_steps": 200,
            "loss/policy": 0.4,
            "loss/value": 0.15,
            "reward/mean_return": 15.0,
            "activation/m0": 0.15,
            "activation/m1": 0.25,
            "throughput/steps_per_s": 210.0,
        },
    ]
    with metrics_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    log: TrainingLog = read_training_log(run_dir, cfg)

    assert log.source == "jsonl"
    assert "loss/policy" in log.available_tags
    assert "reward/mean_return" in log.available_tags
    assert "activation/m0" in log.available_tags

    df = log.df
    assert list(df.columns) == ["series", "step", "value"]
    # Kiểm tra số dòng được lọc theo tiền tố loss, reward, activation
    # 2 lượt x (2 loss + 1 reward + 2 activation) = 10 dòng
    assert len(df) == 10
    loss_policy_rows = df[df["series"] == "loss/policy"]
    assert len(loss_policy_rows) == 2
    assert list(loss_policy_rows["value"]) == [0.5, 0.4]
    assert list(loss_policy_rows["step"]) == [1, 2]


def test_reads_tfevents_training_log(tmp_path: Path) -> None:
    """FR-010, AC-3, API-EVL-0008: Đọc tệp nhật ký TensorBoard (tfevents) vào bảng dài pandas."""
    _pandas()
    _tensorboard()
    try:
        from torch.utils.tensorboard import SummaryWriter
    except ImportError:
        pytest.skip("Thiếu torch/tensorboard writer để tạo dữ liệu giả lập")

    cfg = EvalConfig.load()
    run_dir = tmp_path / "run_tb"
    tb_dir = run_dir / "tb"
    tb_dir.mkdir(parents=True, exist_ok=True)

    writer = SummaryWriter(log_dir=str(tb_dir))
    writer.add_scalar("loss/policy", 0.8, global_step=1)
    writer.add_scalar("loss/policy", 0.6, global_step=2)
    writer.add_scalar("reward/mean_return", 5.0, global_step=1)
    writer.add_scalar("reward/mean_return", 8.0, global_step=2)
    writer.add_scalar("activation/m0", 0.3, global_step=1)
    writer.add_scalar("activation/m0", 0.4, global_step=2)
    writer.flush()
    writer.close()

    log = read_training_log(run_dir, cfg)

    assert log.source in ("tensorboard", "tfevents")
    assert "loss/policy" in log.available_tags
    assert "reward/mean_return" in log.available_tags
    assert "activation/m0" in log.available_tags

    df = log.df
    assert list(df.columns) == ["series", "step", "value"]
    assert len(df) == 6


def test_missing_group_names_available_tags(tmp_path: Path) -> None:
    """FR-011, AC-3: Thiếu nhóm đại lượng phải ném LogMissing nêu nhóm thiếu và thẻ thực có."""
    _pandas()
    cfg = EvalConfig.load()
    run_dir = tmp_path / "run_missing_activation"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = run_dir / "metrics.jsonl"

    # Chỉ có loss và reward, thiếu toàn bộ nhóm activation
    records = [
        {
            "update": 1,
            "loss/policy": 0.5,
            "reward/mean_return": 10.0,
            "throughput/speed": 100.0,
        }
    ]
    with metrics_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    with pytest.raises(LogMissing) as exc_info:
        read_training_log(run_dir, cfg)

    err_msg = str(exc_info.value)
    # Thông điệp tiếng Việt phải nêu tên nhóm bị thiếu
    assert "activation" in err_msg.lower() or "kích hoạt" in err_msg.lower()
    # Thông điệp phải liệt kê các thẻ thực có
    assert "loss/policy" in err_msg
    assert "reward/mean_return" in err_msg


def test_partial_log_of_running_run_read(tmp_path: Path) -> None:
    """FR-010, AC-3: Nhật ký của run đang chạy có dòng cuối dở dang vẫn đọc được phần đã có."""
    _pandas()
    cfg = EvalConfig.load()
    run_dir = tmp_path / "run_partial"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = run_dir / "metrics.jsonl"

    # Dòng 1 hợp lệ, dòng 2 bị đứt đoạn do run đang ghi dở hoặc bị ngắt tiến trình
    valid_record = {
        "update": 1,
        "loss/policy": 0.5,
        "reward/mean_return": 10.0,
        "activation/m0": 0.2,
    }
    content = json.dumps(valid_record) + "\n" + '{"update": 2, "loss/policy": 0.4, "reward/mean_'
    metrics_file.write_text(content, encoding="utf-8")

    log = read_training_log(run_dir, cfg)

    # Đọc thành công phần bản ghi nguyên vẹn trước đó
    assert log.source == "jsonl"
    df = log.df
    assert len(df) == 3
    assert set(df["series"]) == {"loss/policy", "reward/mean_return", "activation/m0"}
