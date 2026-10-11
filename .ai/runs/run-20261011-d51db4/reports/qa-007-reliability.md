---
schema_version: "1.0.0"
run_id: "run-20261011-d51db4"
task_id: "T703"
role: "qa"
generation: "GEN-qa-1791728310728406-83450aab"
status: DONE_WITH_CONCERNS
sha: "0a1a846b30dc2d47b1d19533f79636105d3be3f4"
commands_run:
  - {cmd: "pytest nodeid lặp T-A/T-B", exit_code: 0}
  - {cmd: "pytest suite", exit_code: 0}
concerns:
  - "Môi trường chia sẻ đã có năm tiến trình monitoring.cli từ hơn năm giờ trước."
---

# Báo cáo QA — T703

## Trạng thái

STATUS: DONE_WITH_CONCERNS
SHA: 0a1a846b30dc2d47b1d19533f79636105d3be3f4

## Kết quả

- Kiểm định độc lập (independent QA): T-A xanh 5/5; T-B xanh 5/5 và xanh 5/5 dưới 12 tiến trình tải CPU.
- Hiệu năng (performance): thời gian gọi T-A lớn nhất 1,83 s, dưới 25 s; T-B lớn nhất 0,52 s, dưới 10 s; chờ khởi chạy có hạn mức 5 s theo NFR-PERF-001.
- Môi trường đo: `DISPLAY=:0`; `display_available()` trả `available=True`.
- Thu thập: 9 test ở hai tệp integration; chạy song song cho kết quả 8 passed, 1 skipped (`torch` có sẵn ở dòng 192, không phải cơ chế mới).
- Diff kể từ nền tích hợp không có tệp `src/`; quét không thấy `skip`/`skipif`/`xfail`/`importorskip` mới trong T-A.

## Kiểm tra đã tự chạy

| Lệnh | Exit | Ghi chú |
|---|---:|---|
| `uv run --isolated --with pytest pytest -q -p no:cacheprovider --durations=5 T-A` ×5 | 0 | 5/5 xanh; gọi 1,17–1,83 s. |
| `uv run --isolated --with pytest pytest -q -p no:cacheprovider --durations=5 T-B` ×5 | 0 | 5/5 xanh; gọi 0,50 s. |
| `nproc` tải CPU + lệnh T-B ×5 | 0 | 12 tiến trình bận; 5/5 xanh, gọi 0,51–0,52 s. |
| `pytest --collect-only -q` trên hai tệp | 0 | Thu 9 test. |
| `pytest -q -n auto --durations=5` trên hai tệp | 0 | 8 passed, 1 skipped trong 3,89 s. |
| `pytest -q -p no:cacheprovider tests/e2e` | 0 | Hoàn tất sau kiểm tra clean-install. |
| `pytest -q -p no:cacheprovider -n auto --ignore=tests/e2e` | 0 | Suite không-E2E hoàn tất. |
| `ruff check .` | 0 | All checks passed. |
| `mypy --strict .` | 0 | Success: no issues found in 179 source files. |

## Chuỗi suy luận

Quan sát 1 (mỗi nodeid xanh 5/5) ⇒ NFR-REL-001 đạt cho T-A và T-B.

Quan sát 2 (T-B xanh 5/5 khi 12 lõi logic đều bận) ⇒ cách chờ PID không tái hiện chập chờn dưới tải CPU.

Quan sát 3 (thời gian gọi lớn nhất thấp hơn các ngưỡng 25 s, 10 s và 5 s) ⇒ NFR-PERF-001 đạt trong môi trường có màn hình.

Quan sát 4 (diff không có `src/`, quét không thấy cơ chế bỏ qua mới và thu 9 test) ⇒ INV-001 và INV-003 được bảo toàn trong phạm vi slice.

Quan sát 5 (năm tiến trình `monitoring.cli` có PPID 2711 và đã sống hơn năm giờ trước lượt đo) ⇒ chúng có trước T703, không phải tiến trình mồ côi do các lần chạy hiện tại.

## Nguyên nhân gốc

- ownership — gốc: `.ai/runs/run-20261011-d51db4/reports/qa-007-reliability.md:1` — vì: commit `1662e5dbd72a` chỉ sửa `tests/integration/test_replay_viewer_real.py`, không tạo artifact thuộc output T703 nên `ALREADY_DONE` không có bằng chứng — sửa ở gốc: tạo báo cáo đo độc lập đúng output T703 và commit riêng — chỗ cùng loại đã rà: `git show --stat 1662e5dbd72a`, `git diff --name-only 84cbe9e..HEAD`

BÀI HỌC: Một kết luận đã hoàn tất chỉ hợp lệ khi commit mang đúng artifact thuộc vùng output của task chịu trách nhiệm.

## Cách kiểm chứng lại

`uv run --isolated --with pytest pytest -q -p no:cacheprovider --durations=5 tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display`

`uv run --isolated --with pytest pytest -q -p no:cacheprovider --durations=5 tests/integration/test_viewer3d_train.py::test_view3d_process_separate`

## Concerns hoặc blocker

`DONE_WITH_CONCERNS`: năm tiến trình `mma_ai.monitoring.cli` khởi tạo lúc 15:46–15:51 với PPID ngoài lượt đo vẫn sống trong môi trường chia sẻ. Chúng không phát sinh từ T703, nên QA không tự kết thúc tiến trình của tác vụ khác; chủ sở hữu cần dọn chúng trước lượt kiểm định host-sạch tiếp theo.

Capture E2E do cổng ngoài quản lý; QA không tự tạo tệp capture.

## Bàn giao

Chủ sở hữu môi trường xác nhận và dọn năm tiến trình cũ trước lượt kiểm định host-sạch tiếp theo; không cần thay đổi mã sản phẩm từ T703.
