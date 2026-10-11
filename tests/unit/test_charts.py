"""Kiểm thử đơn vị kết xuất biểu đồ đánh giá không cần màn hình (API-EVL-0009).

Chứng minh các yêu cầu và bất biến:
- FR-010, AC-3: Tạo ba tệp ảnh PNG (loss, reward, activation) từ nhật ký huấn luyện.
- FR-011, AC-3: Báo rõ khi thiếu dữ liệu, không tạo ảnh rỗng thay thế, các biểu đồ khác giữ nguyên.
- FR-012, AC-3: Loại trừ điểm không hữu hạn (NaN/Inf) và đếm vào points_dropped.
- NFR-HEADLESS-001: Hoạt động trơn tru trong môi trường headless khi DISPLAY bị gỡ bỏ.
- API-EVL-0009: Trả về đối tượng ChartResult và ChartData để kiểm chứng nội dung bằng dữ liệu.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pytest

from mma_ai.evaluation.charts import ChartData, ChartResult, ChartSeriesData, render_charts
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import TrainingLog

PNG_MAGIC_BYTES: bytes = b"\x89PNG\r\n\x1a\n"
DEFAULT_MUSCLE_NAMES: list[str] = [
    "TRIlong",
    "TRIlat",
    "TRImed",
    "BIClong",
    "BICshort",
    "BRA",
]


def _eval_deps() -> tuple[Any, Any]:
    """Nạp pandas và matplotlib hoặc bỏ qua kiểm thử nếu thiếu nhóm phụ thuộc eval."""
    pd = pytest.importorskip("pandas")
    mpl = pytest.importorskip("matplotlib")
    return pd, mpl


def _create_sample_training_log(
    n_steps: int = 20,
    include_loss: bool = True,
    include_reward: bool = True,
    include_activation: bool = True,
    inject_nonfinite: bool = False,
    muscle_names: Sequence[str] = DEFAULT_MUSCLE_NAMES,
) -> tuple[TrainingLog, int]:
    """Tạo đối tượng TrainingLog mẫu với bảng dữ liệu dài (long-form DataFrame)."""
    pd, _ = _eval_deps()
    rows: list[dict[str, object]] = []
    dropped_count = 0

    steps = [idx * 10 for idx in range(1, n_steps + 1)]

    if include_loss:
        for idx, st in enumerate(steps):
            val = float(1.0 / (idx + 1))
            if inject_nonfinite and idx == 5:
                val = float("nan")
                dropped_count += 1
            rows.append({"series": "loss/policy", "step": st, "value": val})

    if include_reward:
        for idx, st in enumerate(steps):
            val = float(idx * 0.5)
            if inject_nonfinite and idx == 10:
                val = float("inf")
                dropped_count += 1
            rows.append({"series": "reward/mean_return", "step": st, "value": val})

    if include_activation:
        for m_idx, m_name in enumerate(muscle_names):
            tag = f"activation/{m_name}"
            for idx, st in enumerate(steps):
                val = float(0.2 + 0.1 * m_idx + 0.01 * (idx % 5))
                if inject_nonfinite and m_idx == 0 and idx == 2:
                    val = float("-inf")
                    dropped_count += 1
                rows.append({"series": tag, "step": st, "value": val})

    df = pd.DataFrame(rows, columns=["series", "step", "value"])
    available_tags = sorted(df["series"].unique().tolist())
    log = TrainingLog(df=df, source="jsonl", available_tags=available_tags)
    return log, dropped_count


def _eval_config() -> EvalConfig:
    """Nạp cấu hình đánh giá chuẩn mặc định phục vụ kiểm thử."""
    return EvalConfig.load()


def test_independent_assertion_charts_contract() -> None:
    """Assertion độc lập trên base chứng minh mô-đun và hàm render_charts tồn tại (API-EVL-0009)."""
    assert callable(render_charts)
    assert issubclass(ChartResult, object)
    assert issubclass(ChartData, object)
    assert issubclass(ChartSeriesData, object)


def test_render_charts_signature_and_docstring() -> None:
    """API-EVL-0009: Kiểm tra chữ ký hàm và docstring tiếng Việt."""
    import inspect

    sig = inspect.signature(render_charts)
    assert "log" in sig.parameters
    assert "muscle_names" in sig.parameters
    assert "out_dir" in sig.parameters
    assert "cfg" in sig.parameters
    doc = inspect.getdoc(render_charts)
    assert doc is not None and "API-EVL-0009" in doc


def test_three_files_valid_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chứng minh FR-010, AC-3, NFR-HEADLESS-001:
    Tạo đủ ba tệp ảnh PNG hợp lệ khi không có DISPLAY.
    """
    _eval_deps()
    import matplotlib.image as mpimg  # type: ignore[import-not-found,import-untyped,unused-ignore]

    monkeypatch.delenv("DISPLAY", raising=False)

    log, _ = _create_sample_training_log(n_steps=15)
    charts_dir = tmp_path / "charts"

    result: ChartResult = render_charts(
        log=log,
        muscle_names=DEFAULT_MUSCLE_NAMES,
        out_dir=charts_dir,
        cfg=_eval_config(),
    )

    assert result.status == "complete"
    assert result.reason is None
    assert result.points_dropped == 0

    expected_files = ["loss", "reward", "activation"]
    for chart_name in expected_files:
        file_name = f"{chart_name}.png"
        file_path = charts_dir / file_name

        assert file_path.is_file(), f"Tệp {file_name} phải tồn tại trên đĩa."
        assert file_path.stat().st_size > 0, f"Tệp {file_name} không được rỗng."

        content = file_path.read_bytes()
        assert content.startswith(
            PNG_MAGIC_BYTES
        ), f"Tệp {file_name} phải chứa chữ ký tệp PNG hợp lệ."

        img_data = mpimg.imread(str(file_path))
        assert img_data.ndim >= 2, f"Tệp {file_name} phải đọc lại được thành mảng ảnh hợp lệ."


