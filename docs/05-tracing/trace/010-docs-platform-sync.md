---
id: "TRACE-010"
title: "Ma trận truy vết 010-docs-platform-sync"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-13"
---

# Ma trận truy vết 010-docs-platform-sync

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/010-docs-platform-sync.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/010-docs-platform-sync/spec.md` (yêu cầu) và `specs/010-docs-platform-sync/tasks.md` (task `T1001`…`T1005`).
> Feature chỉ sửa/thêm tài liệu và một tệp test tài liệu, không thêm hành vi sản phẩm. Mức `entrypoint` = test e2e `tests/e2e/test_008_docs_entrypoints.py` chạy lệnh thật bằng tiến trình con (`env_report`, `pytest --help`) và đọc tài liệu thật, không mock; mức `cổng` = lệnh đo trên diff/bằng chứng hoặc cổng máy (`ai-sdlc verify`, `ruff`, `mypy`) và verdict của reviewer. Mã `INV-*`, `AC-*`, `FR-*` không kèm "của 00x" là mã của spec 010. Tên test ở cột "Test / cổng máy" là tên DỰ KIẾN do `T1004` sinh/sửa (các test 008 hiện có giữ tên).

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | README/CHANGELOG/guides mô tả đúng mã đã gộp; mọi liên kết nội bộ tồn tại; mọi lệnh nêu chạy được hoặc có thật trong mã | T1001, T1002, T1003, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac1_ac2_ac3_ac4_ac5_document_structure`; `::test_ac2_ac3_ac4_ac5_inv004_relative_links` (+`platforms.md`); `::test_ac2_ac3_ac5_inv001_documented_flags` (+`platforms.md`); `::test_ac2_inv004_readme_quickstart`; `evidence/reviews/T1005.verdict` | entrypoint | dự kiến |
| AC-2 | Linux = đã kiểm; Windows 11/macOS/CUDA/CI thật = chưa kiểm, ghi rõ, không khẳng định hơn bằng chứng | T1001, T1002, T1003, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support` (phân tích từng dòng đã/chưa kiểm); test CHANGELOG `[Unreleased]` có câu giới hạn | entrypoint | dự kiến |
| AC-3 | `ai-sdlc verify --branch ai-sdlc/integration` xanh ở `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` | T1004, T1005 | cổng `ai-sdlc verify --branch ai-sdlc/integration`; `evidence/reviews/T1005.verdict` | cổng | dự kiến |
| FR-001 | README mục "Tình trạng nền tảng" mô tả đúng bốn thành phần đã gộp của 006; mọi tên/đường dẫn có thật | T1002, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support`; `::test_ac2_ac3_ac4_ac5_inv004_relative_links` | entrypoint | dự kiến |
| FR-002 | Linux = đã kiểm; Windows 11, macOS, CUDA, ô CI thật = chưa kiểm bằng lời trực tiếp; giữ liên kết `specs/006-cross-platform-support/` | T1002, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support` | entrypoint | dự kiến |
| FR-003 | README giữ 10 tiêu đề `##`, bốn lệnh nhanh, huy hiệu; nội dung mới đúng hai mục đã có | T1002, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac1_ac2_ac3_ac4_ac5_document_structure`; `::test_ac2_inv004_readme_quickstart` | entrypoint | dự kiến |
| FR-004 | `[Unreleased]` có `### Added`/`### Changed` cho 006, 007, 008, 009, mỗi dòng một liên kết spec | T1003, T1004 | test CHANGELOG mới của `tests/e2e/test_008_docs_entrypoints.py` (đủ 4 liên kết `specs/006…009`, đủ 6 tên dấu năng lực có thật trong `tests/unit/capability_gate.py`) | entrypoint | dự kiến |
| FR-005 | `[Unreleased]` nêu giới hạn "chưa kiểm Windows/macOS/CI thật"; `[0.1.0]` nguyên từng ký tự; không khối lệnh | T1003, T1004, T1005 | test CHANGELOG mới của `tests/e2e/test_008_docs_entrypoints.py` (không khối `sh`); `git diff` mục `[0.1.0]` rỗng (reviewer) | entrypoint | dự kiến |
| FR-006 | Thêm `docs/guides/platforms.md` (≤ 120 dòng, frontmatter, `../../README.md`, song ngữ) gồm env_report, sáu dấu, báo cáo "bị loại X/Y", lý do loại test git, giới hạn đã/chưa kiểm | T1001, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac1_ac2_ac3_ac4_ac5_document_structure` (+`platforms.md`); test `platforms.md` nêu đủ sáu dấu | entrypoint | dự kiến |
| FR-007 | README mục "Tài liệu" có liên kết tới `docs/guides/platforms.md` | T1002, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_ac3_ac4_ac5_inv004_relative_links`; test README liên kết tới `platforms.md` | entrypoint | dự kiến |
| FR-008 | Ba hướng dẫn cũ đối chiếu với mã/`--help`; chỉ sửa chỗ đã đổi; kết quả ghi trong báo cáo review | T1001, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac5_inv001_guide_options` (giữ nguyên); `.ai/runs/*/reports/reviewer-docs-sync-check.md` | cổng | dự kiến |
| FR-009 | Mọi lệnh/đường dẫn/tên dấu có thật; lệnh chạy được ở Linux; không phát biểu ngoài mức đã/chưa kiểm; không `scripts/check_env.py` | T1001, T1002, T1003, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_ac3_ac5_inv001_documented_flags` (chạy thật `env_report --json`); test `platforms.md` không chứa `check_env.py`; `.ai/runs/*/reports/reviewer-docs-sync-check.md` | entrypoint | dự kiến |
| FR-010 | qa cập nhật assert nền tảng và các assert cấu trúc để bao gồm `platforms.md`, không bỏ kiểm tra | T1004 | diff `tests/e2e/test_008_docs_entrypoints.py` (reviewer); `::test_ac2_inv003_platform_claims_match_draft_support`; `::test_ac1_ac2_ac3_ac4_ac5_document_structure` | cổng | dự kiến |
| FR-011 | Không `skip`/`skipif`/`xfail`/`importorskip`, không nới test khác, không giảm số test, không sửa thân test INV-002 của 008 | T1004, T1005 | quét diff bốn từ khoá; `pytest --collect-only` số test ≥ mốc trước; `git diff` thân `test_inv002_document_commits_keep_product_code_untouched` rỗng | cổng | dự kiến |
| FR-012 | Reviewer độc lập (vai khác docs) duyệt, ghi verdict kèm đối chiếu lệnh/đường dẫn/marker | T1005 | `evidence/reviews/T1005.verdict`; `.ai/runs/*/reports/reviewer-docs-sync-check.md` | cổng | dự kiến |
| FR-013 | Không sửa `src/`, `pyproject.toml`, `uv.lock`, `.github/`; không đổi `status:` của spec 006 | T1005 | `git diff --name-only` đối chiếu vùng ghi; `grep '^status: draft$' specs/006-cross-platform-support/spec.md` | cổng | dự kiến |
| FR-014 | `ai-sdlc verify --branch ai-sdlc/integration` xanh 5 cổng | T1005 | cổng `ai-sdlc verify --branch ai-sdlc/integration` | cổng | dự kiến |
| NFR-DOC-001 | 0 liên kết tương đối hỏng trong README, CHANGELOG, `platforms.md` và ba hướng dẫn cũ | T1001, T1002, T1003, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_ac3_ac4_ac5_inv004_relative_links` (mở rộng cho `platforms.md`) | entrypoint | dự kiến |
| NFR-DOC-002 | `platforms.md` ≤ 120 dòng; mỗi hướng dẫn cũ vẫn ≤ 120 dòng | T1001, T1004 | `tests/e2e/test_008_docs_entrypoints.py::test_ac1_ac2_ac3_ac4_ac5_document_structure` | entrypoint | dự kiến |
| NFR-GATE-001 | Tỉ lệ loại theo năng lực ≤ 5% mỗi phiên `tests`/`e2e`, kể cả bản archive không `.git` | T1004, T1005 | `pytest tests/e2e/test_008_docs_entrypoints.py --capability-report=<tệp>` đọc `ratio` ≤ 0,05; `.ai/runs/*/reports/reviewer-docs-sync-check.md` | cổng | dự kiến |
| NFR-QUAL-001 | `ruff check` và `mypy --strict` xanh 0 lỗi trên toàn kho sau khi sửa test | T1004, T1005 | cổng `lint` (`ruff check .`), cổng `typecheck` (`mypy --strict .`) | cổng | dự kiến |
| INV-001 | Không khẳng định hơn bằng chứng: Windows 11, macOS, CUDA, ô CI thật = chưa kiểm; Linux duy nhất "đã kiểm"; không chép số liệu một lượt chạy | T1001, T1002, T1003, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support` (dòng chưa kiểm không chứa "đã kiểm"); `evidence/reviews/T1005.verdict` | entrypoint | dự kiến |
| INV-002 | Vùng ghi: không sửa `src/`, `pyproject.toml`, `uv.lock`, `.github/`, `[0.1.0]`, `status:` của 006; test chỉ sửa ở tệp test 008 | T1001, T1002, T1003, T1004, T1005 | `git diff --name-only` đối chiếu cột outputs của `specs/010-docs-platform-sync/tasks.md`; `evidence/reviews/T1005.verdict` | cổng | dự kiến |
| INV-003 | Không che lỗi bằng test (kế thừa INV-006 của 006): không skip/xfail, không nới/xoá assert, số test không giảm, thân test INV-002 của 008 nguyên | T1004, T1005 | quét diff; `pytest --collect-only`; `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` (chạy ở máy có git) | cổng | dự kiến |
| INV-004 | Mọi lệnh/đường dẫn/tên marker có thật tại HEAD; cờ đối chiếu với nguồn thật | T1001, T1003, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_ac3_ac5_inv001_documented_flags` (`env_report --json`, `pytest --help`); test 6 dấu ⊆ `tests/unit/capability_gate.py` | entrypoint | dự kiến |
| INV-005 | `status:` của `specs/006-cross-platform-support/spec.md` giữ `draft` | T1002, T1004, T1005 | `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support` (đòi `^status: draft$`); `git diff` spec 006 rỗng | entrypoint | dự kiến |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Vai | Mã phủ |
|---|---|---|
| T1001 | docs | AC-1, AC-2, FR-006, FR-008, FR-009, NFR-DOC-001, NFR-DOC-002, INV-001, INV-004 |
| T1002 | docs | AC-1, AC-2, FR-001, FR-002, FR-003, FR-007, FR-009, INV-001, INV-005 |
| T1003 | docs | AC-1, AC-2, FR-004, FR-005, FR-009, INV-001, INV-004 |
| T1004 | qa | AC-1, AC-2, AC-3, FR-010, FR-011, NFR-DOC-001, NFR-DOC-002, NFR-GATE-001, NFR-QUAL-001, INV-003, INV-004, INV-005 |
| T1005 | reviewer | AC-3, FR-008, FR-012, FR-013, FR-014, NFR-GATE-001, NFR-QUAL-001, INV-002, INV-005 |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không có mã nào của spec 010 thiếu task. Cột "Trạng thái" là `dự kiến` vì tài liệu và test chưa được thi công ở lượt lập kế hoạch này; đổi thành `có` khi `T1005` ghi verdict `APPROVE`.
- `AC-3`, `FR-011`…`FR-014`, `INV-002`, `NFR-GATE-001`, `NFR-QUAL-001` chỉ chứng minh được bằng cổng máy và quét diff của reviewer, không có test trong repo gọi các lệnh đó (mức `cổng`); nếu cổng `risk_coverage` đòi tên có tiền tố `010/…` cho các mã này thì xử lý ở lượt hội tụ riêng, như `T904` của 009.
- INV-002 của 008 (test lịch sử commit) chỉ chứng minh ở môi trường có `.git`; ở bản archive nó bị loại có báo cáo (feature 009). Windows 11, macOS, CUDA và ô CI chạy thật vẫn CHƯA KIỂM — feature này chỉ ghi thẳng điều đó vào tài liệu.
