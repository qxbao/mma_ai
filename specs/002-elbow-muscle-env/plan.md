---
id: "PLAN-002"
title: "M1 (1/4) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Implementation Plan: M1 (1/4) — Môi trường khuỷu tay điều khiển bằng cơ & tập mục tiêu train/test

- [Summary](#summary)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Phụ thuộc vào 001 (M0)](#phu-thuoc-vao-001-m0)
- [Kiến trúc & tách trách nhiệm](#kien-truc-tach-trach-nhiem)
  - [Quyết định thiết kế](#quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 002 thêm vào cây của 001](#source-code-repository-root-chi-phan-002-them-vao-cay-cua-001)
- [Lệnh build / test (cho task khung dựng đúng một lần)](#lenh-build-test-cho-task-khung-dung-dung-mot-lan)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Complexity Tracking](#complexity-tracking)


**Branch**: `002-elbow-muscle-env` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-elbow-muscle-env/spec.md` (bản hiện tại, REQ-0101)

<a id="summary"></a>
## Summary

Feature dựng **môi trường Gymnasium một agent** `ElbowReachEnv` (`single_agent.py`) bọc mô hình **MyoElbow 6 cơ** (`myo-sim==0.2.3`) chạy headless, chỉ điều khiển bằng kích thích cơ `u ∈ [0,1]^6`, cùng **bộ sinh mục tiêu** tách tập train/test theo seed với giao rỗng, và **quyết định phiên bản** `gymnasium`/`myosuite`. Đây là nền cho con 2 (PPO), con 3 (đánh giá), con 4 (replay/demo) của M1.

Cách tiếp cận kỹ thuật (chi tiết và số đo ở `research.md`): **bỏ MyoSuite**, dùng `myo-sim` + `mujoco` + `gymnasium>=1.4,<1.5` (MyoSuite 3.0.0 ghim `gymnasium<1.3` — không giải được cùng 1.4.0; Q1); **tái dùng** các mô-đun `physics` của 001 (nạp mô hình, kiểm tra vector kích hoạt, `HeadlessSimulator` chỉ ghi `ctrl`, quét NaN/Inf); mục tiêu là vị trí đầu mút tay (site `wrist`) ở một góc khớp hợp lệ nên luôn với tới được, tách train/test theo **khối cung** với khoảng cách tối thiểu (Q3); observation 14 chiều có cận hữu hạn đã khai báo (Q4); reward gồm hai thành phần có trọng số và kết thúc terminated/truncated (Q6); mọi tham số ở `configs/elbow_env.yaml` (FR-014). Không PPO, không replay, không đánh giá (Out of Scope).

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Python 3.11 (ghim `.python-version` và `requires-python = ">=3.11,<3.13"` của 001)

**Primary Dependencies**: `mujoco` (ĐÃ ĐO 3.15.0), `myo-sim==0.2.3` (ĐÃ ĐO), `gymnasium>=1.4,<1.5` (ĐÃ ĐO 1.4.0), `numpy` (ĐÃ ĐO 2.4.6), `pyyaml`; extra `dev`: `pytest`, `jsonschema`. **Không** `myosuite`, **không** `torch` (extra `gpu` của 001, `rl` của con 2).

**Storage**: tệp — cấu hình `configs/elbow_env.yaml`; bản ghi JSON (`TargetSet`, `ModelRecord`) theo `contracts/*.schema.json`; log kiểm chứng ở `logs/m1/`; không CSDL

**Testing**: `pytest` (`python -m pytest`); test hợp đồng bằng `jsonschema`; `gymnasium.utils.env_checker.check_env` làm một test; test chạy với `DISPLAY` bỏ đặt

**Target Platform**: Linux gốc / WSL2 Ubuntu (như 001); headless

**Project Type**: thư viện + CLI nghiên cứu (không web, không giao diện đồ hoạ)

**Performance Goals**: không có ngưỡng tốc độ trong spec; số thăm dò ≈ 9,1 nghìn hành động/s (một môi trường, CPU phát triển; research Q7) chỉ để tham khảo, không phải cam kết

**Constraints**: headless, không pixel observation; policy chỉ xuất `u_i ∈ [0,1]` (INV-003); không sửa XML mô hình; hằng số chỉ ở cấu hình (FR-014); không suy thời gian huấn luyện (master plan XI.10)

**Scale/Scope**: 1 mô hình (1 DoF, 6 cơ); ≈ 6 mô-đun mới trong `mma_ai.environment`; ≈ 10 tệp test; 1 tệp cấu hình; 1 script xác minh cài sạch

<a id="constitution-check"></a>
## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | AC-5 chứng minh bằng `scripts/verify_clean_install.py` (ghi mã thoát + đầu ra vào `logs/m1/`), không bằng khẳng định; AC-1…AC-4 bằng test chạy trên mô hình thật; quickstart nêu tên test |
| II. Test trước, sửa sau | Đạt | Mỗi mô-đun có test đặt tên sẵn trong bảng truy vết; task tạo test trước mã |
| III. Lát cắt nhỏ, một vai một task | Đạt | Mỗi mô-đun một trách nhiệm một tệp; không tệp nào chung chủ với 001 trừ `pyproject.toml` (xem Phụ thuộc) |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…INV-004 và NFR-REL/REPRO/HEADLESS/INST-001 khai ở `spec.md`; plan chỉ tham chiếu mã. Không có INV/NFR mới phát hiện ở bước plan |
| V. Không đổi cái không được yêu cầu | Đạt | Không `myosuite`, không `torch`, không mô-đun PPO/replay/đánh giá; không sửa XML; không thêm thực thể ngoài 5 Key Entities của spec |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; bản ghi JSON dùng đường dẫn tương đối/tên gói (kiểm bằng `test_repo_hygiene` của 001) |
| VII. Nhánh bảo vệ | Đạt | Lượt spec không commit, không đổi nhánh |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số đo trong `research.md` ghi nguồn "ĐÃ ĐO"/"CHƯA KIỂM"; số kiểm chứng sau này do script sinh |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Quyết định phiên bản CHỈ ở `research.md` Q1 (README/pyproject chỉ trỏ tới); hợp đồng/data model CHỈ ở `specs/002-…/`; `docs/` không có tệp chiến lược/chiến thuật để đồng bộ |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm dependency ngoài danh sách trên; không có vi phạm cần ghi ở Complexity Tracking.

<a id="phu-thuoc-vao-001-m0"></a>
## Phụ thuộc vào 001 (M0)

001 mới có spec + plan, **chưa có mã**. 002 dựa vào các phần sau theo đúng plan của 001 (`specs/001-m0-physics-benchmark/contracts/cli.md`, `data-model.md`):

| Thành phần của 001 | Dùng để | Ghi chú |
|---|---|---|
| `mma_ai.physics.body_model.load_muscle_model` · `MuscleModelInfo` (`n_muscles`, `n_non_muscle_actuators`, `sha256`, `muscle_names`, `joint_ranges_rad`) | FR-001, FR-013, INV-003 | 002 không nạp XML lần thứ hai |
| `mma_ai.physics.simulator.validate_activation` · `HeadlessSimulator` (chỉ ghi `data.ctrl`) · `StepReadout` (`ctrl_requested`, `ctrl_effective`) | FR-003, FR-004 | đường ghi ctrl duy nhất |
| `mma_ai.physics.numeric_health` | FR-006 | quét NaN/Inf + `data.warning` |
| `mma_ai.config` (đọc `configs/*.yaml`) · `pyproject.toml` · `.python-version` | FR-014, FR-016 | 002 thêm `configs/elbow_env.yaml` và một dòng dependency `gymnasium` vào `pyproject.toml` |
| `mma_ai.reporting.runlog.write_record` | ghi bản ghi JSON (từ chối NaN/Inf, đường dẫn tuyệt đối) | |

**Quy tắc thứ tự** (cho bước tasks): mọi task của 002 chạm mã đứng SAU task tương ứng của 001 (`depends_on`). Tệp chung duy nhất là `pyproject.toml` (thêm `gymnasium`): một task riêng của 002 phụ trách việc này, sau task khung của 001. Nếu `HeadlessSimulator` của 001 chưa cho đọc-chỉ `model`/`data` (research Q5), task của 002 thêm accessor đọc-chỉ vào đúng tệp đó sau task của 001 — không sao chép mã.

<a id="kien-truc-tach-trach-nhiem"></a>
## Kiến trúc & tách trách nhiệm

Phụ thuộc một chiều: `environment → physics (001) → config`. `physics` không import `environment`. Mô-đun mới (đều dưới `src/mma_ai/environment/`):

| Mô-đun | Trách nhiệm | FR / INV |
|---|---|---|
| `env_config` | `ElbowEnvConfig` (dataclass bất biến) đọc từ `configs/elbow_env.yaml`, kiểm khoá bắt buộc và ràng buộc (dương, `min_separation_m < split_block_m`, kích thước ≥ 1…); ném `EnvConfigError` | FR-014 |
| `errors` | `EnvConfigError`, `TargetConfigError`, `ObservationError`, `PhysicsInstabilityError`, `EnvStateError` (thông điệp tiếng Việt nêu giá trị/ ngữ cảnh) | FR-003, FR-006 |
| `targets` | `Target`, `TargetSet`, `TargetGenerator`: động học thuận trên `MjData` riêng, tách khối cung, lấy mẫu phân tầng theo seed, tự kiểm giao rỗng + khoảng cách; `to_dict/from_dict` theo `contracts/target-set.schema.json` | FR-010, FR-011, INV-001, INV-002 |
| `observation` | `ObservationLayout` (14 thành phần, cận), `build_observation`, `validate_observation`; chuẩn hoá từ hằng số suy ra từ mô hình | FR-005, FR-006, INV-004 |
| `reward` | `compute_reward(distance, action, cfg) -> RewardTerms` (hai thành phần + tổng), `is_reached` | FR-008, FR-009 |
| `single_agent` | `ElbowReachEnv(gymnasium.Env)`: `reset(seed, options={"split": ...})`, `step`, `observation_space`, `action_space`, `model_record()`; `make_env(config_path=None, split="train")`; đăng ký `MmaElbowReach-v0` | FR-002, FR-004, FR-012, FR-013 |

<a id="quyet-dinh-thiet-ke"></a>
### Quyết định thiết kế

- **Một đường điều khiển**: `ElbowReachEnv.step` chỉ gọi `validate_activation` rồi `HeadlessSimulator.step(u, n_steps=substeps)`; không có phương thức nào ghi `qpos/qvel/site_xpos/actuator_force` (INV-003). Động học thuận cho mục tiêu dùng `MjData` riêng, không bao giờ chạm `MjData` của episode.
- **Chọn nguồn mục tiêu**: cấu hình `target_split ∈ {train, test}` hoặc `reset(options={"split": "test"})`; mục tiêu chọn bằng `self.np_random.integers` trên đúng tập đó ⇒ không bao giờ bốc tập kia (INV-001). `reset` luôn trả `info` có `target_split`, `target_index`, `seed` thực dùng (kể cả khi gọi `reset(seed=None)`), `model_sha256` (FR-012, FR-013).
- **Trạng thái đầu cố định**: `mj_resetData` (góc 0, kích hoạt 0); ngẫu nhiên chỉ ở lựa chọn mục tiêu (INV-002).
- **Lỗi hiển thị cho người dùng** (tiếng Việt): thông điệp nêu giá trị vi phạm, số cơ/actuator tìm thấy, bước và đại lượng gây NaN.
- **Không mock physics**: test dùng mô hình thật (1 DoF, rất nhanh); `monkeypatch` chỉ dùng để tiêm NaN vào hàm quét và được gọi tên rõ.
- **Không tự viết validator an ninh/công cụ kiểm riêng** ngoài `validate_observation` và `validate_activation` theo spec; test assert thẳng trên sản phẩm.
- **Quyết định phiên bản** (AC-5): bỏ MyoSuite — chi tiết ở `research.md` Q1; `pyproject.toml` có chú thích một dòng trỏ tới `specs/002-elbow-muscle-env/research.md`; `test_dependency_decision` khẳng định `myosuite` không có trong `pyproject.toml`/`uv.lock` và `gymnasium` ≥ 1.4.

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/002-elbow-muscle-env/
├── plan.md
├── research.md          # Q1 = quyết định phiên bản gymnasium/myosuite (AC-5)
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── python-api.md
│   ├── env-config.schema.json
│   ├── model-record.schema.json
│   ├── target-set.schema.json
│   ├── reset-info.schema.json
│   ├── step-info.schema.json
│   └── examples/        # ví dụ hợp schema (đã kiểm bằng jsonschema draft 2020-12)
├── checklists/requirements.md
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

<a id="source-code-repository-root-chi-phan-002-them-vao-cay-cua-001"></a>
### Source Code (repository root) — chỉ phần 002 thêm vào cây của 001

```text
configs/
└── elbow_env.yaml       # physics_timestep_s, substeps_per_action, reward.*, tolerance_m, max_actions,
                         # targets.{n_train,n_test,min_separation_m,split_block_m,angle_margin_rad,default_seed},
                         # obs.{qvel_scale_rad_s}, fingertip_site, target_split
src/mma_ai/environment/
├── __init__.py          # register_envs() → MmaElbowReach-v0
├── env_config.py
├── errors.py
├── targets.py
├── observation.py
├── reward.py
└── single_agent.py
scripts/
└── verify_clean_install.py   # AC-5: venv sạch + uv sync --frozen + pytest, ghi logs/m1/verify_clean_install.json
tests/
├── unit/        # test_env_config, test_targets, test_observation, test_reward
├── integration/ # test_elbow_env (6 cơ, spaces, rollout, split, info, check_env), test_control_structure,
│                # test_headless, test_dependency_decision, test_contract_examples_m1
└── regression/  # test_target_determinism (hai lần sinh cùng seed + giao rỗng)
logs/m1/         # đầu ra chạy (bỏ khỏi git)
```

**Structure Decision**: dự án đơn (single project), mở rộng cây `src/mma_ai/` của 001 bằng đúng một gói con `environment/`. Các gói `learning/`, `evaluation/`, `visualization/` (con 2–4) **chưa tạo**. `.gitignore` đã có `logs/` theo plan của 001.

<a id="lenh-build-test-cho-task-khung-dung-dung-mot-lan"></a>
## Lệnh build / test (cho task khung dựng đúng một lần)

| Việc | Lệnh |
|---|---|
| Dựng môi trường | `uv python install 3.11 && uv sync --extra dev` |
| Toàn bộ test | `uv run python -m pytest -q` |
| Test riêng feature | `uv run python -m pytest -q tests/unit/test_targets.py tests/integration/test_elbow_env.py` |
| Tạo môi trường (thử nhanh) | `uv run python -c "from mma_ai.environment.single_agent import make_env; e=make_env(); print(e.reset(seed=42)[1])"` |
| Xác minh cài sạch (AC-5) | `uv run python scripts/verify_clean_install.py` |
| Khoá phiên bản | `uv lock` — CHỈ sau khi smoke test/`pytest` của môi trường đạt; commit `uv.lock` |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng/Test |
|---|---|---|
| FR-001, INV-003 | `single_agent` + `body_model` (001) | `test_elbow_env::test_loads_exactly_six_muscles`, `::test_rejects_model_without_six_muscles` |
| FR-002, NFR-HEADLESS-001 | `single_agent`, `__init__` | `test_elbow_env::test_gymnasium_check_env`, `test_headless::test_runs_without_display` |
| FR-003 | `validate_activation` (001) + `action_space` | `test_elbow_env::test_action_space_is_unit_box_6`, `::test_rejects_invalid_actions` |
| FR-004, INV-003 | `single_agent` (đường ctrl duy nhất) | `test_control_structure::test_all_actuators_are_muscle`, `::test_state_not_written_outside_mj_step` |
| FR-005, INV-004 | `observation` | `test_observation::test_layout_is_14_with_finite_bounds`, `::test_normalisation_matches_bounds` |
| FR-006, NFR-REL-001 | `observation.validate_observation`, `numeric_health` | `test_observation::test_rejects_out_of_bounds`, `test_elbow_env::test_random_rollout_no_nan_inf`, `::test_physics_instability_raises` |
| FR-007 | bộ test rollout | `test_elbow_env::test_random_rollout_no_nan_inf` (≥ 10 episode) |
| FR-008 | `reward` | `test_reward::test_closer_is_better`, `::test_effort_penalty_scales_and_zero_weight`, `::test_reward_finite` |
| FR-009 | `reward.is_reached`, `single_agent` | `test_elbow_env::test_terminated_on_reach`, `::test_truncated_at_max_actions` |
| FR-010, NFR-REPRO-001, INV-002 | `targets` | `test_target_determinism::test_same_seed_same_sets`, `test_targets::test_all_targets_reachable` |
| FR-011, INV-001 | `targets` | `test_target_determinism::test_train_test_disjoint`, `test_targets::test_min_separation`, `::test_infeasible_config_raises` |
| FR-012 | `single_agent` | `test_elbow_env::test_test_split_never_samples_train`, `::test_reset_info_fields` |
| FR-013 | `single_agent.model_record` | `test_elbow_env::test_model_sha256_in_info`, `test_contract_examples_m1` |
| FR-014 | `env_config`, `configs/elbow_env.yaml` | `test_env_config::test_defaults_load`, `::test_invalid_values_raise`, `::test_timestep_set_without_editing_xml` |
| FR-015 | `research.md` Q1 | `test_dependency_decision` |
| FR-016, NFR-INST-001 | `pyproject.toml`, `uv.lock`, `verify_clean_install.py` | `scripts/verify_clean_install.py` (mã thoát 0 + `logs/m1/verify_clean_install.json`) |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

1. **001 chưa có mã** — 002 dựa vào giao diện theo plan của 001; lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu (001), 002 chỉ thêm accessor đọc-chỉ (research Q5).
2. **`gymnasium 1.4` ↔ thư viện PPO/`torch` của con 2** — chưa kiểm; nếu buộc lùi `gymnasium`, đổi ghim và chạy lại `verify_clean_install` (research Q1).
3. **Tham số reward/dung sai** (`w_dist`, `w_effort`, `tolerance_m = 0,02`) — chưa kiểm bằng huấn luyện; con 2 chỉnh trong cấu hình, không đổi mã.
4. **Số mục tiêu 200/50 so với độ phân giải đích** (≈ 14 vị trí phân biệt ở dung sai 0,02 m, research Q3) — con 3 không được coi 50 mục tiêu test là 50 tình huống độc lập.
5. **Khớp vượt nhẹ giới hạn mềm** (qpos tới −0,11 rad) — cận góc chuẩn hoá ±1,5 đã tính; test `test_normalisation_matches_bounds` phải chạy rollout cực đoan (toàn 0, toàn 1, nhóm gập, nhóm duỗi) để xác nhận không ngoài cận.

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
