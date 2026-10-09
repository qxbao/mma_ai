---
id: "DM-001"
title: "M0 — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Mô hình dữ liệu — M0

- [Quy ước chung](#quy-uoc-chung)
- [Thực thể → bản ghi](#thuc-the-ban-ghi)
- [Thực thể: MuscleModelInfo (tính khi nạp mô hình)](#thuc-the-musclemodelinfo-tinh-khi-nap-mo-hinh)
  - [Ánh xạ nhãn ↔ khoá (chỉ số kích hoạt ↔ tên cơ)](#anh-xa-nhan-khoa-chi-so-kich-hoat-ten-co)
- [Thực thể: ActivationSample (phần tử của `SmokeResult.samples`)](#thuc-the-activationsample-phan-tu-cua-smokeresultsamples)
- [Máy trạng thái của một AC trong AcceptanceReport](#may-trang-thai-cua-mot-ac-trong-acceptancereport)
- [Bất biến liên quan (đã khai ở spec.md, chỉ tham chiếu mã)](#bat-bien-lien-quan-da-khai-o-specmd-chi-tham-chieu-ma)
- [Cấu hình (đọc, không phải bản ghi báo cáo)](#cau-hinh-doc-khong-phai-ban-ghi-bao-cao)


M0 không có cơ sở dữ liệu, nên không có bảng `TBL-*` và không có index. Dữ liệu là các **bản ghi báo cáo JSON** (JSON report record) ghi vào `logs/m0/<run_id>/` bởi script và đọc lại bởi test + `scripts/m0_report.py`. Khuôn dây của từng bản ghi nằm ở `contracts/*.schema.json` (không chép lại tên trường ở đây). Không có sự kiện `EVT-*`, không có `CMD-*`/`QRY-*`/`API-*` (không có dịch vụ mạng); lệnh dòng lệnh ghi ở `contracts/cli.md`.

<a id="quy-uoc-chung"></a>
## Quy ước chung

- `run_id`: `<UTC yyyymmddThhmmssZ>-s<seed>` (ví dụ `20261009T101500Z-s42`). Một lần chạy = một thư mục `logs/m0/<run_id>/`.
- Đường dẫn trong bản ghi luôn tương đối gốc repo hoặc mô tả tên gói (`myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml`), không bao giờ tuyệt đối (INV-003).
- Giá trị không đo/không dò được: trường nullable = `null` **và** trường `reason` (hoặc `*_reason`) giải thích — không điền số giả (INV-001).

<a id="thuc-the-ban-ghi"></a>
## Thực thể → bản ghi

| Thực thể (spec) | Bản ghi | Tệp | Khuôn dây | Người ghi | Người đọc |
|---|---|---|---|---|---|
| Hồ sơ môi trường | EnvironmentProfile | `env.json` | `contracts/environment-profile.schema.json` | `scripts/check_env.py` | benchmark, m0_report, test |
| Kết quả smoke test | SmokeResult | `smoke.json` | `contracts/smoke-result.schema.json` | `scripts/smoke_test.py` | m0_report, test hồi quy |
| Báo cáo benchmark | BenchmarkReport | `benchmark.json` | `contracts/benchmark-report.schema.json` | `scripts/benchmark.py` | m0_report, test |
| Báo cáo nghiệm thu M0 | AcceptanceReport | `acceptance.json` + `acceptance.md` | `contracts/acceptance-report.schema.json` | `scripts/m0_report.py` | người, test NFR-DOC-001 |
| Mô hình cơ–xương | MuscleModelInfo (nhúng trong SmokeResult/BenchmarkReport, tính từ XML — không lưu riêng) | — | `$defs/muscle_model` trong schema smoke | `mma_ai.physics.body_model` | — |
| Vector kích hoạt cơ | `numpy.ndarray(6,)` trong bộ nhớ; chỉ lưu dưới dạng mẫu có tên trong SmokeResult | — | — | — | — |

<a id="thuc-the-musclemodelinfo-tinh-khi-nap-mo-hinh"></a>
## Thực thể: MuscleModelInfo (tính khi nạp mô hình)

| Trường | Kiểu | Nguồn | Ghi chú / luật hợp lệ |
|---|---|---|---|
| `source` | chuỗi | cấu hình `configs/body.yaml` | đường dẫn trong gói `myo-sim` |
| `sha256` | chuỗi hex 64 | băm byte tệp XML | định danh mô hình (FR-011, FR-018) |
| `n_muscles` | số nguyên | `model.nu` | MUST = 6 nếu không SmokeResult `passed=false` (Edge Case) |
| `n_non_muscle_actuators` | số nguyên | đếm actuator có `gaintype != muscle` | MUST = 0 (INV-004) |
| `n_dof` | số nguyên | `model.nv` | 1 với bản MyoElbow này |
| `muscle_names` | mảng chuỗi (độ dài `n_muscles`) | tên actuator | thứ tự = chỉ số trong vector kích hoạt |
| `joint_ranges_rad` | mảng [lo, hi] mỗi khớp | `jnt_range` | giới hạn góc khớp (FR-004) |
| `muscle_f0_n` | mảng số | `gainprm[:,2]` | lực cực đại đẳng trường khai báo |
| `force_bound_n` | mảng số | `f0·(fvmax+fpmax)` — xem research Q3 | ngưỡng kiểm lực mỗi cơ |
| `ctrl_range` | [lo, hi] mỗi cơ | `actuator_ctrlrange` | thực tế [0.001, 1] — nguồn của `ctrl_effective` |
| `timestep_s` | số | `model.opt.timestep` | 0.002 mặc định |

<a id="anh-xa-nhan-khoa-chi-so-kich-hoat-ten-co"></a>
### Ánh xạ nhãn ↔ khoá (chỉ số kích hoạt ↔ tên cơ)

Dây chỉ mang **chỉ số** `0..5` trong vector kích hoạt và khoá tên cơ trong `muscle_names`; nhãn hiển thị (nếu có) chỉ sinh ở báo cáo `.md`.

| Chỉ số | Khoá (`muscle_names[i]`) |
|---|---|
| 0 | `TRIlong` |
| 1 | `TRIlat` |
| 2 | `TRImed` |
| 3 | `BIClong` |
| 4 | `BICshort` |
| 5 | `BRA` |

Bảng này được **đọc từ mô hình khi nạp** và so với danh sách trên trong test (`tests/unit/test_body_model.py`); lệch ⇒ không đạt, không tự đổi tên.

<a id="thuc-the-activationsample-phan-tu-cua-smokeresultsamples"></a>
## Thực thể: ActivationSample (phần tử của `SmokeResult.samples`)

| Trường | Kiểu | Luật |
|---|---|---|
| `name` | chuỗi | `zeros`, `ones`, `half`, `random_<k>` |
| `kind` | enum `constant` · `random` | |
| `ctrl_requested` | mảng 6 số trong [0,1] | vector yêu cầu (với `random`: giá trị đầu; đổi mỗi 16 bước) |
| `ctrl_effective` | mảng 6 số | sau kẹp theo `ctrl_range` (INV-004) |
| `steps` | số nguyên > 0 | |
| `nan_count`, `inf_count` | số nguyên ≥ 0 | tổng trên mọi đại lượng quét, mọi bước |
| `physics_warnings` | số nguyên ≥ 0 | tổng `mjData.warning[*].number` |
| `max_abs_force_n` | số | cực đại của `|actuator_force|` toàn mẫu |
| `force_within_bound` | bool | `|F_i| ≤ force_bound_n[i]` mọi cơ, mọi bước |
| `joint_state_final` | `{qpos, qvel}` | trạng thái khớp cuối mẫu (FR-007) |
| `muscle_activation_final` | mảng 6 số | `mjData.act` cuối mẫu (FR-007) |
| `muscle_force_final_n` | mảng 6 số | `actuator_force` cuối mẫu (FR-007) |

<a id="may-trang-thai-cua-mot-ac-trong-acceptancereport"></a>
## Máy trạng thái của một AC trong AcceptanceReport

```text
chua_chay ──(có bằng chứng đo, đạt tiêu chí)──▶ dat
chua_chay ──(có bằng chứng đo, không đạt / lỗi)──▶ chua_dat
dat | chua_dat ──(chạy lại, run_id mới)──▶ dat | chua_dat
```

- `dat` yêu cầu ≥ 1 mục `evidence` trỏ tới tệp thật trong `logs/m0/<run_id>/` (INV-001). Không có đường chuyển trực tiếp `chua_chay → dat` bằng khai báo.
- AC-4 ở máy không có GPU: `chua_dat` với `note` nêu nguyên nhân (Tự chốt trong spec); `gate_open = false` khi bất kỳ AC nào ≠ `dat`.

<a id="bat-bien-lien-quan-da-khai-o-specmd-chi-tham-chieu-ma"></a>
## Bất biến liên quan (đã khai ở spec.md, chỉ tham chiếu mã)

INV-001 (số đo thật) · INV-002 (tất định theo seed) · INV-003 (không đường dẫn tuyệt đối/bí mật) · INV-004 (chỉ actuator cơ, ghi ctrl hiệu dụng).

<a id="cau-hinh-doc-khong-phai-ban-ghi-bao-cao"></a>
## Cấu hình (đọc, không phải bản ghi báo cáo)

| Tệp | Khoá chính | Dùng bởi |
|---|---|---|
| `configs/body.yaml` | `model.source`, `model.expected_muscles` (6), `model.expected_muscle_names`, `force_bound.formula` | `body_model`, smoke |
| `configs/simulation.yaml` | `smoke.{steps_per_sample, random_samples, policy_hold_steps}`, `benchmark.{timesteps_s, steps_per_repeat, repeats, warmup_repeats, scenarios}`, `seed_default` | smoke, benchmark |
