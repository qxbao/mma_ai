---
id: "SURVEY-CONTEXT-CP01"
title: "Ngữ cảnh dự án mma_ai"
doc_type: survey
owner_agent: surveyor
status: draft
updated: "2026-10-11"
---

# Ngữ cảnh dự án mma_ai

## Lệnh

- [đo: worktree HEAD `ff7b568`] `uv run --isolated --with pytest pytest -q -p no:cacheprovider --ignore=tests/e2e` được chạy trong worktree mới không có `.venv`; kết quả hoàn tất được ghi trong báo cáo survey.
- Cổng ứng viên lint/typecheck/build được chạy cùng worktree: Ruff, mypy strict và `python -m compileall -q src tests`; chỉ cổng thoát 0 được đưa vào đề xuất stack.

## Cấu trúc

- Gói Python nguồn ở `src/mma_ai`; các bounded context (ngữ cảnh giới hạn) là physics, environment, learning, monitoring, evaluation, visualization (`docs/MAP.md:15`).
- `pyproject.toml:5` khai Python 3.11–3.12; Hatch đóng gói YAML theo package tại `pyproject.toml:34`.

## Bất biến

- Writer checkpoint/manifest/episode dùng temp, `fsync`, rồi `os.replace` (`src/mma_ai/learning/checkpoint.py:338`, `src/mma_ai/learning/manifest.py:502`, `src/mma_ai/visualization/episode.py:713`).
- Viewer train chỉ nạp `mujoco.viewer` sau guard display (`src/mma_ai/monitoring/viewer3d.py:86`).

## Bẫy

- `resource` nhập vô điều kiện và phép chia RAM chỉ phù hợp Linux (`src/mma_ai/learning/resources.py:8`, `src/mma_ai/learning/resources.py:77`).
- Display hiện suy ra qua DISPLAY/WAYLAND ở viewer và benchmark (`src/mma_ai/monitoring/viewer3d.py:48`, `src/mma_ai/learning/benchmark.py:146`).
- `xfail(strict=False)` còn che vấn đề POSIX/path (`tests/challenge/test_env_invariants.py:230`, `tests/challenge/test_train_invariants.py:783`).

## Cổng

- Pytest chỉ có marker display hiện hữu (`pyproject.toml:48`); chưa có `.github/**` hay `scripts/check_env.py` [đo: `find .github scripts -type f`].
- Ghi/đọc UTF-8 xuất hiện rõ ở episode (`src/mma_ai/visualization/episode.py:661`, `src/mma_ai/visualization/episode.py:715`).

## Đọc tiếp

- Xem điểm neo, phạm vi ảnh hưởng (blast radius), hành vi và nợ đa nền tảng tại `docs/00-survey/mma-ai-cross-platform.md`.
