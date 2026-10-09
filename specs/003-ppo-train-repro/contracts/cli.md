---
id: "CLI-003"
title: "M1 (2/4) — Hợp đồng dòng lệnh & điểm HTTP đọc-chỉ"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Hợp đồng — dòng lệnh và giao diện quan sát

Không có dịch vụ mạng ngoài máy. "Hợp đồng dây" gồm (1) bốn lệnh CLI, (2) MỘT điểm HTTP đọc-chỉ chỉ trên loopback cho giao diện quan sát. Khuôn bản ghi KHÔNG chép ở đây — xem tệp `*.schema.json` (JSON Schema draft 2020-12, ví dụ ở `examples/`, test `test_contract_examples_train`; schema của hồ sơ dùng `$ref` tới `checkpoint-meta.schema.json` nên test nạp mọi schema vào một registry).

## Lệnh (CMD)

| Mã | Lệnh | Vào | Ra | FR / AC |
|---|---|---|---|---|
| `CMD-TRN-0001` | `python scripts/train.py --stage elbow --seed 42 [--config PATH] [--total-steps N] [--resume CKPT] [--runs-dir DIR] [--ui web\|none] [--ui-port N] [--view3d]` | cấu hình (`configs/train_elbow.yaml` mặc định, khuôn [train-config.schema.json](train-config.schema.json)); cờ dòng lệnh ghi đè cấu hình và được lưu nguyên văn vào hồ sơ | thư mục `runs/<run_id>/` ([run-manifest.schema.json](run-manifest.schema.json), [checkpoint-meta.schema.json](checkpoint-meta.schema.json), tfevents, `metrics.jsonl`, [progress-snapshot.schema.json](progress-snapshot.schema.json)); báo cáo env steps/s + wall-clock + URL giao diện trên stdout | FR-001, FR-006, FR-011, FR-013, FR-015, FR-020 / AC-1, AC-3, AC-5 |
| `CMD-TRN-0002` | `python scripts/watch_train.py --run RUN_DIR [--port N] [--view3d]` | thư mục run (chỉ đọc) | máy chủ HTTP loopback (bảng dưới) và, nếu `--view3d`, cửa sổ MuJoCo Viewer | FR-020, FR-021, FR-022 / AC-7 |
| `CMD-TRN-0003` | `python scripts/compare_runs.py RUN_A RUN_B` | hai thư mục run | in kết quả so sánh đường reward đầu kỳ theo dung sai của hồ sơ; mã thoát 0 = trong dung sai | FR-014 / AC-4 |
| `CMD-TRN-0004` | `python scripts/benchmark_train.py --seed 42 [--repeats 5]` | cấu hình smoke mở rộng | `logs/m1/benchmark_train.json` ([train-benchmark.schema.json](train-benchmark.schema.json)); mã thoát 0 khi `passed` | FR-023 / NFR-PERF-001 |

### Quy tắc của `train.py`

- `--stage`: chỉ `elbow`. `balance`, `locomotion`, `selfplay` và mọi giá trị khác ⇒ in `chưa triển khai: stage '<tên>' (M1 chỉ hỗ trợ 'elbow')` ra stderr, thoát **3**, **không** tạo thư mục run (AC-5).
- `--resume CKPT`: `CKPT` là tệp `.pt` hoặc `checkpoints/latest.json` (con trỏ tới checkpoint hợp lệ mới nhất); tạo run mới, ghi `resumed_from` (FR-009). Checkpoint hỏng/thiếu thành phần/khác cấu trúc/khác hash XML ⇒ thoát **4** kèm thông báo nêu nguyên nhân (AC-2).
- `--ui web` (mặc định) khởi chạy `watch_train.py` ở TIẾN TRÌNH RIÊNG và in URL; giao diện không khởi động được ⇒ cảnh báo, train vẫn chạy (INV-005). `--ui none` tắt giao diện; `--view3d` bật hiển thị 3D (tiến trình riêng, mặc định tắt); train luôn headless.
- Không có lệnh nào dừng/sửa train từ giao diện (FR-021).

### Mã thoát

| Mã | Ý nghĩa |
|---|---|
| 0 | xong (hoặc `compare_runs` trong dung sai, `benchmark_train` đạt ngưỡng) |
| 1 | lỗi huấn luyện: NaN/Inf, môi trường mất ổn định, không ghi được checkpoint (hồ sơ `status:error`); `compare_runs` ngoài dung sai |
| 2 | tham số hoặc cấu hình không hợp lệ (trước khi tạo run) |
| 3 | stage chưa triển khai (khớp quy ước các lệnh chưa triển khai của 001) |
| 4 | checkpoint không dùng được để nạp/train tiếp |
| 130 | bị ngắt bằng Ctrl-C (hồ sơ `status:interrupted`) |

## Điểm HTTP đọc-chỉ (giao diện quan sát)

Máy chủ của `watch_train.py`: chỉ nghe địa chỉ loopback (`ui.host`), chỉ nhận **GET**; mọi phương thức khác ⇒ `405`, đường dẫn khác ⇒ `404`. Không xác thực vì không ra ngoài máy (INV-005; không có phân quyền ⇒ không `rbac.md`).

| Mã | Yêu cầu | Phản hồi | FR / AC / INV |
|---|---|---|---|
| `API-TRN-0001` | `GET /api/progress` | `200` JSON đúng [progress-snapshot.schema.json](progress-snapshot.schema.json) (nguyên văn `progress.json`; ví dụ `examples/progress-snapshot.*.json`); `503` kèm thân `{"error": "chưa có dữ liệu"}` khi `progress.json` chưa tồn tại (trang hiện "chưa có dữ liệu", không lỗi) | FR-020 / AC-7, NFR-PERF-002 |
| `API-TRN-0002` | `GET /` | `200` trang HTML tĩnh một tệp (JS nội tuyến, không tải tài nguyên ngoài) thăm dò `API-TRN-0001` mỗi `ui.poll_interval_ms`; có các khối: reward, loss, kích hoạt 6 cơ, env steps/s, `env_steps / total_steps`, trạng thái checkpoint | FR-020 / AC-7 |

`null` trong snapshot nghĩa là "chưa có số liệu" (ví dụ `loss` trước lượt cập nhật đầu), không phải lỗi; trang hiện "chưa có dữ liệu" (Edge Case). Khi `status` là `done`/`error`/`interrupted` trang hiện số liệu cuối kèm trạng thái.

## Quy tắc xuyên suốt

- Đường dẫn trong mọi bản ghi là tương đối so với gốc dự án hoặc thư mục run, không tuyệt đối riêng của máy (constitution VI).
- Giá trị không áp dụng ghi tường minh `null`, không bỏ trường.
- Hành động policy đưa vào môi trường luôn là `u_i ∈ [0,1]` cho 6 cơ (INV-002); không CLI nào nhận hành động hay toạ độ tay từ người dùng.
