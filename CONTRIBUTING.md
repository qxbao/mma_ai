# Đóng góp cho MMA AI

Xem [README](README.md) để cài đặt và bắt đầu sử dụng dự án.

## Kiểm tra thay đổi

Chạy bộ kiểm thử (test), kiểm tra quy tắc mã (lint) và kiểm tra kiểu tĩnh (static type checking) trước khi gửi thay đổi:

```sh
uv run --isolated --with pytest pytest -q
uv run --isolated --with ruff ruff check .
uv run --isolated --with mypy mypy --strict .
```

## Quy ước ngôn ngữ

Viết văn xuôi, chú thích (comment), chuỗi tài liệu (docstring) và thông báo hiển thị cho người dùng bằng tiếng Việt. Giữ nguyên định danh trong mã và lệnh bằng tiếng Anh. Ở lần xuất hiện đầu tiên trong mỗi tài liệu, viết thuật ngữ kỹ thuật bằng tiếng Việt kèm tiếng Anh trong ngoặc; nếu không có cách gọi tiếng Việt thông dụng, giữ tiếng Anh và giải nghĩa ngắn.

## Luồng làm việc ai-sdlc

Thực hiện lần lượt: đặc tả → kế hoạch → đầu việc (task) → triển khai. Mỗi task chỉ ghi vào vùng ở cột `outputs` trong `specs/*/tasks.md`; dùng [bản đồ phân hệ](docs/MAP.md) để tìm đặc tả, tài liệu và mã liên quan. Chạy các lệnh kiểm tra phù hợp rồi tạo bản ghi thay đổi (commit) cho task.
