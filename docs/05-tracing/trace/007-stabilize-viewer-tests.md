---
id: "TRACE-007"
title: "Ma trận truy vết 007-stabilize-viewer-tests"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-11"
---

# Ma trận truy vết 007-stabilize-viewer-tests

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/007-stabilize-viewer-tests.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/007-stabilize-viewer-tests/spec.md` (yêu cầu) và `specs/007-stabilize-viewer-tests/tasks.md` (task `T701`…`T704`).
> Feature chỉ sửa kiểm thử nên "test" ở đây chính là hai kiểm thử được sửa và các cổng máy đo chúng. Mức `entrypoint` = kiểm thử chạy lệnh thật `python -m mma_ai.visualization.cli` hoặc `python -m mma_ai.monitoring.cli` bằng tiến trình con; mức `cổng` = lệnh đo của cổng (`ruff`, `mypy`, so diff, quét `skip`/`xfail`, chạy lặp). Chưa có mã sửa nên cột trạng thái "có" nghĩa là đã có task + test/cổng dự kiến, KHÔNG có nghĩa đã chạy xanh. Mã AC-1, AC-2, FR-011, FR-014 **của 005** không thuộc ma trận này (xem `docs/05-tracing/trace/005-replay-3d-muscle-demo.md`).

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Kiểm thử viewer thật chọn nhánh theo `display_available()` và cho kết quả xanh tất định ở cả hai nhánh (có màn hình: mã 0, đủ mục tóm tắt, trong hạn; không màn hình: mã 7 ≤ 5 s); không lần nào treo tới quá hạn mà không có chẩn đoán | T702, T703, T704 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_forced_no_display_reports_code_7` | entrypoint | có |
| AC-2 | `test_view3d_process_separate` chờ tiến trình View3D có PID trong hạn mức rồi mới khẳng định; xanh kể cả khi máy bận | T701, T703, T704 | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` | entrypoint | có |
| AC-3 | Nguyên nhân thật của từng kiểm thử được đo (chạy riêng, nhiều lần, ghi môi trường) và ghi lại trước khi sửa; bản sửa tác động đúng nguyên nhân | T701, T702, T703, T704 | báo cáo `.ai/runs/*/reports/builder-*.md` (mục `Nguyên nhân gốc`), `.ai/runs/*/reports/qa-007-reliability.md`, `evidence/reviews/T704.verdict` | cổng | có |
| AC-4 | Không che lỗi, không nới nghiệm thu: không `skip`/`xfail`/`importorskip` mới, khẳng định còn nguyên hoặc chặt hơn, chỉ hai tệp kiểm thử bị sửa | T701, T702, T703, T704 | quét `skip`/`skipif`/`xfail`/`importorskip`, `pytest --collect-only -q` (số kiểm thử không giảm), `git diff --name-only` (đúng hai tệp), `evidence/reviews/T704.verdict` | cổng | có |
| AC-5 | Nguyên nhân ở `src/` thì DỪNG và báo (tệp, hàm, bằng chứng, đề xuất), không tự sửa `src/`; kiểm thử còn lại vẫn được sửa và chứng minh | T702, T703, T704 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` (còn đỏ CÓ chẩn đoán nếu gốc ở `src/`), `git diff --name-only` (0 tệp trong `src/`), `evidence/reviews/T704.verdict` | entrypoint | có |
| FR-001 | Kiểm thử viewer thật chọn nhánh theo `display_available()`, xanh tất định ở cả hai nhánh | T702 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| FR-002 | Mọi lệnh con có hạn mức hữu hạn khai tường minh; quá hạn thì dừng, dọn nhóm tiến trình, báo lệnh/hạn mức/đầu ra thay vì `TimeoutExpired` trần | T702 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` (qua `_run_cli_bounded`), `tests/integration/test_replay_viewer_real.py::test_real_viewer_forced_no_display_reports_code_7` | entrypoint | có |
| FR-003 | `test_view3d_process_separate` chờ có hạn mức tới khi tiến trình View3D có PID; hết hạn báo "không khởi chạy được trong hạn mức" | T701 | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` | entrypoint | có |
| FR-004 | Mọi khẳng định nghiệm thu còn nguyên hoặc chặt hơn (005 AC-1/AC-2/FR-001/FR-004/FR-005/FR-011/FR-014; 003 FR-022, INV-005) | T701, T702, T704 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display`, `tests/integration/test_viewer3d_train.py::test_view3d_process_separate`, `evidence/reviews/T704.verdict` | entrypoint | có |
| FR-005 | Nguyên nhân thật xác định bằng chạy riêng nhiều lần và ghi cùng bằng chứng trước khi sửa | T701, T702, T703 | báo cáo `.ai/runs/*/reports/builder-*.md` (`Nguyên nhân gốc`, `BÀI HỌC`), `.ai/runs/*/reports/qa-007-reliability.md` | cổng | có |
| FR-006 | Không `skip`/`skipif`/`xfail`/`importorskip` mới, không giảm số kiểm thử, không nới ngưỡng; `pytest.mark.display` giữ nguyên | T701, T702, T703 | quét `skip`/`xfail`/`importorskip` trong hai tệp, `pytest --collect-only -q` trên hai tệp | cổng | có |
| FR-007 | Chỉ hai tệp kiểm thử được sửa; nguyên nhân ở `src/` thì dừng sửa kiểm thử đó và báo | T701, T702, T704 | `git diff --name-only` (đúng hai tệp), `evidence/reviews/T704.verdict` | cổng | có |
| FR-008 | Thông báo lỗi của kiểm thử bằng tiếng Việt, nêu giá trị và ngữ cảnh (lệnh, hạn mức, mã thoát, đầu ra) | T701, T702 | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| NFR-REL-001 | Mỗi kiểm thử chạy riêng xanh 5/5 liên tiếp; T-B thêm 5/5 có tải CPU nền; 0 lần quá hạn không chẩn đoán | T701, T702, T703 | `pytest <nodeid>` lặp 5 lần mỗi kiểm thử (cộng dồn qua các lượt), `.ai/runs/*/reports/qa-007-reliability.md` | cổng | có |
| NFR-PERF-001 | T-A lệnh con ≤ 25 s (có màn hình) / ≤ 5 s (không màn hình); T-B phần tiến trình tách riêng ≤ 10 s, chờ khởi chạy ≤ 5 s | T701, T702, T703 | `pytest --durations=5 <nodeid>`, `.ai/runs/*/reports/qa-007-reliability.md` | cổng | có |
| NFR-QUAL-001 | `ruff check` và `mypy --strict` xanh (0 lỗi) trên hai tệp kiểm thử đã sửa | T701, T702 | cổng `lint` (`ruff check .`), cổng `typecheck` (`mypy --strict .`) | cổng | có |
| INV-001 | Số kiểm thử và độ chặt khẳng định trong hai tệp không giảm; không thêm cơ chế bỏ qua | T701, T702, T703, T704 | `pytest --collect-only -q` trên hai tệp (số kiểm thử không giảm), quét `skip`/`xfail`/`importorskip`, `evidence/reviews/T704.verdict` | cổng | có |
| INV-002 | Kiểm thử độc lập thứ tự và trạng thái lần trước; không để tiến trình, luồng, tệp mồ côi ngoài `tmp_path` | T701, T702, T703 | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` (dọn bằng `stop_event`), `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` (giết nhóm tiến trình), chạy lặp và chạy cả bộ ở `.ai/runs/*/reports/qa-007-reliability.md` | entrypoint | có |
| INV-003 | Vùng ghi đúng hai tệp kiểm thử; `src/` không đổi | T701, T702, T703, T704 | `git diff --name-only` (đúng hai tệp, 0 tệp trong `src/`), `evidence/reviews/T704.verdict` | cổng | có |
| SC-001 | Cổng tests xanh ở hai kiểm thử, 5/5 lần mỗi kiểm thử chạy riêng và 5/5 có tải nền ở T-B; 0 lần đỏ chập chờn | T701, T702, T703 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display`, `tests/integration/test_viewer3d_train.py::test_view3d_process_separate`, `.ai/runs/*/reports/qa-007-reliability.md` | entrypoint | có |
| SC-002 | 0 lần T-A treo tới quá hạn mà không có chẩn đoán; quá hạn luôn kèm lệnh, hạn mức, đầu ra | T702, T703 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| SC-003 | 100% khẳng định nghiệm thu của FR-004 còn nguyên hoặc chặt hơn; 0 `skip`/`xfail` mới; số kiểm thử không giảm | T701, T702, T703, T704 | quét `skip`/`xfail`/`importorskip`, `pytest --collect-only -q`, `evidence/reviews/T704.verdict` | cổng | có |
| SC-004 | Mỗi kiểm thử có đúng một mục nguyên nhân thật kèm số lần chạy và kết quả đo trước/sau, ghi môi trường đo | T701, T702, T703 | báo cáo `.ai/runs/*/reports/builder-*.md` (`Nguyên nhân gốc`), `.ai/runs/*/reports/qa-007-reliability.md` | cổng | có |
| SC-005 | Diff chỉ chứa hai tệp kiểm thử; 0 thay đổi trong `src/`; nguyên nhân ở `src/` thì báo cáo nêu tệp, hàm, bằng chứng, đề xuất | T702, T703, T704 | `git diff --name-only`, `evidence/reviews/T704.verdict` | cổng | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Vai | Mã hiện thực (FR · INV · NFR · AC) | Tệp test / cổng |
|---|---|---|---|
| T701 | builder | FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, INV-001, INV-002, INV-003, NFR-PERF-001, NFR-QUAL-001, NFR-REL-001, AC-2, AC-3, AC-4 | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` |
| T702 | builder | FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008, INV-001, INV-002, INV-003, NFR-PERF-001, NFR-QUAL-001, NFR-REL-001, AC-1, AC-3, AC-4, AC-5 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` |
| T703 | qa | NFR-REL-001, NFR-PERF-001, INV-001, INV-002, INV-003, AC-1, AC-2, AC-3, AC-4, AC-5, FR-004, FR-006 | `.ai/runs/*/reports/qa-007-reliability.md` |
| T704 | reviewer | AC-1, AC-2, AC-3, AC-4, AC-5, INV-001, INV-002, INV-003, NFR-REL-001, NFR-PERF-001, NFR-QUAL-001, FR-005, FR-007 | `evidence/reviews/T704.verdict` |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không mã nào ở trạng thái `THIẾU`: mọi `AC-*`, `FR-*`, `INV-*`, `NFR-*`, `SC-*` của `spec.md` đều có task và test/cổng dự kiến.
- Giới hạn của bằng chứng (không phải mã thiếu): nguyên nhân của `test_real_viewer_plays_or_reports_no_display` CHƯA ĐO; môi trường của cổng tests có hay không có cửa sổ GL dùng được CHƯA KIỂM. Nếu phép đo ở `T702` cho thấy gốc ở `src/` (viewer treo lúc mở/đóng, hoặc `display_available()` báo "có" mà không có cửa sổ GL dùng được), AC-1 của kiểm thử đó chưa thể xanh bằng sửa kiểm thử: AC-5 áp dụng, báo cáo nêu tệp, hàm, bằng chứng, đề xuất. Người xử phần `src/`: người dùng hoặc vai khác được giao ở feature sau.
- `NFR-QUAL-001` không có kiểm thử riêng; được đo bằng cổng `lint` và `typecheck` của dự án, hai cổng này chạy trên cả hai tệp.
- Số "5 lần" của `NFR-REL-001` là ngưỡng tự chốt (spec, Assumptions); nâng nếu số đo cho thấy tỷ lệ đỏ gốc thấp hơn 1/5.
