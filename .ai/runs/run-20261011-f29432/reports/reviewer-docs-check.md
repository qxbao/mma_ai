---
id: REPORT-REVIEWER-DOCS-CHECK
title: Báo cáo đối chiếu tài liệu 008-project-docs (T803)
doc_type: report
owner_agent: reviewer
status: active
updated: "2026-10-12"
---

# Báo cáo đối chiếu tài liệu 008-project-docs (T803)

Diff được chấm: `4ca4dfe7634d..a67e83c559d9` (head `a67e83c559d96c9e5a5c3cbff054659f6f9d3d85`). Verdict: `APPROVE` (0 CRITICAL, 3 MINOR, 2 OPTIONAL) tại `evidence/reviews/T803.verdict`. Số lệnh CHƯA KIỂM: **0 lệnh trợ giúp**; 1 hành trình (NFR-DOC-002, mục e) CHƯA KIỂM.

## Chuỗi suy luận

1. Spec 008 yêu cầu mọi lệnh/cờ trong tài liệu khớp `--help` thật (INV-001). Vì vậy tôi chạy `--help` của cả 4 CLI trong môi trường `uv run --isolated`, gom cờ thật, rồi quét cờ `--xxx` trong 6 tệp Markdown và so từng tệp.
2. Cờ lạ chỉ là `--extra`, `--isolated`, `--with`, `--strict`: đều là cờ của `uv`/`mypy`, không phải của CLI sản phẩm. Kết luận: 0 cờ không tồn tại trong tài liệu.
3. Với mã thoát, tôi đọc docstring/mã của `evaluation/cli.py:197`, `visualization/replay.py:18-20` (cộng các `return` 1/2/4/5/6/7/8) và đối chiếu bảng trong guide. Các mã khớp bảng `contracts/cli-commands.md`.
4. Nơi lưu checkpoint trong `training.md` bước 4 (`checkpoints/`, `latest.json`) khớp `learning/checkpoint.py:189,331,391`.
5. Mục (d) quickstart: đo trực tiếp (bảng dưới). Chạy `tests/e2e/test_008_docs_entrypoints.py` được 24 test pass, 0 skip, nên không có lệnh nào bị bỏ vì thiếu nhóm `rl`/`eval`.
6. INV-002: `git show --stat` cho thấy commit của T801 (d1665d9), T802 (98366d6), T804 (bfa5cbb, 04b6c83) chỉ chạm tệp trong vùng ghi của feature. Diff có `src/mma_ai/compat/*` nhưng đó là T601/T602/T605 của spec 006, không thuộc feature 008, nên không vi phạm INV-002.
7. Không có route/màn hình (CLI thuần), nên không có ảnh E2E để mở và không có cổng `route_coverage`; bằng chứng "app thật" là chính các lần chạy `--help` và E2E trên entrypoint thật ở trên.

## Bảng đối chiếu lệnh

| Lệnh trong tài liệu | Lệnh trợ giúp đã chạy | Kết quả | Môi trường |
|---|---|---|---|
| `python scripts/train.py --stage elbow --seed 42` (README, training.md) | `uv run --isolated python scripts/train.py --help` · exit 0 | KHỚP: `--stage --seed --config --total-steps --resume --runs-dir --ui {web,none} --ui-port --view3d` | uv isolated, Linux |
| `python -m mma_ai.evaluation.cli --checkpoint <ckpt>` (README, evaluation.md) | `uv run --isolated python -m mma_ai.evaluation.cli --help` · exit 0 | KHỚP: `--checkpoint` bắt buộc, `--config --out --repeats --eval-seed --runs-dir` | uv isolated, Linux |
| `python -m mma_ai.visualization.cli --episode <tệp>` / `--checkpoint <ckpt>` (README, replay-demo.md) | `uv run --isolated python -m mma_ai.visualization.cli --help` · exit 0 | KHỚP: `--episode --checkpoint --headless --save-episode --speed --loop --allow-model-mismatch --split --target-index --seed --config` | uv isolated, Linux |
| `python -m mma_ai.learning.benchmark --seed 42 --repeats 5` (README, training.md) | `uv run --isolated python -m mma_ai.learning.benchmark --help` · exit 0 | KHỚP: `--seed --repeats` có trong trợ giúp | uv isolated, Linux |
| `uv run --isolated --with pytest pytest -q` (README, CONTRIBUTING) | Không chạy lại (suite 1403 test thuộc cổng `tests`) | Cú pháp khớp D4; ghi nhận cổng `tests` GREEN ở `evidence/gates/T804.json` | — |
| `uv run --isolated --with ruff ruff check .` · `uv run --isolated --with mypy mypy --strict .` (CONTRIBUTING) | Không chạy lại; cổng `lint`/`typecheck` GREEN ở `evidence/gates/T804.json` | KHỚP lệnh cổng máy | — |
| `uv sync`, `uv sync --extra rl|eval|dev` (README) | Đối chiếu `pyproject.toml` `[project.optional-dependencies]` | KHỚP: đúng ba nhóm `rl`, `eval`, `dev` | — |

