---
id: "MAP"
title: "Bản đồ dự án — phân hệ ↔ tài liệu ↔ vùng mã"
doc_type: guide
owner_agent: spec
status: draft
---

# Bản đồ dự án — phân hệ ↔ tài liệu ↔ vùng mã

MÁY sinh (bước `docs_indexed`) từ `specs/*`, thư mục phân hệ trong `docs/` và cột outputs/role của `tasks.md`. Sai thì sửa nguồn, không sửa tệp này.

| Phân hệ | Tài liệu | Thư mục chính | Vùng mã đầy đủ (outputs của tasks.md) | Vai |
|---|---|---|---|---|
| **001-m0-physics-benchmark** | `specs/001-m0-physics-benchmark/` | — | — | — |
| **002-elbow-muscle-env** | `specs/002-elbow-muscle-env/` | — | — | — |
| **003-ppo-train-repro** | `specs/003-ppo-train-repro/` | — | — | — |
| **004-eval-vs-random-plots** | `specs/004-eval-vs-random-plots/` | — | — | — |
| **005-replay-3d-muscle-demo** | `specs/005-replay-3d-muscle-demo/` · `docs/05-tracing/trace/005-replay-3d-muscle-demo.md` | `pyproject.toml` · `conftest.py` · `src/mma_ai/` · `tests/unit/` · `tests/integration/` · `tests/e2e/` · `tests/challenge/` · `evidence/reviews/` | `pyproject.toml` · `conftest.py` · `src/mma_ai/__init__.py` · `tests/unit/test_smoke_mma_ai.py` · `src/mma_ai/visualization/__init__.py` · `src/mma_ai/visualization/errors.py` · `src/mma_ai/visualization/replay_config.py` · `src/mma_ai/visualization/replay.yaml` · `tests/unit/test_replay_config.py` · `src/mma_ai/visualization/episode.py` · `tests/unit/test_episode.py` · `src/mma_ai/environment/single_agent.py` · `tests/unit/test_env_read_state.py` · `src/mma_ai/visualization/model_check.py` · `tests/unit/test_model_check.py` · `src/mma_ai/visualization/summary.py` · `tests/unit/test_summary.py` · `src/mma_ai/visualization/pacing.py` · `tests/unit/test_pacing.py` · `src/mma_ai/visualization/hud.py` · `tests/unit/test_hud.py` · `src/mma_ai/visualization/playback.py` · `tests/unit/test_playback.py` · `src/mma_ai/visualization/display.py` · `tests/unit/test_display.py` · `src/mma_ai/visualization/viewer.py` · `tests/unit/test_viewer.py` · `src/mma_ai/visualization/recorder.py` · `tests/unit/test_recorder.py` · `src/mma_ai/visualization/replay.py` · `tests/unit/test_run_replay.py` · `src/mma_ai/visualization/cli.py` · `tests/unit/test_script_exit.py` · `tests/integration/test_replay_headless.py` · `tests/integration/test_replay_nodisplay.py` · `tests/integration/test_replay_model_mismatch.py` · `tests/integration/test_replay_bad_input.py` · `tests/integration/test_demo_cli.py` · `tests/integration/test_replay_readonly.py` · `tests/integration/test_replay_viewer_real.py` · `tests/integration/test_visualization_imports.py` · `tests/integration/test_contract_examples_replay.py` · `tests/e2e/test_replay_acceptance.py` · `tests/challenge/test_replay_invariants.py` · `evidence/reviews/T522.challenge` · `evidence/reviews/T523.verdict` | builder, qa, challenger, reviewer |
