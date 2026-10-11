---
id: "TRACE-008"
title: "Ma trận truy vết 008-project-docs"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-12"
---

# Ma trận truy vết 008-project-docs

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/008-project-docs.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/008-project-docs/spec.md` (yêu cầu) và `specs/008-project-docs/tasks.md` (task `T801`…`T803`).
> Feature chỉ thêm tài liệu Markdown và tệp giấy phép, không đổi mã và không có kiểm thử tự động mới (hiến chương V), nên cột "Test / cổng máy" là các phép kiểm của `quickstart.md` (KB-1…KB-8) và bằng chứng của reviewer `T803`. Mức `entrypoint` = chạy lệnh thật `--help` của bốn điểm vào CLI (`scripts/train.py`, `python -m mma_ai.evaluation.cli`, `python -m mma_ai.visualization.cli`, `python -m mma_ai.learning.benchmark`) bằng tiến trình con; mức `cổng` = lệnh đo trên tệp tài liệu (`grep`, `wc -l`, `file --mime-encoding`, quét liên kết, `git diff --name-only`) hoặc verdict của reviewer. Cột trạng thái "có" nghĩa là đã có task + phép kiểm dự kiến, KHÔNG có nghĩa đã chạy xanh. Bằng chứng reviewer là `evidence/reviews/T803.verdict` và `.ai/runs/*/reports/reviewer-docs-check.md`.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | `LICENSE` là MIT chuẩn với dòng `Copyright (c) 2026 Dương Quan Bao` | T801, T803 | `grep -n "Copyright (c) 2026 Dương Quan Bao" LICENSE` (KB-1), `evidence/reviews/T803.verdict` | cổng | có |
| AC-2 | `README.md` tiếng Việt, đủ 10 mục, đúng 4 lệnh, ba nhóm `rl`/`eval`/`dev`, nền tảng nói thẳng | T801, T803 | `python -m mma_ai.evaluation.cli --help` · `python -m mma_ai.visualization.cli --help` · `python -m mma_ai.learning.benchmark --help` · `python scripts/train.py --help`, `grep -c '^## ' README.md` (KB-2), `.ai/runs/*/reports/reviewer-docs-check.md` | entrypoint | có |
| AC-3 | `CONTRIBUTING.md` ngắn gọn: test/lint/mypy, quy ước tiếng Việt, luồng ai-sdlc | T801, T803 | `grep -n "ai-sdlc\|pytest\|ruff\|mypy" CONTRIBUTING.md`, `wc -l CONTRIBUTING.md` (KB-5), `evidence/reviews/T803.verdict` | cổng | có |
| AC-4 | `CHANGELOG.md` theo Keep a Changelog, `[Unreleased]` và `[0.1.0]` tóm tắt M0–M1 | T802, T803 | `grep -nE '^## \[' CHANGELOG.md` so `grep '^version' pyproject.toml` (KB-6), `evidence/reviews/T803.verdict` | cổng | có |
| AC-5 | `docs/guides/` có đúng 3 hướng dẫn (huấn luyện, đánh giá, phát lại/demo), khớp `--help` và mã | T802, T803 | `ls docs/guides` (KB-7), `python -m mma_ai.visualization.cli --help`, `python -m mma_ai.evaluation.cli --help`, `python scripts/train.py --help`, `.ai/runs/*/reports/reviewer-docs-check.md` | entrypoint | có |
| FR-001 | `LICENSE` MIT chuẩn ở gốc repo, bản quyền đúng tên và năm | T801 | `grep -n "MIT License" LICENSE` và dòng bản quyền (KB-1) | cổng | có |
| FR-002 | `README.md` tiếng Việt, song ngữ ở lần đầu, tiêu đề + mô tả, huy hiệu, đủ 10 mục | T801 | `grep -c '^## ' README.md` và đối chiếu 10 mục (KB-2), `.ai/runs/*/reports/reviewer-docs-check.md` | cổng | có |
| FR-003 | Mục Cài đặt nêu `uv sync` và đúng ba nhóm `rl`, `eval`, `dev` như `pyproject.toml` | T801 | `grep -n "uv sync" README.md`, `grep -nE "rl\|eval\|dev" README.md` so `pyproject.toml` (KB-2) | cổng | có |
| FR-004 | Bắt đầu nhanh có đúng 4 lệnh thật | T801, T803 | `python scripts/train.py --help`, `python -m mma_ai.evaluation.cli --help`, `python -m mma_ai.visualization.cli --help`, `python -m mma_ai.learning.benchmark --help` (KB-3) | entrypoint | có |
| FR-005 | Cấu trúc thư mục liệt kê đủ mục tồn tại thật; mục kiểm thử nêu lệnh chạy bộ test | T801, T803 | `test -d src/mma_ai/physics …`, `.ai/runs/*/reports/reviewer-docs-check.md` (KB-2) | cổng | có |
| FR-006 | Tình trạng nền tảng: hiện nhắm Linux/WSL2, Windows/macOS đang làm ở spec 006, không hứa quá | T801, T803 | `grep -n "006" README.md` (KB-2), `evidence/reviews/T803.verdict` | cổng | có |
| FR-007 | Mục Tài liệu trỏ `docs/MAP.md`, `specs/`, 3 guide; Đóng góp trỏ `CONTRIBUTING.md`; Giấy phép trỏ `LICENSE` | T801 | quét liên kết tương đối trong `README.md` (KB-4) | cổng | có |
| FR-008 | `CONTRIBUTING.md` ngắn gọn: test, lint, mypy; quy ước tiếng Việt; luồng ai-sdlc | T801 | `grep -n "ai-sdlc\|pytest\|ruff\|mypy" CONTRIBUTING.md` (KB-5) | cổng | có |
| FR-009 | `CHANGELOG.md` Keep a Changelog, `[Unreleased]` + `[0.1.0]` khớp `version` của `pyproject.toml` | T802, T803 | `grep -nE '^## \[' CHANGELOG.md` so `grep '^version' pyproject.toml` (KB-6) | cổng | có |
| FR-010 | `docs/guides/` đúng 3 hướng dẫn, mỗi hướng dẫn có lệnh, cờ chính, đầu vào/đầu ra, lỗi/mã thoát | T802, T803 | `ls docs/guides`, `python -m mma_ai.visualization.cli --help` (cờ `--headless`, mã 7), `python -m mma_ai.evaluation.cli --help` (cờ `--out`) (KB-7) | entrypoint | có |
| FR-011 | Mọi lệnh/cờ chạy được hoặc có `--help` đúng; có lượt đối chiếu độc lập của reviewer ghi báo cáo | T803 | `.ai/runs/*/reports/reviewer-docs-check.md`, `evidence/reviews/T803.verdict` (KB-3) | entrypoint | có |
| FR-012 | Mọi tệp Markdown mới UTF-8, liên kết tương đối hợp lệ | T801, T802, T803 | `file --mime-encoding README.md LICENSE CONTRIBUTING.md CHANGELOG.md docs/guides/*.md`, quét liên kết tương đối (KB-4) | cổng | có |
| NFR-DOC-001 | 100% lệnh/cờ trong README, CONTRIBUTING, guides khớp `--help`/mã; 0 cờ không tồn tại; lệnh chưa chạy ghi CHƯA KIỂM | T801, T802, T803 | `grep -ohE -- '--[a-z][a-z0-9-]+' README.md CONTRIBUTING.md docs/guides/*.md` so `--help` của bốn lệnh (KB-3), `.ai/runs/*/reports/reviewer-docs-check.md` | entrypoint | có |
| NFR-DOC-002 | Từ đọc README tới lệnh đầu tiên ≤ 10 phút (không kể tải phụ thuộc) | T801, T803 | kiểm tay của reviewer trên môi trường sạch, ghi thời gian vào `.ai/runs/*/reports/reviewer-docs-check.md` (KB-2) | cổng | có |
| NFR-DOC-003 | `CONTRIBUTING.md` ≤ 100 dòng; mỗi guide ≤ 120 dòng | T801, T802, T803 | `wc -l CONTRIBUTING.md docs/guides/*.md` (KB-4) | cổng | có |
| NFR-DOC-004 | 0 liên kết tương đối gãy; 100% tệp mới UTF-8 | T801, T802, T803 | `file --mime-encoding …`, quét liên kết tương đối (KB-4) | cổng | có |
| INV-001 | Mọi lệnh/cờ khớp `--help` hoặc mã; lệch thì sửa tài liệu | T801, T802, T803 | `python scripts/train.py --help`, `python -m mma_ai.evaluation.cli --help`, `python -m mma_ai.visualization.cli --help`, `python -m mma_ai.learning.benchmark --help`, `evidence/reviews/T803.verdict` | entrypoint | có |
| INV-002 | Không đổi `src/`, `scripts/`, `tests/`, `pyproject.toml`, CI, `deliverables/`; vùng ghi chỉ gồm tệp tài liệu của feature | T801, T802, T803 | `git diff --name-only <base>..HEAD -- src scripts tests pyproject.toml deliverables` rỗng (KB-8), `evidence/reviews/T803.verdict` | cổng | có |
| INV-003 | Không hứa Windows native/macOS khi spec 006 chưa hoàn thành | T801, T803 | `grep -n "006" README.md`, reviewer đọc mục Tình trạng nền tảng (KB-2), `evidence/reviews/T803.verdict` | cổng | có |
| INV-004 | Mỗi sự thật (lệnh, nhóm cài đặt, nền tảng) có một chỗ gốc, nơi khác trỏ tới | T801, T802, T803 | đối chiếu `CONTRIBUTING.md` và `docs/guides/*` trỏ về `README.md` (KB-3), `.ai/runs/*/reports/reviewer-docs-check.md` | cổng | có |
| SC-001 | `LICENSE` ở gốc repo, MIT chuẩn, dòng bản quyền đúng | T801 | `grep -n "Copyright (c) 2026 Dương Quan Bao" LICENSE` (KB-1) | cổng | có |
| SC-002 | `README.md` đủ 10 mục, đúng 4 lệnh, đúng ba nhóm `rl`/`eval`/`dev` | T801, T803 | `grep -c '^## ' README.md` (KB-2), `.ai/runs/*/reports/reviewer-docs-check.md` | cổng | có |
| SC-003 | Người mới cài và chạy lệnh đầu trong ≤ 10 phút chỉ nhờ README | T801, T803 | kiểm tay của reviewer, ghi thời gian vào `.ai/runs/*/reports/reviewer-docs-check.md` (KB-2) | cổng | có |
| SC-004 | `CONTRIBUTING.md` đủ ba nội dung và ≤ 100 dòng | T801 | `grep -n "ai-sdlc\|pytest\|ruff\|mypy" CONTRIBUTING.md`, `wc -l CONTRIBUTING.md` (KB-4, KB-5) | cổng | có |
| SC-005 | `CHANGELOG.md` theo Keep a Changelog, bản 0.1.0 tóm tắt M0–M1, mỗi ý truy được về spec/mã | T802, T803 | `grep -nE '^## \[' CHANGELOG.md`, reviewer đối chiếu `specs/001…005` (KB-6) | cổng | có |
| SC-006 | `docs/guides/` có đúng 3 hướng dẫn, mỗi hướng dẫn ≤ 120 dòng | T802 | `ls docs/guides`, `wc -l docs/guides/*.md` (KB-4, KB-7) | cổng | có |
| SC-007 | 100% lệnh được đối chiếu với trợ giúp thật; 0 lệnh sai; số lệnh CHƯA KIỂM liệt kê rõ | T803 | `.ai/runs/*/reports/reviewer-docs-check.md`, `evidence/reviews/T803.verdict` (KB-3) | entrypoint | có |
| SC-008 | `git diff --name-only` chỉ gồm tệp tài liệu của feature; 0 thay đổi ở mã nguồn, CI, `deliverables/` | T801, T802, T803 | `git diff --name-only <base>..HEAD` (KB-8), `evidence/reviews/T803.verdict` | cổng | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Vai | Mã hiện thực (FR · INV · NFR · AC · SC) | Tệp test / cổng |
|---|---|---|---|
| T801 | docs | AC-1, AC-2, AC-3, FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-012, NFR-DOC-001, NFR-DOC-002, NFR-DOC-003, NFR-DOC-004, INV-001, INV-002, INV-003, INV-004, SC-001, SC-002, SC-003, SC-004, SC-008 | `README.md`, `LICENSE`, `CONTRIBUTING.md` qua quickstart KB-1, KB-2, KB-4, KB-5 |
| T802 | docs | AC-4, AC-5, FR-009, FR-010, FR-012, NFR-DOC-001, NFR-DOC-003, NFR-DOC-004, INV-001, INV-002, INV-004, SC-005, SC-006, SC-008 | `CHANGELOG.md`, `docs/guides/*.md` qua quickstart KB-4, KB-6, KB-7 |
| T803 | reviewer | AC-1, AC-2, AC-3, AC-4, AC-5, FR-011, FR-012, NFR-DOC-001, NFR-DOC-002, NFR-DOC-003, NFR-DOC-004, INV-001, INV-002, INV-003, INV-004, SC-007, SC-008 | `evidence/reviews/T803.verdict`, `.ai/runs/*/reports/reviewer-docs-check.md` |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không mã nào ở trạng thái `THIẾU`: mọi `AC-*`, `FR-*`, `INV-*`, `NFR-DOC-*`, `SC-*` của `spec.md` đều có task và phép kiểm dự kiến.
- Giới hạn của bằng chứng (không phải mã thiếu): feature không có kiểm thử tự động mới vì không đổi mã (hiến chương V); "mức entrypoint" ở đây là `--help` thật của bốn lệnh do reviewer `T803` chạy. `--help` cần nhập mô-đun nên có thể lỗi khi thiếu nhóm `rl`/`eval`: lệnh đó ghi CHƯA KIỂM kèm lỗi nguyên văn, không ghi "đạt" (plan, mục Rủi ro).
- `NFR-DOC-002`/`SC-003` (≤ 10 phút) chỉ đo được bằng kiểm tay trên môi trường sạch; nếu reviewer không có môi trường sạch thì ghi CHƯA KIỂM.
- Câu "Windows/macOS đang làm ở spec 006" sẽ lỗi thời khi spec 006 hoàn thành; chỉ sửa một chỗ gốc ở `README.md` (INV-004). Người xử: vai `docs` ở feature sau.
