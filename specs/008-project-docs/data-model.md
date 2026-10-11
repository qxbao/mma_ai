---
id: "DATA-MODEL-008"
title: "Bộ tài liệu dự án mma_ai — Khung tài liệu (Phase 1)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Data Model (Phase 1): khung tài liệu

- [README.md — thứ tự mục (FR-002…FR-007)](#readmemd-thu-tu-muc-fr-002fr-007)
- [CONTRIBUTING.md (FR-008, ≤ 100 dòng)](#contributingmd-fr-008-100-dong)
- [CHANGELOG.md (FR-009)](#changelogmd-fr-009)
- [docs/guides/*.md (FR-010, mỗi tệp ≤ 120 dòng)](#docsguidesmd-fr-010-moi-tep-120-dong)


Feature không có thực thể dữ liệu bền vững, bảng hay Key Entity (spec không khai). File này chỉ ghi **khung mục** của từng tài liệu để vai `docs` viết và reviewer đối chiếu — không mở rộng phạm vi so với spec.

Không có bảng ánh xạ nhãn ↔ khoá trong yêu cầu đầu vào nên không có mục "Ánh xạ nhãn ↔ khoá".

<a id="readmemd-thu-tu-muc-fr-002fr-007"></a>
## README.md — thứ tự mục (FR-002…FR-007)

| # | Mục | Nội dung bắt buộc | Nguồn | Mã |
|---|---|---|---|---|
| 1 | Tiêu đề + mô tả 2–3 dòng | dự án làm gì (mô phỏng cơ–xương, huấn luyện PPO, đánh giá, phát lại 3D) | `pyproject.toml` `description` | AC-2 |
| 2 | Huy hiệu | Python 3.11–3.12; giấy phép MIT (trỏ `LICENSE`) | `pyproject.toml` `requires-python` | AC-2 |
| 3 | Tính năng | 4 năng lực M0–M1 bằng văn xuôi, không số liệu | spec 001–005 | AC-2 |
| 4 | Yêu cầu hệ thống | Python 3.11–3.12, `uv`; GPU không bắt buộc (không khẳng định thêm) | `pyproject.toml` | AC-2 |
| 5 | Cài đặt bằng uv | `uv sync`; extra `rl`, `eval`, `dev` | `pyproject.toml` | AC-2 |
| 6 | Bắt đầu nhanh | đúng 4 lệnh | [contracts/cli-commands.md](contracts/cli-commands.md) | AC-2 |
| 7 | Cấu trúc thư mục | `src/mma_ai/{physics,environment,learning,monitoring,evaluation,visualization}`, `specs/`, `docs/`, `tests/` | cây thư mục | AC-2 |
| 8 | Chạy kiểm thử | lệnh `pytest` | cổng dự án | AC-2 |
| 9 | Tình trạng nền tảng | Linux/WSL2 nay; Windows/macOS ở spec 006 | research.md Q4 | AC-2 |
| 10 | Tài liệu | `docs/MAP.md`, `specs/`, `docs/guides/*` | cây thư mục | AC-2, AC-5 |
| 11 | Đóng góp | trỏ `CONTRIBUTING.md` | — | AC-2 |
| 12 | Giấy phép | trỏ `LICENSE` | — | AC-2 |

(Mục 3–12 là 10 mục bắt buộc của FR-002 — Tính năng, Yêu cầu hệ thống, Cài đặt, Bắt đầu nhanh, Cấu trúc thư mục, Kiểm thử, Tình trạng nền tảng, Tài liệu, Đóng góp, Giấy phép; mục 1–2 (tiêu đề + mô tả, huy hiệu) là phần đầu trang.)

<a id="contributingmd-fr-008-100-dong"></a>
## CONTRIBUTING.md (FR-008, ≤ 100 dòng)

Nhóm nội dung: (1) chạy test/lint/mypy theo cổng dự án; (2) quy ước tiếng Việt (văn xuôi, comment, thông báo; định danh/lệnh giữ tiếng Anh; thuật ngữ song ngữ ở lần đầu); (3) luồng ai-sdlc (đặc tả → kế hoạch → task → triển khai; vùng ghi mỗi task theo `specs/*/tasks.md`; bản đồ `docs/MAP.md`); trỏ README cho cài đặt.

<a id="changelogmd-fr-009"></a>
## CHANGELOG.md (FR-009)

`# Changelog` + đoạn dẫn Keep a Changelog/Semantic Versioning → `## [Unreleased]` → `## [0.1.0] - <ngày>` → `### Added` theo năm ý của research.md Q3 → liên kết so sánh nếu có thẻ git (hiện chưa; không bịa liên kết).

<a id="docsguidesmd-fr-010-moi-tep-120-dong"></a>
## docs/guides/*.md (FR-010, mỗi tệp ≤ 120 dòng)

| Tệp | Lệnh chính | Phải có | Mã |
|---|---|---|---|
| `training.md` | `python scripts/train.py --stage elbow --seed 42` | cờ chính, nơi checkpoint, mã thoát, `--resume`, `--ui`, `--view3d`, trỏ benchmark | AC-5 |
| `evaluation.md` | `python -m mma_ai.evaluation.cli --checkpoint <ckpt>` | đầu vào `.pt`/`latest.json`, `--out` khi ngoài run, mã thoát | AC-5 |
| `replay-demo.md` | `python -m mma_ai.visualization.cli --episode <tệp>` / `--checkpoint <ckpt>` | chọn đúng một chế độ, `--headless`, mã 7, `--save-episode` | AC-5 |

Mỗi guide: frontmatter (`doc_type: guide`), mô tả 1–2 dòng, Điều kiện tiên quyết, Các bước, Lỗi thường gặp, liên kết ngược README.
