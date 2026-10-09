---
id: "API-002"
title: "M1 (1/4) — Hợp đồng API Python & định dạng bản ghi"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Hợp đồng — môi trường khuỷu tay (API Python)

Không có dịch vụ mạng; "hợp đồng dây" là (1) API Python dưới đây mà con 2 (PPO), con 3 (đánh giá), con 4 (replay) gọi, và (2) các bản ghi JSON có khuôn ở `*.schema.json` (JSON Schema draft 2020-12, ví dụ ở `examples/`, test: `test_contract_examples_m1`). Tên trường KHÔNG chép lại ở đây — xem schema.

## Hàm và lớp

| Ký hiệu | Mô-đun | Hợp đồng | FR |
|---|---|---|---|
| `ElbowEnvConfig.load(path=None) -> ElbowEnvConfig` | `mma_ai.environment.env_config` | Đọc `configs/elbow_env.yaml` (khuôn: [env-config.schema.json](env-config.schema.json)); ném `EnvConfigError` nêu khoá/giá trị sai | FR-014 |
| `TargetGenerator(model, cfg).generate(seed) -> TargetSetPair` | `mma_ai.environment.targets` | Cùng `seed` + cấu hình ⇒ cùng kết quả; giao rỗng + khoảng cách Euclid tối thiểu; ném `TargetConfigError` nếu cấu hình bất khả thi | FR-010, FR-011 |
| `TargetSetPair.to_dict() / from_dict(d)` | `mma_ai.environment.targets` | Dạng dây: [target-set.schema.json](target-set.schema.json) | FR-011 |
| `ElbowReachEnv(cfg=None, targets=None, split=None)` | `mma_ai.environment.single_agent` | `gymnasium.Env`; `action_space = Box(0,1,(6,))`, `observation_space = Box` 14 chiều cận hữu hạn; ném `ModelError` (001) nếu số cơ ≠ 6 hoặc có actuator không phải cơ | FR-001, FR-002 |
| `env.reset(seed=None, options={"split": "train"\|"test"})` | | Trả `(obs, info)`; `info` theo [reset-info.schema.json](reset-info.schema.json); `seed=None` ⇒ rút seed và ghi vào `info["seed"]` | FR-012 |
| `env.step(action)` | | Trả `(obs, reward, terminated, truncated, info)`; `info` theo [step-info.schema.json](step-info.schema.json); `ActivationError` (001) khi hành động sai; `PhysicsInstabilityError` khi NaN/Inf/cảnh báo vật lý; `EnvStateError` khi gọi trước `reset` hoặc sau khi episode kết thúc | FR-003, FR-004, FR-006, FR-009 |
| `env.model_record() -> dict` | | Hồ sơ mô hình theo [model-record.schema.json](model-record.schema.json) | FR-013 |
| `make_env(config_path=None, split="train") -> ElbowReachEnv` | `mma_ai.environment.single_agent` | Cách tạo môi trường chuẩn cho con 2–4 | FR-002 |
| `register_envs()` | `mma_ai.environment` | Đăng ký id `MmaElbowReach-v0` với Gymnasium | FR-002 |

## Quy tắc xuyên suốt

- Đường điều khiển duy nhất là `step(action)` với `action ∈ [0,1]^6`; không có phương thức công khai nào ghi lực, góc khớp hay toạ độ tay (INV-003).
- Giá trị không áp dụng ghi tường minh `null` (ví dụ `end_reason` khi episode chưa kết thúc), không bỏ trường.
- Đường dẫn trong bản ghi là tương đối/tên gói, không tuyệt đối (INV-003 của 001).
- Observation: thứ tự và cận 14 thành phần ghi ở `research.md` Q4 và `data-model.md`; test đối chiếu `observation_space` với bảng đó.
