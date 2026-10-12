---
id: "TRACE-009"
title: "Ma trận truy vết 009-git-history-capability"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-12"
---

# Ma trận truy vết 009-git-history-capability

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/009-git-history-capability.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/009-git-history-capability/spec.md` (yêu cầu) và `specs/009-git-history-capability/tasks.md` (task `T901`…`T903`).
> Feature chỉ thêm test và một dấu năng lực, không thêm hành vi sản phẩm. Mức `entrypoint` = chạy pytest thật bằng tiến trình con (không mock) hoặc chạy test e2e 008 trên môi trường thật; mức `đơn vị` = test thay `subprocess.run` bằng bản giả trong mô-đun `capability_gate`; mức `cổng` = lệnh đo trên diff/bằng chứng hoặc cổng máy `ai-sdlc verify`. Cột trạng thái "có" nghĩa là đã có task + phép kiểm dự kiến, KHÔNG có nghĩa đã chạy xanh. Giới hạn (FR-010): INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên bản archive không chứng minh nó.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Ở môi trường có git, test INV-002 của 008 chạy thật và PASS như cũ | T901, T902 | `tests/unit/test_capability_gate.py::test_ac1_git_history_probe_true_when_git_exits_zero`; `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` (máy có git, `deselected == 0`) | entrypoint | có |
| AC-2 | Ở archive không có `.git`, test INV-002 bị loại có báo cáo, lý do `Máy không có lịch sử git`, tỉ lệ ≤ 5% | T901, T902, T903 | `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git`; `test_ac2_git_history_probe_false_when_git_exits_128`; `…_on_oserror`; `…_on_timeout`; `pytest tests/e2e --capability-report=<tệp>` trên archive (quickstart kịch bản 2) | entrypoint | có |
| AC-3 | `ai-sdlc verify --branch ai-sdlc/integration` xanh ở 5 cổng | T903 | cổng `ai-sdlc verify --branch ai-sdlc/integration` (`lint`, `tests`, `typecheck`, `e2e`, `risk_coverage`); `evidence/reviews/T903.verdict` | cổng | có |
| FR-001 | Phép dò trả `True` khi `subprocess.run` giả trả mã 0 | T901 | `tests/unit/test_capability_gate.py::test_ac1_git_history_probe_true_when_git_exits_zero` | đơn vị | có |
| FR-002 | Phép dò trả `False`, không ném ngoại lệ, ở mã 128 / `OSError` / `TimeoutExpired`; `timeout` ≤ 5 s | T901 | `tests/unit/test_capability_gate.py::test_ac2_git_history_probe_false_when_git_exits_128`, `…_on_oserror`, `…_on_timeout` | đơn vị | có |
| FR-003 | Một test pytest thật trong cây tạm không có `.git`: bị loại `1/20`, có lý do, 19 PASS, thoát mã 0 | T901 | `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` | entrypoint | có |
| FR-004 | Không đổi `capability_gate.py` trừ khi test chứng minh lỗi (task sửa riêng, test đỏ trước) | T901, T903 | `git diff --name-only` không có `tests/unit/capability_gate.py`; `evidence/reviews/T903.verdict` | cổng | có |
| FR-005 | Test INV-002 của 008 mang đúng một decorator `requires_git_history(reason=…)` mức hàm | T902 | `git diff -U0 -- tests/e2e/test_008_docs_entrypoints.py` (đúng một dòng thêm); `pytest --collect-only` thấy dấu | cổng | có |
| FR-006 | Thân hàm, assert và test khác của tệp 008 giữ nguyên; ở môi trường có git phép kiểm thật vẫn PASS | T902 | `tests/e2e/test_008_docs_entrypoints.py` (cả tệp, máy có git); `git diff -U0` | entrypoint | có |
| FR-007 | Không `skip`/`skipif`/`xfail`/`importorskip`, không nhánh dự phòng PASS | T901, T902, T903 | quét diff của `evidence/reviews/T903.verdict` (`grep` bốn từ khoá trong phần thêm) | cổng | có |
| FR-008 | Ở archive không `.git`: đúng 1 test bị loại, lý do `Máy không có lịch sử git`, tỉ lệ ≤ 5% không đổi ngưỡng | T902, T903 | `pytest tests/e2e --capability-report=<tệp>` trên archive (quickstart kịch bản 2 bước 3) | entrypoint | có |
| FR-009 | Sau khi vào nhánh tích hợp, cổng toàn hệ xanh 5 cổng trên archive | T903 | cổng `ai-sdlc verify --branch ai-sdlc/integration` | cổng | có |
| FR-010 | Báo cáo ghi giới hạn: INV-002 của 008 chỉ chứng minh ở môi trường có git | T903 | `.ai/runs/*/reports/reviewer-git-history-check.md` có câu giới hạn; `evidence/reviews/T903.verdict` | cổng | có |
| FR-011 | Vùng ghi chỉ hai tệp test + tệp feature/bằng chứng; không `pyproject.toml`, `uv.lock`, ngưỡng, test 008 khác | T901, T902, T903 | `git diff --name-only` đối chiếu vùng ghi (quickstart kịch bản 4) | cổng | có |
| NFR-REL-001 | Phép dò ≤ 5 s, trả `False` ở mọi nhánh lỗi, 0 ngoại lệ thoát ra | T901 | `tests/unit/test_capability_gate.py::test_ac2_git_history_probe_false_on_timeout` (kiểm `timeout` ≤ 5); `…_on_oserror` | đơn vị | có |
| NFR-GATE-001 | Tỉ lệ loại ≤ 5% mỗi phiên `tests`/`e2e`; mẫu số ≥ 20; `ratio` đọc từ báo cáo | T901, T902, T903 | `tests/unit/test_capability_gate.py::test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` (`ratio == 0.05`); `--capability-report` trên archive | entrypoint | có |
| NFR-QUAL-001 | `ruff check` và `mypy --strict` xanh trên hai tệp đã sửa | T901, T902, T903 | cổng `lint` (`ruff check .`), cổng `typecheck` (`mypy --strict .`) | cổng | có |
| INV-001 | Không che lỗi bằng test (kế thừa INV-006 của 006: loại có báo cáo); số test không giảm; bản giả `subprocess.run` được khôi phục | T901, T902, T903 | quét diff (`skip`/`skipif`/`xfail`/`importorskip`); `pytest --collect-only` số test không giảm; `monkeypatch` tự khôi phục | cổng | có |
| INV-002 | Thân hàm, assert và test khác của tệp 008 nguyên vẹn; thay đổi duy nhất là một dòng decorator | T902, T903 | `git diff -U0 -- tests/e2e/test_008_docs_entrypoints.py` | cổng | có |
| INV-003 | Ngưỡng 5%, `pyproject.toml`, `uv.lock` nguyên vẹn | T901, T903 | `git diff --name-only` (không có `pyproject.toml`, `uv.lock`); `grep "default=0.05" tests/unit/capability_gate.py` | cổng | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Vai | Mã hiện thực |
|---|---|---|
| T901 | builder | AC-1, AC-2, FR-001, FR-002, FR-003, FR-004, NFR-REL-001, NFR-GATE-001, NFR-QUAL-001, INV-001, INV-003 |
| T902 | qa | AC-1, AC-2, FR-005, FR-006, FR-007, FR-008, NFR-GATE-001, INV-001, INV-002 |
| T903 | reviewer | AC-3, FR-009, FR-010, FR-011, NFR-QUAL-001, INV-001, INV-002, INV-003 |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không có mã nào ở trạng thái `THIẾU`: mọi AC/FR/NFR/INV của spec có ít nhất một task và một phép kiểm.
- AC-3 và FR-009 không có test trong repo (cổng `ai-sdlc verify` chạy ngoài repo, quyết định D-7 của plan); bằng chứng là kết quả cổng máy và verdict của `T903`. Việc chạy cổng chưa được đo trong lượt này (CHƯA KIỂM).
- Giới hạn còn lại (FR-010): INV-002 của 008 chỉ được chứng minh ở môi trường có git; trên archive không có `.git` nó được báo cáo là "bị loại", không phải "đã chứng minh". Rủi ro R-2 (archive nằm trong cây git khác) CHƯA KIỂM — `T903` đo và ghi.
