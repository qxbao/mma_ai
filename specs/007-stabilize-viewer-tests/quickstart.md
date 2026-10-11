---
id: "QUICKSTART-007"
title: "Quickstart — kiểm chứng sửa hai test hiển thị/tiến trình"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "007-stabilize-viewer-tests"
version: "1.0.0"
---

# Quickstart: kiểm chứng sửa hai test hiển thị/tiến trình

- [Kịch bản 1 — T-B không còn chập chờn khi máy bận (AC-2, INV-002)](#kich-ban-1-t-b-khong-con-chap-chon-khi-may-ban-ac-2-inv-002)
- [Kịch bản 2 — T-A xanh tất định hoặc dừng-và-báo có chẩn đoán (AC-1, AC-3, AC-5)](#kich-ban-2-t-a-xanh-tat-dinh-hoac-dung-va-bao-co-chan-doan-ac-1-ac-3-ac-5)
- [Kịch bản 3 — Không che lỗi, không nới nghiệm thu (AC-4, INV-001, INV-003)](#kich-ban-3-khong-che-loi-khong-noi-nghiem-thu-ac-4-inv-001-inv-003)
- [Kịch bản 4 — Hạn mức và thời gian (NFR-PERF-001)](#kich-ban-4-han-muc-va-thoi-gian-nfr-perf-001)


Tiền đề: worktree của task trên nhánh tích hợp có `src/` và `tests/`; môi trường có `mujoco`, `myo-sim` (và `torch` nếu muốn chạy phần huấn luyện thật của T-B). Chi tiết thiết kế ở [plan.md](plan.md), nguyên nhân và cách đo ở [research.md](research.md); không lặp lại ở đây.

<a id="kich-ban-1-t-b-khong-con-chap-chon-khi-may-ban-ac-2-inv-002"></a>
## Kịch bản 1 — T-B không còn chập chờn khi máy bận (AC-2, INV-002)

1. Chạy `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/integration/test_viewer3d_train.py::test_view3d_process_separate` — kỳ vọng xanh.
2. Lặp bước 1 tới 5 lần liên tiếp — kỳ vọng 5/5 xanh (NFR-REL-001).
3. Bật tải CPU nền (số tiến trình bận ≥ số lõi logic) rồi lặp bước 1 tới 5 lần — kỳ vọng 5/5 xanh.
4. Kiểm cửa sổ giữa "tạo" và `.start()` đã được xử lý: test tự động `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` chờ PID có hạn mức (không còn `pid is None`).
5. Kiểm đường lỗi: hạn mức hết khi tiến trình không khởi chạy cho thông báo "không khởi chạy được trong hạn mức" (kiểm bằng bản thử nghiệm trong `tmp`, không đổi `src/`).

<a id="kich-ban-2-t-a-xanh-tat-dinh-hoac-dung-va-bao-co-chan-doan-ac-1-ac-3-ac-5"></a>
## Kịch bản 2 — T-A xanh tất định hoặc dừng-và-báo có chẩn đoán (AC-1, AC-3, AC-5)

1. Ghi môi trường đo (`DISPLAY`, `WAYLAND_DISPLAY`, `MUJOCO_GL`) và kết quả `display_available()`.
2. Chạy `uv run --isolated --with pytest pytest -q -p no:cacheprovider -m display tests/integration/test_replay_viewer_real.py` — kỳ vọng: nếu `available=True` thì lệnh con kết thúc ≤ 25 s, mã 0, đủ các mục "Tóm tắt phiên phát lại:"; nếu `available=False` thì mã 7 ≤ 5 s kèm gợi ý `--headless` (test tự động `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display`).
3. Lặp bước 2 tới 5 lần — kỳ vọng 5/5 xanh (NFR-REL-001); chạy kèm `-n auto` cùng bộ tích hợp một lần — kỳ vọng xanh.
4. Nhánh không màn hình cưỡng bức vẫn xanh: `tests/integration/test_replay_viewer_real.py::test_real_viewer_forced_no_display_reports_code_7`.
5. Nếu đo cho thấy nguyên nhân ở `src/` (research.md Q2: H1/H2): kỳ vọng báo cáo nêu tệp, hàm, ngăn xếp/số đo, đề xuất; `git diff --stat` không có tệp trong `src/`; T-A ghi "còn đỏ vì nguyên nhân ở `src/`" (AC-5).

<a id="kich-ban-3-khong-che-loi-khong-noi-nghiem-thu-ac-4-inv-001-inv-003"></a>
## Kịch bản 3 — Không che lỗi, không nới nghiệm thu (AC-4, INV-001, INV-003)

1. `git diff --name-only <nhánh tích hợp>` — kỳ vọng đúng hai tệp: `tests/integration/test_replay_viewer_real.py`, `tests/integration/test_viewer3d_train.py`.
2. Quét hai tệp tìm `skip`, `skipif`, `xfail`, `importorskip` mới — kỳ vọng 0 kết quả mới (dấu `pytest.mark.display` có sẵn không tính).
3. So danh sách khẳng định nghiệm thu của FR-004 (005 AC-1/AC-2, FR-001/004/005/011/014; 003 FR-022/INV-005) với diff — kỳ vọng còn nguyên hoặc chặt hơn; `pytest --collect-only -q` trên hai tệp cho số kiểm thử không giảm.
4. `uv run --isolated --with ruff ruff check <hai tệp>` và `uv run --isolated --with mypy mypy --strict <hai tệp>` — kỳ vọng 0 lỗi (NFR-QUAL-001).

<a id="kich-ban-4-han-muc-va-thoi-gian-nfr-perf-001"></a>
## Kịch bản 4 — Hạn mức và thời gian (NFR-PERF-001)

1. `uv run --isolated --with pytest pytest -q -p no:cacheprovider --durations=5 <nodeid>` cho từng kiểm thử — kỳ vọng T-A lệnh con ≤ 25 s (có màn hình) hoặc ≤ 5 s (không màn hình); T-B phần tiến trình tách riêng ≤ 10 s, chờ khởi chạy ≤ 5 s.
2. Kiểm thông báo lỗi khi quá hạn nêu lệnh, hạn mức, đầu ra (FR-002/FR-008) bằng bản thử nghiệm trong `tmp` với lệnh con ngủ lâu — kỳ vọng kiểm thử đỏ có chẩn đoán và không để tiến trình mồ côi (INV-002).
