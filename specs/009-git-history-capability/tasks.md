---
id: "TASKS-009"
title: "Năng lực requires_git_history cho cổng năng lực — Nhiệm vụ (Tasks)"
doc_type: tasks
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Nhiệm vụ: Năng lực `requires_git_history` cho cổng năng lực

- [Đầu vào](#dau-vao)
- [Quy ước task](#quy-uoc-task)
  - [Phụ thuộc chéo feature](#phu-thuoc-cheo-feature)
- [User story US1–US4](#user-story-us1us4)
- [Đối chiếu độc lập](#doi-chieu-doc-lap)
  - [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Bảng task](#bang-task)
- [Dependencies và wave](#dependencies-va-wave)
- [Điều kiện hoàn thành](#dieu-kien-hoan-thanh)

> Đích: `specs/009-git-history-capability/tasks.md`. Sinh từ `spec.md` + `plan.md` + `research.md` + `data-model.md` + `quickstart.md` HIỆN TẠI (viết lại hoàn toàn ở lượt 2026-10-12). Feature chỉ thêm test và một dấu năng lực: không có màn hình ⇒ không có mã `UI-*`; không có HTTP/`contracts/` ⇒ không có mã `API-*`; không có kế hoạch hạ tầng `infra/deploy/009-git-history-capability*.md` ⇒ không có task `platform`.

<a id="dau-vao"></a>
## Đầu vào

- `spec.md`: AC-1…AC-3, FR-001…FR-011, NFR-REL-001, NFR-GATE-001, NFR-QUAL-001, INV-001…INV-003, SC-001…SC-006.
- `plan.md` (quyết định D-1…D-7, rủi ro R-1…R-6, gợi ý ba task), `research.md` (cách dựng cây tạm không có `.git`), `data-model.md`, `quickstart.md` (bốn kịch bản kiểm).
- Mã nguồn của cổng năng lực (`tests/unit/capability_gate.py`, `conftest.py`) và hai tệp test nằm trên nhánh tích hợp `ai-sdlc/integration` (@ffea840); task chạy ở worktree trên nhánh đó.

<a id="quy-uoc-task"></a>
## Quy ước task

- **Dải mã `T901`…`T903`**: id task duy nhất toàn dự án (009 dùng dải `T9xx`, không va với `T2xx`…`T8xx`).
- **Ba task**: `T901` (builder, một tệp), `T902` (qa, một tệp), `T903` (reviewer, đo trên bản archive không có `.git` và ghi giới hạn). Không có task nào sửa `tests/unit/capability_gate.py`: tệp đó chỉ đổi khi `T901` chứng minh lỗi (FR-004), khi đó dừng và thêm task sửa riêng có test đỏ trước (ghi nguyên nhân gốc).
- **Mỗi tệp một chủ** (FR-011): `tests/unit/test_capability_gate.py` thuộc `T901`; `tests/e2e/test_008_docs_entrypoints.py` thuộc `T902`. `pyproject.toml`, `uv.lock`, ngưỡng 5%, test 008 khác KHÔNG đổi (INV-003).
- **Test trước mã**: cả hai task chỉ đổi test nên miễn `tdd_red`; test của `T901` bám hành vi đã đọc của phép dò nên dự kiến xanh ngay — chỉ đỏ nếu rủi ro R-4 xảy ra.
- **Không che lỗi (INV-001, FR-007)**: không `skip`/`skipif`/`xfail`/`importorskip`, không nhánh dự phòng PASS; bản giả `subprocess.run` dùng `monkeypatch` để tự khôi phục.
- **Chạy được mọi nền tảng**: test của `T901` dùng `sys.executable`, `pathlib`, `shutil`, không giả định dấu `/`, không đường dẫn tuyệt đối của máy riêng.
- **Giới hạn phải ghi (FR-010)**: INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên bản archive không chứng minh nó.
- **Tự chốt**: dấu năng lực đặt ở mức hàm kèm `reason="Máy không có lịch sử git"` — lý do: đúng một test bị loại và cổng năng lực bắt buộc có lý do.
- **Tự chốt**: AC-3 (`ai-sdlc verify --branch ai-sdlc/integration` xanh) do cổng máy chạy ngoài repo, không có test trong repo gọi lệnh đó; `T903` chỉ ghi nhận kết quả cổng và đo bằng chứng thật trên bản archive — lý do: hiến chương I, bằng chứng thắng lời khai.

<a id="phu-thuoc-cheo-feature"></a>
### Phụ thuộc chéo feature

`T901` và `T902` đều **dùng** mã năng lực `requires_git_history` đã có trong `tests/unit/capability_gate.py` (do task F022 của nhánh tích hợp sinh ra) và cơ chế loại có báo cáo của 006 (task T6xx); hai thứ đó là mã đã vào nhánh tích hợp @ffea840, không phải đầu ra của task nào trong lượt này nên không có id task để khai ở `depends_on`. `T902` chỉ gắn dấu lên test do `T804` của 008 sinh ra (`tests/e2e/test_008_docs_entrypoints.py`), nên `T902` `depends_on` `T804` (task của feature khác trong cùng dự án). Cột `depends_on` còn lại chỉ nối task nội bộ 009.

Không có task nào đổi hành vi làm sai test đã có: `T902` chỉ thêm một dấu; ở môi trường có git test vẫn chạy và PASS như cũ, ở archive không có `.git` test bị loại có báo cáo. Không cần task "cập nhật test cũ".

<a id="user-story-us1us4"></a>
## User story US1–US4

- **US1 — Phép dò năng lực được chứng minh đủ nhánh (P1)**: `T901` (FR-001…FR-004, NFR-REL-001, NFR-GATE-001).
- **US2 — Test INV-002 của 008 mang dấu năng lực, thân giữ nguyên (P1)**: `T902` (FR-005…FR-008, INV-002).
- **US3 — Cổng toàn hệ trên archive không đỏ vì test này (P1)**: `T903` (FR-009, FR-010, NFR-QUAL-001).
- **US4 — Không che lỗi, không nới ngưỡng, đúng vùng ghi (P2)**: `T901`, `T902`, `T903` (FR-007, FR-011, INV-001…INV-003).

<a id="doi-chieu-doc-lap"></a>
## Đối chiếu độc lập

- [ ] T901 [US1] Builder: thêm năm test vào `tests/unit/test_capability_gate.py` (bốn nhánh của phép dò bằng bản giả `subprocess.run` + một phép chạy pytest thật trong cây tạm không có `.git`) — tests/unit/test_capability_gate.py
- [ ] T902 [US2] QA: gắn đúng một decorator `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` lên test INV-002 của 008, thân test giữ nguyên — tests/e2e/test_008_docs_entrypoints.py
- [ ] T903 [US3] [US4] Reviewer: đo bản archive không có `.git`, quét diff, ghi giới hạn FR-010 và verdict — evidence/reviews/T903.verdict; .ai/runs/*/reports/reviewer-git-history-check.md

<a id="quyet-dinh-ve-vai-challenger"></a>
### Quyết định về vai `challenger`

**KHÔNG DÙNG** vai `challenger`. Ba bất biến `INV-001…003` của spec là bất biến về **nội dung diff và vùng ghi** (không thêm skip/xfail/nhánh PASS giả, thân test 008 không đổi, ngưỡng 5% và `pyproject.toml`/`uv.lock` không đổi), không phải bất biến của một hàm nhận đầu vào từ người dùng nên không có vector/fuzz nào "đánh sập" được. Chúng được kiểm tất định bằng quét `git diff` (`T903`) và bằng test tiến trình con thật của `T901` (đo `ratio == 0,05`, lý do loại, 0 skip/xfail). Phép dò của `T901` đã phủ cả bốn nhánh lỗi (mã 128, `OSError`, `TimeoutExpired`) nên không cần thêm lượt phản biện tốn kém; cổng review chỉ cần verdict của reviewer `T903`.

<a id="bang-task"></a>
## Bảng task

| id | mô tả | outputs | depends_on | role | độ khó |
|---|---|---|---|---|---|
| T901 | Thêm năm test vào `tests/unit/test_capability_gate.py`, giữ nguyên mọi test hiện có (số test không giảm). (1) `test_ac1_git_history_probe_true_when_git_exits_zero`: `monkeypatch.setattr(capability_gate.subprocess, "run", giả)` trả `returncode == 0` ⇒ `_capability_available("requires_git_history")` là `True`. (2) `test_ac2_git_history_probe_false_when_git_exits_128`: bản giả trả mã 128 ⇒ `False`. (3) `test_ac2_git_history_probe_false_on_oserror`: bản giả ném `OSError` ⇒ `False`, không ném ra ngoài. (4) `test_ac2_git_history_probe_false_on_timeout`: bản giả ném `subprocess.TimeoutExpired` ⇒ `False`; cùng test này (hoặc test kèm theo) kiểm lời gọi `subprocess.run` mang `timeout` hữu hạn ≤ 5 giây. (5) `test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git`: dựng cây tạm (`tmp_path`) có bản sao `capability_gate.py` ở `gốc/tests/unit/` (phép dò neo `cwd` ở hai cấp trên tệp plugin nên chỉ đổi thư mục hiện hành sẽ đo nhầm `.git` của dự án thật), KHÔNG có `.git`; môi trường tiến trình con xoá `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` và đặt `GIT_CEILING_DIRECTORIES` là cha của cây tạm; chạy `sys.executable -m pytest -p capability_gate --capability-report=<tệp>` trên một tệp test gồm 1 test gắn `requires_git_history(reason="Máy không có lịch sử git")` + 19 test thường; khẳng định: thoát mã 0, 19 PASS, test gắn dấu không PASS/skip/xfail, báo cáo ghi `bị loại 1/20`, tên test, tên dấu, lý do `Máy không có lịch sử git`, `ratio == 0.05`. Bản giả được khôi phục sau mỗi test. Không đổi `capability_gate.py`; nếu test nào chứng minh lỗi của nó thì DỪNG, ghi nguyên nhân gốc và báo để thêm task sửa riêng có test đỏ trước (FR-004). Hiện thực (kế thừa INV-006 của 006: loại có báo cáo, không skip/xfail) AC-1 · AC-2 · FR-001 · FR-002 · FR-003 · FR-004 · NFR-REL-001 · NFR-GATE-001 · NFR-QUAL-001 · INV-001 · INV-003. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/unit/test_capability_gate.py`, `uv run --isolated --with ruff ruff check .`, `uv run --isolated --with mypy mypy --strict .`. | tests/unit/test_capability_gate.py |  | builder | vừa |
| T902 | Chỉ thêm đúng một dòng decorator `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` ngay trên `def test_inv002_document_commits_keep_product_code_untouched` trong `tests/e2e/test_008_docs_entrypoints.py`; thân hàm, mọi `assert`, mọi test khác và `import` giữ NGUYÊN; không thêm `skip`/`skipif`/`xfail`/`importorskip` hay nhánh dự phòng "chỉ kiểm tệp có trên đĩa". Kiểm bằng `git diff -U0 -- tests/e2e/test_008_docs_entrypoints.py` chỉ thêm một dòng. Ở môi trường có git chạy test thật và ghi PASS (AC-1, `--capability-report` cho `deselected == 0`); trên bản archive không có `.git` test bị loại có báo cáo với lý do `Máy không có lịch sử git`, tỉ lệ ≤ 5% (đếm mẫu số bằng `pytest --collect-only` của phiên `e2e`; nếu < 20 thì báo cáo, KHÔNG nới ngưỡng). Hiện thực AC-1 · AC-2 · FR-005 · FR-006 · FR-007 · FR-008 · NFR-GATE-001 · INV-001 · INV-002. Kiểm chứng: `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --capability-report=<tệp>` ở máy có git (`1 passed` cho test INV-002), và `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e`. | tests/e2e/test_008_docs_entrypoints.py | T804 | qa | dễ |
| T903 | Reviewer độc lập (khác vai viết) đối chiếu, KHÔNG sửa tệp test: (a) quét `git diff` của feature: chỉ hai tệp test, tệp của feature và bằng chứng; 0 thay đổi ở `pyproject.toml`, `uv.lock`, `tests/unit/capability_gate.py` (trừ khi FR-004 kích hoạt), 0 `skip`/`skipif`/`xfail`/`importorskip` mới, `default=0.05` ở `capability_gate.py` nguyên vẹn, `pytest --collect-only` số test không giảm, tệp e2e chỉ thêm một dòng decorator; (b) trên một bản archive KHÔNG có `.git` của nhánh tích hợp (giải nén thư mục riêng, đối chiếu quickstart kịch bản 2) chạy phiên `e2e` với `--capability-report`, ghi: đúng 1 test bị loại với lý do `Máy không có lịch sử git`, `ratio` ≤ 0,05, 0 test PASS giả; kiểm bản archive không nằm trong cây git khác (rủi ro R-2, nếu có thì ghi CHƯA KIỂM/giới hạn); (c) ghi kết quả của cổng `ai-sdlc verify --branch ai-sdlc/integration` ở 5 cổng `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` (AC-3, FR-009) — chỉ ghi cái cổng máy đã chạy, nếu chưa có thì ghi CHƯA KIỂM; (d) báo cáo MUST có câu giới hạn: INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên bản archive không chứng minh nó (FR-010); mọi khẳng định chưa đo nhãn CHƯA KIỂM. Ghi báo cáo và verdict APPROVE hoặc REQUEST_CHANGES nêu AC-1…AC-3, INV-001…INV-003, NFR-REL-001, NFR-GATE-001, NFR-QUAL-001 đã được chứng minh bằng lần chạy ngoài hay chưa. Hiện thực AC-3 · FR-009 · FR-010 · FR-011 · NFR-QUAL-001 · INV-001 · INV-002 · INV-003. Kiểm chứng: tệp `evidence/reviews/T903.verdict` tồn tại với dòng `APPROVE` hoặc `REQUEST_CHANGES`, và báo cáo `.ai/runs/*/reports/reviewer-git-history-check.md` có câu giới hạn FR-010. | evidence/reviews/T903.verdict; .ai/runs/*/reports/reviewer-git-history-check.md | T901; T902 | reviewer | vừa |

<a id="dependencies-va-wave"></a>
## Dependencies và wave

- Wave 1: `T901` (builder) và `T902` (qa) — hai tệp khác nhau, chạy song song được; dấu năng lực đã có ở plugin nên `T902` không chờ `T901`. `T902` chỉ chờ `T804` của 008 (đã xong, tệp test 008 đã có).
- Wave 2: `T903` (reviewer; phụ thuộc `T901`, `T902` để có diff và test mới mới đối chiếu được).
- DAG: `T901 → T903`, `T902 → T903`, `T804 → T902`; không vòng.
- Không có task đổi hành vi mà test của task/feature trước đang khẳng định ⇒ không cần task "cập nhật test cũ". Feature không có giao diện nên không có bảng chuyển màn; không chụp màn hình.

<a id="dieu-kien-hoan-thanh"></a>
## Điều kiện hoàn thành

- `tests/unit/test_capability_gate.py` có thêm 5 test, xanh; ở máy có git phép dò trả `True` thật, ở cây tạm không `.git` test gắn dấu bị loại có báo cáo `1/20`, `ratio == 0.05` (SC-004).
- `tests/e2e/test_008_docs_entrypoints.py` chỉ thêm một dòng decorator; ở môi trường có git test INV-002 PASS (SC-001); ở archive không `.git` bị loại, lý do `Máy không có lịch sử git`, tỉ lệ ≤ 5% (SC-002).
- `evidence/reviews/T903.verdict` là `APPROVE`; báo cáo có câu giới hạn FR-010 (SC-006).
- `git diff --name-only` không chứa `pyproject.toml`, `uv.lock`, `tests/unit/capability_gate.py` (SC-005).
- `ai-sdlc verify --branch ai-sdlc/integration` xanh 5/5 cổng (SC-003), do cổng máy chạy.
- `ai-sdlc check tasks .` và `ai-sdlc check docs .` sạch.
