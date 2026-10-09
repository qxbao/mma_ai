---
id: "TASKS-005"
title: "M1 (4/4) — Nhiệm vụ (Tasks): replay 3D và demo khuỷu tay do cơ điều khiển"
doc_type: tasks
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Nhiệm vụ: M1 (4/4) — Replay 3D và demo khuỷu tay do cơ điều khiển

- [Đầu vào](#dau-vao)
- [Quy ước task](#quy-uoc-task)
  - [Phụ thuộc chéo feature (khoảng trống đã biết)](#phu-thuoc-cheo-feature-khoang-trong-da-biet)
- [Setup](#setup)
- [Foundational](#foundational)
- [User story US1 — phát lại 3D một episode đã lưu (P1, MVP)](#user-story-us1-phat-lai-3d-mot-episode-da-luu-p1-mvp)
- [User story US2 — demo: chạy policy từ checkpoint (P1)](#user-story-us2-demo-chay-policy-tu-checkpoint-p1)
- [User story US3 — thấy và ghi 6 activation theo thời gian (P1)](#user-story-us3-thay-va-ghi-6-activation-theo-thoi-gian-p1)
- [User story US4 — episode tự đủ để phát lại đúng mô hình (P1)](#user-story-us4-episode-tu-du-de-phat-lai-dung-mo-hinh-p1)
- [User story US5 — máy không có màn hình (P2)](#user-story-us5-may-khong-co-man-hinh-p2)
- [User story US6 — lệch mô hình thì cảnh báo, không phát sai ngầm (P2)](#user-story-us6-lech-mo-hinh-thi-canh-bao-khong-phat-sai-ngam-p2)
- [User story US7 — nguồn không dùng được thì báo lỗi, mã thoát khác 0 (P2)](#user-story-us7-nguon-khong-dung-duoc-thi-bao-loi-ma-thoat-khac-0-p2)
- [QA và review độc lập](#qa-va-review-doc-lap)
  - [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Dependencies và wave](#dependencies-va-wave)
- [Điều kiện hoàn thành](#dieu-kien-hoan-thanh)

> Đích: `specs/005-replay-3d-muscle-demo/tasks.md`. Sinh từ `spec.md` + `plan.md` + `data-model.md` + `contracts/` HIỆN TẠI (viết lại hoàn toàn ở lượt này).

<a id="dau-vao"></a>
## Đầu vào

- `spec.md` (FR-001…FR-019 · NFR-PERF/HEADLESS/REPRO/REL-001 · INV-001…006 · AC-1…AC-5), `plan.md`, `research.md`, `data-model.md`.
- Hợp đồng: `contracts/cli.md` (`CMD-VIS-0001`, mã thoát), `contracts/python-api.md` (`API-VIS-0001`…`API-VIS-0012`), `contracts/episode.schema.json`, `contracts/replay-summary.schema.json`, `contracts/replay-config.schema.json`, `contracts/examples/`.
- Ghi chú đo của plan: mọi con số "ĐÃ ĐO" nằm ở `research.md`; task không tự đặt ngưỡng FPS (spec Clarifications; master plan XI.10).

<a id="quy-uoc-task"></a>
## Quy ước task

- **Dải mã `T501`…**: id task duy nhất toàn dự án; 005 dùng dải `T5xx` để không va với `tasks.md` của 001–004 (chưa được sinh). Mô tả task KHÔNG viết id task của feature khác (xem "Phụ thuộc chéo feature" bên dưới).
- **Test cùng task với mã** (test-first trong task): mỗi task mô-đun liệt kê tệp test trong `outputs`; builder viết test ĐỎ trước rồi mã cho xanh (hiến chương II), không `skip`/`xfail`. Test tích hợp chạy qua entrypoint CLI `python -m mma_ai.visualization.cli` (thật, subprocess) đứng SAU task CLI (T515).
- **Lệnh chung**: dựng môi trường `uv sync --extra dev --extra rl`; chạy test `uv run python -m pytest -q <tệp>`. Không thêm phụ thuộc, `pyproject.toml` KHÔNG đổi (plan, research Q10).
- **Mọi test không phải `test_replay_viewer_real` chạy với `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt**; một test viewer thật rẽ nhánh theo `display_available()` (plan, research Q9).
- **Một chủ một tệp**: không hai task cùng ghi một tệp; tệp dùng chung của 001–003 (`single_agent.py`, `test_unimplemented_cli.py`) mỗi tệp một task chủ của 005, đứng sau task chủ cũ; `test_unimplemented_cli.py` được cập nhật CÙNG task thay stub (T515) để cổng `tests` không đỏ.

<a id="phu-thuoc-cheo-feature-khoang-trong-da-biet"></a>
### Phụ thuộc chéo feature (khoảng trống đã biết)

001–004 mới có spec + plan, CHƯA có `tasks.md` nên chưa có id task để khai ở cột `depends_on`. Khi các `tasks.md` đó được sinh, bước converge/`plan_fix` PHẢI thêm `depends_on` vào đúng các task sau của 005:

- task sửa `src/mma_ai/environment/single_agent.py` (accessor `read_state()`, `options["target_index"]`) đứng sau task chủ `single_agent.py` của `002-elbow-muscle-env`;
- task tương lai thay stub `scripts/replay.py` + sửa `tests/integration/test_unimplemented_cli.py` (cùng task; hiện CHƯA CÓ CHỦ vì `scripts/**` ngoài vùng ghi của mọi vai — plan.md, "Quyết định ở bước tasks") đứng sau `T515` và sau task tạo stub/tệp test đó của `001-m0-physics-benchmark` (tuần tự với task cùng tệp test của `003-ppo-train-repro`, `004-eval-vs-random-plots`);
- task `recorder` đứng sau task `load_policy` / `load_checkpoint` của `003-ppo-train-repro`;
- task dựng khung đầu tiên (`pyproject.toml`, `conftest.py`) đứng sau (hoặc nhường cho) task dựng khung của `001-m0-physics-benchmark` — một chủ một tệp.

<a id="setup"></a>
## Setup

- [ ] T501 Khung dự án tối thiểu (manifest, `conftest.py`, test khói) nếu repo chưa có — pyproject.toml, conftest.py, src/mma_ai/__init__.py
- [ ] T502 Dựng gói con `visualization` và các lớp lỗi — src/mma_ai/visualization/__init__.py, errors.py

<a id="foundational"></a>
## Foundational

**Mục tiêu**: các mô-đun thuần dữ liệu mà mọi story dùng — cấu hình, định dạng episode, accessor đọc trạng thái, kiểm mô hình.

- [ ] T503 Cấu hình replay một tệp — src/mma_ai/visualization/replay_config.py, replay.yaml
- [ ] T504 Định dạng episode (đọc/ghi nguyên tử/kiểm R1–R7) — src/mma_ai/visualization/episode.py
- [ ] T505 [P] Accessor đọc-chỉ `read_state()` ở môi trường của 002 — src/mma_ai/environment/single_agent.py
- [ ] T506 Kiểm lệch mô hình — src/mma_ai/visualization/model_check.py

<a id="user-story-us1-phat-lai-3d-mot-episode-da-luu-p1-mvp"></a>
## User story US1 — phát lại 3D một episode đã lưu (P1, MVP)

**Mục tiêu**: `--episode <path>` mở MuJoCo Viewer, phát đúng thứ tự khung, thoát mã 0 (AC-1, KQ-1); entrypoint hiện là `python -m mma_ai.visualization.cli`, sẽ là `python scripts/replay.py` khi vỏ script có chủ.

**Kiểm thử độc lập**: `RecordingSink` kiểm thứ tự khung ở mọi môi trường; viewer thật ở máy có màn hình (T519).

- [ ] T508 [P] [US1] Bộ lập nhịp thời gian thực và nội suy khung — src/mma_ai/visualization/pacing.py
- [ ] T510 [US1] Vòng phát `play` + giao diện `FrameSink` — src/mma_ai/visualization/playback.py
- [ ] T512 [US1] `ViewerSink` bọc `launch_passive` — src/mma_ai/visualization/viewer.py
- [ ] T514 [US1] Điều phối `run_replay` và ánh xạ ngoại lệ → mã thoát — src/mma_ai/visualization/replay.py
- [ ] T515 [US1] CLI mỏng `cli.py` (`main`) + `os._exit` có điều kiện — src/mma_ai/visualization/cli.py
- [ ] T519 [US1] Test viewer thật rẽ nhánh theo môi trường — tests/integration/test_replay_viewer_real.py

<a id="user-story-us2-demo-chay-policy-tu-checkpoint-p1"></a>
## User story US2 — demo: chạy policy từ checkpoint (P1)

**Mục tiêu**: `--checkpoint <path>` chạy MỘT episode bằng policy trên môi trường của 002, chỉ qua kích thích cơ `u ∈ [0,1]^6`, rồi phát bằng đúng đường phát của replay (AC-2, KQ-2).

- [ ] T513 [US2] Bộ ghi episode `record_episode` — src/mma_ai/visualization/recorder.py
- [ ] T518 [US2] Test demo và chỉ-đọc qua CLI — tests/integration/test_demo_cli.py, test_replay_readonly.py

<a id="user-story-us3-thay-va-ghi-6-activation-theo-thoi-gian-p1"></a>
## User story US3 — thấy và ghi 6 activation theo thời gian (P1)

**Mục tiêu**: bảng 6 activation có tên cơ trong viewer và trong tóm tắt (AC-1, AC-2, AC-3, KQ-4).

- [ ] T509 [P] [US3] HUD tên cơ + giá trị + thanh — src/mma_ai/visualization/hud.py
- [ ] T507 [US3] Tóm tắt không màn hình `summarize_episode` — src/mma_ai/visualization/summary.py

<a id="user-story-us4-episode-tu-du-de-phat-lai-dung-mo-hinh-p1"></a>
## User story US4 — episode tự đủ để phát lại đúng mô hình (P1)

**Mục tiêu**: hợp đồng dữ liệu của con 4 (AC-1, AC-4) — thực hiện ở T504; kiểm hợp đồng schema ở:

- [ ] T520 [US4] Test import sạch và ví dụ hợp schema — tests/integration/test_visualization_imports.py, test_contract_examples_replay.py

<a id="user-story-us5-may-khong-co-man-hinh-p2"></a>
## User story US5 — máy không có màn hình (P2)

**Mục tiêu**: không treo; báo lỗi rõ hoặc `--headless` (AC-3, KQ-3).

- [ ] T511 [P] [US5] Kiểm màn hình khả dụng trước khi mở viewer — src/mma_ai/visualization/display.py
- [ ] T516 [US5] Test `--headless` và không màn hình qua CLI — tests/integration/test_replay_headless.py, test_replay_nodisplay.py

<a id="user-story-us6-lech-mo-hinh-thi-canh-bao-khong-phat-sai-ngam-p2"></a>
## User story US6 — lệch mô hình thì cảnh báo, không phát sai ngầm (P2)

**Mục tiêu**: AC-4 — logic ở T506; kiểm qua CLI cùng nhóm US7:

- [ ] T517 [US6] Test lệch mô hình và đầu vào hỏng qua CLI — tests/integration/test_replay_model_mismatch.py, test_replay_bad_input.py

<a id="user-story-us7-nguon-khong-dung-duoc-thi-bao-loi-ma-thoat-khac-0-p2"></a>
## User story US7 — nguồn không dùng được thì báo lỗi, mã thoát khác 0 (P2)

**Mục tiêu**: AC-5 — logic ở T504, T514; kiểm ở T517.

<a id="qa-va-review-doc-lap"></a>
## QA và review độc lập

- [ ] T521 QA: E2E AC-1…AC-5 trên entrypoint thật `python -m mma_ai.visualization.cli` — tests/e2e/test_replay_acceptance.py
- [ ] T522 Challenger: dựng vector đánh sập INV-001…INV-005 — tests/challenge/test_replay_invariants.py, evidence/reviews/T522.challenge
- [ ] T523 Reviewer: đối chiếu bằng chứng, ghi verdict — evidence/reviews/T523.verdict

<a id="quyet-dinh-ve-vai-challenger"></a>
### Quyết định về vai `challenger`

**CÓ DÙNG** vai `challenger` (task T522): spec khai sáu bất biến `INV-*` mà đầu vào người dùng chạm được — chuỗi hash/cấu trúc mô hình (INV-001), hành động policy ngoài `[0,1]^6` hoặc NaN (INV-002), episode thiếu trường/NaN/Infinity (INV-003), đường ghi/ngắt giữa chừng (INV-004), ghi đè tệp có sẵn (INV-005). Đó đúng là loại bất biến property/fuzz đánh sập được mà không cần màn hình. Cổng review qua khi reviewer VÀ challenger cùng duyệt (nhất trí hai vai độc lập). Chi phí: thêm một lượt; chấp nhận vì lỗi "phát sai ngầm" là thứ feature này tồn tại để chặn.

<a id="dependencies-va-wave"></a>
## Dependencies và wave

| id | mô tả | outputs | depends_on | role | độ khó |
|---|---|---|---|---|---|
| T501 | Khung dự án (walking skeleton) cho gói `mma_ai` nếu repo CHƯA có (hiện repo chưa có manifest): `pyproject.toml` với Python `>=3.11,<3.13`, bố cục `src/`, phụ thuộc kế thừa 001–003 và KHÔNG thêm mới (`mujoco==3.15.0`, `myo-sim==0.2.3`, `gymnasium>=1.4,<1.5`, `numpy`, `pyyaml`; extra `rl`: `torch`; extra `dev`: `pytest`, `jsonschema`), `conftest.py` đặt `DISPLAY`/`WAYLAND_DISPLAY` bỏ đặt cho mọi test trừ khi test tự bật, `src/mma_ai/__init__.py`, package data cho `src/mma_ai/visualization/*.yaml`, và một test khói. Nếu 001-m0-physics-benchmark đã giao các tệp này thì GIỮ NGUYÊN nội dung của họ và chỉ bổ sung phần còn thiếu — một chủ một tệp, không tạo phụ thuộc mới. Produces: môi trường `uv sync --extra dev --extra rl` chạy được, `uv run python -m pytest -q tests/unit/test_smoke_mma_ai.py` xanh. Hiện thực FR-015 (tiến trình riêng, không phụ thuộc huấn luyện) · FR-019. | pyproject.toml; conftest.py; src/mma_ai/__init__.py; tests/unit/test_smoke_mma_ai.py | | builder | vừa |
| T502 | Dựng gói `mma_ai.visualization`: `__init__.py` (rỗng ngoài docstring tiếng Việt, KHÔNG nhập `mujoco.viewer`, `glfw`, `torch`, `learning.trainer`, `learning.ppo`) và `errors.py` với `ReplayConfigError`, `EpisodeNotFound`, `EpisodeInvalid`, `EpisodeWriteError`, `CheckpointUnusable`, `ModelMismatch`, `DisplayUnavailable`, `DemoUnstable` (cùng lớp cha `ReplayError` mang thuộc tính `exit_code` theo bảng mã thoát ở `contracts/cli.md`: 2, 5, 5, 8, 4, 6, 7, 1). Produces: các lớp lỗi mà T503…T514 ném/bắt. Hiện thực FR-013 · FR-018 · INV-004. Kiểm chứng: `uv run python -c "import mma_ai.visualization.errors as e; assert e.ModelMismatch.exit_code == 6"` thoát 0. | src/mma_ai/visualization/__init__.py; src/mma_ai/visualization/errors.py | T501 | builder | dễ |
| T503 | `ReplayConfig.load(path=None, overrides=None) -> ReplayConfig` (`API-VIS-0001`) đọc cấu hình mặc định đóng gói `src/mma_ai/visualization/replay.yaml` (hoặc tệp người dùng qua tham số `path`) theo `contracts/replay-config.schema.json`: `playback.{speed, loop, display_hz, hold_after_end_s}`, `demo.{split, target_index, seed}`, `hud.{decimals, bar_width}`, `target_marker.{radius_m, rgba}`; ném `ReplayConfigError` nêu khoá/giá trị sai (speed ≤ 0, thiếu khoá, `display_hz` ngoài [1,240]); `overrides` ghi đè khoá cùng tên cho cờ dòng lệnh. Mặc định phải nạp được từ gói đã cài (khai package data cho `*.yaml` ở T501). Viết `tests/unit/test_replay_config.py` ĐỎ trước (`test_defaults_load`, `test_invalid_values_raise`) rồi mã. Hiện thực FR-006 · FR-017 · API-VIS-0001. Produces: `ReplayConfig` cho T508–T514. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_replay_config.py`. | src/mma_ai/visualization/replay_config.py; src/mma_ai/visualization/replay.yaml; tests/unit/test_replay_config.py | T502 | builder | vừa |
| T504 | `Episode`/`Frame`, `read_episode(path) -> Episode` (`API-VIS-0002`) và `write_episode(episode, path) -> Path` (`API-VIS-0003`) theo `contracts/episode.schema.json` + luật R1–R7 của `data-model.md`: `n_actions = số khung − 1`, `t_s` không giảm, `qpos`/`qvel` đúng chiều, khung 0 `excitation = null`, 6 tên cơ khác nhau, `end_reason` nhất quán, mọi số hữu hạn (`allow_nan=False` khi ghi; `parse_constant` từ chối `NaN`/`Infinity` khi đọc), activation/excitation trong `[0,1]`, phiên bản định dạng lạ bị từ chối nêu hai phiên bản; ghi nguyên tử (`.tmp` → kiểm khuôn + hữu hạn → `os.replace`), từ chối khi đích đã tồn tại (`EpisodeWriteError`), tệp tạm bị xoá khi ngắt; đường dẫn tương đối. Viết `tests/unit/test_episode.py` ĐỎ trước: `test_write_read_roundtrip_and_schema`, `test_required_provenance_fields`, `test_refuse_overwrite`, `test_atomic_write_no_partial`, `test_n_actions_matches_frames`, `test_time_monotonic`, `test_state_dims_match_model`, `test_first_frame_has_no_action`, `test_muscle_names_unique`, `test_outcome_consistent`, `test_nonfinite_rejected`. Hiện thực FR-007 · FR-008 · FR-009 · INV-003 · INV-005 · NFR-REL-001 · API-VIS-0002 · API-VIS-0003. Produces: `Episode`, `Frame` cho T506…T514. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_episode.py`. | src/mma_ai/visualization/episode.py; tests/unit/test_episode.py | T502 | builder | khó |
| T505 | Thêm accessor đọc-chỉ `ElbowReachEnv.read_state()` trả bản sao `qpos`, `qvel`, `act`, `fingertip_position_m`, `target_position_m`, `time_s` (và cùng task đó bảo đảm `reset(seed, options={"split", "target_index"})` nhận `target_index` nếu task của 004 chưa giao — một chủ một tệp) mà KHÔNG đổi hành vi mặc định của `reset`/`step`/reward. Viết `tests/unit/test_env_read_state.py` ĐỎ trước: bản sao (sửa kết quả không đổi `MjData`), không đổi quỹ đạo khi gọi thêm `read_state()` giữa các `step`. Consumes: môi trường của `002-elbow-muscle-env` (D-2 của plan). Hiện thực FR-002 · FR-003 · INV-002 (đường đọc không ghi vào mô phỏng). Kiểm chứng: `uv run python -m pytest -q tests/unit/test_env_read_state.py tests/unit` không test cũ nào đỏ. | src/mma_ai/environment/single_agent.py; tests/unit/test_env_read_state.py | T501 | builder | khó |
| T506 | `check_model(episode, model_info) -> ModelCheck{match, compatible, episode_sha256, current_sha256, reasons[]}` và `enforce(check, allow_mismatch)` (`API-VIS-0005`): so SHA-256 XML, `nq`, `nv`, số cơ, `muscle_names` theo thứ tự; hash lệch + cấu trúc tương thích + `allow_mismatch=True` ⇒ tiếp tục (kèm cảnh báo); hash lệch không cờ hoặc cấu trúc không tương thích (kể cả có cờ) ⇒ `ModelMismatch` nêu cả hai hash hoặc số khớp/số cơ mong đợi và thực có. Viết `tests/unit/test_model_check.py` ĐỎ trước (`test_hash_and_structure_cases`). Consumes: `MuscleModelInfo` của `001-m0-physics-benchmark` (SHA-256, tên cơ, `nq`, `nv`). Hiện thực FR-012 · INV-001 · API-VIS-0005. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_model_check.py`. | src/mma_ai/visualization/model_check.py; tests/unit/test_model_check.py | T502; T504 | builder | vừa |
| T507 | `summarize_episode(episode, model_check, *, source, saved_episode=None, playback=None, warnings=()) -> dict` (`API-VIS-0006`) theo `contracts/replay-summary.schema.json`: số khung/hành động, thời lượng mô phỏng (episode một khung ⇒ 0 s, không chia cho 0), mục tiêu, seed, kết quả, hai hash + `model_match`, activation nhỏ nhất/lớn nhất/trung bình/cuối từng cơ (không làm tròn — INV-006), cảnh báo; từ chối NaN/Infinity; đường dẫn tương đối. Viết `tests/unit/test_summary.py` ĐỎ trước: `test_activation_stats_match_hand_values`, `test_paths_relative`. Hiện thực FR-010 · FR-018 · INV-006 · NFR-REL-001 · API-VIS-0006. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_summary.py`. | src/mma_ai/visualization/summary.py; tests/unit/test_summary.py | T504; T506 | builder | vừa |
| T508 | `Pacer(clock=time.perf_counter, sleep=time.sleep)` với `run(duration_sim_s, speed, display_hz, on_tick) -> PlaybackStats{wall_s, sim_s, ratio, frames_late}` và `frame_at(episode, t_sim_s) -> Frame` (`API-VIS-0007`): đồng hồ tiêm vào để test tất định; nội suy tuyến tính `qpos`, `activation` giữa hai khung liền kề (khung đầu/cuối giữ nguyên, episode một khung không chia cho 0); khung trễ được ĐẾM và báo, KHÔNG bỏ âm thầm. Viết `tests/unit/test_pacing.py` ĐỎ trước: `test_ratio_within_5pct_at_speed_1` (tỷ lệ ∈ [0,95 ; 1,05] trên episode 0,2–4 s, đồng hồ giả), `test_late_frames_reported_not_dropped`, `test_single_frame_episode_no_zero_division`, `test_loop_repeats_until_sink_closed`. Hiện thực FR-006 · NFR-PERF-001 · API-VIS-0007. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_pacing.py`. | src/mma_ai/visualization/pacing.py; tests/unit/test_pacing.py | T502; T503; T504 | builder | khó |
| T509 | `hud_lines(activation, muscle_names, cfg, warning=None) -> list[str]` (`API-VIS-0012`): 6 dòng "tên cơ + giá trị làm tròn `hud.decimals` chữ số + thanh `hud.bar_width`" cộng dòng cảnh báo "MÔ HÌNH LỆCH" khi có; làm tròn CHỈ ở đây, không đổi dữ liệu. Viết `tests/unit/test_hud.py` ĐỎ trước (`test_rounding_only_in_display`, tên cơ khớp `muscle_names`). Hiện thực FR-005 · INV-006 · API-VIS-0012. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_hud.py`. | src/mma_ai/visualization/hud.py; tests/unit/test_hud.py | T503 | builder | dễ |
| T510 | Giao diện `FrameSink` (`show(frame, hud)` · `is_open()` · `close()`) và `play(episode, cfg, sink, pacer) -> PlaybackStats` (`API-VIS-0009`): đi qua các khung theo nhịp `Pacer`, đưa `Frame` + `Hud` (6 cặp tên–giá trị activation lấy đúng từ `Frame`, cảnh báo lệch mô hình liên tục) vào `sink`; mục tiêu đúng vị trí đã ghi; dừng khi `sink.is_open()` sai; lặp nếu `cfg.loop`; giữ khung cuối tới khi sink đóng; KHÔNG nhập `mujoco.viewer`. Consumes: `Episode`/`Frame` (T504), `Pacer`/`frame_at` (T508), `hud_lines` (T509), `ReplayConfig` (T503). Viết `tests/unit/test_playback.py` ĐỎ trước với `RecordingSink`: `test_frames_in_recorded_order`, `test_target_marker_at_recorded_position`, `test_hud_shows_recorded_activation_each_frame`, `test_hud_names_match_muscle_names`. Hiện thực FR-001 · FR-004 · FR-005 · FR-006 · INV-001 (cảnh báo luôn hiện) · INV-006 · API-VIS-0009. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_playback.py`. | src/mma_ai/visualization/playback.py; tests/unit/test_playback.py | T503; T504; T508; T509 | builder | khó |
| T511 | `display_available() -> DisplayStatus{available, reason}` (`API-VIS-0008`): `glfw.init()` trong tiến trình (nhập lười), không treo/không crash khi `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt hoặc `DISPLAY` hỏng; `reason` tiếng Việt. Viết `tests/unit/test_display.py` ĐỎ trước (`test_unavailable_reports_reason_without_crash`, chạy với biến hiển thị bỏ đặt và với `DISPLAY` giả hỏng). Hiện thực FR-011 · NFR-HEADLESS-001 · API-VIS-0008. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_display.py`. | src/mma_ai/visualization/display.py; tests/unit/test_display.py | T502 | builder | vừa |
| T512 | `ViewerSink(model, data, cfg)` (`API-VIS-0010`) hiện thực `FrameSink` bằng `mujoco.viewer.launch_passive`: đặt `qpos`/`act` của khung + `mj_forward` (replay chỉ đặt trạng thái đã ghi để vẽ, KHÔNG chạy điều khiển), vẽ mục tiêu bằng hình cầu ở `user_scn` tách rõ khỏi thân khuỷu, HUD bằng `set_texts`, `sync`; chỉ mô-đun này nhập `mujoco.viewer` (nhập lười trong `__init__` của `ViewerSink`). Consumes: `FrameSink` (T510), `ReplayConfig.target_marker` (T503). Viết `tests/unit/test_viewer.py` ĐỎ trước: nhập mô-đun không cần màn hình, `ViewerSink` đủ phương thức của `FrameSink`. Hiện thực FR-001 · FR-004 · FR-005 · INV-002 · API-VIS-0010. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_viewer.py`. | src/mma_ai/visualization/viewer.py; tests/unit/test_viewer.py | T503; T510 | builder | vừa |
| T513 | `record_episode(env, policy, *, split, target_index, seed, source) -> Episode` (`API-VIS-0004`): `reset(seed, options={"split", "target_index"})`; mỗi hành động chỉ qua `policy.act_deterministic(obs)`, kiểm hữu hạn và `[0,1]^6` NGAY TRƯỚC `env.step` (vi phạm ⇒ chặn tại biên, episode `abnormal`, không gọi `step` với giá trị sai); sau mỗi bước đọc trạng thái bằng `env.read_state()` (chỉ đọc, không ghi `MjData`, không truy cập thuộc tính riêng); `PhysicsInstabilityError` ⇒ đóng gói phần đã chạy `end_reason="abnormal"` rồi ném `DemoUnstable`; `source` = tên + hash nội dung checkpoint hoặc `null`; nhập `learning.checkpoint` lười, KHÔNG nhập `learning.trainer`/`learning.ppo`. Consumes: `read_state()` (T505), `Episode`/`Frame` (T504), `DemoUnstable` (T502); policy của `003-ppo-train-repro` qua giao diện `act_deterministic`. Viết `tests/unit/test_recorder.py` ĐỎ trước với mô hình MuJoCo thật và policy kịch bản: `test_actions_checked_before_step`, `test_recorder_never_writes_env_state`, hành động NaN/ngoài biên, chọn mục tiêu theo chỉ số. Hiện thực FR-002 · FR-003 · FR-016 · INV-002 · NFR-REPRO-001 · API-VIS-0004. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_recorder.py`. | src/mma_ai/visualization/recorder.py; tests/unit/test_recorder.py | T502; T504; T505 | builder | khó |
| T514 | `run_replay(args) -> int` (`API-VIS-0011`, `CMD-VIS-0001`; hợp đồng `API-005` ở `contracts/python-api.md`) điều phối ĐÚNG thứ tự của `contracts/cli.md`: (1) tham số + cấu hình (đúng một trong `--episode`/`--checkpoint`; `--split/--target-index/--seed` chỉ với `--checkpoint`; `--save-episode` chỉ với `--checkpoint`; `--speed` > 0; chỉ số mục tiêu trong phạm vi) ⇒ mã 2; (2) nạp nguồn ⇒ mã 5/4 (checkpoint kiểm hash XML mô hình); (3) `check_model` + `enforce` ⇒ mã 6; (4) không `--headless`: `display_available()` ⇒ mã 7 trong ≤ 5 s; (5) demo: `record_episode`; (6) `--save-episode` ghi nguyên tử TRƯỚC khi mở cửa sổ (đường dẫn tồn tại ⇒ mã 8, không ghi đè); (7) `--headless`: in tóm tắt JSON ra stdout, thông báo ra stderr, không nhập `glfw`/`mujoco.viewer`/`torch` cho `--episode`; ngược lại mở `ViewerSink` và `play`, in thời lượng mô phỏng + gợi ý `--speed 0.1`/`--loop` khi episode < 1 s, in dòng tóm tắt tiếng Việt cuối phiên (thời lượng mô phỏng, thời gian thực, tỷ lệ, khung trễ). Ngắt Ctrl-C ⇒ xoá tệp tạm, mã 130. Trả mã thoát, KHÔNG tự `os._exit`. Mọi lỗi tiếng Việt nêu giá trị/ngữ cảnh. Consumes: T502 (lỗi), T503 (cấu hình), T504 (`read_episode`/`write_episode`), T506 (`check_model`/`enforce`), T507 (`summarize_episode`), T510 (`play`), T511 (`display_available`), T512 (`ViewerSink`), T513 (`record_episode`). Viết `tests/unit/test_run_replay.py` ĐỎ trước cho ánh xạ lỗi → mã (thiếu/có cả hai chế độ ⇒ 2, đường dẫn không tồn tại ⇒ 5, tốc độ ≤ 0 ⇒ 2) và thứ tự (lỗi tham số TRƯỚC mọi ghi đĩa/mở cửa sổ). Hiện thực FR-001 · FR-002 · FR-008 · FR-010 · FR-011 · FR-012 · FR-013 · FR-016 · FR-018 · INV-001 · INV-004 · INV-005 · API-VIS-0011 · CMD-VIS-0001. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_run_replay.py`. | src/mma_ai/visualization/replay.py; tests/unit/test_run_replay.py | T503; T504; T506; T507; T510; T511; T512; T513 | builder | khó |
| T515 | CLI mỏng `src/mma_ai/visualization/cli.py` với `main(argv=None)`: nạp tham số (`--episode/--checkpoint/--headless/--save-episode/--speed/--loop/--allow-model-mismatch/--split/--target-index/--seed/--config`), gọi `run_replay`, xả stdout/stderr rồi `os._exit(mã)` CHỈ khi viewer đã mở (đóng handle trước) để mã thoát không phụ thuộc dọn dẹp đồ hoạ (MuJoCo Viewer làm tiến trình `SIGSEGV` lúc thoát); mọi đường không mở viewer thoát bình thường; chạy được bằng `python -m mma_ai.visualization.cli`. Đây là entrypoint thật của feature cho tới khi vỏ `scripts/replay.py` có chủ (khoảng trống năng lực — plan.md, "Quyết định ở bước tasks"): vỏ đó chỉ là `from mma_ai.visualization.cli import main; main()`, KHÔNG task nào của bảng này ghi được `scripts/**` nên không khai ở đây. Consumes: `run_replay` (T514). Viết `tests/unit/test_script_exit.py` ĐỎ trước: `test_os_exit_only_when_viewer_opened`, `test_exit_code_is_result_not_teardown` (`monkeypatch` chặn `os._exit`, gọi tên rõ). Hiện thực FR-014 · CMD-VIS-0001 · hợp đồng `CLI-005`. Kiểm chứng: `uv run python -m pytest -q tests/unit/test_script_exit.py` và `uv run python -m mma_ai.visualization.cli --episode khong-ton-tai.json` thoát mã 5. | src/mma_ai/visualization/cli.py; tests/unit/test_script_exit.py | T514 | builder | vừa |
| T516 | Test tích hợp qua entrypoint CLI `python -m mma_ai.visualization.cli` (subprocess), US5/AC-3: `test_replay_headless.py` (`test_summary_has_all_fields` hợp `replay-summary.schema.json` với đủ trường; `test_short_episode_hint_on_stderr`), `test_replay_nodisplay.py` (`test_no_display_exits_7_fast_with_hint` ≤ 5 s và gợi ý `--headless`; `test_headless_exit0_with_summary`; `test_bogus_display_handled_like_no_display`; chạy được khi thiếu thư viện hiển thị). Mọi tiến trình con chạy với `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt. Consumes: CLI từ T515. Hiện thực FR-010 · FR-011 · FR-006 · NFR-HEADLESS-001 · AC-3. Kiểm chứng: `uv run python -m pytest -q tests/integration/test_replay_headless.py tests/integration/test_replay_nodisplay.py`. | tests/integration/test_replay_headless.py; tests/integration/test_replay_nodisplay.py | T515 | builder | vừa |
| T517 | Test tích hợp qua CLI, US6 + US7/AC-4, AC-5: `test_replay_model_mismatch.py` (`test_mismatch_stops_names_both_hashes` mã 6 không viewer; `test_mismatch_allowed_warns_persistently` có `--allow-model-mismatch` ⇒ `model_match=false` trong tóm tắt; `test_incompatible_structure_always_refused` kể cả có cờ); `test_replay_bad_input.py` (`test_missing_episode_exit5`, `test_missing_checkpoint_exit4_no_viewer_no_file`, `test_corrupt_json_exit5_names_field`, `test_nonfinite_values_exit5`, `test_both_or_neither_mode_exit2`, `test_target_index_out_of_range_exit2`, `test_existing_save_path_exit8_not_overwritten`, `test_checkpoint_xml_hash_mismatch_exit4`, `test_interrupt_leaves_no_partial_episode` mã 130, `test_errors_are_vietnamese_with_context`). Hiện thực FR-009 · FR-012 · FR-013 · FR-016 · FR-018 · INV-001 · INV-004 · NFR-REL-001 · AC-4 · AC-5. Kiểm chứng: `uv run python -m pytest -q tests/integration/test_replay_model_mismatch.py tests/integration/test_replay_bad_input.py`. | tests/integration/test_replay_model_mismatch.py; tests/integration/test_replay_bad_input.py | T515 | builder | vừa |
| T518 | Test tích hợp qua CLI, US2/AC-2: `test_demo_cli.py` (`test_demo_saves_episode_headless` với `--checkpoint ... --headless --save-episode`; `test_demo_only_muscle_excitation_in_unit_interval` mọi hành động trong `[0,1]^6`; `test_demo_selects_requested_target` theo chỉ số tập kiểm thử; `test_demo_same_seed_same_episode` hai lần chạy lệch ≤ 1×10⁻⁶ và chuỗi hành động giống hệt; `test_no_file_written_without_save_flag`); `test_replay_readonly.py` (`test_run_files_unchanged_by_replay_and_demo` băm thư mục run trước/sau). Dùng mô hình MuJoCo thật và policy kịch bản/checkpoint ngắn; `monkeypatch` chỉ để tiêm lỗi ghi đĩa, gọi tên rõ. Hiện thực FR-002 · FR-003 · FR-008 · FR-016 · INV-002 · INV-005 · NFR-REPRO-001 · AC-2. Kiểm chứng: `uv run python -m pytest -q tests/integration/test_demo_cli.py tests/integration/test_replay_readonly.py`. | tests/integration/test_demo_cli.py; tests/integration/test_replay_readonly.py | T515; T513 | builder | vừa |
| T519 | Test viewer thật, AC-1/AC-2: `test_real_viewer_plays_or_reports_no_display` rẽ nhánh theo `display_available()` — có màn hình: `python -m mma_ai.visualization.cli --episode` mở viewer, phát đủ 100% khung, thoát mã 0 (FR-014); không màn hình: mã 7 + thông báo tiếng Việt; cả hai nhánh là khẳng định thật, KHÔNG `skip`/`xfail`. Consumes: CLI từ T515. Hiện thực FR-001 · FR-004 · FR-005 · FR-014 · AC-1 · AC-2. Kiểm chứng: `uv run python -m pytest -q tests/integration/test_replay_viewer_real.py`. | tests/integration/test_replay_viewer_real.py | T515 | builder | dễ |
| T520 | Test ràng buộc nhập và hợp đồng, US4: `test_visualization_imports.py` (`test_visualization_has_no_training_imports` — không `learning.trainer`/`learning.ppo`; `test_episode_path_does_not_import_torch`; `test_headless_never_imports_viewer`), `test_contract_examples_replay.py` (`test_examples_match_schemas` mọi tệp `contracts/examples/*` hợp schema tương ứng; `test_no_nonfinite_values`). Hiện thực FR-015 · FR-007 · INV-003 · NFR-REL-001 · AC-1 · AC-4. Kiểm chứng: `uv run python -m pytest -q tests/integration/test_visualization_imports.py tests/integration/test_contract_examples_replay.py`. | tests/integration/test_visualization_imports.py; tests/integration/test_contract_examples_replay.py | T514 | builder | dễ |
| T521 | E2E trên entrypoint thật `python -m mma_ai.visualization.cli` (subprocess, không tự dựng app): AC-1 episode hợp lệ phát/`--headless` mã 0 (viewer thật chỉ khi có `DISPLAY`, nhánh còn lại khẳng định mã 7); AC-2 `--checkpoint ... --headless --save-episode` sinh episode rồi `--episode` đọc lại được, activation 6 cơ có tên; AC-3 không `DISPLAY` ⇒ mã 7 ≤ 5 s và `--headless` mã 0; AC-4 sửa hash XML trong episode ⇒ mã 6 nêu hai hash; AC-5 đường dẫn không tồn tại ⇒ mã khác 0, không viewer, không tệp. Tên test: `test_ac_1_replay_episode`, `test_ac_2_demo_from_checkpoint`, `test_ac_3_no_display`, `test_ac_4_model_mismatch`, `test_ac_5_missing_path`. Cổng chạy bằng `uv run python -m pytest -q tests/e2e`. Hiện thực AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · FR-001 · FR-010 · FR-011 · FR-012 · FR-013 · SC-001…SC-006. Kiểm chứng: lệnh cổng trên xanh. | tests/e2e/test_replay_acceptance.py | T516; T517; T518; T519; T520 | qa | vừa |
| T522 | Challenger: dựng property/fuzz nhắm bất biến qua MỌI lối vào của CLI — INV-001 (đột biến hash/`nq`/`nv`/thứ tự tên cơ của episode ⇒ không bao giờ phát mà không dừng hoặc không cảnh báo; thử cờ `--allow-model-mismatch` với cấu trúc lệch), INV-002 (policy giả xuất NaN/Inf/âm/lớn hơn 1/sai số chiều ⇒ không bao giờ tới `env.step`), INV-003 (xoá/đổi kiểu từng trường bắt buộc, `NaN`/`Infinity`/`1e999`, tên cơ trùng/rỗng ⇒ luôn bị từ chối, không bao giờ ghi ra tệp có NaN), INV-004 (ngắt/ghi lỗi ở mọi bước ⇒ không tệp episode dở dang, không treo), INV-005 (đích ghi đã tồn tại, symlink, thư mục tổ tiên không ghi được ⇒ không ghi đè). Ghi verdict `evidence/reviews/T522.challenge` (kèm vector đã thử và đã bác). Ca đánh sập được đánh dấu `xfail` không strict kèm mã finding. Hiện thực INV-001 · INV-002 · INV-003 · INV-004 · INV-005. Kiểm chứng: `uv run python -m pytest -q tests/challenge`. | tests/challenge/test_replay_invariants.py; evidence/reviews/T522.challenge | T521 | challenger | khó |
| T523 | Reviewer: đối chiếu `spec.md`/`plan.md`/`tasks.md` với bằng chứng cổng (`evidence/gates/*`) và e2e, ghi verdict APPROVE hoặc REQUEST_CHANGES nêu AC-1…AC-5, INV-001…INV-006 và NFR đã được chứng minh bằng test chạy ngoài hay chưa; không tin lời khai của báo cáo task. | evidence/reviews/T523.verdict | T522 | reviewer | vừa |

> Không có cột `Wave` — wave do Kahn sinh ra từ `depends_on` + va chạm `outputs`.

<a id="dieu-kien-hoan-thanh"></a>
## Điều kiện hoàn thành

- Mọi task có artifact thật; `uv run python -m pytest -q` xanh, số test không giảm; không `skip`/`xfail` trừ ca của challenger.
- Mỗi AC-1…AC-5 có ít nhất một test mức entrypoint (CLI `python -m mma_ai.visualization.cli`; chuỗi `python scripts/replay.py` chờ vỏ script có chủ) — xem `docs/05-tracing/trace/005-replay-3d-muscle-demo.md`.
- Phần "viewer thật" (AC-1/AC-2 trên màn hình) chỉ chứng minh được ở máy có màn hình; WSL2/WSLg CHƯA KIỂM (spec Clarifications) — không mô tả là đã chạy khi chưa có bằng chứng.
- Không còn câu hỏi nghiệp vụ mở; mọi verdict chặn merge (reviewer VÀ challenger) đã được giải quyết.
