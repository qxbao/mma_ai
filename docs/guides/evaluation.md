---
id: GUIDE-EVALUATION
title: Hướng dẫn đánh giá
doc_type: guide
owner_agent: docs
status: active
updated: "2026-10-12"
---

# Hướng dẫn đánh giá

Đánh giá chính sách đã lưu và đối chiếu với chính sách ngẫu nhiên (random policy). Xem [README](../../README.md) để cài đặt và lấy lệnh bắt đầu nhanh.

## Điều kiện tiên quyết

- Đã cài đặt theo [README](../../README.md), gồm nhóm phụ thuộc `eval`.
- Có điểm kiểm tra (checkpoint) dạng `.pt` hoặc con trỏ `latest.json`; chạy trong môi trường đã `uv sync` bằng `.venv` hoặc `uv run`.

## Các bước

1. Dùng lệnh đánh giá trong [README](../../README.md), thay `<ckpt>` bằng đường dẫn checkpoint:

   ```sh
   python -m mma_ai.evaluation.cli --checkpoint <ckpt>
   ```

2. Nếu checkpoint nằm ngoài thư mục lần chạy, thêm `--out` để chỉ nơi ghi kết quả; thiếu cờ này lệnh báo lỗi.
3. Khi cần, dùng `--config` chọn cấu hình, `--repeats` đặt số lần đánh giá (lớn hơn 0), `--eval-seed` đặt hạt giống đánh giá (từ 0 trở lên), và `--runs-dir` chọn thư mục chứa các lần chạy.

## Lỗi thường gặp

| Mã thoát | Ý nghĩa và cách xử lý |
|---|---|
| `0` | Hoàn tất. |
| `1` | Lỗi thực thi; xem thông báo của lệnh. |
| `2` | Tham số sai; kiểm tra `--checkpoint` và `--out` khi cần. |
| `4` | Checkpoint lỗi; kiểm tra tệp `.pt` hoặc `latest.json`. |
| `5` | Rò rỉ tập dữ liệu (data leakage); kiểm tra cách chia tập. |
| `6` | Thiếu biểu đồ; kiểm tra phụ thuộc đánh giá. |
| `7` | Lỗi ghi đĩa; kiểm tra nơi xuất kết quả. |
| `130` | Đã ngắt bằng Ctrl-C. |
