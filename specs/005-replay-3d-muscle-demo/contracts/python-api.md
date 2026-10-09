---
id: "API-005"
title: "M1 (4/4) — Hợp đồng API Python"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Hợp đồng — API Python của gói `mma_ai.visualization`

API mà `scripts/replay.py` và test gọi; con 3 có thể đọc tệp episode bằng `read_episode` nhưng không bắt buộc. Dạng dây của bản ghi: xem `*.schema.json` (không chép tên trường ở đây). Lệnh CLI và mã thoát: [cli.md](cli.md). `API-VIS-*` là mã hàm Python (không có HTTP).

## Hàm và lớp

| Mã | Ký hiệu | Mô-đun | Hợp đồng | FR |
|---|---|---|---|---|
| `API-VIS-0001` | `ReplayConfig.load(path=None, overrides=None) -> ReplayConfig` | `visualization.replay_config` | Đọc `src/mma_ai/visualization/replay.yaml` (cấu hình mặc định đóng gói; `--config PATH` để dùng tệp khác — xem plan.md, "Quyết định ở bước tasks") (khuôn [replay-config.schema.json](replay-config.schema.json)); ném `ReplayConfigError` nêu khoá/giá trị sai (hệ số tốc độ ≤ 0, thiếu khoá, `display_hz` ngoài [1,240]) | FR-006, FR-017 |
| `API-VIS-0002` | `read_episode(path) -> Episode` | `visualization.episode` | Đọc JSON, kiểm khuôn và nhất quán (độ dài chuỗi, `n_actions = số khung − 1`, `t_s` không giảm, 6 tên cơ khác nhau, giá trị hữu hạn, activation/excitation trong `[0,1]`, phiên bản được hỗ trợ); ném `EpisodeNotFound` / `EpisodeInvalid` nêu trường và lý do | FR-009, NFR-REL-001 |
| `API-VIS-0003` | `write_episode(episode, path) -> Path` | `visualization.episode` | Ghi nguyên tử (`.tmp` → kiểm hợp khuôn + hữu hạn → `os.replace`); từ chối khi `path` đã tồn tại; ném `EpisodeWriteError` | FR-007, FR-008, INV-003, INV-005 |
| `API-VIS-0004` | `record_episode(env, policy, *, split, target_index, seed, source) -> Episode` | `visualization.recorder` | Chạy MỘT episode: `reset(seed, options={"split", "target_index"})`; mỗi hành động `policy.act_deterministic(obs)`, kiểm `[0,1]^6` và hữu hạn *trước* `step`; sau mỗi bước đọc trạng thái bằng `env.read_state()` (chỉ đọc); ghi khung; `PhysicsInstabilityError` ⇒ episode `end_reason="abnormal"` và ném `DemoUnstable` sau khi đã đóng gói phần đã chạy | FR-002, FR-003, INV-002 |
| `API-VIS-0005` | `check_model(episode, model_info) -> ModelCheck` | `visualization.model_check` | So SHA-256 XML, `nq`, `nv`, số cơ, `muscle_names` (theo thứ tự) với mô hình hiện tại; `ModelCheck{match, compatible, episode_sha256, current_sha256, reasons[]}`; `enforce(check, allow_mismatch)` ném `ModelMismatch` theo INV-001 | FR-012, INV-001 |
| `API-VIS-0006` | `summarize_episode(episode, model_check, *, source, saved_episode=None, playback=None, warnings=()) -> dict` | `visualization.summary` | Dựng tóm tắt theo [replay-summary.schema.json](replay-summary.schema.json): số khung/hành động, thời lượng, mục tiêu, kết quả, activation nhỏ nhất/lớn nhất/trung bình/cuối từng cơ; từ chối NaN/Infinity | FR-010, NFR-REL-001 |
| `API-VIS-0007` | `Pacer(clock=time.perf_counter, sleep=time.sleep)` · `frame_at(episode, t_sim_s) -> Frame` | `visualization.pacing` | `Pacer.run(duration_sim_s, speed, display_hz, on_tick) -> PlaybackStats{wall_s, sim_s, ratio, frames_late}`; đồng hồ tiêm vào để test tất định; `frame_at` nội suy tuyến tính `qpos`, `activation` giữa hai khung liền kề (khung đầu/cuối giữ nguyên; episode một khung không chia cho 0) | FR-006, NFR-PERF-001 |
| `API-VIS-0008` | `display_available() -> DisplayStatus` | `visualization.display` | `glfw.init()` trong tiến trình (nhập lười); `DisplayStatus{available, reason}`; không treo, không crash khi không có màn hình | FR-011, NFR-HEADLESS-001 |
| `API-VIS-0009` | `FrameSink` (giao diện: `show(frame, hud)` · `is_open() -> bool` · `close()`) · `play(episode, cfg, sink, pacer) -> PlaybackStats` | `visualization.playback` | `play` đi qua các khung theo nhịp `Pacer`, đưa `Frame` + `Hud` (6 cặp tên–giá trị activation, cảnh báo lệch mô hình) vào `sink`; dừng khi `sink.is_open()` sai; lặp nếu `cfg.loop`; không import `mujoco.viewer` | FR-001, FR-004…FR-006 |
| `API-VIS-0010` | `ViewerSink(model, data, cfg)` | `visualization.viewer` | `FrameSink` bọc `mujoco.viewer.launch_passive`: đặt trạng thái + `mj_forward`, vẽ mục tiêu bằng `user_scn`, HUD bằng `set_texts`, `sync`; chỉ mô-đun này nhập `mujoco.viewer` | FR-001, FR-004, FR-005 |
| `API-VIS-0011` | `run_replay(args) -> int` | `visualization.replay` | Điều phối đúng thứ tự ở `cli.md`, trả mã thoát (không tự `os._exit`); ánh xạ ngoại lệ → mã thoát | FR-001, FR-002, FR-010…FR-014 |
| `API-VIS-0012` | `hud_lines(activation, muscle_names, cfg, warning=None) -> list[str]` | `visualization.hud` | Sinh dòng chữ HUD (tên cơ, giá trị làm tròn `decimals` chữ số, thanh); làm tròn chỉ ở đây (INV-006) | FR-005, INV-006 |

## Quy tắc xuyên suốt

- `visualization.*` chỉ ĐỌC checkpoint, hồ sơ và nhật ký của con 2 và tệp episode nguồn; đầu ra duy nhất là tệp episode mới (INV-005). `visualization` không import `learning.trainer`/`learning.ppo` (chỉ `learning.checkpoint`, nhập lười, chỉ ở `recorder`), kiểm bằng `test_visualization_has_no_training_imports`.
- Đường `--episode`/`--headless` không nhập `torch`, `glfw` hay `mujoco.viewer` (`test_episode_path_does_not_import_torch`, `test_headless_never_imports_viewer`).
- `recorder` không ghi vào `MjData` của môi trường và không truy cập thuộc tính riêng của nó; mọi trạng thái đọc qua `env.read_state()` (research Q6); không hàm nào có đường điều khiển lực, góc khớp hay toạ độ tay (INV-002).
- Lỗi hiển thị cho người dùng bằng tiếng Việt, nêu giá trị/ngữ cảnh.
