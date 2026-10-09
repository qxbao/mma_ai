---
id: "DM-002"
title: "M1 (1/4) — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Mô hình dữ liệu — M1 (1/4)

Không có cơ sở dữ liệu ⇒ không có bảng `TBL-*`, không có index; không có `EVT-*`, `CMD-*`/`QRY-*`/`API-*` mạng. Dữ liệu là các đối tượng trong bộ nhớ và **bản ghi JSON** theo `contracts/*.schema.json` (không chép lại tên trường ở đây — chỉ ghi luật và quan hệ).

## Thực thể → đối tượng / bản ghi

| Thực thể (spec) | Đối tượng | Khuôn dây | Người tạo | Người đọc |
|---|---|---|---|---|
| Môi trường khuỷu tay | `ElbowReachEnv` (không lưu) | — | `make_env` | con 2, 3, 4 |
| Mục tiêu | `Target` (nhúng trong `TargetSetPair`) | `$defs/target` trong [target-set.schema.json](contracts/target-set.schema.json) | `TargetGenerator` | env, con 3 |
| Tập mục tiêu | `TargetSetPair` (hai vai `train`, `test`) | [target-set.schema.json](contracts/target-set.schema.json) | `TargetGenerator.generate(seed)` | env, test, hồ sơ thí nghiệm |
| Cấu hình môi trường | `ElbowEnvConfig` | [env-config.schema.json](contracts/env-config.schema.json) | `ElbowEnvConfig.load` | mọi mô-đun `environment` |
| Hồ sơ mô hình | `ModelRecord` (dict) | [model-record.schema.json](contracts/model-record.schema.json) | `env.model_record()` | hồ sơ thí nghiệm (con 2, 3) |
| Info của reset / step | dict | [reset-info.schema.json](contracts/reset-info.schema.json), [step-info.schema.json](contracts/step-info.schema.json) | env | PPO, đánh giá, test |

## Thực thể: Target / TargetSetPair

| Trường | Kiểu | Luật hợp lệ |
|---|---|---|
| `index` | số nguyên ≥ 0 | duy nhất trong từng vai; là chỉ số `target_index` ở `reset` |
| `angle_rad` | số | thuộc `[jnt_lo + angle_margin_rad, jnt_hi − angle_margin_rad]` ⇒ với tới được (FR-010) |
| `position_m` | 3 số | = vị trí site `wrist` ở `angle_rad` (động học thuận trên `MjData` riêng) |
| `train`, `test` | danh sách `Target` | độ dài = `n_train`, `n_test`; không rỗng |
| `min_cross_distance_m` | số > 0 | đo Euclid 3D mọi cặp (train, test); MUST ≥ `min_separation_m` (INV-001) |
| `fingerprint_sha256` | hex 64 | băm `train+test` chuẩn hoá; hai lần sinh cùng seed MUST bằng nhau (INV-002, NFR-REPRO-001) |

Luật tách: cung khả dụng chia thành `n_blocks = ⌊L_khả_dụng / split_block_m⌋` khối; seed xáo trộn rồi gán khối cho `test` (⌈n_blocks · n_test/(n_train+n_test)⌉ khối, tối đa `n_blocks − 1`) và `train` (phần còn lại); mỗi khối thu hẹp `1,1 · min_separation_m / 2` ở hai biên (hệ số 1,1 bù chênh dây cung–cung). Bất khả thi (`split_block_m ≤ 1,1 · min_separation_m`, `n_blocks < 2`, kích thước ≤ 0) ⇒ `TargetConfigError`. Lý do và số đo: `research.md` Q3.

## Thực thể: Cấu hình môi trường

Khoá và ràng buộc ở [env-config.schema.json](contracts/env-config.schema.json); ràng buộc chéo mà schema không diễn đạt, kiểm bởi `ElbowEnvConfig.load`: `split_block_m > 1,1 · min_separation_m`; `tolerance_m` > 0 (khởi đầu 0,02 và bằng `min_separation_m` khởi đầu theo Tự chốt của spec, nhưng không buộc bằng nhau); `n_train`, `n_test` ≥ 1. Giá trị khởi đầu: ví dụ [examples/env-config.default.json](contracts/examples/env-config.default.json).

## Bố cục Observation (14 chiều, `float32`)

Nguồn chân lý của bố cục và cận: `research.md` Q4 (bảng chỉ số 0–13). Dây chỉ mang **chỉ số** trong vector; nhãn thành phần chỉ có ở tài liệu/ test. Test `test_layout_is_14_with_finite_bounds` đối chiếu `observation_space.shape == (14,)`, cận hữu hạn, và thứ tự với bảng.

### Ánh xạ chỉ số ↔ cơ (nhắc từ 001)

| Chỉ số trong action / `act` | Khoá (`muscle_names[i]`) |
|---|---|
| 0 | `TRIlong` |
| 1 | `TRIlat` |
| 2 | `TRImed` |
| 3 | `BIClong` |
| 4 | `BICshort` |
| 5 | `BRA` |

Bảng được đọc từ mô hình khi nạp (001 đã ghi ĐÃ ĐO) và so với danh sách này trong `test_elbow_env::test_loads_exactly_six_muscles`; lệch ⇒ không đạt, không tự đổi tên.

## Máy trạng thái của môi trường

```text
created ──reset()──▶ ready ──step()──▶ ready            (chưa kết thúc)
ready ──step() với d ≤ tolerance_m──▶ done(terminated, end_reason="reached")
ready ──step() với n_actions ≥ max_actions──▶ done(truncated, end_reason="max_actions")
done ──reset()──▶ ready
created | done ──step()──▶ EnvStateError
```

Khi cả hai điều kiện kết thúc cùng bước: `terminated=True`, `truncated=False`, `end_reason="reached"`.

## Bất biến liên quan (đã khai ở spec.md, chỉ tham chiếu mã)

INV-001 (train ∩ test = ∅ + khoảng cách tối thiểu) · INV-002 (tất định theo seed) · INV-003 (chỉ điều khiển bằng kích thích cơ) · INV-004 (observation đúng chiều, hữu hạn, trong cận).

## Cấu hình (đọc, không phải bản ghi báo cáo)

| Tệp | Khoá chính | Dùng bởi |
|---|---|---|
| `configs/elbow_env.yaml` | `physics_timestep_s`, `substeps_per_action`, `reward.*`, `tolerance_m`, `max_actions`, `obs.qvel_scale_rad_s`, `targets.*`, `target_split`, `fingertip_site` | `env_config` → toàn bộ gói `environment` |
| `configs/body.yaml` (001) | `model.source`, `model.expected_muscles` | `body_model` (001) |
