---
id: "CLI-006"
title: "Hỗ trợ đa nền tảng — Hợp đồng dòng lệnh"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Hợp đồng — dòng lệnh kiểm môi trường và hành vi CLI chung

Không có dịch vụ mạng, không điểm HTTP, không phân quyền (lệnh cục bộ, không vai/khoá/token) ⇒ không `rbac.md`. "Hợp đồng dây" gồm (1) MỘT lệnh mới `check_env`, (2) một khuôn JSON Schema (draft 2020-12) [check-env-report.schema.json](check-env-report.schema.json) cùng ví dụ ở `examples/` (test `test_contract_examples_platform`; mọi ví dụ là **minh hoạ khuôn**, không phải số đo — chuỗi `release`, phiên bản và tên GPU là giá trị giả), (3) quy ước chung cho mọi CLI đã có. Tên trường KHÔNG chép ở đây — xem schema.

- [Lệnh (CMD)](#lenh-cmd)
  - [Mã thoát của `CMD-PLT-0001`](#ma-thoat-cua-cmd-plt-0001)
- [Quy ước chung cho mọi CLI `python -m mma_ai…` và `scripts/*.py`](#quy-uoc-chung-cho-moi-cli-python-m-mma-ai-va-scripts-py)
- [Hợp đồng thu thập test (cơ chế loại theo năng lực)](#hop-dong-thu-thap-test-co-che-loai-theo-nang-luc)

<a id="lenh-cmd"></a>
## Lệnh (CMD)

| Mã | Lệnh | Vào | Ra | Aggregate · sự kiện · quyền | FR / AC |
|---|---|---|---|---|---|
| `CMD-PLT-0001` | `python scripts/check_env.py [--json]` (vỏ mỏng gọi `mma_ai.compat.env_report.main`; chạy được cả bằng `python -m mma_ai.compat.env_report`) | Môi trường đang chạy; không đọc tệp cấu hình; không tham số bắt buộc | Mặc định: bảng văn bản tiếng Việt, mỗi phép kiểm một dòng `[ok]`/`[CẢNH BÁO]`/`[LỖI]` kèm thông điệp và dòng kết luận. `--json`: đúng MỘT đối tượng JSON theo [check-env-report.schema.json](check-env-report.schema.json) trên **stdout** (thông báo cho người đọc ở **stderr**) | Hồ sơ nền tảng · không phát sự kiện · không quyền | FR-017, FR-024; AC-5 |

<a id="ma-thoat-cua-cmd-plt-0001"></a>
### Mã thoát của `CMD-PLT-0001`

| Mã | Khi nào |
|---|---|
| 0 | Không có phép kiểm `fail` (có thể có `warn`: chưa cài torch, không có màn hình, không có quyền symlink, ổ Windows gắn trong WSL2, tổ hợp OS/kiến trúc chưa kiểm) |
| 1 | Có ít nhất một phép kiểm `fail`: Python ngoài khoảng `>=3.11,<3.13`; thiếu `mujoco`, `myo-sim`, `gymnasium` hoặc `numpy` |
| 2 | Tham số sai (cờ không biết) |

Quy tắc: `overall` trong JSON = `fail` ⇔ mã thoát 1. Thời gian chạy ≤ 30 s (NFR-ENV-001); `torch` chỉ được nhập (lười) khi đã cài, và việc nhập thất bại ghi `warn` chứ không làm lệnh sập.

<a id="quy-uoc-chung-cho-moi-cli-python-m-mma-ai-va-scripts-py"></a>
## Quy ước chung cho mọi CLI `python -m mma_ai…` và `scripts/*.py`

| Quy ước | Nội dung | FR / INV |
|---|---|---|
| Đầu ra chuẩn | Ở đầu `main()`, đặt `stdout`/`stderr` sang UTF-8 với `errors="replace"` (nếu luồng hỗ trợ `reconfigure`); thông báo tiếng Việt không bao giờ gây `UnicodeEncodeError` | FR-013, NFR-ENC-001 |
| Mã thoát | **Không đổi** mã thoát đã công bố của `001`…`005` trên bất kỳ OS nào; lỗi nền tảng mới dùng mã sẵn có của nhóm lỗi tương ứng (ví dụ "không có màn hình" giữ mã của `005`) | INV-001 |
| Đường dẫn | Mọi đường dẫn in ra hoặc ghi vào bản ghi là tương đối và dùng `/` | FR-011, INV-005 |
| Viewer 3D trên macOS | Chạy bằng `mjpython -m <mô-đun>` thay cho `python -m <mô-đun>`; nếu chạy bằng `python`, lệnh in lỗi tiếng Việt nêu cách chạy bằng `mjpython` và thoát bằng mã "không có màn hình" của CLI đó | FR-007 |
| `--headless` | Không nạp GLFW/viewer trên cả ba OS | FR-008 |
| Ghi tệp | Mọi tệp dữ liệu ghi nguyên tử (FR-009); lỗi ghi nêu đường dẫn đích | INV-003 |

<a id="hop-dong-thu-thap-test-co-che-loai-theo-nang-luc"></a>
## Hợp đồng thu thập test (cơ chế loại theo năng lực)

| Mục | Nội dung | FR / INV |
|---|---|---|
| Dấu | `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `posix_only`, `linux_only`, `macos_only`; cú pháp `@pytest.mark.<dấu>("<lý do tiếng Việt>")` hoặc `reason="…"` | FR-021 |
| Thiếu lý do | Lỗi thu thập (`UsageError`), không test nào chạy | INV-006 |
| Loại | Test bị loại khi thu thập (`deselected`), không phải `skipped`/`xfailed`; mỗi test bị loại có tên + lý do ở phần tổng kết cuối | FR-021, INV-006 |
| Tuỳ chọn | `--capability-report <tệp>` ghi danh sách bị loại ra JSON (artefact CI); `--capability-max-ratio <số>` (mặc định 0,05): phiên thất bại nếu tỷ lệ loại vượt ngưỡng | NFR-CI-001 |
