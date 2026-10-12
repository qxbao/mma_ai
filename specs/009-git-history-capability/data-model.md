---
id: "DM-009"
title: "Năng lực requires_git_history — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Mô hình dữ liệu (Data model) — 009

- [Đối tượng tạm của kiểm thử (Transient test objects)](#doi-tuong-tam-cua-kiem-thu-transient-test-objects)
- [Báo cáo năng lực (đã có từ 006, chỉ đọc)](#bao-cao-nang-luc-da-co-tu-006-chi-doc)
- [Quan hệ và trạng thái](#quan-he-va-trang-thai)


Feature chỉ thêm test và một dấu pytest nên **không có thực thể nghiệp vụ, bảng, sự kiện hay tệp dữ liệu mới**: không `TBL-*`, không `EVT-*`, không `CMD-*`/`QRY-*`/`API-*`, không `contracts/`. Tài liệu này ghi các đối tượng tạm trong bộ nhớ/thư mục tạm của test để người đọc biết chúng không bền vững và không đổi hợp đồng của 006.

<a id="doi-tuong-tam-cua-kiem-thu-transient-test-objects"></a>
## Đối tượng tạm của kiểm thử (Transient test objects)

| Đối tượng | Kiểu | Vòng đời | Người tạo | Người dùng | Ghi chú |
|---|---|---|---|---|---|
| Bản giả `subprocess.run` | hàm trả `subprocess.CompletedProcess` hoặc ném `OSError`/`TimeoutExpired`, ghi lại `args`/`kwargs` | một test (monkeypatch tự khôi phục) | test FR-001, FR-002 | `_capability_available` | kiểm `timeout` ≤ 5 (NFR-REL-001); không đổi mã `capability_gate.py` |
| Cây tạm "không có .git" | thư mục `gốc/tests/unit/capability_gate.py` + `gốc/work/test_example.py` | một test (`tmp_path`) | test FR-003 | pytest tiến trình con | `parents[2]` của bản sao plugin = `gốc` (không có `.git`); `GIT_CEILING_DIRECTORIES` chặn leo kho cha |
| Tệp báo cáo năng lực | JSON (`--capability-report`) | một test (`tmp_path`) | pytest tiến trình con | test FR-003 | khuôn dưới đây; chỉ đọc |
| Dấu `requires_git_history` | decorator pytest | vĩnh viễn trong tệp e2e | QA (W-2) | cổng năng lực lúc thu thập | kèm `reason="Máy không có lịch sử git"`; mức hàm |

<a id="bao-cao-nang-luc-da-co-tu-006-chi-doc"></a>
## Báo cáo năng lực (đã có từ 006, chỉ đọc)

Khuôn do `capability_gate.pytest_collection_modifyitems` sinh (**ĐÃ ĐỌC**), feature này chỉ **đọc** để khẳng định, không đổi:

| Khoá | Kiểu | Nghĩa | Giá trị kỳ vọng ở test FR-003 |
|---|---|---|---|
| `collected` | số nguyên | tổng test thu thập (gồm cả bị loại) | 20 |
| `deselected` | số nguyên | số test bị loại | 1 |
| `ratio` | số thực | `deselected / collected` | 0,05 (không vượt ngưỡng vì so sánh `>`) |
| `items[].nodeid` | chuỗi | định danh test bị loại | `test_example.py::test_…` |
| `items[].marker` | chuỗi | tên dấu năng lực | `requires_git_history` |
| `items[].reason` | chuỗi | lý do tiếng Việt từ dấu | `Máy không có lịch sử git` |

<a id="quan-he-va-trang-thai"></a>
## Quan hệ và trạng thái

Trạng thái của test INV-002 của 008 theo năng lực (mỗi phiên pytest, không lưu):

| Năng lực `git rev-parse --is-inside-work-tree` ở gốc dự án | Phép dò | Trạng thái test lúc thu thập | Kết quả |
|---|---|---|---|
| mã 0 | `True` | còn trong bộ chạy | chạy thật: PASS (hoặc đỏ vì lỗi thật) — AC-1 |
| mã ≠ 0 (ví dụ 128) | `False` | bị loại, có báo cáo + lý do | không PASS/skip/xfail — AC-2 |
| `OSError` (không có `git`) | `False` | bị loại, có báo cáo + lý do | như trên — AC-2 |
| `TimeoutExpired` (> 5 s) | `False` | bị loại, có báo cáo + lý do | như trên — AC-2, NFR-REL-001 |

Bất biến liên quan: INV-001 (không che lỗi, khôi phục bản giả), INV-002 (thân test 008 giữ nguyên), INV-003 (ngưỡng 5%, `pyproject.toml`, `uv.lock` giữ nguyên) — khai ở [spec.md](spec.md), không khai lại ở đây.
