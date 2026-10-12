---
id: "SURVEY-CONTEXT-DOCS01"
title: "Ngữ cảnh dự án mma_ai sau gộp 006–009"
doc_type: survey
owner_agent: surveyor
status: draft
updated: "2026-10-13"
---

# Ngữ cảnh dự án mma_ai sau gộp 006–009

- [Lệnh](#lenh)
- [Cấu trúc](#cau-truc)
- [Bất biến](#bat-bien)
- [Bẫy](#bay)
- [Cổng](#cong)
- [Đọc tiếp](#doc-tiep)

<a id="lenh"></a>
## Lệnh

- Đo lượt T8304693 trong cây làm việc tách biệt (worktree) mới `/tmp/fighterl-survey-T8304693-head`, HEAD `b82d69067510ceba011c75f11f006de5f18d8e32`; ban đầu không `.venv`/`node_modules` [đo: kiểm hai thư mục và `git rev-parse HEAD`; báo cáo cổng dưới].
- `uv run --isolated --with pytest --with pytest-xdist pytest -q -p no:cacheprovider -n auto --ignore=tests/e2e`: exit 0, 1626 passed/117 skipped/11 xfailed; loại năng lực 1/1753 [đo: lệnh trên; báo cáo cổng dưới].
- `uv run --isolated --with ruff ruff check .`, `uv build`, `uv run --isolated python -m mma_ai.compat.env_report`: exit 0 [đo: từng lệnh trên HEAD]. Env_report cảnh báo thiếu torch, không chứng minh huấn luyện đã chạy.
- Trợ giúp `--help` train/evaluate/replay/benchmark với đủ phụ thuộc tùy chọn (extras) thoát 0 trong worktree; không có căn cứ đổi lệnh của ba guides cũ [đo: `help-*.log` theo báo cáo cổng].
- `uv run --isolated --extra dev --extra rl --extra eval --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e`: exit 0, 55 passed, loại 0/55; E2E tài liệu 008 riêng có 24 passed [đo: lệnh và báo cáo cổng T8304693].

<a id="cau-truc"></a>
## Cấu trúc

- Python 3.11–3.12, Hatch đóng gói `src/mma_ai`; nhóm phụ thuộc (dependency) rl/eval/dev và nhóm công cụ dev riêng (`pyproject.toml:9`, `pyproject.toml:20`, `pyproject.toml:34`, `pyproject.toml:101`).
- Các phân hệ physics, environment, learning, evaluation, visualization, monitoring chia theo trách nhiệm; compat dùng chung (`docs/MAP.md:20`, `src/mma_ai/learning/resources.py:13`). Physics nhập lỗi environment, không áp tầng một chiều (`src/mma_ai/physics/simulator.py:18`).

<a id="bat-bien"></a>
## Bất biến

- Đánh giá kiểm chia tập trước rollout (chạy tập phim) (`src/mma_ai/evaluation/runner.py:330`). Replay chọn đúng một trong episode/checkpoint (`src/mma_ai/visualization/replay.py:223`).
- INV-002 tài liệu dựa lịch sử git: giữ nguyên thân và marker requires_git_history (`tests/e2e/test_008_docs_entrypoints.py:118`). Guide mới không được đổi GUIDES lịch sử vì dùng trong allowed (`tests/e2e/test_008_docs_entrypoints.py:123`).
- Mã đã gộp khác bằng chứng chạy: Linux đã kiểm; Windows/macOS/CUDA/CI thật chưa kiểm (QA `.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md:55`, dòng 62, 66, 71, 73).

<a id="bay"></a>
## Bẫy

- `os.tested` suy theo cấu hình, không phải hồ sơ QA native (máy chạy hệ điều hành thật); Windows/macOS có thể True (`src/mma_ai/compat/platform_info.py:106`, `src/mma_ai/compat/platform_info.py:119`).
- Thêm platforms.md chạm assert đúng ba guides (`tests/e2e/test_008_docs_entrypoints.py:249`), ngoài assert câu README cũ (`tests/e2e/test_008_docs_entrypoints.py:150`).
- Mypy strict nháp đỏ tại `tests/challenge/test_env_invariants.py:585` [đo: `uv run --isolated --with mypy mypy --strict .` exit 1]; chưa chứng minh AC-3 xanh.
- GitNexus chậm HEAD 93 commit [đo: query/context/impact]; xác nhận neo bằng git grep và dòng mã. Helper viewer còn phụ thuộc POSIX (`tests/e2e/test_007_viewer_entrypoint.py:57`).

<a id="cong"></a>
## Cổng

- `.ai/stack-proposal.yml` chỉ khai tests/lint/build/e2e/app_smoke exit 0 đo trong lượt T8304693; bỏ preset do nhập chéo các phân hệ (`src/mma_ai/physics/simulator.py:18`). Typecheck đỏ, chưa chứng nhận `ai-sdlc verify --branch ai-sdlc/integration` hoặc risk_coverage [đo: báo cáo cổng T8304693].
- Kết quả, lệnh đỏ và giới hạn môi trường ở [báo cáo cổng T8304693](../../.ai/runs/spec/reports/surveyor-gates-T8304693.md). Reviewer độc lập duyệt tài liệu mới theo phân vai (`specs/008-project-docs/tasks.md:78`).

<a id="doc-tiep"></a>
## Đọc tiếp

- [Khảo sát tài liệu](mma-ai-project-docs.md) và [khảo sát đa nền tảng](mma-ai-cross-platform.md) có điểm neo, phạm vi ảnh hưởng (blast radius), hành vi và nợ.
- Chỉ đề xuất ghép ngữ cảnh này vào AGENTS.md; không tự sửa cấu hình người dùng (quy định synthesize-project-context, đã đọc trong lượt).
