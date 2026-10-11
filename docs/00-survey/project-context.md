---
id: "SURVEY-CONTEXT-DOCS01"
title: "Ngữ cảnh dự án mma_ai"
doc_type: survey
owner_agent: surveyor
status: draft
updated: "2026-10-12"
---

# Ngữ cảnh dự án mma_ai

- [Lệnh](#lenh)
- [Cấu trúc](#cau-truc)
- [Bất biến](#bat-bien)
- [Bẫy](#bay)
- [Cổng](#cong)
- [Đọc tiếp](#doc-tiep)


<a id="lenh"></a>
## Lệnh

- `[đo: worktree sạch HEAD 629550d]` Bốn điểm vào `scripts/train.py`, `mma_ai.evaluation.cli`, `mma_ai.visualization.cli`, `mma_ai.learning.benchmark` đều nhận `--help` và thoát 0 qua `uv run --isolated python`.
- `[đo: worktree sạch HEAD 629550d]` `uv run --isolated --with pytest pytest -q -p no:cacheprovider --ignore=tests/e2e` thoát 0: 1272 passed, 116 skipped, 11 xfailed.
- `[đo: worktree sạch HEAD 629550d]` `uv run --isolated --with ruff ruff check .` và `uv run --isolated python -m compileall -q src tests scripts` thoát 0.
- `[đo: worktree sạch HEAD 629550d]` `uv run --isolated --with mypy mypy --strict .` thoát 1 tại `tests/challenge/test_env_invariants.py:582`; không đưa vào cổng đề xuất.

<a id="cau-truc"></a>
## Cấu trúc

- `pyproject.toml:5-31` khai gói Python 3.11–3.12 và các nhóm `rl`, `eval`, `dev`; Hatch đóng `src/mma_ai` tại `pyproject.toml:34-46`.
- `docs/MAP.md:16-20` nối spec với các phân hệ physics, environment, learning, monitoring, evaluation, visualization; `scripts/train.py:3-9` là wrapper huấn luyện.

<a id="bat-bien"></a>
## Bất biến

- Đánh giá kiểm tập huấn luyện/kiểm thử không giao trước rollout (`src/mma_ai/evaluation/runner.py:329-339`; `src/mma_ai/evaluation/split_guard.py:470-513`).
- Phát lại chỉ nhận một trong `--episode` và `--checkpoint` (`src/mma_ai/visualization/replay.py:219-235`); viewer thiếu màn hình trả 7 (`src/mma_ai/visualization/replay.py:451-458`).
- Benchmark cần `--repeats` tối thiểu 5 (`src/mma_ai/learning/benchmark.py:446-450`).

<a id="bay"></a>
## Bẫy

- `resource` nhập vô điều kiện; RAM đỉnh chia 1024 theo Linux (`src/mma_ai/learning/resources.py:8,77-79`).
- `dev` chỉ gồm pytest/jsonschema (`pyproject.toml:29-32`), nên lệnh Ruff/mypy cần cài qua `uv run --with`.
- `scripts/check_env.py` chưa có `[đo: git ls-files scripts/check_env.py` trả 0 dòng]`; tình trạng Windows/macOS nằm ở `specs/006-cross-platform-support/spec.md:54-58`.

<a id="cong"></a>
## Cổng

- Cổng đã đo thoát 0 trong worktree sạch: pytest, Ruff và compileall ở mục Lệnh.
- Mypy strict hiện đỏ tại `tests/challenge/test_env_invariants.py:582`; không đưa vào `.ai/stack-proposal.yml` cho tới khi sửa trong task được phép.

<a id="doc-tiep"></a>
## Đọc tiếp

- Điểm neo, phạm vi ảnh hưởng (blast radius), hành vi và rủi ro của bộ tài liệu: `docs/00-survey/mma-ai-project-docs.md`.
- Các neo kỹ thuật đa nền tảng được cập nhật ở `docs/00-survey/mma-ai-cross-platform.md`; chỉ đề xuất ghép tệp này vào `AGENTS.md`, không tự sửa cấu hình người dùng.
