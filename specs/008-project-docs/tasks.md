---
id: "TASKS-008"
title: "Bộ tài liệu dự án mma_ai (README · giấy phép · đóng góp · nhật ký thay đổi · hướng dẫn dùng) — Nhiệm vụ (Tasks)"
doc_type: tasks
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Nhiệm vụ: Bộ tài liệu dự án mma_ai

- [Đầu vào](#dau-vao)
- [Quy ước task](#quy-uoc-task)
  - [Phụ thuộc chéo feature](#phu-thuoc-cheo-feature)
- [User story US1–US4 — README, giấy phép, CONTRIBUTING (P1/P2)](#user-story-us1us4-readme-giay-phep-contributing-p1p2)
- [User story US5–US6 — CHANGELOG và ba hướng dẫn (P2)](#user-story-us5us6-changelog-va-ba-huong-dan-p2)
- [Đối chiếu độc lập](#doi-chieu-doc-lap)
  - [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Bảng task](#bang-task)
- [Dependencies và wave](#dependencies-va-wave)
- [Điều kiện hoàn thành](#dieu-kien-hoan-thanh)

> Đích: `specs/008-project-docs/tasks.md`. Sinh từ `spec.md` + `plan.md` + `research.md` + `data-model.md` + `contracts/cli-commands.md` + `quickstart.md` HIỆN TẠI (viết lại hoàn toàn ở lượt 2026-10-12). Feature chỉ thêm tài liệu Markdown và một tệp giấy phép: không có màn hình ⇒ không có mã `UI-*`; dự án là ứng dụng dòng lệnh, `contracts/` chỉ là bảng lệnh ↔ cờ (không có HTTP) ⇒ không có mã `API-*`; không có kế hoạch hạ tầng `infra/deploy/008-project-docs*.md` ⇒ không có task `platform`.

<a id="dau-vao"></a>
## Đầu vào

- `spec.md`: AC-1…AC-5 (AC-1 = LICENSE · AC-2 = README · AC-3 = CONTRIBUTING · AC-4 = CHANGELOG · AC-5 = `docs/guides/`), FR-001…FR-012, NFR-DOC-001…004, INV-001…004, SC-001…008.
- `plan.md` (bố cục 3 task, quyết định D1…D8), `contracts/cli-commands.md` (bảng nguồn sự thật cho lệnh và cờ — vai `docs` chỉ chép từ đây), `data-model.md` (khung mục từng tài liệu), `quickstart.md` (kịch bản kiểm KB-1…KB-8), `research.md`.
- Khảo sát nguồn: `docs/00-survey/mma-ai-project-docs.md`.

<a id="quy-uoc-task"></a>
## Quy ước task

- **Dải mã `T801`…`T804`**: id task duy nhất toàn dự án; 008 dùng dải `T8xx` để không va với `T2xx`…`T7xx` của 001–007.
- **Vai thi công là `docs`** (outputs `README.md` `LICENSE` `CONTRIBUTING.md` `CHANGELOG.md` `docs/guides/**`); task đối chiếu do vai `reviewer`. Một task `qa` (`T804`) sinh kiểm thử đầu-cuối (E2E) ở `tests/e2e/**` chạy trên entrypoint thật; **không** có task `challenger` (xem [quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)). Bốn task.
- **Vùng ghi của feature (INV-002, SC-008)**: chỉ `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/**` cộng `tests/e2e/test_008_docs_entrypoints.py` của `T804` và báo cáo/verdict của reviewer. `src/`, `scripts/`, `tests/`, `pyproject.toml`, CI, `deliverables/` KHÔNG đổi. Mỗi tệp đúng một task chủ.
- **Lệnh chỉ chép từ `contracts/cli-commands.md`** (INV-001): cờ nào chưa có trong bảng thì đọc `_build_parser` / chạy `--help` rồi cập nhật bảng cùng lượt; cờ lệch với mã thì sửa tài liệu, không sửa mã. Ví dụ dùng `<ckpt>`, `<tệp>` làm chỗ giữ chỗ, không đường dẫn tuyệt đối của máy riêng (hiến chương VI).
- **Không số liệu viết tay** (hiến chương VIII): README/CHANGELOG/guides không ghi số test, số bước, tốc độ; tên nhóm cài đặt, cờ, mã thoát lấy từ `pyproject.toml` và mã.
- **Một chỗ gốc cho mỗi sự thật (INV-004)**: bốn lệnh nhanh, ba nhóm cài đặt và trạng thái nền tảng nằm ở `README.md`; `CONTRIBUTING.md` và guides trỏ về README thay vì chép lệch.
- **Nền tảng (INV-003)**: chỉ ghi "hiện nhắm Linux/WSL2; Windows/macOS đang làm ở spec 006"; đọc lại `specs/006-cross-platform-support/spec.md` lúc viết để câu chữ không lệch hiện trạng.
- **Frontmatter**: tệp dưới `docs/guides/` có frontmatter (`id`, `title`, `doc_type: guide`, `owner_agent: docs`, `status`, `updated`) theo khuôn `docs/MAP.md` (D2); bốn tệp ở gốc repo KHÔNG có frontmatter.
- **Giới hạn độ dài (NFR-DOC-003)**: `CONTRIBUTING.md` ≤ 100 dòng; mỗi guide ≤ 120 dòng.
- **Mã hoá và liên kết (NFR-DOC-004, FR-012)**: UTF-8; liên kết tương đối phải trỏ tới tệp có thật (tệp guide chỉ trỏ tới tệp đã có sau T801/T802).
- **Tự chốt**: `docs/MAP.md` là tệp máy sinh nên KHÔNG task nào sửa; README chỉ trỏ tới nó — lý do: `CLAUDE.md` của dự án, chỉ mục do máy sinh khi có `tasks.md`.
- **Tự chốt**: báo cáo đối chiếu của `T803` đặt ở `.ai/runs/*/reports/reviewer-docs-check.md` (đúng glob của vai reviewer) cạnh `evidence/reviews/T803.verdict` — lý do: FR-011 đòi báo cáo từng lệnh; verdict một dòng không đủ chứa bảng lệnh.

<a id="phu-thuoc-cheo-feature"></a>
### Phụ thuộc chéo feature

Không task nào của 008 đọc hay sửa tệp do task của feature khác sinh ra; tài liệu chỉ *mô tả* mã đã có của 001–005 và trạng thái của 006 (đọc spec, không tiêu thụ đầu ra task). Vì vậy cột `depends_on` chỉ nối các task nội bộ 008 (`T802` sau `T801`; `T804` sau `T801`, `T802`; `T803` sau `T801`, `T802`, `T804`).

Không có task nào đổi hành vi mà test của task/feature trước đang khẳng định: grep `README`/`CHANGELOG`/`CONTRIBUTING`/`docs/guides` trong `tests/` và `conftest.py` không có kết quả ⇒ không cần task "cập nhật test cũ".

<a id="user-story-us1us4-readme-giay-phep-contributing-p1p2"></a>
## User story US1–US4 — README, giấy phép, CONTRIBUTING (P1/P2)

**Mục tiêu**: người lần đầu tới repo hiểu dự án làm gì, cài bằng `uv`, chạy đúng 4 lệnh thật trong ≤ 10 phút (NFR-DOC-002); `LICENSE` là MIT chuẩn với bản quyền đã xác nhận; người đóng góp biết test/lint/mypy, quy ước tiếng Việt, luồng ai-sdlc.

**Kiểm thử độc lập**: quickstart KB-1, KB-2, KB-4, KB-5 (grep mục, đếm lệnh, `wc -l`, UTF-8, liên kết).

- [ ] T801 [US1] [US2] [US4] Viết `LICENSE` (MIT chuẩn, `Copyright (c) 2026 Dương Quan Bao`), `README.md` (tiêu đề + mô tả 2–3 dòng, huy hiệu, 10 mục bắt buộc, đúng 4 lệnh) và `CONTRIBUTING.md` (≤ 100 dòng) — README.md; LICENSE; CONTRIBUTING.md

<a id="user-story-us5us6-changelog-va-ba-huong-dan-p2"></a>
## User story US5–US6 — CHANGELOG và ba hướng dẫn (P2)

**Mục tiêu**: `CHANGELOG.md` theo Keep a Changelog với bản `[0.1.0]` tóm tắt M0–M1 truy được về spec/mã; `docs/guides/` có đúng ba hướng dẫn ngắn (huấn luyện, đánh giá, phát lại/demo), mỗi cái có liên kết ngược README.

**Kiểm thử độc lập**: quickstart KB-6, KB-7, KB-4.

- [ ] T802 [US5] [US6] Viết `CHANGELOG.md` (Keep a Changelog, `[Unreleased]` + `[0.1.0]`) và ba hướng dẫn `docs/guides/training.md`, `docs/guides/evaluation.md`, `docs/guides/replay-demo.md` (mỗi tệp ≤ 120 dòng) — CHANGELOG.md; docs/guides/training.md; docs/guides/evaluation.md; docs/guides/replay-demo.md

<a id="doi-chieu-doc-lap"></a>
## Đối chiếu độc lập

- [ ] T804 [US1] [US5] [US6] QA: viết E2E `tests/e2e/test_008_docs_entrypoints.py` chạy `--help` của bốn entrypoint thật và đối chiếu cờ trong tài liệu
- [ ] T803 [US3] Reviewer: chạy `--help` bốn lệnh và đối chiếu từng lệnh/cờ trong `README.md`, `CONTRIBUTING.md`, `docs/guides/*` với trợ giúp thật và mã; ghi báo cáo và verdict — evidence/reviews/T803.verdict; .ai/runs/*/reports/reviewer-docs-check.md

<a id="quyet-dinh-ve-vai-challenger"></a>
### Quyết định về vai `challenger`

**KHÔNG DÙNG** vai `challenger`. Bốn bất biến `INV-001…004` của spec là bất biến về **nội dung và vùng ghi của tài liệu** (lệnh khớp `--help`, không đổi mã, không hứa nền tảng chưa hỗ trợ, một chỗ gốc cho mỗi sự thật), không phải bất biến của một hàm nhận đầu vào người dùng nên không có vector/fuzz nào "đánh sập" được; chúng được kiểm tất định bằng đối chiếu `--help` và quét cờ (`T803`), so `git diff --name-only` với vùng ghi (quickstart KB-8) và grep (`006`, ba nhóm cài đặt). Dùng challenger chỉ thêm một lượt mà không thêm bằng chứng, và đổi cổng review thành nhất trí hai vai; yêu cầu gốc cũng cấm dùng challenger cho feature này. (Task `qa` `T804` được thêm sau lượt lint `NO_E2E` — xem mục Dependencies và wave.) Quyết định cũng được ghi ở `plan.md`.

<a id="bang-task"></a>
## Bảng task

| id | mô tả | outputs | depends_on | role | độ khó |
|---|---|---|---|---|---|
| T801 | Viết ba tệp ở gốc repo. (1) `LICENSE`: văn bản giấy phép MIT chuẩn, đúng một dòng `Copyright (c) 2026 Dương Quan Bao`, lưu UTF-8. (2) `README.md` bằng tiếng Việt, thuật ngữ song ngữ ở lần xuất hiện đầu (ví dụ "chính sách ngẫu nhiên (random policy)"), không frontmatter: tiêu đề + mô tả 2–3 dòng (nguồn `pyproject.toml` `description`); hai huy hiệu tĩnh Python 3.11–3.12 và giấy phép MIT trỏ `LICENSE` (D7); đủ 10 mục theo khung `data-model.md`: Tính năng (bốn năng lực M0–M1 bằng văn xuôi, không số liệu) · Yêu cầu hệ thống · Cài đặt bằng uv (`uv sync`; đúng ba nhóm tuỳ chọn `rl`, `eval`, `dev` như `pyproject.toml`, không nhóm khác) · Bắt đầu nhanh (một dòng nêu chạy trong môi trường đã `uv sync`, kích hoạt `.venv` hoặc tiền tố `uv run`, rồi ĐÚNG 4 lệnh: `python scripts/train.py --stage elbow --seed 42`; `python -m mma_ai.evaluation.cli --checkpoint <ckpt>`; `python -m mma_ai.visualization.cli --episode <tệp>` hoặc `--checkpoint <ckpt>`; `python -m mma_ai.learning.benchmark --seed 42 --repeats 5`) · Cấu trúc thư mục (`src/mma_ai/{physics,environment,learning,monitoring,evaluation,visualization}`, `specs/`, `docs/`, `tests/`, mục nào cũng tồn tại thật) · Chạy kiểm thử (lệnh `pytest` của dự án) · Tình trạng nền tảng (nói thẳng hiện nhắm Linux/WSL2; Windows/macOS đang làm ở spec 006; gợi ý WSL2; không hứa chạy được) · Tài liệu (`docs/MAP.md`, `specs/`, ba tệp `docs/guides/*`) · Đóng góp (trỏ `CONTRIBUTING.md`) · Giấy phép (trỏ `LICENSE`). Liên kết tới `docs/guides/*.md` viết đúng tên `training.md`, `evaluation.md`, `replay-demo.md` (do T802 tạo) và tới `CHANGELOG.md`. (3) `CONTRIBUTING.md` ≤ 100 dòng: lệnh test `uv run --isolated --with pytest pytest -q`, lint `uv run --isolated --with ruff ruff check .`, mypy `uv run --isolated --with mypy mypy --strict .` (D4, không dặn `uv sync --extra dev` rồi gọi thẳng ruff/mypy); quy ước tiếng Việt (văn xuôi, comment, thông báo bằng tiếng Việt; định danh/lệnh giữ tiếng Anh; thuật ngữ song ngữ ở lần đầu); luồng ai-sdlc (đặc tả → kế hoạch → task → triển khai, vùng ghi mỗi task theo cột outputs của `specs/*/tasks.md`, bản đồ `docs/MAP.md`); trỏ README cho cài đặt thay vì chép lại (INV-004). Không đổi `src/`, `scripts/`, `tests/`, `pyproject.toml`, CI, `deliverables/`. Hiện thực AC-1 · AC-2 · AC-3 · FR-001 · FR-002 · FR-003 · FR-004 · FR-005 · FR-006 · FR-007 · FR-008 · FR-012 · NFR-DOC-001 · NFR-DOC-002 · NFR-DOC-003 · NFR-DOC-004 · INV-001 · INV-002 · INV-003 · INV-004 · SC-001 · SC-002 · SC-003 · SC-004 · SC-008. Kiểm chứng: quickstart KB-1, KB-2, KB-4, KB-5 — `grep -n "Copyright (c) 2026 Dương Quan Bao" LICENSE` đúng 1 dòng; `grep -c '^## ' README.md` đủ 10 mục; `wc -l CONTRIBUTING.md` ≤ 100; `file --mime-encoding README.md LICENSE CONTRIBUTING.md` là utf-8/us-ascii. | README.md; LICENSE; CONTRIBUTING.md | | docs | vừa |
| T802 | Viết `CHANGELOG.md` ở gốc repo theo Keep a Changelog (không frontmatter): tiêu đề + đoạn dẫn nêu Keep a Changelog và Semantic Versioning, mục `## [Unreleased]` (trống hoặc ghi việc đang làm đã có spec 006), mục `## [0.1.0] - <ngày ghi tài liệu>` khớp `version = "0.1.0"` của `pyproject.toml`, nhóm `### Added` tóm tắt M0–M1 theo năm ý của `research.md` Q3 (mô phỏng vật lý và đo hiệu năng M0 ở `src/mma_ai/physics`; môi trường khuỷu tay cơ bắp; huấn luyện PPO; đánh giá so với random; phát lại/demo 3D), mỗi ý trỏ spec 001…005 hoặc thư mục `src/mma_ai/<phân hệ>`; không nêu script không còn ở `scripts/` (D6), không bịa liên kết so sánh thẻ git. Viết ba hướng dẫn ngắn có frontmatter `doc_type: guide`, mỗi tệp ≤ 120 dòng, tiếng Việt song ngữ, có mô tả 1–2 dòng, Điều kiện tiên quyết, Các bước, Lỗi thường gặp và liên kết ngược `../../README.md`; cờ và mã thoát chỉ lấy từ `contracts/cli-commands.md` (INV-001), lệnh chính trỏ README thay vì chép lệch (INV-004): `docs/guides/training.md` (lệnh `python scripts/train.py --stage elbow --seed 42`; cờ `--config`, `--total-steps`, `--resume` nhận `.pt` hoặc `latest.json`, `--runs-dir`, `--ui`, `--ui-port`, `--view3d`; nơi tìm checkpoint đọc từ `src/mma_ai/learning/run_dir.py` và `checkpoint.py`, chưa xác nhận được thì ghi "xem `--runs-dir`" hoặc CHƯA KIỂM; mã thoát 0/1/2/3/4/130; trỏ lệnh đo hiệu năng `--repeats` tối thiểu 5); `docs/guides/evaluation.md` (lệnh `python -m mma_ai.evaluation.cli --checkpoint <ckpt>`; đầu vào `.pt` hoặc `latest.json`; checkpoint ngoài thư mục run cần `--out`, nếu không lệnh báo lỗi; cờ `--config`, `--repeats`, `--eval-seed`, `--runs-dir`; mã thoát 0/1/2/4/5/6/7/130); `docs/guides/replay-demo.md` (hai chế độ `--episode <tệp>` và `--checkpoint <ckpt>`, chọn đúng một; `--headless`, `--save-episode` chỉ với `--checkpoint`, `--speed`, `--loop`, `--allow-model-mismatch`, `--split`, `--target-index`, `--seed`, `--config`; khi không có màn hình dùng được lệnh thoát mã 7 kèm gợi ý `--headless`; mã thoát 0/1/2/4/5/6/7/8/130). Không đổi `src/`, `scripts/`, `tests/`, `pyproject.toml`, CI, `deliverables/`. Hiện thực AC-4 · AC-5 · FR-009 · FR-010 · FR-012 · NFR-DOC-001 · NFR-DOC-003 · NFR-DOC-004 · INV-001 · INV-002 · INV-004 · SC-005 · SC-006 · SC-008. Kiểm chứng: quickstart KB-6, KB-7, KB-4 — `grep -nE '^## \[' CHANGELOG.md` có cả mục `[Unreleased]` và `[0.1.0]`; `ls docs/guides` đúng 3 tệp; `wc -l docs/guides/*.md` mỗi tệp ≤ 120; liên kết tương đối không gãy. | CHANGELOG.md; docs/guides/training.md; docs/guides/evaluation.md; docs/guides/replay-demo.md | T801 | docs | vừa |
| T804 | QA sinh kiểm thử đầu-cuối (E2E) `tests/e2e/test_008_docs_entrypoints.py` chạy trên entrypoint thật, không mock, không import hàm nội bộ thay cho CLI; theo khuôn `tests/e2e/test_007_viewer_entrypoint.py` (`subprocess`, `sys.executable`, `PROJECT_ROOT`). Docstring tiếng Việt nêu truy vết AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · INV-001 · INV-004. Kịch bản: (1) chạy `python scripts/train.py --help`, `python -m mma_ai.evaluation.cli --help`, `python -m mma_ai.visualization.cli --help`, `python -m mma_ai.learning.benchmark --help` bằng tiến trình con, mã thoát 0; lệnh nào thiếu phụ thuộc nhóm `rl`/`eval` thì `pytest.skip` kèm lỗi nguyên văn, không báo đạt; (2) đếm đúng 4 lệnh nhanh trong `README.md` và trích mọi cờ `--[a-z][a-z0-9-]+` trong khối lệnh của `README.md`, `CONTRIBUTING.md`, `docs/guides/*.md`, khẳng định từng cờ xuất hiện trong đầu ra `--help` của lệnh tương ứng (INV-001); (3) `README.md` có đủ 10 mục `## `, `LICENSE` chứa dòng `Copyright (c) 2026 Dương Quan Bao`, `CHANGELOG.md` có `## [Unreleased]` và `## [0.1.0]`, `docs/guides` đúng ba tệp, `CONTRIBUTING.md` ≤ 100 dòng và mỗi guide ≤ 120 dòng; (4) mọi liên kết tương đối trong sáu tệp Markdown trỏ tới tệp tồn tại. Feature không có giao diện nên không có ảnh chụp màn hình. Không đổi `src/`, `scripts/`, `pyproject.toml`, CI, `deliverables/`. Hiện thực AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · INV-001 · INV-004 · SC-002 · SC-003 · SC-004 · SC-005 · SC-006. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py` thoát 0. | tests/e2e/test_008_docs_entrypoints.py | T801; T802 | qa | vừa |
| T803 | Reviewer độc lập (khác vai viết) đối chiếu, KHÔNG sửa tệp tài liệu: (a) chạy `uv run --isolated python scripts/train.py --help`, `uv run --isolated python -m mma_ai.evaluation.cli --help`, `uv run --isolated python -m mma_ai.visualization.cli --help`, `uv run --isolated python -m mma_ai.learning.benchmark --help`, ghi mã thoát và đầu ra; (b) trích mọi lệnh và cờ trong `README.md`, `CONTRIBUTING.md`, `docs/guides/*` (`grep -ohE -- '--[a-z][a-z0-9-]+'`) và so với `--help` của lệnh tương ứng và `_build_parser`; (c) đối chiếu bảng `contracts/cli-commands.md` (cờ, mã thoát) với mã; (d) chạy `tests/e2e/test_008_docs_entrypoints.py` của `T804`, đối chiếu kết quả (kể cả mục skip) rồi kiểm quickstart KB-1…KB-8: mục README đủ, đúng 4 lệnh, ba nhóm `rl`/`eval`/`dev` khớp `pyproject.toml`, không câu hứa Windows/macOS, `wc -l` (CONTRIBUTING ≤ 100, guide ≤ 120), UTF-8, 0 liên kết tương đối gãy, thân văn bản `LICENSE` là MIT chuẩn, `CHANGELOG.md` có `[Unreleased]` và `[0.1.0]` khớp `pyproject.toml`, `git diff --name-only` chỉ gồm vùng ghi của feature (kể cả `tests/e2e/test_008_docs_entrypoints.py`) và rỗng ở `src scripts pyproject.toml deliverables` cùng phần còn lại của `tests`; (e) làm theo Cài đặt + Bắt đầu nhanh trên môi trường sạch và ghi thời gian tới lệnh đầu tiên (không kể tải phụ thuộc; ngưỡng ≤ 10 phút) hoặc ghi CHƯA KIỂM. Ghi báo cáo `reviewer-docs-check.md` với bảng từng lệnh · lệnh trợ giúp đã chạy · khớp/lệch · môi trường; lệnh không chạy được (thiếu nhóm `rl`/`eval`, thiếu màn hình) ghi "CHƯA KIỂM" kèm lỗi nguyên văn, không ghi "đạt"; liệt kê số lệnh CHƯA KIỂM. Phát hiện lệch thì verdict `REQUEST_CHANGES` nêu tệp và dòng để vai `docs` sửa tài liệu — không sửa mã để khớp tài liệu. Không tin lời khai của báo cáo task. Hiện thực AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · FR-011 · FR-012 · NFR-DOC-001 · NFR-DOC-002 · NFR-DOC-003 · NFR-DOC-004 · INV-001 · INV-002 · INV-003 · INV-004 · SC-007 · SC-008. **Kiểm chứng**: tệp verdict tồn tại với dòng `APPROVE` hoặc `REQUEST_CHANGES`, và báo cáo `reviewer-docs-check.md` có bảng đối chiếu cho 100% lệnh. | evidence/reviews/T803.verdict; .ai/runs/*/reports/reviewer-docs-check.md | T801; T802; T804 | reviewer | vừa |

<a id="dependencies-va-wave"></a>
## Dependencies và wave

- Wave 1: `T801` (README + LICENSE + CONTRIBUTING; là chỗ gốc của lệnh nhanh, nhóm cài đặt, trạng thái nền tảng).
- Wave 2: `T802` (CHANGELOG + guides; trỏ về README nên sau `T801`).
- Wave 3: `T804` (qa; E2E trên bốn entrypoint thật, cần cả README, CONTRIBUTING và guides đã có).
- Wave 4: `T803` (reviewer cuối; phụ thuộc `T801`, `T802`, `T804`, cần cả bộ tài liệu và E2E mới đối chiếu được).
- DAG: `T801 → T802 → T804 → T803` (và `T801 → T804`, `T801 → T803`, `T802 → T803`); không vòng, không phụ thuộc chéo feature.
- Tự chốt: THÊM task `qa` `T804` để dập lint `NO_E2E` (`ai-sdlc check tasks`) theo chỉ dẫn sửa của kit — lý do: yêu cầu gốc nói không dùng QA và tối đa 3 task, nhưng chỉ dẫn lint mới hơn buộc có task `qa` sinh `tests/e2e/**` trên entrypoint thật; `T804` chỉ chạy `--help` của bốn lệnh và đối chiếu cờ trong tài liệu (không dựng giao diện, không đụng `src/`), nên giữ được tinh thần "không bịa tính năng". Đây là điểm lệch có chủ đích so với yêu cầu gốc; người duyệt có thể xoá `T804` nếu muốn giữ đúng 3 task (đổi lại, cảnh báo `NO_E2E` quay lại).
- Không có task đổi hành vi mà test của feature trước đang khẳng định ⇒ không cần task "cập nhật test cũ". Feature không có giao diện và không có bảng chuyển màn ⇒ `T804` không chụp màn hình (không cần `$AI_SDLC_CAPTURE_DIR`); E2E chỉ chạy entrypoint dòng lệnh thật.

<a id="dieu-kien-hoan-thanh"></a>
## Điều kiện hoàn thành

- `LICENSE`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/{training,evaluation,replay-demo}.md` có mặt, đúng khung `data-model.md` (SC-001…SC-006).
- `tests/e2e/test_008_docs_entrypoints.py` có mặt và xanh, hoặc skip có lý do nguyên văn (`T804`).
- `evidence/reviews/T803.verdict` là `APPROVE`; báo cáo đối chiếu nêu đủ 100% lệnh, 0 lệnh sai, số lệnh CHƯA KIỂM liệt kê rõ (SC-007).
- `git diff --name-only` của feature chỉ gồm vùng ghi đã nêu và tệp của chính feature (SC-008, INV-002).
- `ai-sdlc check docs .` và `ai-sdlc check tasks .` sạch.