def test_activation_has_six_named_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chứng minh FR-010, AC-3, API-EVL-0009: Biểu đồ activation có đúng 6 đường mang tên 6 cơ."""
    _eval_deps()
    monkeypatch.delenv("DISPLAY", raising=False)

    log, _ = _create_sample_training_log(n_steps=10)
    result = render_charts(
        log=log,
        muscle_names=DEFAULT_MUSCLE_NAMES,
        out_dir=tmp_path,
        cfg=_eval_config(),
    )

    act_data = result.data["activation"]
    assert len(act_data) == 6, "Biểu đồ activation phải chứa đúng 6 đường dữ liệu."

    series_names = [line.series for line in act_data]
    assert series_names == DEFAULT_MUSCLE_NAMES, "Tên 6 đường phải khớp chính xác với 6 tên cơ."

    assert result.points_plotted["activation"] == 6 * 10
    assert result.files["activation"] is not None


def test_points_match_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chứng minh FR-010, AC-3: Số điểm vẽ, bước bắt đầu và bước kết thúc khớp chính xác với log."""
    _eval_deps()
    monkeypatch.delenv("DISPLAY", raising=False)

    n_steps = 25
    log, _ = _create_sample_training_log(n_steps=n_steps)
    result = render_charts(
        log=log,
        muscle_names=DEFAULT_MUSCLE_NAMES,
        out_dir=tmp_path,
        cfg=_eval_config(),
    )

    loss_series = result.data["loss"]
    assert len(loss_series) == 1
    assert loss_series[0].n_points == n_steps
    assert loss_series[0].first_step == 10
    assert loss_series[0].last_step == 250

    reward_series = result.data["reward"]
    assert len(reward_series) == 1
    assert reward_series[0].n_points == n_steps
    assert reward_series[0].first_step == 10
    assert reward_series[0].last_step == 250


def test_nonfinite_points_dropped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chứng minh FR-012, AC-3:
    Điểm không hữu hạn (NaN/Inf) bị loại bỏ và đếm vào points_dropped.
    """
    _eval_deps()
    monkeypatch.delenv("DISPLAY", raising=False)

    n_steps = 20
    log, expected_dropped = _create_sample_training_log(
        n_steps=n_steps,
        inject_nonfinite=True,
    )
    assert expected_dropped == 3

    result = render_charts(
        log=log,
        muscle_names=DEFAULT_MUSCLE_NAMES,
        out_dir=tmp_path,
        cfg=_eval_config(),
    )

    assert result.points_dropped == expected_dropped
    assert result.points_plotted["loss"] == n_steps - 1
    assert result.points_plotted["reward"] == n_steps - 1
    assert result.points_plotted["activation"] == 6 * n_steps - 1


def test_missing_series_no_empty_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chứng minh FR-011, AC-3: Thiếu chuỗi thì không tạo ảnh rỗng, báo incomplete và nêu lý do."""
    _eval_deps()
    monkeypatch.delenv("DISPLAY", raising=False)

    log, _ = _create_sample_training_log(
        n_steps=10,
        include_loss=True,
        include_reward=True,
        include_activation=False,
    )

    result = render_charts(
        log=log,
        muscle_names=DEFAULT_MUSCLE_NAMES,
        out_dir=tmp_path,
        cfg=_eval_config(),
    )

    assert result.status == "incomplete"
    assert result.reason is not None
    assert "activation" in result.reason.lower()

    # Tệp activation không được phép tạo trên đĩa
    assert not (tmp_path / "activation.png").exists()
    assert result.files["activation"] is None
    assert result.points_plotted["activation"] == 0

    # Các tệp có dữ liệu vẫn phải tạo bình thường
    assert (tmp_path / "loss.png").is_file()
    assert (tmp_path / "reward.png").is_file()
    assert result.files["loss"] is not None
    assert result.files["reward"] is not None
