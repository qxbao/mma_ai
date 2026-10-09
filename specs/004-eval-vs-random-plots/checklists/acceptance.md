---
doc_type: tracing
id: SPEC-004-eval-vs-random-plots-acceptance
title: 'Checklist nghiệm thu: Đánh giá policy và biểu đồ'
owner_agent: spec
status: draft
updated: '2026-10-09'
---

# Checklist nghiệm thu: Đánh giá policy và biểu đồ

Nguồn AC là yêu cầu gốc `REQ-0103` tại `docs/00-input/split/yeu-cau-a7634ac9/request-3.md`; INV và NFR là từ `spec.md`. Bằng chứng máy là cổng kiểm tra; ảnh/chụp vết E2E (end-to-end) của từng AC do máy sinh.

- Tự chốt: dùng `python -m mma_ai.evaluation.cli` là điểm vào thật (entrypoint) — lý do: `scripts/evaluate.py` chưa có task sở hữu; đây là entrypoint được T413 và T424 quy định.

- [ ] AC-1 In và lưu chỉ số của policy đã học và random policy trên cùng tập mục tiêu, gồm tái lập theo seed và lưu cạnh hồ sơ run. Task: T405, T407, T408, T411, T412, T413, T415, T416, T420, T421, T424. tests/integration/test_evaluate_cli.py (entrypoint); tests/integration/test_report_contract.py (entrypoint); tests/integration/test_evaluate_storage.py (entrypoint); tests/integration/test_eval_determinism.py (entrypoint); tests/e2e/test_evaluate_acceptance.py (entrypoint). Bằng chứng máy: cổng kiểm tra; capture E2E AC-1.
- [ ] AC-2 Kết luận policy đã học tốt hơn random theo tiêu chí khai trước, kèm hiệu và khoảng tin cậy. Task: T403, T404, T411, T413, T417, T424. tests/integration/test_verdict_known_policies.py (unit); tests/e2e/test_evaluate_acceptance.py (entrypoint). Bằng chứng máy: cổng kiểm tra; capture E2E AC-2.
- [ ] AC-3 Tạo ảnh loss, reward và activation cho 6 cơ từ log, kể cả khi không có màn hình. Task: T401, T408, T410, T418, T424. tests/integration/test_evaluate_headless.py (entrypoint); tests/e2e/test_evaluate_acceptance.py (entrypoint). Bằng chứng máy: cổng kiểm tra; capture E2E AC-3.
- [ ] AC-4 Từ chối mọi mục tiêu hoặc seed đánh giá giao tập train trước episode đầu. Task: T409, T412, T419, T424, T425. tests/integration/test_evaluate_leakage.py (entrypoint); tests/challenge/test_evaluate_invariants.py (entrypoint); tests/e2e/test_evaluate_acceptance.py (entrypoint). Bằng chứng máy: cổng kiểm tra; capture E2E AC-4; bản ghi challenge T425.
- [ ] AC-5 Báo lỗi rõ, mã thoát khác 0 và không in/lưu kết quả giả khi checkpoint không tồn tại hoặc hỏng. Task: T402, T412, T413, T422, T424, T425. tests/integration/test_evaluate_bad_checkpoint.py (entrypoint); tests/challenge/test_evaluate_invariants.py (entrypoint); tests/e2e/test_evaluate_acceptance.py (entrypoint). Bằng chứng máy: cổng kiểm tra; capture E2E AC-5; bản ghi challenge T425.
- [ ] INV-001 Tập đánh giá, khoảng cách tối thiểu và toàn bộ seed không giao tập train; không xác lập được tập train thì không đánh giá. Task: T409, T412, T419, T425. tests/integration/test_evaluate_leakage.py (entrypoint); tests/challenge/test_evaluate_invariants.py (entrypoint). Bằng chứng máy: cổng kiểm tra; bản ghi challenge T425.
- [ ] INV-002 Hai policy dùng cùng tập, thứ tự, cấu hình, giới hạn episode và hash XML môi trường khớp hồ sơ run. Task: T405, T407, T412, T415, T416. tests/integration/test_evaluate_cli.py (entrypoint); tests/integration/test_report_contract.py (entrypoint). Bằng chứng máy: cổng kiểm tra.
- [ ] INV-003 Mọi hành động là kích thích 6 cơ hữu hạn trong `[0,1]^6`, không có điều khiển lực hoặc toạ độ tay. Task: T406, T407, T415, T425. tests/integration/test_evaluate_cli.py (entrypoint); tests/challenge/test_evaluate_invariants.py (entrypoint). Bằng chứng máy: cổng kiểm tra; bản ghi challenge T425.
- [ ] INV-004 Lỗi hoặc ngắt không để lại, in ra hay công bố kết quả trông hợp lệ; chỉ công bố sau khi hoàn tất. Task: T402, T411, T412, T420, T422, T425. tests/integration/test_evaluate_storage.py (entrypoint); tests/integration/test_evaluate_bad_checkpoint.py (entrypoint); tests/challenge/test_evaluate_invariants.py (entrypoint). Bằng chứng máy: cổng kiểm tra; bản ghi challenge T425.
- [ ] INV-005 Đánh giá chỉ đọc checkpoint, hồ sơ run và nhật ký; không ghi đè kết quả cũ. Task: T411, T412, T420, T423, T425. tests/integration/test_evaluate_storage.py (entrypoint); tests/integration/test_evaluation_imports.py (unit); tests/challenge/test_evaluate_invariants.py (entrypoint). Bằng chứng máy: cổng kiểm tra; bản ghi challenge T425.
- [ ] INV-006 Tiêu chí kết luận được khai trước, không đổi theo kết quả và được ghi nguyên vào báo cáo. Task: T403, T404, T413, T415, T417, T425. tests/integration/test_evaluate_cli.py (entrypoint); tests/unit/test_eval_config.py (unit); tests/challenge/test_evaluate_invariants.py (entrypoint). Bằng chứng máy: cổng kiểm tra; bản ghi challenge T425.
- [ ] INV-007 Cùng checkpoint, cấu hình và seed cho chuỗi hành động random cùng chỉ số trong dung sai quy định. Task: T406, T421. tests/integration/test_eval_determinism.py (entrypoint); tests/unit/test_policies.py (unit). Bằng chứng máy: cổng kiểm tra.
- [ ] NFR-REPRO-001 Tái lập lượt đánh giá cùng seed trên cùng loại thiết bị với sai khác chỉ số không quá `1×10⁻⁶`. Task: T406, T421. tests/integration/test_eval_determinism.py (entrypoint); tests/unit/test_policies.py (unit). Bằng chứng máy: cổng kiểm tra.
- [ ] NFR-REL-001 Báo cáo hợp schema và không có NaN hoặc Inf. Task: T411, T416. tests/integration/test_report_contract.py (entrypoint); tests/unit/test_report.py (unit). Bằng chứng máy: cổng kiểm tra.
- [ ] NFR-HEADLESS-001 Đánh giá và vẽ biểu đồ khi `DISPLAY` không đặt. Task: T401, T410, T418, T423. tests/integration/test_evaluate_headless.py (entrypoint); tests/integration/test_evaluation_imports.py (unit). Bằng chứng máy: cổng kiểm tra; capture E2E AC-3.
- [ ] NFR-STAT-001 Tính đúng khoảng tin cậy và kết luận trên dữ liệu tổng hợp có đáp án. Task: T404, T417. tests/unit/test_stats.py (unit); tests/integration/test_verdict_known_policies.py (unit). THIẾU test mức entrypoint. Bằng chứng máy: cổng kiểm tra.
