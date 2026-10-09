---
id: "TRACE-001-ACCEPTANCE"
title: "Nghiệm thu truy vết M0 — Thiết lập môi trường và Benchmark vật lý"
doc_type: tracing
owner_agent: reviewer
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
---

# Checklist nghiệm thu truy vết (acceptance tracing) M0

- [Ma trận nghiệm thu](#ma-tran-nghiem-thu)


> Mỗi ô chỉ được `ai-sdlc reconcile --mark` tích sau khi mọi Task nêu trên dòng đã xanh, đã gộp vào nhánh tích hợp và mọi tệp kiểm thử (test file) nêu trên dòng tồn tại trên nhánh đó. Dòng không có Task thực không bao giờ được tích.
>
> Tự chốt: dùng `.ai/current-request` theo thứ tự nguồn bắt buộc vì feature không có `request.link`; tệp này trỏ tới yêu cầu M1 `request-4.md`, không phải M0 — lý do: không được đoán hay chép AC của module khác. Mã AC-1…AC-5 trùng nhưng nội dung nguồn và `spec.md` lệch, nên mọi dòng AC giữ trạng thái `THIẾU` cho tới khi nguồn M0 được nối đúng.

<a id="ma-tran-nghiem-thu"></a>
## Ma trận nghiệm thu

- [ ] AC-1 — LỆCH NGUỒN: AC-1 của `docs/00-input/split/yeu-cau-a7634ac9/request-4.md` yêu cầu replay Viewer M1, còn `spec.md` yêu cầu mô phỏng MyoElbow 6 cơ headless M0; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] AC-2 — LỆCH NGUỒN: AC-2 của nguồn yêu cầu demo checkpoint M1, còn `spec.md` yêu cầu smoke test NaN/Inf và lỗi vật lý M0; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] AC-3 — LỆCH NGUỒN: AC-3 của nguồn yêu cầu replay không display M1, còn `spec.md` yêu cầu báo cáo physics steps/second M0; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] AC-4 — LỆCH NGUỒN: AC-4 của nguồn yêu cầu cảnh báo lệch hash XML khi replay M1, còn `spec.md` yêu cầu peak RAM và GPU memory M0; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] AC-5 — LỆCH NGUỒN: AC-5 của nguồn yêu cầu lỗi đường dẫn episode M1, còn `spec.md` yêu cầu dựng lại môi trường theo hướng dẫn M0; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] INV-001 — Số liệu báo cáo phải từ lần đo thật, không đo được ghi đúng trạng thái; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] INV-002 — Cùng seed, cấu hình và phiên bản phải cho cùng kết luận cùng số NaN/Inf; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] INV-003 — Repo không chứa bí mật hoặc đường dẫn tuyệt đối riêng của máy; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] INV-004 — Đường chạy chính chỉ dùng muscle actuator, ghi số actuator khác cơ bằng 0 và giá trị activation yêu cầu/hiệu dụng; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] NFR-REL-001 — Smoke test phải có 0 NaN và 0 Inf trên mọi mẫu kích hoạt; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] NFR-PERF-001 — Benchmark phải lặp ít nhất 5 lần và báo độ phân tán; Test: `tests/**` THIẾU; Mức: THIẾU entrypoint; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] NFR-REPRO-001 — Hai lần smoke test cùng seed không khác kết luận và số NaN/Inf; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
- [ ] NFR-DOC-001 — Báo cáo nghiệm thu phải có trạng thái và bằng chứng cho đủ 5/5 AC; Test: `tests/**` THIẾU; Mức: unit THIẾU, entrypoint THIẾU; Task: T000 (THIẾU — chưa có `specs/001-m0-physics-benchmark/tasks.md`); Máy: evid&#101;nce/gates/ THIẾU; capture E2E: THIẾU.
