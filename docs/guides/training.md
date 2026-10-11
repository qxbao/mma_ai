---
id: GUIDE-TRAINING
title: Hướng dẫn huấn luyện
doc_type: guide
owner_agent: docs
status: active
updated: "2026-10-12"
---

# Hướng dẫn huấn luyện

Huấn luyện chính sách điều khiển khuỷu tay và tìm điểm kiểm tra (checkpoint) để đánh giá hoặc phát lại. Lệnh bắt đầu nhanh và cách chuẩn bị môi trường nằm trong [README](../../README.md).

## Điều kiện tiên quyết

- Đã cài đặt theo [README](../../README.md), gồm nhóm phụ thuộc `rl`.
- Chạy lệnh trong môi trường đã `uv sync`: kích hoạt `.venv` hoặc thêm tiền tố `uv run`.

## Các bước

1. Bắt đầu bằng lệnh huấn luyện trong [README](../../README.md):

   ```sh
   python scripts/train.py --stage elbow --seed 42
   ```

2. Điều chỉnh khi cần: `--config` chọn tệp cấu hình; `--total-steps` đặt số bước; `--runs-dir` chọn thư mục chứa các lần chạy. `--resume` nhận tệp `.pt` hoặc con trỏ `latest.json` để tiếp tục.
3. `--ui web|none` điều khiển giao diện theo dõi (monitoring UI), mặc định `web`; `--ui-port` đặt cổng, với `0` để hệ điều hành tự cấp. Thêm `--view3d` nếu cần xem chuyển động 3D.
4. Trong thư mục đã chọn bằng `--runs-dir`, tìm thư mục lần chạy rồi mở `checkpoints/`: tệp `.pt` là checkpoint và `latest.json` trỏ tới bản mới nhất. Đường dẫn này được tạo bởi `run_dir.py` và `checkpoint.py`.
5. Sau huấn luyện, chạy lệnh đo hiệu năng (benchmark) trong [README](../../README.md) với `--repeats 5` hoặc lớn hơn.

## Lỗi thường gặp

| Mã thoát | Ý nghĩa và cách xử lý |
|---|---|
| `0` | Hoàn tất. |
| `1` | Lỗi số học, mất ổn định hoặc nhập xuất checkpoint; kiểm tra thông báo và tệp lưu. |
| `2` | Tham số hoặc cấu hình sai; kiểm tra giá trị cờ. |
| `3` | Giai đoạn huấn luyện (stage) chưa triển khai; dùng `--stage elbow`. |
| `4` | Checkpoint hỏng; chọn tệp `.pt` hoặc `latest.json` hợp lệ. |
| `130` | Đã ngắt bằng Ctrl-C. |
