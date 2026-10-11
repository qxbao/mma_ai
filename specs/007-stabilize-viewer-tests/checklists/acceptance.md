---
id: "ACCEPTANCE-007"
title: "Checklist nghiệm thu 007-stabilize-viewer-tests"
doc_type: tracing
owner_agent: qa
status: draft
updated: "2026-10-11"
feature: "007-stabilize-viewer-tests"
---

# Checklist nghiệm thu 007-stabilize-viewer-tests

- [Truy vết nghiệm thu](#truy-vet-nghiem-thu)


Nguồn gốc là `docs/00-input/fast-run-20261011-36c037.md` qua `request.link`; yêu cầu gốc không gán mã AC, còn `spec.md` quy ước AC-1…AC-5 cho năm điều kiện đó. Điểm vào thật (entrypoint) là các lệnh `python -m mma_ai.visualization.cli` và `python -m mma_ai.monitoring.cli`; mọi đường dẫn test tính từ gốc kho (repository). Bằng chứng máy là kết quả cổng; bản ghi E2E (end-to-end) là ảnh/chẩn đoán theo mã AC.

- Tự chốt: dùng AC-1…AC-5 của `spec.md` vì yêu cầu gốc không có mã AC nhưng mô tả đủ năm điều kiện; giữ số `25 s` và giới hạn `1–2 lần` mỗi lượt đúng theo yêu cầu gốc — lý do: nguồn gốc ưu tiên hơn spec khi truy vết số liệu.

<a id="truy-vet-nghiem-thu"></a>
## Truy vết nghiệm thu

- [ ] AC-1 — Viewer thật phải chọn nhánh theo `display_available()`; nhánh có màn hình không quá hạn `25 s`, nhánh không có cửa sổ GL không treo và mỗi lượt chỉ chạy 1–2 lần. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705) và `tests/integration/test_replay_viewer_real.py` (unit, T702) chưa tồn tại. Task: T702, T703, T705. Bằng chứng máy: cổng T702, T703, T705 THIẾU; capture E2E: AC-1 của T705 THIẾU.
- [ ] AC-2 — Tiến trình View3D phải được chờ khởi chạy có hạn mức thay vì kiểm PID sớm, để không chập chờn khi máy bận. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại. Task: T701, T703, T705. Bằng chứng máy: cổng T701, T703, T705 THIẾU; capture E2E: AC-2 của T705 THIẾU.
- [ ] AC-3 — Nguyên nhân thật của từng test phải được chạy riêng nhiều lần và ghi báo cáo trước khi sửa, còn mỗi lượt chạy chỉ 1–2 lần. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705), `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại. Task: T701, T702, T703, T705. Bằng chứng máy: cổng T701, T702, T703, T705 và báo cáo T703 THIẾU; capture E2E: AC-3 của T705 THIẾU.
- [ ] AC-4 — Không được thêm `xfail`/`skip` hay nới khẳng định nghiệm thu của 005/003; yêu cầu gốc chỉ cho sửa hai tệp test. THIẾU test mức entrypoint: `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chỉ kiểm gián tiếp; MÂU THUẪN cần xử lý: T705 tạo `tests/e2e/test_007_viewer_entrypoint.py`, là tệp thứ ba trái giới hạn hai tệp của yêu cầu gốc và FR-007. Task: T701, T702, T703. Bằng chứng máy: cổng T701, T702, T703 THIẾU; capture E2E: THIẾU.
- [ ] AC-5 — Nếu phép đo cho thấy gốc ở `src/`, phải dừng, không sửa `src/` và báo nguyên nhân; không được che kiểm thử còn đỏ. THIẾU test mức entrypoint: `tests/integration/test_replay_viewer_real.py` (unit, T702) chưa tồn tại và không có E2E được T705 giao cho nhánh dừng-và-báo này. Task: T702, T703. Bằng chứng máy: cổng T702, T703 và báo cáo T703 THIẾU; capture E2E: THIẾU.
- [ ] INV-001 — Số test và độ chặt khẳng định không giảm, không thêm cơ chế bỏ qua. THIẾU test mức entrypoint: `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại; phép quét của T703 chưa phải entrypoint. Task: T701, T702, T703. Bằng chứng máy: cổng T701, T702, T703 THIẾU; capture E2E: THIẾU.
- [ ] INV-002 — Hai test phải độc lập thứ tự chạy, không để tiến trình, luồng hoặc tệp mồ côi ngoài `tmp_path`. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705), `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại. Task: T701, T702, T703, T705. Bằng chứng máy: cổng T701, T702, T703, T705 THIẾU; capture E2E: AC-1, AC-2 của T705 THIẾU.
- [ ] INV-003 — Vùng sửa phải đúng hai tệp integration và không đổi `src/`. THIẾU test mức entrypoint: `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại; MÂU THUẪN cần xử lý: output E2E của T705 là tệp thứ ba nên chưa chứng minh bất biến này. Task: T701, T702, T703. Bằng chứng máy: cổng T701, T702, T703 THIẾU; capture E2E: THIẾU.
- [ ] NFR-REL-001 — Mỗi test riêng phải xanh 5/5, riêng View3D xanh thêm 5/5 dưới tải CPU nền, không có lần quá hạn thiếu chẩn đoán. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705), `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại; chuỗi 5/5 phải do T703 chạy. Task: T701, T702, T703, T705. Bằng chứng máy: cổng T701, T702, T703, T705 và báo cáo T703 THIẾU; capture E2E: AC-1, AC-2 của T705 THIẾU.
- [ ] NFR-PERF-001 — Viewer có màn hình tối đa 25 s, không màn hình tối đa 5 s; phần View3D riêng tối đa 10 s và chờ khởi chạy tối đa 5 s. THIẾU trên nhánh tích hợp: `tests/e2e/test_007_viewer_entrypoint.py` (entrypoint, T705), `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại. Task: T701, T702, T703, T705. Bằng chứng máy: cổng T701, T702, T703, T705 và phép đo `--durations=5` của T703 THIẾU; capture E2E: AC-1, AC-2 của T705 THIẾU.
- [ ] NFR-QUAL-001 — `ruff check` và `mypy` phải 0 lỗi trên hai tệp test đã sửa. THIẾU test mức entrypoint: `tests/integration/test_replay_viewer_real.py` (unit, T702) và `tests/integration/test_viewer3d_train.py` (unit, T701) chưa tồn tại; lint/kiểu không chạy ứng dụng thật. Task: T701, T702. Bằng chứng máy: cổng T701, T702 THIẾU; capture E2E: THIẾU.
