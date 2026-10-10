"""Mô-đun vẽ biểu đồ đánh giá không cần màn hình (API-EVL-0009, headless charts).

Mô-đun này cung cấp chức năng kết xuất (render) ba biểu đồ huấn luyện:
- Mất mát (loss): diễn biến hàm mất mát theo bước huấn luyện.
- Phần thưởng (reward): diễn biến phần thưởng theo bước huấn luyện.
- Mức kích hoạt (activation): mức kích hoạt của đúng 6 cơ (muscle activation).

Tuân thủ các yêu cầu và bất biến:
- FR-010, AC-3: Kết xuất ba biểu đồ từ nhật ký huấn luyện dạng bảng dài.
- FR-011, AC-3: Hoạt động chế độ không đầu (headless), không tạo ảnh rỗng khi thiếu dữ liệu.
- FR-012, AC-3: Loại trừ điểm không hữu hạn (NaN/Inf) và đếm số điểm bị bỏ.
- NFR-HEADLESS-001: Hoạt động trơn tru khi biến môi trường DISPLAY bị bỏ đặt.
- API-EVL-0009: Trả về đối tượng ChartResult chứa ChartData với thông tin điểm vẽ chi tiết.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import TrainingLog


@dataclass(frozen=True)
class ChartSeriesData:
    """Dữ liệu chuỗi điểm vẽ của một đường trên biểu đồ (API-EVL-0009)."""

    series: str
    n_points: int
    first_step: int | None
    last_step: int | None


class ChartData:
    """Tập hợp dữ liệu các đường vẽ hỗ trợ truy xuất linh hoạt để kiểm thử."""

    def __init__(
        self,
        series_list: list[ChartSeriesData],
        by_chart: dict[str, list[ChartSeriesData]],
    ) -> None:
        self._series_list = list(series_list)
        self._by_chart = {k: list(v) for k, v in by_chart.items()}

    def __iter__(self) -> Any:
        return iter(self._series_list)

    def __len__(self) -> int:
        return len(self._series_list)

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, str):
            return self._by_chart.get(key, [])
        return self._series_list[key]

    @property
    def series(self) -> list[str]:
        """Danh sách tên các chuỗi đã vẽ."""
        return [s.series for s in self._series_list]


@dataclass(frozen=True)
class ChartResult:
    """Kết quả kết xuất bộ ba biểu đồ huấn luyện (API-EVL-0009)."""

    status: str
    files: dict[str, str | None]
    points_plotted: dict[str, int]
    points_dropped: int
    reason: str | None
    log_source: str | None
    data: ChartData

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin biểu đồ sang định dạng từ điển chuẩn schema JSON."""
        return {
            "status": self.status,
            "files": dict(self.files),
            "points_plotted": dict(self.points_plotted),
            "points_dropped": self.points_dropped,
            "reason": self.reason,
            "log_source": self.log_source,
        }