## Quickstart KB-1…KB-8

| Mục | Kết quả | Bằng chứng |
|---|---|---|
| KB-1 `LICENSE` | ĐẠT | `LICENSE:3` đúng một dòng `Copyright (c) 2026 Dương Quan Bao`; thân là văn bản MIT chuẩn |
| KB-2 README | ĐẠT | `grep -c '^## ' README.md` = 10; đúng 4 lệnh Bắt đầu nhanh; badge Python 3.11–3.12 khớp `requires-python = ">=3.11,<3.13"` |
| KB-3 nền tảng | ĐẠT | `README.md` mục Tình trạng nền tảng: nhắm Linux/WSL2, Windows/macOS "đang triển khai" theo `specs/006-cross-platform-support/`, không hứa chạy được |
| KB-4 độ dài, UTF-8 | ĐẠT | CONTRIBUTING 21 dòng (≤ 100); guide 41/41/49 dòng (≤ 120); `file --mime-encoding` = utf-8 cho cả 7 tệp |
| KB-5 liên kết | ĐẠT | test `relative_links` pass cho 6 tệp Markdown; thư mục nêu trong README đều tồn tại |
| KB-6 CHANGELOG | ĐẠT | `CHANGELOG.md:5` `[Unreleased]`, `:7` `[0.1.0] - 2026-10-12`, khớp `version = "0.1.0"`; năm ý trỏ spec 001–005 hoặc `src/mma_ai/<phân hệ>` |
| KB-7 guide | ĐẠT | `docs/guides` đúng 3 tệp, có Điều kiện tiên quyết, Các bước, Lỗi thường gặp, liên kết `../../README.md` |
| KB-8 / mục (e) ≤ 10 phút | CHƯA KIỂM | Chưa chạy `uv sync` rồi 4 lệnh trên môi trường sạch; chỉ đo `--help` (vài giây mỗi lệnh). Lỗi nguyên văn: không có, đây là giới hạn phạm vi lượt |
| Phạm vi diff | ĐẠT | `git diff --name-only` rỗng ở `scripts`, `pyproject.toml`, `deliverables`; `src/` chỉ có `compat/*` của spec 006 |

## Bảng review theo nhóm AC / user story

| Nhóm | AC/INV | Kết luận | Ghi chú |
|---|---|---|---|
| US1 Giấy phép | AC-1, FR-001 | HIT | MIT chuẩn, một dòng bản quyền |
| US2 README | AC-2, INV-003, INV-004 | HIT | 10 mục, 4 lệnh, song ngữ, không hứa Windows/macOS; F-005 về câu "GPU không bắt buộc" chưa có nguồn |
| US3 CONTRIBUTING | AC-3 | HIT | 3 lệnh test/lint/mypy đúng D4; F-002: không test nào chạy các lệnh này |
| US4 CHANGELOG | AC-4 | HIT | Keep a Changelog, `0.1.0` khớp pyproject |
| US5 Guides | AC-5, INV-001 | HIT | Cờ và mã thoát khớp mã thật |
| Phạm vi | INV-002 | HIT có lưu ý | F-001: spec.md:234 cấm `tests/` nhưng tasks.md giao T804 |
| Mã tương thích (T601/T602/T605) | spec 006 | HIT có lưu ý | F-003 (comment kể lại), F-004 (`**extra_kwargs` nuốt tên sai); chưa nối vào CLI nào |

## Cách kiểm chứng lại

```sh
uv run --isolated python scripts/train.py --help
uv run --isolated python -m mma_ai.evaluation.cli --help
uv run --isolated python -m mma_ai.visualization.cli --help
uv run --isolated python -m mma_ai.learning.benchmark --help
uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py
grep -ohE -- '--[a-z][a-z0-9-]+' README.md CONTRIBUTING.md docs/guides/*.md | sort -u
```
