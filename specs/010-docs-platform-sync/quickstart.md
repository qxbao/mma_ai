---
id: "QUICKSTART-010"
title: "Quickstart — kiểm chứng đồng bộ tài liệu với mã đã gộp"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Quickstart: kiểm chứng đồng bộ tài liệu (010)

- [Kịch bản 1 — README nói đúng đã/chưa kiểm (AC-2, AC-1, INV-001, INV-005)](#kich-ban-1-readme-noi-dung-dachua-kiem-ac-2-ac-1-inv-001-inv-005)
- [Kịch bản 2 — CHANGELOG `[Unreleased]` đủ 006–009 và `[0.1.0]` nguyên vẹn (AC-1, AC-2)](#kich-ban-2-changelog-unreleased-du-006009-va-010-nguyen-ven-ac-1-ac-2)
- [Kịch bản 3 — `platforms.md` chạy được và khớp mã (AC-1, INV-004, NFR-DOC-001, NFR-DOC-002)](#kich-ban-3-platformsmd-chay-duoc-va-khop-ma-ac-1-inv-004-nfr-doc-001-nfr-doc-002)
- [Kịch bản 4 — Test 008 đã cập nhật, không nới lỏng (AC-3, INV-003, NFR-GATE-001)](#kich-ban-4-test-008-da-cap-nhat-khong-noi-long-ac-3-inv-003-nfr-gate-001)
- [Kịch bản 5 — Vùng ghi, reviewer độc lập và cổng toàn hệ (AC-3, INV-002, FR-012)](#kich-ban-5-vung-ghi-reviewer-doc-lap-va-cong-toan-he-ac-3-inv-002-fr-012)

**Điều kiện chung**: ở gốc dự án, đã `uv sync`; Linux. Bước nào test tự động làm được thì chỉ tên test (do task D của qa viết/đổi; tên dưới đây là **đề xuất**, qa chốt khi viết). "Kiểm tay" nghĩa là reviewer chạy/đọc.

<a id="kich-ban-1-readme-noi-dung-dachua-kiem-ac-2-ac-1-inv-001-inv-005"></a>
## Kịch bản 1 — README nói đúng đã/chưa kiểm (AC-2, AC-1, INV-001, INV-005)

1. Mở `README.md`, mục "Tình trạng nền tảng": kỳ vọng có danh sách hạng mục; dòng Linux chứa "đã kiểm"; dòng Windows 11, WSL2, macOS, CUDA, ô CI chạy thật trên GitHub Actions đều chứa "chưa kiểm" và không chứa "đã kiểm". Test: `tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support` (đã đổi).
2. Kỳ vọng mục nêu `mma_ai.compat`, `python -m mma_ai.compat.env_report`, cổng năng lực, `.github/workflows/ci.yml`, và liên kết `specs/006-cross-platform-support/`. Cùng test ở bước 1.
3. Kỳ vọng README vẫn đúng 10 tiêu đề `##` và bốn lệnh nhanh. Test: `test_ac1_ac2_ac3_ac4_ac5_document_structure`, `test_ac2_inv004_readme_quickstart`.
4. `grep -n '^status:' specs/006-cross-platform-support/spec.md` → `status: draft` (INV-005). Test: cùng test ở bước 1 (còn đòi `^status: draft$`).
5. **Kiểm tay (reviewer)**: đọc từng câu, đối chiếu với `.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md`; không câu nào khẳng định hơn bằng chứng.

<a id="kich-ban-2-changelog-unreleased-du-006009-va-010-nguyen-ven-ac-1-ac-2"></a>
## Kịch bản 2 — CHANGELOG `[Unreleased]` đủ 006–009 và `[0.1.0]` nguyên vẹn (AC-1, AC-2)

1. Đọc mục `[Unreleased]`: kỳ vọng `### Added`, `### Changed`; dòng cho 006, 007, 008, 009, mỗi dòng liên kết `specs/<NNN-slug>/`; đủ sáu tên dấu năng lực; có câu "chưa kiểm Windows/macOS/CI thật". Test: `test_ac2_ac3_ac4_ac5_inv004_relative_links[CHANGELOG.md]` (liên kết) và test mới `test_ac1_ac2_changelog_unreleased_covers_merged_specs` (nội dung).
2. Không có khối lệnh trong CHANGELOG. Test: `test_ac2_ac3_ac5_inv001_documented_flags[CHANGELOG.md]` (`assert not lines`).
3. `git diff -- CHANGELOG.md` chỉ thêm dòng trong `[Unreleased]`; mục `## [0.1.0] - 2026-10-12` không đổi. **Kiểm tay (reviewer)**: `git diff -U0 -- CHANGELOG.md` không có dòng xoá/sửa ở mục `[0.1.0]`.

<a id="kich-ban-3-platformsmd-chay-duoc-va-khop-ma-ac-1-inv-004-nfr-doc-001-nfr-doc-002"></a>
## Kịch bản 3 — `platforms.md` chạy được và khớp mã (AC-1, INV-004, NFR-DOC-001, NFR-DOC-002)

1. `uv run python -m mma_ai.compat.env_report` → in dòng `[ok]`/`[CẢNH BÁO]`/`[LỖI]` rồi "Môi trường đạt yêu cầu." (mã 0) hoặc "Môi trường chưa đạt yêu cầu." (mã 1). Test: `test_ac1_inv004_platforms_guide_env_report_runs` (chạy thật; mã ∈ {0,1}).
2. `uv run python -m mma_ai.compat.env_report --json` → một dòng JSON có `schema_version`, `os.kind`, `overall`. Cùng test ở bước 1. Cờ lạ: `… --bogus` → mã 2 ("Cờ không được hỗ trợ: --bogus").
3. `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/unit/test_capability_gate.py --capability-report=capability.json` → dòng `Kiểm thử bị loại theo năng lực: X/Y (…; giới hạn 5.0%).`; tệp JSON có `collected`, `deselected`, `ratio`, `items`. Test: cờ trong `platforms.md` ⊆ `python -m pytest --help` (`test_ac5_inv001_platforms_guide_flags`).
4. Mỗi tên trong sáu dấu năng lực nêu ở `platforms.md` ∈ dấu khai ở `tests/unit/capability_gate.py`. Test: `test_ac1_inv004_platforms_guide_markers_exist`.
5. `platforms.md` ≤ 120 dòng, có `../../README.md`, mọi liên kết tương đối có đích. Test: `test_ac1_ac2_ac3_ac4_ac5_document_structure`, `test_ac2_ac3_ac4_ac5_inv004_relative_links[platforms.md]`.
6. README mục "Tài liệu" liên kết tới `docs/guides/platforms.md`. Test: `test_ac1_readme_links_platforms_guide`.
7. **Kiểm tay (reviewer)**: giải thích lịch sử git khớp spec 009 (lý do `Máy không có lịch sử git`; INV-002 của 008 chỉ chứng minh ở môi trường có git); không có `scripts/check_env.py`; hàng mã `7` của `replay-demo.md` nêu `mjpython` kèm "chưa kiểm trên macOS thật"; `training.md` và `evaluation.md` không đổi (đối chiếu research Q3).

<a id="kich-ban-4-test-008-da-cap-nhat-khong-noi-long-ac-3-inv-003-nfr-gate-001"></a>
## Kịch bản 4 — Test 008 đã cập nhật, không nới lỏng (AC-3, INV-003, NFR-GATE-001)

1. `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --capability-report=report.json` → mọi test PASS; `report.json` có `ratio` ≤ 0.05 (ở máy có git: `deselected` = 0).
2. `… tests/e2e/test_008_docs_entrypoints.py --collect-only -q` → số test ≥ 24 (mốc ĐÃ ĐO ở HEAD).
3. `git diff -- tests/e2e/test_008_docs_entrypoints.py | grep -E '^\+.*(skip|xfail|importorskip)'` → không có dòng nào; `git diff` không đụng thân `test_inv002_document_commits_keep_product_code_untouched` và dòng `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")`; hằng `GUIDES` không đổi (D-2).
4. Ở bản archive không có `.git`: test INV-002 của 008 bị loại với lý do `Máy không có lịch sử git`, các test khác PASS (cơ chế của 009; feature này không đổi).

<a id="kich-ban-5-vung-ghi-reviewer-doc-lap-va-cong-toan-he-ac-3-inv-002-fr-012"></a>
## Kịch bản 5 — Vùng ghi, reviewer độc lập và cổng toàn hệ (AC-3, INV-002, FR-012)

1. `git diff --name-only <nhánh gốc>..HEAD` chỉ gồm: `README.md`, `CHANGELOG.md`, `docs/guides/platforms.md`, `docs/guides/replay-demo.md`, `tests/e2e/test_008_docs_entrypoints.py`, `specs/010-docs-platform-sync/**`, `docs/MAP.md`, `docs/05-tracing/**`, bằng chứng review; **không** có tệp trong `src/`, `pyproject.toml`, `uv.lock`, `.github/`. Kiểm tay (reviewer) + cổng vùng ghi theo `outputs` của `tasks.md`.
2. Verdict của reviewer (vai khác `docs`) có bảng đối chiếu lệnh/đường dẫn/marker và kết quả ba hướng dẫn cũ (FR-008, FR-012). Kiểm tay: đọc `evidence/reviews/*.verdict`.
3. `ai-sdlc verify --branch ai-sdlc/integration` → `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` đều xanh (AC-3). Bằng chứng là lần chạy cổng của máy, không phải test trong repo.
4. Báo cáo QA/review nêu giới hạn: Windows 11, WSL2, macOS, CUDA, ô CI thật chưa kiểm; INV-002 của 008 chỉ chứng minh ở môi trường có git.
