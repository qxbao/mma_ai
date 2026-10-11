---
id: "DM-007"
title: "Sửa gốc 2 test hiển thị/tiến trình — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "007-stabilize-viewer-tests"
version: "1.0.0"
---

# Mô hình dữ liệu (Data model) — 007

- [Đối tượng tạm của kiểm thử (Transient test objects)](#doi-tuong-tam-cua-kiem-thu-transient-test-objects)
- [Quan hệ và trạng thái](#quan-he-va-trang-thai)
- [Bất biến liên quan dữ liệu (Invariants)](#bat-bien-lien-quan-du-lieu-invariants)


Feature chỉ sửa hai tệp kiểm thử (test) nên **không có thực thể nghiệp vụ, bảng, sự kiện hay tệp dữ liệu mới**: không `TBL-*`, không `EVT-*`, không `contracts/`. Tài liệu này ghi các đối tượng tạm trong bộ nhớ của kiểm thử (test-scoped, transient) để người đọc biết chúng không bền vững và không đổi hợp đồng dữ liệu của 003/005. Dữ liệu sản phẩm (`ui.json`, `latest.json`, tệp episode) giữ nguyên theo feature gốc — chỉ **đọc** để khẳng định.

<a id="doi-tuong-tam-cua-kiem-thu-transient-test-objects"></a>
## Đối tượng tạm của kiểm thử (Transient test objects)

| Đối tượng | Kiểu | Vòng đời | Người tạo | Người dùng | Ghi chú |
|---|---|---|---|---|---|
| Tiến trình View3D thay thế (stand-in process) | `multiprocessing.Process` | tạo ngay khi hàm tạo được gọi; `.start()` gọi sau ở luồng khác; kết thúc bằng `terminate()` | hàm tạo thay thế trong `test_view3d_process_separate` | `_wait_until_started`, các khẳng định PID/`is_alive()` | `pid is None` đến khi `.start()` chạy ⇒ nguồn gốc chập chờn của T-B |
| Danh sách theo dõi tiến trình | `list[Process]` | trong một lần chạy kiểm thử | hàm tạo thay thế | vòng chờ của kiểm thử | giữ nguyên (D1/D2 trong plan.md): "đã tạo" ≠ "đã có PID" |
| Kết quả lệnh con có hạn mức (bounded subprocess result) | `returncode`, `stdout`, `stderr`, cờ quá hạn | một lần gọi `_run_cli_bounded` | `_run_cli_bounded` | các khẳng định của T-A, thông điệp lỗi | quá hạn ⇒ giết cả nhóm tiến trình, vẫn thu đầu ra còn lại |
| Thư mục làm việc tạm | `tmp_path` | một kiểm thử | pytest | cả hai kiểm thử | nơi duy nhất được ghi tệp (INV-002) |

<a id="quan-he-va-trang-thai"></a>
## Quan hệ và trạng thái

```text
Tiến trình View3D thay thế:
  đã tạo (pid=None) --.start()--> đang chạy (pid≠None) --terminate()--> đã dừng
        |                                  |
        +------ hết hạn chờ ⇒ kiểm thử đỏ (thông điệp "không khởi chạy được trong hạn mức")
                                           +-- thoát sớm (exitcode≠None) ⇒ báo "đã thoát sớm" kèm mã thoát
```

Điều kiện đi tiếp của kiểm thử là "đã có PID" hoặc "đã thoát sớm", không phải "đã được tạo" (FR-003, AC-2).

<a id="bat-bien-lien-quan-du-lieu-invariants"></a>
## Bất biến liên quan dữ liệu (Invariants)

- **INV-001**: số kiểm thử và độ chặt khẳng định không giảm — kiểm bằng đếm kiểm thử và quét `skip`/`xfail`/`importorskip` trong hai tệp.
- **INV-002**: kiểm thử không để tiến trình, luồng hay tệp mồ côi ngoài `tmp_path` — đối tượng tạm ở bảng trên đều bị dọn (`terminate()`, `stop_event`, giết nhóm tiến trình).
- **INV-003**: vùng ghi là đúng hai tệp kiểm thử; `src/` không đổi — nên không đổi schema hay hợp đồng dữ liệu nào.
