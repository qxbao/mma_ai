---
id: "QUICKSTART-009"
title: "Quickstart — kiểm chứng năng lực requires_git_history"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Quickstart: kiểm chứng năng lực `requires_git_history`

- [Kịch bản 1 — Có git: test INV-002 của 008 chạy thật (AC-1)](#kich-ban-1-co-git-test-inv-002-cua-008-chay-that-ac-1)
- [Kịch bản 2 — Không có .git: bị loại có báo cáo (AC-2, NFR-GATE-001, NFR-REL-001)](#kich-ban-2-khong-co-git-bi-loai-co-bao-cao-ac-2-nfr-gate-001-nfr-rel-001)
- [Kịch bản 3 — Cổng toàn hệ xanh (AC-3, NFR-QUAL-001)](#kich-ban-3-cong-toan-he-xanh-ac-3-nfr-qual-001)
- [Kịch bản 4 — Không che lỗi, đúng vùng ghi (INV-001, INV-002, INV-003)](#kich-ban-4-khong-che-loi-dung-vung-ghi-inv-001-inv-002-inv-003)


Tiền đề: worktree của task trên nhánh tích hợp `ai-sdlc/integration` (có `tests/`, `conftest.py`, `tests/unit/capability_gate.py`) và có `uv`. Thiết kế ở [plan.md](plan.md), lý do và số đo ở [research.md](research.md); không lặp lại ở đây. Tên test dưới đây là tên **đề xuất** của plan; builder/QA chốt tên cuối khi viết và cập nhật bảng truy vết.

<a id="kich-ban-1-co-git-test-inv-002-cua-008-chay-that-ac-1"></a>
## Kịch bản 1 — Có git: test INV-002 của 008 chạy thật (AC-1)

1. Test tự động `tests/unit/test_capability_gate.py::test_ac1_git_history_probe_true_when_git_exits_zero` chứng minh phép dò trả `True` khi `git` thoát mã 0 (bản giả).
2. Ở worktree có `.git`, chạy `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched --capability-report=<tệp>` — kỳ vọng `1 passed`, báo cáo `deselected == 0`.
3. Đối chiếu diff của tệp: `git diff -U0 -- tests/e2e/test_008_docs_entrypoints.py` chỉ thêm đúng một dòng `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` (INV-002).

<a id="kich-ban-2-khong-co-git-bi-loai-co-bao-cao-ac-2-nfr-gate-001-nfr-rel-001"></a>
## Kịch bản 2 — Không có .git: bị loại có báo cáo (AC-2, NFR-GATE-001, NFR-REL-001)

1. Test tự động: `test_ac2_git_history_probe_false_when_git_exits_128`, `test_ac2_git_history_probe_false_on_oserror`, `test_ac2_git_history_probe_false_on_timeout` (kiểm `timeout` ≤ 5) trong `tests/unit/test_capability_gate.py`.
2. Test tự động: `test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` chạy pytest thật trong cây tạm không có `.git` và khẳng định "bị loại 1/20", lý do `Máy không có lịch sử git`, không skip/xfail, mã thoát 0, `ratio == 0.05`.
3. Tái hiện trên archive thật (QA, mục [Q4 của research](research.md#q4-tai-hien-ac-2-tren-mot-ban-archive-that-o-buoc-qa)): `git archive <nhánh task> | tar -x -C <thư mục sạch>`; trong đó chạy `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e --capability-report=report.json`; kỳ vọng mã thoát 0, `items` chứa `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` với `marker == "requires_git_history"`, `ratio <= 0.05`; các test khác của tệp PASS.

<a id="kich-ban-3-cong-toan-he-xanh-ac-3-nfr-qual-001"></a>
## Kịch bản 3 — Cổng toàn hệ xanh (AC-3, NFR-QUAL-001)

1. Sau khi hai việc vào nhánh tích hợp, chạy `ai-sdlc verify --branch ai-sdlc/integration` trên bản archive; kỳ vọng `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` đều xanh. Đây là lệnh của cổng máy, không có test trong repo gọi nó (Clarifications của spec).
2. Cổng `lint`/`typecheck` đo NFR-QUAL-001: `uv run --isolated --with ruff ruff check .` và `uv run --isolated --with mypy mypy --strict .` — 0 lỗi.
3. Báo cáo của lượt MUST ghi giới hạn (FR-010): INV-002 của 008 chỉ chứng minh ở môi trường có git; cổng toàn hệ trên archive không chứng minh nó.

<a id="kich-ban-4-khong-che-loi-dung-vung-ghi-inv-001-inv-002-inv-003"></a>
## Kịch bản 4 — Không che lỗi, đúng vùng ghi (INV-001, INV-002, INV-003)

1. Quét diff: `git diff <mốc>..HEAD | grep -nE "pytest\.(skip|importorskip)|skipif|xfail"` — kỳ vọng không có dòng mới (INV-001).
2. Số test không giảm: `pytest --collect-only -q tests/unit/test_capability_gate.py tests/e2e/test_008_docs_entrypoints.py` so với mốc trước (INV-001, INV-002).
3. `git diff --name-only <mốc>..HEAD` chỉ gồm `tests/unit/test_capability_gate.py`, `tests/e2e/test_008_docs_entrypoints.py`, tệp của `specs/009-git-history-capability/` và bằng chứng; không có `pyproject.toml`, `uv.lock`, `tests/unit/capability_gate.py` (trừ khi FR-004 kích hoạt) (INV-002, INV-003).
4. Hằng ngưỡng: `git show <nhánh>:tests/unit/capability_gate.py | grep -n "default=0.05"` vẫn cho đúng một dòng (INV-003).
