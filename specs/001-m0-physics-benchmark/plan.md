---
id: "PLAN-001"
title: "M0 — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Implementation Plan: M0 — Thiết lập môi trường & Benchmark vật lý

**Branch**: `001-m0-physics-benchmark` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-m0-physics-benchmark/spec.md` (bản hiện tại, gồm INV-004 thêm ở bước plan)

## Summary

M0 dựng nền tảng tối thiểu của MMA-AI-LAB và chứng minh bằng đo thật rằng mô hình cơ–xương **MyoElbow 6 cơ** (gói `myo-sim`) chạy headless trên MuJoCo, chỉ điều khiển bằng kích hoạt cơ. Kết quả là bốn script CLI (`check_env`, `smoke_test`, `benchmark`, `m0_report`) ghi bản ghi JSON theo hợp đồng ở `contracts/`, một bộ test pytest, README dựng lại môi trường, và `uv.lock` khoá sau khi smoke test đạt. Không PPO, không toàn thân, không MMA (FR-019).

Cách tiếp cận kỹ thuật (xem `research.md`): Python 3.11 qua `uv`; `mujoco` + `myo-sim==0.2.3` (không cài `myosuite` ở M0); lỗi vật lý bắt bằng bộ đếm `mjData.warning`; benchmark lặp 7 lần × 100 000 bước, hai kịch bản và hai bước thời gian; RAM đỉnh bằng `resource.getrusage`; GPU bằng `torch` (extra `gpu`) + `nvidia-smi`.

## Technical Context

**Language/Version**: Python 3.11 (ghim `.python-version`; `requires-python = ">=3.11,<3.13"`)

**Primary Dependencies**: `mujoco` (ứng viên 3.15.0, ĐÃ ĐO nạp mô hình được), `myo-sim==0.2.3` (ĐÃ ĐO), `numpy`, `pyyaml`; extra `gpu`: `torch` (phiên bản chọn bằng kiểm tra thật trên máy đích — research Q6); extra `dev`: `pytest`, `jsonschema`

**Storage**: tệp JSON/Markdown dưới `logs/m0/<run_id>/` (xem `data-model.md`); không CSDL

**Testing**: `pytest` (`python -m pytest`), test hợp đồng bằng `jsonschema` trên `contracts/*.schema.json`

**Target Platform**: Windows 11 + WSL2 Ubuntu (Legion Pro 5: RTX 5060 8GB, Ryzen 9 HX, 32GB RAM); phát triển thêm trên Linux gốc (Python 3.12.3 hệ thống, 12 luồng, chưa có NVIDIA) với Python 3.11 do `uv` cấp

**Project Type**: thư viện + CLI nghiên cứu (không web, không giao diện đồ hoạ)

**Performance Goals**: không có ngưỡng steps/s tối thiểu (Tự chốt trong spec); mục tiêu là *đo và báo cáo* — NFR-PERF-001: ≥ 5 lần lặp kèm độ phân tán

**Constraints**: headless; CPU cho vật lý; CPU không tải GPU nặng; mọi số trong báo cáo là số đo (INV-001); không đường dẫn tuyệt đối/bí mật trong repo (INV-003); không joint motor trong đường chạy chính (INV-004, FR-006)

**Scale/Scope**: 1 mô hình (1 DoF, 6 cơ), 4 script thật + 3 script "chưa triển khai", ≈ 10 mô-đun, ≈ 12 tệp test

## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | Mọi AC chỉ `dat` khi có tệp bằng chứng trong `logs/m0/` (máy trạng thái ở `data-model.md`); `m0_report.py` không có đường khai báo `dat` tay; cổng máy khai theo mục "Lệnh build/test" |
| II. Test trước, sửa sau | Đạt | Task tạo test trước mã cho từng mô-đun; kịch bản quickstart gắn tên test |
| III. Lát cắt nhỏ, một vai một task | Đạt | Cây thư mục tách mô-đun theo trách nhiệm; mỗi tệp một chủ để bước tasks cắt lát ≤ 600 LoC |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…INV-004 và NFR-REL/PERF/REPRO/DOC-001 khai ở spec.md; plan chỉ tham chiếu mã (INV-004 là bất biến mới phát hiện lúc plan, đã khai vào spec.md) |
| V. Không đổi cái không được yêu cầu | Đạt | Không `myosuite`, không `psutil`, không `pynvml`, không đa môi trường; không sửa XML mô hình |
| VI. Bí mật chỉ qua biến môi trường | Đạt | M0 không có bí mật; `test_repo_hygiene` quét mẫu đường dẫn riêng (INV-003) |
| VII. Nhánh bảo vệ | Đạt | Làm trên nhánh `001-m0-physics-benchmark`; không commit hộ vai khác |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | `acceptance.md`, bảng số liệu sinh từ JSON; README chỉ trỏ tới lệnh sinh số, không chép số đo |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Một bounded context ⇒ không có `docs/02-strategic`, `docs/03-tactical`; data model/hợp đồng CHỈ ở `specs/001-…/`; không có `docs/` sẵn để đồng bộ |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm dependency ngoài danh sách trên; không có vi phạm cần ghi ở Complexity Tracking.

## Kiến trúc & tách trách nhiệm

Bám cấu trúc dự án của yêu cầu gốc (mục IV) nhưng **chỉ tạo mô-đun M0 thực sự dùng** (không tạo tệp rỗng — FR-003). Phụ thuộc một chiều: `scripts → reporting/diagnostics → physics → config`; `physics` không import `reporting`/`diagnostics`.

| Mô-đun | Trách nhiệm | FR |
|---|---|---|
| `mma_ai.config` | Đọc `configs/*.yaml`, kiểm khoá bắt buộc, trả cấu hình bất biến | FR-003 |
| `mma_ai.physics.body_model` | Tìm XML trong gói `myo-sim`, nạp `MjModel`, băm SHA-256, tính `MuscleModelInfo`, ném `ModelError` | FR-004, FR-006 |
| `mma_ai.physics.simulator` | `validate_activation`, `HeadlessSimulator` (chỉ ghi `ctrl`), `StepReadout` | FR-005, FR-007 |
| `mma_ai.physics.numeric_health` | Đếm NaN/Inf, đọc `data.warning`, ngưỡng lực | FR-008, FR-009 |
| `mma_ai.diagnostics.environment` | OS/WSL2, Python, CPU, RAM, `nvidia-smi`, phiên bản thư viện | FR-001 |
| `mma_ai.diagnostics.memory` | `peak_ram_mb` | FR-012 |
| `mma_ai.diagnostics.gpu` | `probe_gpu`: CUDA, arch, phép nhân ma trận nhỏ, bộ nhớ GPU | FR-013 |
| `mma_ai.diagnostics.stats` | median/mean/min/max/stdev/cv | FR-010 |
| `mma_ai.reporting.runlog` | `run_id`, ghi/đọc JSON an toàn (từ chối NaN/Inf, đường dẫn tuyệt đối riêng) | FR-014, FR-018 |
| `mma_ai.reporting.acceptance` | Máy trạng thái AC, sinh `acceptance.json`/`.md` | FR-020 |

### Quyết định thiết kế

- **Ghi `ctrl` duy nhất**: `HeadlessSimulator` chỉ có đường ghi `data.ctrl`; test `test_simulator_never_writes_state` kiểm `qpos`/`qvel` chỉ đổi qua `mj_step` (không teleport — ràng buộc nền của yêu cầu gốc).
- **Kẹp ctrl**: MuJoCo kẹp về `[0.001, 1]` (research Q3). Simulator ghi `ctrl_effective` cạnh `ctrl_requested` (INV-004); không đổi XML.
- **Lỗi hiển thị cho người dùng** (tiếng Việt): `ActivationError`, `ModelError` có thông điệp nêu giá trị/ số cơ tìm thấy.
- **Tất định**: `numpy.random.default_rng(seed)` là nguồn ngẫu nhiên duy nhất; `trajectory_fingerprint` cho test hồi quy.
- **Không mock physics**: test dùng mô hình thật (nhanh — 1 DoF); `monkeypatch` chỉ dùng cho hành vi dự phòng (thiếu CUDA, tiêm NaN vào hàm quét) và được gọi tên rõ trong test.
- **Không tự viết validator an ninh/công cụ kiểm riêng** ngoài hàm kiểm vector kích hoạt theo spec; test assert thẳng trên sản phẩm.

## Project Structure

### Documentation (this feature)

```text
specs/001-m0-physics-benchmark/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── environment-profile.schema.json
│   ├── smoke-result.schema.json
│   ├── benchmark-report.schema.json
│   ├── acceptance-report.schema.json
│   └── examples/        # 7 ví dụ hợp schema (đã kiểm bằng jsonschema draft 2020-12)
├── checklists/requirements.md
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

### Source Code (repository root)

```text
pyproject.toml           # build hatchling, deps, extras gpu/dev, cấu hình pytest
uv.lock                  # chỉ tạo/commit SAU khi smoke test đạt (FR-002)
.python-version          # 3.11
README.md                # hướng dẫn cài lại, kiểm GPU/CUDA, xử lý sự cố, lệnh chưa triển khai (FR-015, FR-016)
configs/
├── simulation.yaml      # seed_default, smoke.*, benchmark.*
└── body.yaml            # model.source, expected_muscles, expected_muscle_names, force_bound
src/mma_ai/
├── __init__.py
├── config.py
├── physics/
│   ├── __init__.py
│   ├── body_model.py
│   ├── simulator.py
│   └── numeric_health.py
├── diagnostics/
│   ├── __init__.py
│   ├── environment.py
│   ├── memory.py
│   ├── gpu.py
│   └── stats.py
└── reporting/
    ├── __init__.py
    ├── runlog.py
    └── acceptance.py
scripts/
├── check_env.py
├── smoke_test.py
├── benchmark.py
├── m0_report.py
├── train.py             # chưa triển khai → thoát 3
├── evaluate.py          # chưa triển khai → thoát 3
└── replay.py            # chưa triển khai → thoát 3
tests/
├── unit/                # test_body_model, test_activation_validation, test_numeric_health, test_force_bound,
│                        # test_stats, test_gpu_probe, test_runlog, test_acceptance, test_config
├── integration/         # test_smoke_cli, test_benchmark_cli, test_unimplemented_cli, test_repo_hygiene,
│                        # test_contract_examples (ví dụ hợp schema)
└── regression/          # test_determinism
logs/                    # đầu ra chạy (m0/<run_id>/…); bỏ khỏi git trừ báo cáo nghiệm thu được chọn lưu
```

**Structure Decision**: dự án đơn (single project) theo cấu trúc `src/` của yêu cầu gốc, thu gọn cho M0. Các thư mục `environment/`, `learning/`, `evaluation/`, `visualization/`, `physiology/`, `assets/` của cấu trúc đầy đủ **chưa tạo** vì M0 chưa có mã thật cho chúng; `mma_ai.physics.contact` cũng hoãn tới M6. `.gitignore` bổ sung `logs/` và `checkpoints/` (đã có `.venv/`, `__pycache__/`).

## Lệnh build / test (cho task khung dựng đúng một lần)

| Việc | Lệnh |
|---|---|
| Dựng môi trường | `uv python install 3.11 && uv sync --extra dev` (thêm `--extra gpu` trên máy có GPU) |
| Kiểm môi trường | `uv run python scripts/check_env.py` |
| Smoke test | `uv run python scripts/smoke_test.py --seed 42` |
| Benchmark | `uv run python scripts/benchmark.py --seed 42` |
| Báo cáo nghiệm thu | `uv run python scripts/m0_report.py` |
| Toàn bộ test | `uv run python -m pytest` |
| Khoá phiên bản | `uv lock` — CHỈ sau khi smoke test đạt; commit `uv.lock` |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng/Test |
|---|---|---|
| FR-001 | `diagnostics.environment`, `scripts/check_env.py` | `env.json`; kịch bản 1, 5 |
| FR-002 | `pyproject.toml`, `uv.lock`, thứ tự "smoke đạt → lock" | `test_lockfile_exists_and_pins_core_libs` |
| FR-003, FR-019 | cây thư mục trên; không mô-đun RL/MMA | rà tay trong review; `test_repo_hygiene` |
| FR-004, FR-006, INV-004 | `physics.body_model` | `test_loads_exactly_six_muscles`, `test_no_non_muscle_actuators` |
| FR-005, FR-007 | `physics.simulator` | `test_activation_validation`, `StepReadout` trong smoke |
| FR-008, FR-009, NFR-REL-001 | `physics.numeric_health`, `scripts/smoke_test.py` | `test_numeric_health`, `test_smoke_cli` |
| FR-010, FR-011, NFR-PERF-001 | `scripts/benchmark.py`, `diagnostics.stats` | `test_benchmark_cli`, `test_stats` |
| FR-012 | `diagnostics.memory` | `peak_ram_mb` trong `benchmark.json` |
| FR-013 | `diagnostics.gpu` | `test_gpu_probe` + đo trên máy đích |
| FR-014, FR-018, FR-020, NFR-DOC-001, INV-001, INV-003 | `reporting.*`, `scripts/m0_report.py` | `test_acceptance`, `test_runlog`, `test_repo_hygiene` |
| FR-015, FR-016 | README, `scripts/train|evaluate|replay.py` | `test_unimplemented_cli` |
| FR-017 | `tests/` | `python -m pytest` |
| INV-002, NFR-REPRO-001 | seed + `trajectory_fingerprint` | `test_determinism` |

## Rủi ro & việc CHƯA KIỂM

1. **Torch trên Blackwell (`sm_120`)** — chưa kiểm; task cài GPU phải ghi `arch_list`. Nếu bản torch mặc định thiếu `sm_120`, AC-4 `chua_dat` cho tới khi cài bản có kiến trúc đó. Không đoán số phiên bản.
2. **Công thức ngưỡng lực** `F0·(fvmax+fpmax)` — chưa quét toàn dải góc; kết quả quét quyết định giữ/sửa công thức (ghi lý do vào `configs/body.yaml` và báo cáo).
3. **Máy phát triển hiện không có NVIDIA** — AC-4 chỉ chốt trên máy đích; M0 giữ trạng thái chưa đóng tới lúc đó (Tự chốt trong spec).
4. **Hiệu năng WSL2 so với Linux gốc** — số benchmark chỉ có giá trị cho đúng cấu hình đo; báo cáo ghi rõ OS (WSL2 hay không) và không suy thời gian huấn luyện.
5. **`myosuite` ở M1** — xung đột `gymnasium<1.3` cần quyết định ở plan M1 (research Q2).

## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
