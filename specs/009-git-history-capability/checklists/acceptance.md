---
id: "TRACE-009-ACCEPTANCE"
title: "Nghiệm thu năng lực requires_git_history"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Danh sách nghiệm thu (Acceptance checklist): `requires_git_history`

**Mục đích**: ánh xạ tiêu chí chấp nhận (acceptance criteria), bất biến (invariants) và yêu cầu phi chức năng (non-functional requirements) tới nhiệm vụ (task), kiểm thử (test) và bằng chứng máy cho người đối chiếu (reviewer) sau khi gộp vào nhánh tích hợp (integration branch).

**Ngày tạo**: 2026-10-12.

**Nguồn ưu tiên**: [yêu cầu gốc](../../../.ai/chat/request-git-history-gate.md) qua [request.link](../request.link), sau đó [spec.md](../spec.md), [tasks.md](../tasks.md), [plan.md](../plan.md) và [quickstart.md](../quickstart.md). AC-1, AC-2, AC-3 và con số của yêu cầu gốc khớp spec; không thêm dòng AC của feature khác.

- [Quy ước (Conventions)](#quy-uoc-conventions)
- [Tiêu chí chấp nhận (Acceptance criteria)](#tieu-chi-chap-nhan-acceptance-criteria)
- [Bất biến (Invariants)](#bat-bien-invariants)
- [Yêu cầu phi chức năng (Non-functional requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)

<a id="quy-uoc-conventions"></a>
## Quy ước (Conventions)

- `entrypoint`: chạy qua điểm vào thật của ứng dụng hoặc công cụ dòng lệnh (command-line interface, CLI), như pytest/git. `unit`: kiểm thử đơn vị với đối tượng giả (mock), hoặc đọc tệp mà không chạy điểm vào thật. Thư mục `tests/e2e/` không tự quyết định mức kiểm thử.
- Đường dẫn test tính từ gốc repo. Các tên hàm mới T901 dưới đây là **dự kiến theo tasks.md**, chưa có trên `ai-sdlc/integration` khi đọc lượt này; tệp T902 có nhưng chưa gắn dấu `requires_git_history`. `THIẾU` nêu phần chưa có test `entrypoint` đầy đủ hoặc test chưa gộp; `CHƯA KIỂM` nêu lần chạy chưa có bằng chứng được đối chiếu trong lượt này.
- Chỉ máy tích dấu bằng `ai-sdlc reconcile --mark` khi mọi task trên dòng đã xanh và đã gộp, mọi tệp nêu trên dòng có trên nhánh tích hợp; run tự gọi sau mỗi lần gộp. Dòng không nêu task không bao giờ được tích. Reviewer chỉ đối chiếu, không ghi `specs/**`. Lượt này để mọi dòng chưa tích.
- Bằng chứng phải là kết quả cổng (gate), đầu ra tiến trình và báo cáo năng lực JSON do máy sinh, gắn với cùng commit sau gộp. Báo cáo đối chiếu và phán quyết (verdict) T903 là bổ sung, không thay kết quả máy. Không tự tạo hay chép bằng chứng.
- Tự chốt: AC-3 và các tiêu chí chỉ kiểm bằng cổng vẫn ghi `THIẾU` test `entrypoint` — lý do: plan D-7 không tạo test gọi verify, yêu cầu lượt này buộc công khai thiếu test; không bịa test hoặc sửa tasks.md.
- Tự chốt: bằng chứng kiểm thử đầu-cuối (end-to-end, E2E) dùng đầu ra tiến trình và JSON, không cần ảnh chụp (capture), dấu vết trình duyệt (trace) hay nhật ký trình duyệt (console) — lý do: feature không có giao diện/URL. Cổng tự động `EVIDENCE_WRITE` chặn cả bản vá checklist có chuỗi đường dẫn bằng chứng; do đó tài liệu nhận diện bằng chứng bằng tên cổng, lệnh và trường kết quả cần đọc.
- `docs/MAP.md` chưa có dòng 009 khi đọc lượt này; căn cứ phân công và vùng ghi của tasks.md. Giữ nguyên thay đổi sẵn có ngoài tệp đầu ra.

<a id="tieu-chi-chap-nhan-acceptance-criteria"></a>
## Tiêu chí chấp nhận (Acceptance criteria)

- [ ] AC-1: ở môi trường có git, test INV-002 của **008** chạy thật và PASS như cũ. Task: T901, T902, T903. Test `entrypoint`: `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` gọi `git log`/`git show` thật; test `unit` dự kiến: `tests/unit/test_capability_gate.py::test_ac1_git_history_probe_true_when_git_exits_zero`. Bằng chứng máy: cổng `tests` T901, cổng `e2e` T902 trên cây có git, đầu ra `1 passed` cho hàm đích và JSON `--capability-report` có `deselected == 0`; T903 đối chiếu độc lập. THIẾU: hàm unit mới và dấu của T902 chưa gộp; CHƯA KIỂM: kết quả chạy/gộp T901–T903. [Yêu cầu gốc AC-1; Spec US1, US2; FR-001, FR-005, FR-006]
- [ ] AC-2: ở bản lưu trữ (archive) không có .git, test INV-002 của **008** bị loại và báo cáo ghi "bị loại" với lý do "Máy không có lịch sử git"; cổng toàn hệ không đỏ vì test này; tỉ lệ loại ≤ 5%. Task: T901, T902, T903. Test `entrypoint` dự kiến: `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` chạy pytest thật trong cây tạm (1 test gắn dấu + 19 test thường, `ratio == 0.05`, mã thoát 0); phiên archive chạy toàn bộ `tests/e2e`, chứa `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched`; test `unit` dự kiến trong `tests/unit/test_capability_gate.py`: `test_ac2_git_history_probe_false_when_git_exits_128`, `test_ac2_git_history_probe_false_on_oserror`, `test_ac2_git_history_probe_false_on_timeout`. Bằng chứng máy: cổng `tests`/`e2e`, đầu ra tiến trình và JSON `--capability-report` ghi `nodeid`, `marker`, lý do, `ratio <= 0.05`, hàm đích không PASS/skip/xfail, mã thoát 0; T903 kiểm archive không nằm trong kho git cha. THIẾU: test `entrypoint` mới và dấu của T902 chưa gộp; CHƯA KIỂM: phiên archive và cổng toàn hệ sau gộp. [Yêu cầu gốc AC-2; Spec US1–US3; FR-002, FR-003, FR-007, FR-008]
- [ ] AC-3: `ai-sdlc verify --branch ai-sdlc/integration` xanh (lint, tests, typecheck, e2e, risk_coverage). Task: T901, T902, T903. Test hỗ trợ `unit` dự kiến: `tests/unit/test_capability_gate.py` với bốn nhánh phép dò; test hỗ trợ `entrypoint`: `tests/e2e/test_008_docs_entrypoints.py` và hàm dự kiến `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git`. THIẾU: test `entrypoint` trong repo chứng minh đủ năm cổng; các test hỗ trợ chỉ chứng minh từng phần. Bằng chứng máy: kết quả lệnh verify ghi từng cổng, mã thoát và commit đã gộp; T903 đối chiếu verdict và báo cáo `.ai/runs/*/reports/reviewer-git-history-check.md` phải ghi: INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên archive không chứng minh nó. CHƯA KIỂM: verify và đối chiếu độc lập. [Yêu cầu gốc AC-3; Spec US3; FR-009–FR-011; SC-003]

<a id="bat-bien-invariants"></a>
## Bất biến (Invariants)

- [ ] INV-001: không thêm skip/skipif/xfail/importorskip hoặc nhánh dự phòng PASS khi thiếu lịch sử git; số test hai tệp không giảm; đối tượng giả `subprocess.run` được khôi phục sau mỗi test. Task: T901, T902, T903. Test `entrypoint` dự kiến hỗ trợ loại có báo cáo: `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git`; test `unit` dự kiến: bốn nhánh phép dò trong `tests/unit/test_capability_gate.py`; tệp đối chiếu thêm: `tests/e2e/test_008_docs_entrypoints.py`. THIẾU: test `entrypoint` đầy đủ cho nội dung thay đổi (diff), số test không giảm và khôi phục đối tượng giả; test tiến trình con mới chưa gộp. Bằng chứng máy: báo cáo năng lực, đầu ra `pytest --collect-only` trước/sau, quét diff không có cơ chế che lỗi; T903 đối chiếu cách dùng `monkeypatch`. CHƯA KIỂM: các kết quả trước/sau và đối chiếu độc lập. [Spec INV-001; US4; FR-007]
- [ ] INV-002: thân hàm và phép khẳng định (assert) của test INV-002 **của 008**, mọi test khác và import giữ nguyên; tệp chỉ thêm một dòng dấu hàm (decorator) với lý do không rỗng. Task: T902, T903. Test `entrypoint` hỗ trợ hành vi lịch sử: `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` ở cây có git; hàm này chứng minh bất biến của 008, không tự chứng minh diff của 009. THIẾU: test `entrypoint` chứng minh tệp chỉ thêm decorator; dấu mới chưa gộp. Bằng chứng máy: đầu ra `git diff -U0` so mốc trước với commit T902, kết quả cổng `e2e` cho hàm đích; T903 đối chiếu không đổi thân/assert/import/test khác. CHƯA KIỂM: diff và lần chạy sau gộp. [Spec INV-002; US2; FR-005, FR-006]
- [ ] INV-003: ngưỡng loại 5%, `pyproject.toml` và `uv.lock` giữ nguyên. Task: T901, T902, T903. Test `entrypoint` dự kiến hỗ trợ ngưỡng: `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` đo 1/20, `ratio == 0.05`; tệp test liên quan: `tests/e2e/test_008_docs_entrypoints.py`. THIẾU: test `entrypoint` chứng minh hai tệp cấu hình không đổi và ngưỡng không bị nới so mốc trước; test mới chưa gộp. Bằng chứng máy: JSON năng lực, `git diff --name-only`, đối chiếu `default=0.05` tại `tests/unit/capability_gate.py`; T903 xác nhận 0 thay đổi cấu hình/ngưỡng. CHƯA KIỂM: kết quả sau gộp. [Spec INV-003; US4; FR-011; yêu cầu gốc: ràng buộc]

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
## Yêu cầu phi chức năng (Non-functional requirements)

- [ ] NFR-REL-001: phép dò gọi git với hạn mức ≤ 5 giây; mọi nhánh lỗi trả `False` trong ≤ 5 giây, 0 ngoại lệ thoát ra. Task: T901, T903. Test `unit` dự kiến trong `tests/unit/test_capability_gate.py`: `test_ac2_git_history_probe_false_when_git_exits_128`, `test_ac2_git_history_probe_false_on_oserror`, `test_ac2_git_history_probe_false_on_timeout` kiểm thời gian chờ (timeout) hữu hạn ≤ 5 và kết quả `False`. THIẾU: test `entrypoint` đo lỗi/git chậm thật và thời gian trả về; đối tượng giả chỉ chứng minh đối số/nhánh xử lý; các hàm mới chưa gộp. Bằng chứng máy: cổng `tests` T901 ghi kết quả từng hàm; T903 nêu giới hạn phép đo. CHƯA KIỂM: kết quả test mới và thời gian thực. [Spec NFR-REL-001; FR-002; trường hợp biên (edge case)]
- [ ] NFR-GATE-001: tỉ lệ loại ≤ 5% (0,05) trên mỗi phiên `tests` và `e2e` của archive không `.git`; mẫu số mỗi phiên ≥ 20 test. Task: T901, T902, T903. Test `entrypoint` dự kiến: `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` đo 1/20; phiên archive chạy toàn bộ `tests/e2e` chứa `tests/e2e/test_008_docs_entrypoints.py`, hàm đích bị loại. Bằng chứng máy: JSON `--capability-report` riêng của cả phiên `tests` và `e2e` có `collected >= 20`, `ratio <= 0.05`, lý do loại, đầu ra tiến trình mã thoát 0. THIẾU: test `entrypoint` mới chưa gộp; CHƯA KIỂM: báo cáo cả hai phiên trên archive; không thay báo cáo toàn phiên bằng phép đo 1/20. [Spec NFR-GATE-001; FR-003, FR-008; yêu cầu gốc AC-2]
- [ ] NFR-QUAL-001: `ruff check` và `mypy --strict` xanh, 0 lỗi trên hai tệp sửa. Task: T901, T902, T903. Tệp test chịu kiểm: `tests/unit/test_capability_gate.py` và `tests/e2e/test_008_docs_entrypoints.py`; các test `unit`/`entrypoint` không chứng minh kết quả phân tích mã. THIẾU: test `entrypoint` cho tiêu chí này; chứng minh bằng cổng `lint`/`typecheck`. Bằng chứng máy: kết quả `uv run --isolated --with ruff ruff check .` và `uv run --isolated --with mypy mypy --strict .`, mã thoát 0, 0 lỗi, commit chứa T901/T902; T903 đối chiếu cùng lần verify. CHƯA KIỂM: cổng trên thay đổi đã gộp. [Spec NFR-QUAL-001; FR-009; yêu cầu gốc AC-3]