def render_charts(
    log: TrainingLog,
    muscle_names: Sequence[str],
    out_dir: str | Path,
    cfg: EvalConfig,
) -> ChartResult:
    """Kết xuất ba biểu đồ loss, reward và activation từ nhật ký huấn luyện (API-EVL-0009).

    Args:
        log: Đối tượng nhật ký huấn luyện chứa bảng dữ liệu (series, step, value).
        muscle_names: Danh sách 6 tên cơ tương ứng của mô hình môi trường.
        out_dir: Thư mục đích để lưu các tệp ảnh biểu đồ PNG.
        cfg: Cấu hình đánh giá chứa tham số dpi và tiền tố thẻ nhật ký.

    Returns:
        ChartResult: Kết quả kết xuất chứa trạng thái, đường dẫn tệp và dữ liệu vẽ.

    Raises:
        ImportError: Khi thiếu thư viện matplotlib (thuộc nhóm phụ thuộc tùy chọn 'eval').
    """
    try:
        import matplotlib  # type: ignore[import-not-found,import-untyped,unused-ignore]

        # Bắt buộc đặt backend Agg trước mọi import pyplot để chạy không cần màn hình
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore[import-not-found,import-untyped,unused-ignore]
    except ImportError as err:
        raise ImportError(
            "Cần cài đặt thư viện 'matplotlib' (nhóm phụ thuộc tùy chọn 'eval') để vẽ biểu đồ."
        ) from err

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Trích xuất và phân loại dữ liệu chuỗi điểm từ bảng nhật ký
    df = getattr(log, "df", None)
    points_dropped = 0
    series_points_map: dict[str, list[tuple[int, float]]] = {}

    if df is not None and not df.empty and {"series", "step", "value"}.issubset(df.columns):
        for row in df.itertuples(index=False):
            s_name = str(getattr(row, "series"))
            s_step = getattr(row, "step")
            s_val = getattr(row, "value")

            try:
                num_val = float(s_val)
                step_val = int(s_step)
            except (ValueError, TypeError):
                points_dropped += 1
                continue

            if not math.isfinite(num_val):
                points_dropped += 1
                continue

            series_points_map.setdefault(s_name, []).append((step_val, num_val))

    # Sắp xếp các điểm theo thứ tự bước huấn luyện
    for s_name in series_points_map:
        series_points_map[s_name].sort(key=lambda item: item[0])

    loss_pfx = cfg.logs.tags.loss_prefix
    reward_pfx = cfg.logs.tags.reward_prefix
    activation_pfx = cfg.logs.tags.activation_prefix

    # 2. Chuẩn bị các đường vẽ cho biểu đồ loss
    loss_lines: list[tuple[str, list[tuple[int, float]]]] = []
    for s_name, pts in series_points_map.items():
        if s_name.startswith(loss_pfx):
            loss_lines.append((s_name, pts))
    loss_lines.sort(key=lambda item: item[0])

    # 3. Chuẩn bị các đường vẽ cho biểu đồ reward
    reward_lines: list[tuple[str, list[tuple[int, float]]]] = []
    for s_name, pts in series_points_map.items():
        if s_name.startswith(reward_pfx):
            reward_lines.append((s_name, pts))
    reward_lines.sort(key=lambda item: item[0])

    # 4. Chuẩn bị các đường vẽ cho biểu đồ activation (đúng 6 đường mang tên 6 cơ)
    activation_lines: list[tuple[str, list[tuple[int, float]]]] = []
    all_series_keys = list(series_points_map.keys())

    for idx, m_name in enumerate(muscle_names):
        candidate_keys = [
            f"{activation_pfx}{m_name}",
            f"{activation_pfx}m{idx}",
            f"{activation_pfx}muscle_{idx}",
            f"{activation_pfx}{idx}",
            m_name,
        ]
        matched_key: str | None = None
        for ck in candidate_keys:
            if ck in series_points_map:
                matched_key = ck
                break

        # Tìm kiếm dự phòng theo thứ tự chuỗi bắt đầu bằng activation_prefix
        if matched_key is None:
            act_keys = sorted([k for k in all_series_keys if k.startswith(activation_pfx)])
            if idx < len(act_keys):
                matched_key = act_keys[idx]

        pts = series_points_map.get(matched_key, []) if matched_key else []
        activation_lines.append((m_name, pts))

    # 5. Hàm nội bộ vẽ và lưu một biểu đồ
    def _render_chart_file(
        chart_key: str,
        lines: list[tuple[str, list[tuple[int, float]]]],
        x_label: str,
        y_label: str,
        title: str,
    ) -> tuple[str | None, int, list[ChartSeriesData], str | None]:
        chart_series_list: list[ChartSeriesData] = []
        total_points = 0

        for line_label, line_pts in lines:
            n_pts = len(line_pts)
            first_st = line_pts[0][0] if n_pts > 0 else None
            last_st = line_pts[-1][0] if n_pts > 0 else None
            chart_series_list.append(
                ChartSeriesData(
                    series=line_label,
                    n_points=n_pts,
                    first_step=first_st,
                    last_step=last_st,
                )
            )
            total_points += n_pts

        # Nếu không có đường nào hoặc toàn bộ điểm đều bằng 0, không tạo ảnh rỗng (FR-011)
        if total_points == 0 or not lines:
            reason_msg = f"{chart_key}: không có dữ liệu chuỗi hợp lệ trong nhật ký"
            return None, 0, chart_series_list, reason_msg

        # Tiến hành vẽ biểu đồ thật với Matplotlib
        fig, ax = plt.subplots(figsize=(8, 5))
        try:
            for line_label, line_pts in lines:
                if line_pts:
                    xs = [p[0] for p in line_pts]
                    ys = [p[1] for p in line_pts]
                    ax.plot(xs, ys, label=line_label)

            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(title)
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.6)
            fig.tight_layout()

            fmt = cfg.charts.format or "png"
            file_name = f"{chart_key}.{fmt}"
            dest_file = out_path / file_name
            fig.savefig(dest_file, dpi=cfg.charts.dpi, format=fmt)

            rel_file_path = f"charts/{file_name}" if out_path.name == "charts" else file_name
            return rel_file_path, total_points, chart_series_list, None
        finally:
            plt.close(fig)

    # 6. Kết xuất từng biểu đồ độc lập
    files_dict: dict[str, str | None] = {}
    points_plotted_dict: dict[str, int] = {}
    by_chart_data: dict[str, list[ChartSeriesData]] = {}
    reasons_list: list[str] = []

    # Kết xuất biểu đồ loss
    loss_file, loss_pts, loss_series_data, loss_err = _render_chart_file(
        chart_key="loss",
        lines=loss_lines,
        x_label="Bước huấn luyện (step)",
        y_label="Mất mát (Loss)",
        title="Biểu đồ hàm mất mát (Loss)",
    )
    files_dict["loss"] = loss_file
    points_plotted_dict["loss"] = loss_pts
    by_chart_data["loss"] = loss_series_data
    if loss_err:
        reasons_list.append(loss_err)

    # Kết xuất biểu đồ reward
    reward_file, reward_pts, reward_series_data, reward_err = _render_chart_file(
        chart_key="reward",
        lines=reward_lines,
        x_label="Bước huấn luyện (step)",
        y_label="Phần thưởng (Reward)",
        title="Biểu đồ phần thưởng (Reward)",
    )
    files_dict["reward"] = reward_file
    points_plotted_dict["reward"] = reward_pts
    by_chart_data["reward"] = reward_series_data
    if reward_err:
        reasons_list.append(reward_err)

    # Kết xuất biểu đồ activation
    act_file, act_pts, act_series_data, act_err = _render_chart_file(
        chart_key="activation",
        lines=activation_lines,
        x_label="Bước huấn luyện (step)",
        y_label="Mức kích hoạt (Activation)",
        title="Mức kích hoạt 6 cơ (Activation)",
    )
    files_dict["activation"] = act_file
    points_plotted_dict["activation"] = act_pts
    by_chart_data["activation"] = act_series_data
    if act_err:
        reasons_list.append(act_err)

    # 7. Tổng hợp kết quả tổng quát
    all_series_list: list[ChartSeriesData] = (
        loss_series_data + reward_series_data + act_series_data
    )
    chart_data = ChartData(series_list=all_series_list, by_chart=by_chart_data)

    is_complete = all(files_dict[k] is not None for k in ("loss", "reward", "activation"))
    status = "complete" if is_complete else "incomplete"
    reason = None if is_complete else "; ".join(reasons_list)
    log_source = getattr(log, "source", None)

    return ChartResult(
        status=status,
        files=files_dict,
        points_plotted=points_plotted_dict,
        points_dropped=points_dropped,
        reason=reason,
        log_source=log_source,
        data=chart_data,
    )
