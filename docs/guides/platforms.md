---
id: GUIDE-PLATFORMS
title: Hướng dẫn kiểm tra môi trường đa nền tảng
doc_type: guide
owner_agent: docs
status: active
updated: "2026-10-13"
---

# Kiểm tra môi trường đa nền tảng (Cross-platform environment checks)

Cách cài đặt nằm trong [README](../../README.md). Chạy các lệnh dưới đây ở gốc dự án, trong môi trường ảo (virtual environment) đã cài các phụ thuộc (dependencies) cần dùng.

## Báo cáo môi trường (Environment report)

```sh
python -m mma_ai.compat.env_report
python -m mma_ai.compat.env_report --json
```

Báo cáo kiểm tra Python, các gói và năng lực (capabilities) của máy. Đầu ra văn bản dùng `[ok]`, `[CẢNH BÁO]`, `[LỖI]`; dòng kết luận là `Môi trường đạt yêu cầu.` hoặc `Môi trường chưa đạt yêu cầu.`.

| Mã thoát (Exit code) | Ý nghĩa |
|---|---|
| `0` | Môi trường đạt yêu cầu: không có mục `fail`; vẫn có thể có cảnh báo `warn`. |
| `1` | Môi trường chưa đạt yêu cầu: có ít nhất một mục `fail`; đọc thông báo để xử lý. |
| `2` | Có cờ không được hỗ trợ; kiểm tra lại lệnh. |

Cờ `--json` ghi báo cáo JSON ra đầu ra chuẩn (stdout), gồm `schema_version`, `os`, `python`, `packages`, `capabilities`, `checks` và `overall`; thông báo hoàn tất nằm ở đầu ra lỗi chuẩn (stderr). Đọc `checks` để hiểu từng trạng thái, thay vì chỉ nhìn `overall`. Chẳng hạn thiếu `torch` chỉ là cảnh báo nhưng máy chưa thể huấn luyện; mã `0` không chứng minh mọi chức năng đều chạy được. Trường `os.tested` là giá trị từ mã dò nền tảng, không thay cho bằng chứng chạy trên máy thật.

## Dấu năng lực (Capability markers)

Cổng năng lực (capability gate) của pytest dùng các dấu khai trong `tests/unit/capability_gate.py` để loại kiểm thử (deselect tests) khi máy không đáp ứng điều kiện.

| Dấu | Điều kiện cần |
|---|---|
| `requires_display` | Màn hình hiển thị khả dụng. |
| `requires_cuda` | CUDA (nền tảng tính toán trên GPU NVIDIA) khả dụng. |
| `requires_symlink` | Tạo được liên kết tượng trưng (symbolic link). |
| `windows_only` | Chỉ chạy trên Windows. |
| `requires_xdist` | Có pytest-xdist (gói chạy kiểm thử song song). |
| `requires_git_history` | Có lịch sử git (git history) của kho dự án. |

```sh
python -m pytest -q --capability-report capability.json
```

Cuối phiên, đọc dòng `Kiểm thử bị loại theo năng lực: X/Y (tỉ lệ; giới hạn 5.0%).`. `X` là số kiểm thử bị loại, `Y` là tổng số đã thu thập; tỉ lệ được in theo phần trăm. Bên dưới là danh sách `nodeid [dấu]: lý do`, trong đó `nodeid` là định danh kiểm thử. Đây là mẫu cách đọc, không phải số liệu của một lượt chạy.

Ngưỡng loại mặc định là 5% (`0.05`): vượt ngưỡng thì phiên kiểm thử thất bại, kể cả khi các kiểm thử còn lại đạt. Cờ `--capability-report <tệp>` ghi báo cáo JSON với `collected`, `deselected`, `ratio` và `items`; mỗi mục có `nodeid`, `marker`, `reason`. Đọc cả báo cáo để biết phần hành vi chưa được kiểm.

Trong bản đóng gói mã nguồn (archive) không có `.git`, kiểm thử INV-002 của 008 bị loại với lý do `Máy không có lịch sử git`. Cơ chế này có báo cáo; không dùng bỏ qua (skip) hoặc thất bại dự kiến (xfail), không coi kiểm thử bị loại là đã đạt. INV-002 của 008 chỉ chứng minh được ở môi trường có git; phiên xanh trên archive không chứng minh bất biến (invariant) đó.

## Giới hạn kiểm chứng (Verification limits)

| Môi trường | Tình trạng |
|---|---|
| Linux | Đã kiểm: báo cáo môi trường và các cổng kiểm thử trên Linux. |
| Windows 11 | Chưa kiểm trên máy thật. |
| WSL2 (lớp Linux trên Windows) | Chưa kiểm. |
| macOS | Chưa kiểm trên máy thật, kể cả trình xem (viewer) bằng `mjpython`. |
| CUDA | Chưa kiểm trên phần cứng thật. |
| Các ô tích hợp liên tục (continuous integration, CI) chạy thật trên GitHub Actions | Chưa kiểm. |

[Đặc tả 006](../../specs/006-cross-platform-support/) đặt mục tiêu Windows gốc là môi trường chính, CUDA tùy chọn và macOS chạy tốt. Đây là mục tiêu của 006, không phải kết quả đã kiểm. Mã tương thích đã gộp và ma trận CI đã khai báo không thay thế bằng chứng chạy thật trên từng môi trường.
