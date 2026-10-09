---
id: "API-003"
title: "M1 (2/4) — Hợp đồng API Python"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Hợp đồng — API Python của gói `mma_ai.learning` và `mma_ai.monitoring`

API Python mà con 3 (đánh giá) và con 4 (replay/demo) gọi, cộng các hàm nội bộ mà test dùng. Dạng dây của bản ghi: xem `*.schema.json` (không chép tên trường ở đây). Lệnh CLI và điểm HTTP: [cli.md](cli.md).

## Hàm và lớp

| Ký hiệu | Mô-đun | Hợp đồng | FR |
|---|---|---|---|
| `TrainConfig.load(path=None, overrides=None) -> TrainConfig` | `learning.train_config` | Đọc `configs/train_elbow.yaml` (khuôn [train-config.schema.json](train-config.schema.json)); ném `TrainConfigError` nêu khoá/giá trị sai (≤ 0, thiếu khoá, `batch_size > n_steps`, `ui.host` không loopback) | FR-018 |
| `ActorCritic(obs_dim, act_dim, cfg)` | `learning.networks` | `actor`/`critic` MLP theo `cfg.network` (mặc định 2×256); `act(obs, deterministic) -> (u, log_prob, value)` với `u = sigmoid(a) ∈ (0,1)^6` | FR-002, FR-005 |
| `RunningNorm` | `learning.normalizer` | `update(batch)`, `__call__(obs)`, `state_dict()/load_state_dict()` | FR-003 |
| `PPOAgent(model, cfg)` | `learning.ppo` | `collect/compute_gae/update(buffer) -> UpdateStats` (loss chính sách/giá trị/entropy, chuẩn gradient sau clipping); gradient clipping theo `max_grad_norm` | FR-002, FR-004 |
| `save_checkpoint(agent, run_dir, kind, ctx) -> CheckpointMeta` | `learning.checkpoint` | Ghi nguyên tử (`.tmp` → quét hữu hạn → `os.replace`), tên có chỉ số lượt, cập nhật `latest.json`; ném `NonFiniteError`/`CheckpointIOError`; meta theo [checkpoint-meta.schema.json](checkpoint-meta.schema.json) | FR-006, FR-007 |
| `load_checkpoint(path, for_training=False) -> LoadedCheckpoint` | `learning.checkpoint` | Nạp `weights_only=True`; kiểm đủ 6 thành phần, hình dạng mạng, `model_sha256`; ném `CheckpointError` nêu nguyên nhân; `for_training=True` từ chối khi hash XML khác | FR-008, FR-009 |
| `load_policy(path) -> Policy` | `learning.checkpoint` | Chỉ-đọc cho con 3/4: `Policy.act_deterministic(obs_raw) -> u` (đã áp bộ chuẩn hoá của checkpoint) | FR-008 |
| `create_run_dir(runs_dir, stage, seed) -> RunDir` | `learning.run_dir` | `os.mkdir` loại trừ; không ghi đè; ném `RunDirError` sau 100 lần trùng | FR-011, INV-001 |
| `build_manifest(...) / write_manifest(run_dir, manifest)` | `learning.manifest` | Dựng và ghi nguyên tử hồ sơ theo [run-manifest.schema.json](run-manifest.schema.json); từ chối NaN/Inf | FR-011, FR-012 |
| `compare_runs(run_a, run_b) -> ReproReport` | `learning.repro` | So `head_mean_return` K điểm đầu theo `rel_tolerance` của hồ sơ; chỉ so khi cùng loại thiết bị/phiên bản thư viện/số luồng, nếu không trả `comparable=False` kèm lý do | FR-014 |
| `Trainer(cfg, env, run_dir).run() -> RunResult` | `learning.trainer` | Vòng thu mẫu → GAE → cập nhật; quét NaN/Inf; ghi TensorBoard/`metrics.jsonl`/`progress.json`; checkpoint định kỳ + `final`; dùng `make_env(split="train")` | FR-001, FR-010, FR-016, FR-017 |
| `ProgressWriter.write(snapshot)` | `learning.progress` | Ghi `progress.json` nguyên tử, tối đa mỗi `snapshot_interval_s`; cắt `history` ở `history_points` | FR-020 |
| `serve(run_dir, host, port) -> Server` | `monitoring.dashboard` | `http.server` loopback đọc-chỉ (xem [cli.md](cli.md)); không import `trainer`/`ppo` | FR-020, FR-021 |
| `View3D(run_dir).run()` | `monitoring.viewer3d` | Tiến trình riêng; đọc `latest.json`, nạp policy, chạy episode trên bản sao môi trường; thiếu `DISPLAY` ⇒ in "3D không khả dụng" và thoát 0 | FR-022 |

## Quy tắc xuyên suốt

- Hành động chuyển cho môi trường LUÔN là `sigmoid(a)` (INV-002); `Trainer` không có đường nào ghi lực, góc khớp hay toạ độ tay.
- `Trainer` chỉ lấy mục tiêu từ môi trường tạo bằng `split="train"` (INV-003); test khẳng định `info["target_split"] == "train"` ở mọi `reset` trong lúc train.
- `monitoring.*` chỉ đọc tệp trong thư mục run và không import `learning.trainer`/`learning.ppo` (INV-005; `test_monitoring_has_no_training_imports`).
- Lỗi hiển thị cho người dùng bằng tiếng Việt, nêu giá trị/ngữ cảnh (lượt, đại lượng, thành phần thiếu).
