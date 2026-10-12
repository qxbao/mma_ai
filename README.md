# MMA AI

Hệ thống mô phỏng và điều khiển cử động cơ bắp MMA AI.
Dự án cung cấp môi trường cơ xương để huấn luyện, đánh giá và phát lại chuyển động qua giao diện 3D.

![Python 3.11–3.12](https://img.shields.io/badge/Python-3.11--3.12-blue) [![Giấy phép MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Tính năng

- Mô phỏng vật lý cơ xương và môi trường điều khiển khuỷu tay để thử nghiệm chuyển động.
- Huấn luyện chính sách bằng thuật toán tối ưu chính sách gần đúng (Proximal Policy Optimization, PPO), kèm theo dõi quá trình huấn luyện.
- Đánh giá chính sách đã lưu so với chính sách ngẫu nhiên (random policy) và tạo biểu đồ kết quả.
- Phát lại phiên chạy và trình diễn chuyển động trong không gian 3D.

## Yêu cầu hệ thống

- Python 3.11–3.12 và công cụ `uv`.
- Bộ xử lý đồ hoạ (GPU) không bắt buộc.

## Cài đặt bằng uv

Đồng bộ môi trường và cài dự án:

```sh
uv sync
```

Ba nhóm phụ thuộc tuỳ chọn (optional dependencies) trong `pyproject.toml` là `rl` (huấn luyện), `eval` (đánh giá) và `dev` (kiểm thử). Chọn nhóm cần dùng bằng `uv sync --extra rl`, `uv sync --extra eval` hoặc `uv sync --extra dev`.

## Bắt đầu nhanh

Chạy các lệnh sau trong môi trường đã `uv sync`: kích hoạt `.venv` hoặc thêm tiền tố `uv run` vào mỗi lệnh; cài các nhóm phụ thuộc phù hợp với thao tác bạn chọn.

```sh
python scripts/train.py --stage elbow --seed 42
python -m mma_ai.evaluation.cli --checkpoint <ckpt>
python -m mma_ai.visualization.cli --episode <tệp>
python -m mma_ai.learning.benchmark --seed 42 --repeats 5
```

Với phát lại, có thể dùng `--checkpoint <ckpt>` thay cho `--episode <tệp>`.

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `src/mma_ai/physics/` | Mô phỏng vật lý. |
| `src/mma_ai/environment/` | Môi trường điều khiển. |
| `src/mma_ai/learning/` | Huấn luyện và đo hiệu năng. |
| `src/mma_ai/monitoring/` | Theo dõi quá trình chạy. |
| `src/mma_ai/evaluation/` | Đánh giá kết quả. |
| `src/mma_ai/visualization/` | Phát lại và hiển thị. |
| `specs/` | Đặc tả tính năng. |
| `docs/` | Tài liệu dự án. |
| `tests/` | Kiểm thử. |

## Chạy kiểm thử

Chạy bộ kiểm thử bằng lệnh của dự án:

```sh
uv run --isolated --with pytest pytest -q
```

## Tình trạng nền tảng

Đã gộp bốn thành phần của [đặc tả 006](specs/006-cross-platform-support/): gói `mma_ai.compat` dò nền tảng, bộ nhớ RAM, màn hình và thay tệp nguyên tử (atomic file replacement); báo cáo môi trường qua `python -m mma_ai.compat.env_report`; cổng năng lực (capability gate) loại kiểm thử theo năng lực của máy; ma trận tích hợp liên tục (continuous integration, CI) gồm ba hệ điều hành × Python 3.11/3.12 trong `.github/workflows/ci.yml`. Windows gốc (native Windows) là mục tiêu chính, cùng CUDA tuỳ chọn và macOS; đây là các mục tiêu, chưa kiểm.

- **Linux**: **đã kiểm** — đã chạy kiểm tra trên Linux.
- **Windows 11**: **chưa kiểm** — chưa kiểm chứng trên Windows gốc.
- **WSL2**: **chưa kiểm** — chưa kiểm chứng trên lớp Linux trên Windows (Windows Subsystem for Linux 2, WSL2).
- **macOS**: **chưa kiểm** — chưa kiểm chứng trên máy macOS, kể cả trình xem (viewer) chạy bằng `mjpython`.
- **CUDA**: **chưa kiểm** — chưa kiểm chứng trên máy có CUDA.
- **Ô CI chạy thật trên GitHub Actions**: **chưa kiểm** — đã có cấu hình ma trận, chưa có kết quả chạy thật được xác nhận.

## Tài liệu

- [Bản đồ phân hệ](docs/MAP.md) và [các đặc tả](specs/).
- [Hướng dẫn huấn luyện](docs/guides/training.md), [hướng dẫn đánh giá](docs/guides/evaluation.md), [hướng dẫn phát lại](docs/guides/replay-demo.md) và [hướng dẫn đa nền tảng](docs/guides/platforms.md).
- [Nhật ký thay đổi](CHANGELOG.md).

## Đóng góp

Xem [hướng dẫn đóng góp](CONTRIBUTING.md).

## Giấy phép

Dự án được phát hành theo [giấy phép MIT](LICENSE).
