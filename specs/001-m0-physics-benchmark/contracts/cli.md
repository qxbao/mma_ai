---
id: "CT-001"
title: "M0 — Hợp đồng dòng lệnh (CLI contract)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Hợp đồng dòng lệnh — M0

M0 không có dịch vụ mạng; giao diện duy nhất là các script CLI chạy từ gốc repo và các tệp JSON chúng ghi. Khuôn dây của tệp nằm ở:

- `contracts/environment-profile.schema.json` — ví dụ `contracts/examples/environment-profile.*.json`
- `contracts/smoke-result.schema.json` — ví dụ `contracts/examples/smoke-result.*.json`
- `contracts/benchmark-report.schema.json` — ví dụ `contracts/examples/benchmark-report.*.json`
- `contracts/acceptance-report.schema.json` — ví dụ `contracts/examples/acceptance-report.*.json`

Quy tắc chung: mã thoát `0` = đạt; `1` = chạy xong nhưng **không đạt** tiêu chí; `2` = lỗi môi trường/đầu vào (thiếu thư viện, không nạp được mô hình, đối số sai); `3` = lệnh **chưa triển khai** ở M0 (FR-016). Mọi lệnh nhận `--seed` (mặc định từ `configs/simulation.yaml`), `--out-dir` (mặc định `logs/m0/<run_id>`) và in một dòng cuối `RUN_ID=<run_id>`; đường dẫn in ra luôn tương đối gốc repo (INV-003).

| Lệnh | Mục đích | Đầu vào chính | Đầu ra | Thoát | FR / AC |
|---|---|---|---|---|---|
| `python scripts/check_env.py` | Dò OS/WSL2, Python, CPU, RAM, `nvidia-smi`, torch/CUDA/arch, phiên bản thư viện | — | `env.json` (EnvironmentProfile) | 0 luôn (mục không dò được = null + reason); 2 nếu không ghi được tệp | FR-001 · AC-4, AC-5 |
| `python scripts/smoke_test.py [--seed N] [--steps N] [--samples N]` | Nạp mô hình MyoElbow, chạy các mẫu kích hoạt, quét NaN/Inf + cảnh báo vật lý, kiểm từ chối vector sai | `configs/*.yaml` | `smoke.json` (SmokeResult); dòng tóm tắt `NaN=<n> Inf=<n> WARN=<n> PASS\|FAIL` | 0 đạt · 1 không đạt (nêu đại lượng/bước/mẫu) · 2 lỗi mô hình/môi trường | FR-004…FR-009, FR-018 · AC-1, AC-2 |
| `python scripts/benchmark.py [--seed N] [--repeats N] [--steps N]` | Đo physics steps/s CPU headless, lặp ≥ 5, đo peak RAM và GPU | `configs/*.yaml` | `benchmark.json` (BenchmarkReport) | 0 đo xong (kể cả GPU không khả dụng — ghi reason) · 2 nếu `--repeats < 5` hoặc mô hình không nạp được | FR-010…FR-013 · AC-3, AC-4 |
| `python scripts/m0_report.py [--run-id ID]` | Tổng hợp env + smoke + benchmark thành báo cáo nghiệm thu | `logs/m0/<run_id>/*.json` | `acceptance.json` + `acceptance.md` theo mẫu báo cáo cột mốc (FR-020) | 0 nếu `gate_open=true` · 1 nếu còn AC chưa đạt/chưa chạy · 2 thiếu tệp nguồn không thể phân loại | FR-014, FR-020 · AC-1…AC-5 |
| `python scripts/train.py …` | Chưa triển khai (M1+) | bất kỳ | dòng `chưa triển khai (M0)` ra stderr | 3 | FR-016 |
| `python scripts/evaluate.py …` | Chưa triển khai | bất kỳ | như trên | 3 | FR-016 |
| `python scripts/replay.py …` | Chưa triển khai | bất kỳ | như trên | 3 | FR-016 |
| `python -m pytest` | Chạy toàn bộ unit + tích hợp + hồi quy | — | báo cáo pytest | 0 xanh | FR-017 · AC-1, AC-2 · NFR-REPRO-001, NFR-DOC-001 |

## Giao diện Python (nội bộ, ổn định trong M0)

| Hàm / lớp | Mô-đun | Hợp đồng |
|---|---|---|
| `load_muscle_model(config) -> LoadedModel` | `mma_ai.physics.body_model` | Nạp XML từ gói `myo-sim`, tính `MuscleModelInfo`; ném `ModelError` nếu `n_muscles != expected` hoặc `n_non_muscle_actuators > 0` (không thay mô hình khác) |
| `validate_activation(vec, n_muscles) -> np.ndarray` | `mma_ai.physics.simulator` | Trả bản sao float64; ném `ActivationError` nếu sai kích thước, ngoài [0,1], NaN hoặc Inf |
| `HeadlessSimulator(loaded, timestep_s=None)` · `.reset()` · `.step(activation, n_steps=1)` | `mma_ai.physics.simulator` | Chỉ ghi `data.ctrl`; không bao giờ ghi `qpos`/`qvel`/`xpos` hay dùng motor vị trí. Trả `StepReadout` có `ctrl_requested`, `ctrl_effective`, trạng thái khớp, `act`, `actuator_force` |
| `scan_nonfinite(arrays) -> NonFiniteCount` | `mma_ai.physics.numeric_health` | Đếm NaN và Inf riêng, trả cả tên đại lượng đầu tiên vi phạm |
| `read_physics_warnings(data) -> int` | `mma_ai.physics.numeric_health` | Tổng `data.warning[k].number` |
| `peak_ram_mb() -> float \| None` | `mma_ai.diagnostics.memory` | `ru_maxrss` đổi sang MB; `None` nếu nền tảng không hỗ trợ |
| `probe_gpu() -> GpuProbe` | `mma_ai.diagnostics.gpu` | Không ném ngoại lệ khi thiếu torch/GPU; trả `available=False` + `reason` |
| `write_record(path, obj)` / `load_record(path)` | `mma_ai.reporting.runlog` | Ghi JSON `sort_keys`, từ chối giá trị NaN/Inf (`allow_nan=False`) và chuỗi chứa đường dẫn tuyệt đối riêng của máy (INV-003) |
| `build_acceptance(env, smoke, bench) -> dict` | `mma_ai.reporting.acceptance` | Áp máy trạng thái AC ở `data-model.md`; không trả `dat` khi thiếu bằng chứng |
