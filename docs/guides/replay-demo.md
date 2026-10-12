---
id: GUIDE-REPLAY-DEMO
title: Hướng dẫn phát lại và trình diễn
doc_type: guide
owner_agent: docs
status: active
updated: "2026-10-13"
---

# Hướng dẫn phát lại và trình diễn

Phát lại phiên chuyển động đã lưu hoặc tạo phiên từ điểm kiểm tra (checkpoint). Lệnh bắt đầu nhanh và cách cài đặt nằm trong [README](../../README.md).

## Điều kiện tiên quyết

- Đã cài đặt theo [README](../../README.md) và có tệp phiên hoặc checkpoint phù hợp.
- Chạy trong môi trường đã `uv sync` bằng `.venv` hoặc `uv run`; hiển thị 3D cần màn hình đồ họa.

## Các bước

1. Chọn đúng một chế độ. Với tệp phiên (episode), dùng lệnh phát lại trong [README](../../README.md):

   ```sh
   python -m mma_ai.visualization.cli --episode <tệp>
   ```

   Hoặc tạo phiên từ checkpoint:

   ```sh
   python -m mma_ai.visualization.cli --checkpoint <ckpt>
   ```

2. Dùng `--headless` khi không có màn hình. `--save-episode` lưu tệp phiên và chỉ dùng cùng `--checkpoint`.
3. `--speed` đặt tốc độ phát lại (lớn hơn 0, mặc định 1.0); `--loop` lặp phiên; `--allow-model-mismatch` cho phép khác biệt mô hình; `--config` chọn cấu hình.
4. Riêng chế độ `--checkpoint`, dùng `--split train|test`, `--target-index` và `--seed` để chọn mục tiêu và hạt giống.

## Lỗi thường gặp

| Mã thoát | Ý nghĩa và cách xử lý |
|---|---|
| `0` | Hoàn tất. |
| `1` | Mất ổn định số học; kiểm tra dữ liệu đầu vào. |
| `2` | Tham số sai; chọn đúng một trong `--episode` và `--checkpoint`. |
| `4` | Checkpoint lỗi; kiểm tra tệp đầu vào. |
| `5` | Tệp phiên lỗi; kiểm tra tệp đầu vào. |
| `6` | Mô hình không khớp; kiểm tra tính tương thích. |
| `7` | Không có màn hình dùng được; thử `--headless`. Trên macOS, chạy bằng `python` thường khi không có `--headless` cần trình xem (viewer) qua `mjpython`: khi khởi chạy thất bại, lệnh trả mã `7` kèm gợi ý dùng `mjpython`; chưa kiểm trên macOS thật. |
| `8` | Lỗi ghi tệp; kiểm tra đường dẫn đích. |
| `130` | Đã ngắt bằng Ctrl-C. |
