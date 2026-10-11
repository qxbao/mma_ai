---
id: "QUICKSTART-008"
title: "Bộ tài liệu dự án mma_ai — Kịch bản kiểm (Phase 1)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Quickstart (Phase 1): kịch bản kiểm bộ tài liệu

- [KB-1 — LICENSE đúng MIT và bản quyền (AC-1, FR-001)](#kb-1-license-dung-mit-va-ban-quyen-ac-1-fr-001)
- [KB-2 — README đủ mục và đúng 4 lệnh (AC-2, FR-002…FR-007, NFR-DOC-002, INV-003)](#kb-2-readme-du-muc-va-dung-4-lenh-ac-2-fr-002fr-007-nfr-doc-002-inv-003)
- [KB-3 — Mọi lệnh khớp trợ giúp thật (AC-2, AC-5, FR-011, NFR-DOC-001, INV-001, INV-004)](#kb-3-moi-lenh-khop-tro-giup-that-ac-2-ac-5-fr-011-nfr-doc-001-inv-001-inv-004)
- [KB-4 — Độ dài, liên kết, mã hoá (NFR-DOC-003, NFR-DOC-004, FR-012)](#kb-4-do-dai-lien-ket-ma-hoa-nfr-doc-003-nfr-doc-004-fr-012)
- [KB-5 — CONTRIBUTING (AC-3, FR-008)](#kb-5-contributing-ac-3-fr-008)
- [KB-6 — CHANGELOG (AC-4, FR-009)](#kb-6-changelog-ac-4-fr-009)
- [KB-7 — Ba hướng dẫn (AC-5, FR-010)](#kb-7-ba-huong-dan-ac-5-fr-010)
- [KB-8 — Vùng ghi và không đổi mã (INV-002, SC-008)](#kb-8-vung-ghi-va-khong-doi-ma-inv-002-sc-008)


Tiền điều kiện: các tệp của feature đã có ở gốc repo và `docs/guides/`. Không test tự động mới (không đổi mã); kiểm bằng lệnh có sẵn và đối chiếu của vai reviewer. Hợp đồng lệnh: [contracts/cli-commands.md](contracts/cli-commands.md). Khung mục: [data-model.md](data-model.md).

<a id="kb-1-license-dung-mit-va-ban-quyen-ac-1-fr-001"></a>
## KB-1 — LICENSE đúng MIT và bản quyền (AC-1, FR-001)

1. `grep -n "MIT License" LICENSE` → có dòng tiêu đề.
2. `grep -n "Copyright (c) 2026 Dương Quan Bao" LICENSE` → đúng 1 dòng.
3. So thân văn bản với MIT chuẩn (reviewer; Task 3). Không có test tự động.

<a id="kb-2-readme-du-muc-va-dung-4-lenh-ac-2-fr-002fr-007-nfr-doc-002-inv-003"></a>
## KB-2 — README đủ mục và đúng 4 lệnh (AC-2, FR-002…FR-007, NFR-DOC-002, INV-003)

1. `grep -c '^## ' README.md` và đối chiếu thủ công 10 mục của FR-002 (Tính năng, Yêu cầu hệ thống, Cài đặt, Bắt đầu nhanh, Cấu trúc thư mục, Kiểm thử, Tình trạng nền tảng, Tài liệu, Đóng góp, Giấy phép).
2. Trong khối Bắt đầu nhanh, đếm đúng 4 lệnh khớp bảng "Lệnh Bắt đầu nhanh" của contracts.
3. `grep -n "uv sync" README.md`, và `grep -nE "rl|eval|dev" README.md` — ba nhóm đúng `pyproject.toml`, không nhóm khác.
4. Mục Tình trạng nền tảng: `grep -n "006" README.md` có; không có câu hứa Windows/macOS chạy được (reviewer đọc).
5. Reviewer làm theo Cài đặt + Bắt đầu nhanh trên môi trường sạch và ghi thời gian tới lệnh đầu tiên (≤ 10 phút, không kể tải phụ thuộc).

<a id="kb-3-moi-lenh-khop-tro-giup-that-ac-2-ac-5-fr-011-nfr-doc-001-inv-001-inv-004"></a>
## KB-3 — Mọi lệnh khớp trợ giúp thật (AC-2, AC-5, FR-011, NFR-DOC-001, INV-001, INV-004)

1. Chạy `--help` bốn lệnh (thoát 0, ghi đầu ra):
   - `uv run --isolated python scripts/train.py --help`
   - `uv run --isolated python -m mma_ai.evaluation.cli --help`
   - `uv run --isolated python -m mma_ai.visualization.cli --help`
   - `uv run --isolated python -m mma_ai.learning.benchmark --help`
2. Trích mọi cờ trong README/CONTRIBUTING/guides: `grep -ohE -- '--[a-z][a-z0-9-]+' README.md CONTRIBUTING.md docs/guides/*.md | sort -u`; mỗi cờ phải có trong `--help` của lệnh tương ứng.
3. Ghi báo cáo `.ai/runs/<pha>/reports/reviewer-docs-check.md`: từng lệnh · lệnh trợ giúp đã chạy · khớp/lệch · môi trường; lệnh không chạy được ghi "CHƯA KIỂM" + lỗi nguyên văn.

<a id="kb-4-do-dai-lien-ket-ma-hoa-nfr-doc-003-nfr-doc-004-fr-012"></a>
## KB-4 — Độ dài, liên kết, mã hoá (NFR-DOC-003, NFR-DOC-004, FR-012)

1. `wc -l CONTRIBUTING.md docs/guides/*.md` → CONTRIBUTING ≤ 100, mỗi guide ≤ 120.
2. UTF-8: `file --mime-encoding README.md LICENSE CONTRIBUTING.md CHANGELOG.md docs/guides/*.md` → `utf-8` hoặc `us-ascii`.
3. Liên kết tương đối: với mỗi `](path)` không bắt đầu bằng `http`/`#`, `test -e` đường dẫn (bỏ phần `#neo`) → 0 thiếu.

<a id="kb-5-contributing-ac-3-fr-008"></a>
## KB-5 — CONTRIBUTING (AC-3, FR-008)

1. Có ba nhóm: lệnh test/lint/mypy, quy ước tiếng Việt, luồng ai-sdlc (`grep -n "ai-sdlc\|pytest\|ruff\|mypy" CONTRIBUTING.md`).
2. Lệnh lint/mypy dùng `uv run --isolated --with ruff …`/`--with mypy …`; không dặn `uv sync --extra dev` rồi gọi trực tiếp.
3. Chạy thử đúng các lệnh đó trên repo (ngưỡng: thoát 0 như cổng dự án) — hoặc ghi "CHƯA KIỂM".

<a id="kb-6-changelog-ac-4-fr-009"></a>
## KB-6 — CHANGELOG (AC-4, FR-009)

1. `grep -nE '^## \[(Unreleased|0\.1\.0)\]' CHANGELOG.md` → cả hai mục; `0.1.0` khớp `grep '^version' pyproject.toml`.
2. Mỗi ý `Added` truy được về `specs/001…005` hoặc thư mục `src/mma_ai/<phân hệ>`; không nêu script không có ở `scripts/`.

<a id="kb-7-ba-huong-dan-ac-5-fr-010"></a>
## KB-7 — Ba hướng dẫn (AC-5, FR-010)

1. `ls docs/guides` → đúng 3 tệp: `training.md`, `evaluation.md`, `replay-demo.md`.
2. Mỗi tệp có liên kết ngược `../../README.md`, frontmatter `doc_type: guide`, cờ chỉ lấy từ bảng contracts.
3. Guide replay nêu mã 7 và `--headless`; guide evaluate nêu `--out` cho checkpoint ngoài run.

<a id="kb-8-vung-ghi-va-khong-doi-ma-inv-002-sc-008"></a>
## KB-8 — Vùng ghi và không đổi mã (INV-002, SC-008)

1. `git diff --name-only <base>..HEAD` chỉ gồm `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/**` và tệp của chính feature (`specs/008-project-docs/**`, bằng chứng/báo cáo).
2. `git diff --name-only <base>..HEAD -- src scripts tests pyproject.toml deliverables` → rỗng.
