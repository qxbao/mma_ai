---
id: "CONTRACT-008-CLI"
title: "Hợp đồng lệnh trong tài liệu — lệnh ↔ cờ ↔ nguồn ↔ mã thoát"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Hợp đồng lệnh cho tài liệu (Phase 1)

Dự án là ứng dụng dòng lệnh, không có HTTP route (khảo sát `docs/00-survey/mma-ai-project-docs.md`), nên không có `API-*`/JSON Schema cho feature này. "Hợp đồng" ở đây là **bảng nguồn sự thật cho các lệnh mà tài liệu được phép nêu** (INV-001): vai `docs` chỉ chép từ bảng này; reviewer đối chiếu bảng với `--help` thật. Khi mã đổi cờ, sửa tài liệu, không sửa mã (INV-002).

Cờ lấy từ `argparse` trong mã tại HEAD lúc lập plan; mã thoát lấy từ docstring/mã gần nhất. Cột "Đã đo `--help`" ghi lượt kiểm `--help` thật: CHƯA KIỂM = chưa chạy ở lượt plan, reviewer đo ở Task 3.

## Lệnh Bắt đầu nhanh (đúng 4 lệnh, FR-004)

| # | Lệnh | Điểm vào (nguồn) | Cờ dùng trong README | Mã |
|---|---|---|---|---|
| 1 | `python scripts/train.py --stage elbow --seed 42` | `scripts/train.py` → `src/mma_ai/learning/cli.py` | `--stage`, `--seed` | AC-2 |
| 2 | `python -m mma_ai.evaluation.cli --checkpoint <ckpt>` | `src/mma_ai/evaluation/cli.py` | `--checkpoint` (bắt buộc) | AC-2 |
| 3 | `python -m mma_ai.visualization.cli --episode <tệp>` hoặc `--checkpoint <ckpt>` | `src/mma_ai/visualization/cli.py` → `replay.py` | `--episode` / `--checkpoint` | AC-2 |
| 4 | `python -m mma_ai.learning.benchmark --seed 42 --repeats 5` | `src/mma_ai/learning/benchmark.py` | `--seed`, `--repeats` | AC-2 |

## Cờ được phép nêu trong guide (FR-010)

| Lệnh | Cờ (kiểu · mặc định · nguồn) | Mã thoát (nguồn) |
|---|---|---|
| train | `--stage` str, mặc định `elbow` (M1 chỉ `elbow`) · `--seed` int · `--config` str · `--total-steps` int · `--resume` str (`.pt` hoặc `latest.json`) · `--runs-dir` str · `--ui` `web`\|`none`, mặc định `web` · `--ui-port` int (0 = HĐH cấp) · `--view3d` cờ, mặc định tắt — `src/mma_ai/learning/cli.py` `_build_parser` | 0 xong · 1 lỗi số học/mất ổn định/nhập xuất checkpoint · 2 tham số/cấu hình sai · 3 stage chưa triển khai · 4 checkpoint hỏng · 130 Ctrl-C — docstring `main` |
| evaluate | `--checkpoint` str **bắt buộc** (`.pt` hoặc `latest.json`) · `--config` str · `--out` str (bắt buộc khi checkpoint ngoài thư mục run) · `--repeats` int > 0 · `--eval-seed` int ≥ 0 · `--runs-dir` str — `src/mma_ai/evaluation/cli.py` `_build_parser` | 0 · 1 · 2 tham số · 4 checkpoint lỗi · 5 rò rỉ tập dữ liệu · 6 thiếu biểu đồ · 7 lỗi ghi đĩa · 130 — docstring `main` |
| replay | `--episode` str · `--checkpoint` str (chọn đúng một chế độ) · `--headless` cờ · `--save-episode` str (chỉ với `--checkpoint`) · `--speed` float > 0, mặc định 1.0 · `--loop` cờ · `--allow-model-mismatch` cờ · `--split` `train`\|`test` · `--target-index` int · `--seed` int (ba cờ sau chỉ với `--checkpoint`) · `--config` str — `src/mma_ai/visualization/replay.py` `_build_parser` | 0 · 1 mất ổn định · 2 tham số · 4 checkpoint lỗi · 5 episode lỗi · 6 lệch mô hình · 7 thiếu màn hình (gợi ý `--headless`) · 8 lỗi ghi tệp · 130 — docstring đầu `replay.py` |
| benchmark | `--seed` · `--repeats` (tối thiểu 5) · `--config` · `--total-steps` · `--output` (mặc định `logs/m1/benchmark_train.json`) · `--runs-dir` · `--threshold` (mặc định 0.90) — `src/mma_ai/learning/benchmark.py` (đã đo `--help` ở lượt plan: in đủ các cờ này) | 0 đạt chuẩn · 1 không đạt/lỗi huấn luyện · 2 tham số sai — docstring `main` |

## Quy tắc dùng bảng

- Guide chỉ nêu cờ có trong bảng này; muốn nêu cờ khác thì đọc lại `_build_parser` và cập nhật bảng ở cùng lượt.
- Không nêu đường dẫn đầu ra cụ thể (`runs/…`) nếu chưa đọc mã/`--help` xác nhận; nơi chưa rõ ghi "xem `--runs-dir`" hoặc "CHƯA KIỂM".
- Lệnh có ví dụ trong guide dùng `<ckpt>`, `<tệp>` làm chỗ giữ chỗ, không đường dẫn tuyệt đối của máy riêng (hiến chương VI).
- Cú pháp thật của đầu ra và nơi lưu checkpoint do vai `docs` đọc ở `src/mma_ai/learning/run_dir.py` và `checkpoint.py` lúc viết guide huấn luyện.
