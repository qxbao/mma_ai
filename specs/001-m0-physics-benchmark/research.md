---
id: "RES-001"
title: "M0 — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Nghiên cứu Phase 0 — M0: Thiết lập môi trường & Benchmark vật lý

Mọi mục "ĐÃ ĐO" dưới đây là kết quả chạy thật trên máy phát triển ngày 2026-10-09 (Linux gốc, Python 3.12.3, 12 luồng CPU, chưa có công cụ NVIDIA) trong một môi trường ảo tạm dùng Python 3.11 do `uv` tải về. Mục "CHƯA KIỂM" là việc phải xác minh trên máy đích (Legion Pro 5 + WSL2) ở bước triển khai — plan không giả định kết quả (INV-001).

## Q1. Phiên bản Python

- **Quyết định**: Python **3.11** (ghim bằng `.python-version` và `requires-python = ">=3.11,<3.13"`), cài bằng `uv` (`uv python install 3.11`).
- **Căn cứ (ĐÃ ĐO)**: máy phát triển chỉ có Python 3.12.3; `uv python list` thấy cpython-3.11.15 tải được. `mujoco 3.15.0` + `myo-sim 0.2.3` + `numpy` + `pytest` cài và chạy được trên 3.11 trong môi trường ảo tạm. Yêu cầu gốc nhắm 3.11; metadata MyoSuite 3.0.0 cũng liệt kê hỗ trợ 3.10–3.14.
- **Phương án đã loại**: dùng 3.12.3 hệ thống — lệch mục tiêu của yêu cầu gốc, khó tái lập giữa máy phát triển và máy đích.

## Q2. Gói mô hình cơ–xương: MyoSim hay MyoSuite?

- **Quyết định**: M0 cài **`myo-sim==0.2.3`** (gói tài nguyên mô hình MyoSim) cùng `mujoco`; **không** cài `myosuite` ở M0.
- **Căn cứ (ĐÃ ĐO/ĐỌC)**: wheel `myo_sim-0.2.3` chỉ phụ thuộc `mujoco>=3.4` và `numpy>=1.24`, và chứa `myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml`. `MyoSuite 3.0.0` ghim đúng `myo-sim==0.2.3` nhưng kéo thêm `gymnasium<1.3`, `onnxruntime<1.21`, `h5py`, `scikit-learn`, `mjviser`… — không cần cho M0 (FR-002: chỉ thư viện thật sự cần) và `gymnasium<1.3` sẽ xung đột với `gymnasium 1.4.0` mới nhất khi tới M1.
- **Việc để M1**: quyết định ghim `gymnasium` theo MyoSuite hay bỏ MyoSuite; ghi vào plan của M1.
- **Phương án đã loại**: cài `myosuite[rl]` ngay — thêm bề mặt xung đột phiên bản mà M0 không dùng.

## Q3. Mô hình MyoElbow 6 cơ có đúng như yêu cầu không?

- **Quyết định**: dùng `myoelbow_1dof6muscles.xml` (bản "legacy/elbow" trong myo-sim) làm mô hình M0; hash SHA-256 của tệp XML là định danh mô hình trong mọi báo cáo.
- **Căn cứ (ĐÃ ĐO)** khi nạp bằng `mujoco.MjModel.from_xml_path`:
  - `nu = 6`, `na = 6`, `nq = nv = 1` (một bậc tự do: khớp `r_elbow_flex`, giới hạn `[0, 2.26893]` rad, có `limited`), 29 body, 6 tendon.
  - Tên 6 cơ theo thứ tự chỉ số: `TRIlong, TRIlat, TRImed, BIClong, BICshort, BRA`.
  - Cả 6 actuator đều là cơ Hill của MuJoCo: `gaintype = muscle (2)`, `biastype = muscle (2)`, `dyntype = muscle (4)`, `trntype = tendon (3)` ⇒ không phải joint motor/position controller (FR-006, INV-004).
  - Bước thời gian mô hình `0.002 s`, integrator Euler (0).
  - Lực cực đại đẳng trường khai báo `gainprm[2]` (F0) = 769.6 · 604.4 · 604.2 · 607.8 · 423.7 · 976.2 N (theo thứ tự cơ). Đây là "giới hạn lực mô hình khai báo" dùng cho kiểm tra FR-004.
  - Tốc độ: 20 000 bước `mj_step` với ctrl = 0.5 chạy ≈ 1,35×10⁵ steps/s trên CPU phát triển, qpos hữu hạn. Đây chỉ là phép thăm dò sơ bộ; số chính thức do `scripts/benchmark.py` đo lặp ≥ 5 lần (NFR-PERF-001) và KHÔNG được trích từ đây vào báo cáo.
- **Phát hiện quan trọng #1 (ctrlrange)**: `actuator_ctrlrange = [0.001, 1]` và `ctrllimited` bật. Vector kích hoạt hợp lệ theo spec là [0, 1], nhưng MuJoCo kẹp (clamp) ctrl về [0.001, 1]. ⇒ Mô phỏng ghi `ctrl_effective` (sau kẹp) bên cạnh `ctrl_requested`; kích hoạt 0 thực chất là 0,001. Không đổi XML để "sửa".
- **Phát hiện quan trọng #2 (forcerange)**: `actuator_forcerange = [0, 0]` và `forcelimited = False` ⇒ MuJoCo không tự kẹp lực. "Giới hạn lực" của kiểm tra FR-004 phải lấy từ mô hình cơ: lực chủ động ≤ F0 · hệ số lực–vận tốc cực đại; lực thụ động có thể cộng thêm khi cơ kéo giãn. **Quyết định**: kiểm tra `|actuator_force| ≤ F0 · (fvmax + fpmax)` với `fvmax`, `fpmax` đọc từ `gainprm[8]`, `gainprm[7]` của chính actuator; nếu số đo thực vượt ngưỡng này thì báo cáo ghi là phát hiện (không đạt) chứ không nới ngưỡng cho đẹp. Công thức này CHƯA KIỂM bằng quét toàn dải góc khớp — task kiểm thử đầu tiên phải chạy quét và xác nhận hoặc sửa công thức trong `configs/body.yaml`, ghi lý do.
- **Phương án đã loại**: tự dựng mô hình khuỷu tay có motor — vi phạm FR-006 và ràng buộc "không joint motor" của yêu cầu gốc.

## Q4. Bắt "lỗi vật lý" (AC-2)

- **Quyết định**: sau mỗi mẫu, đọc `mjData.warning[k].number` cho mọi `k` trong `mujoco.mjtWarning` (cảnh báo như `INERTIA`, `CONTACTFULL`, `BADQPOS`, `BADQVEL`, `BADQACC`, `BADCTRL`); tổng > 0 ⇒ không đạt. Thêm quét `np.isfinite` trên `qpos, qvel, qacc, act, ctrl, actuator_force, actuator_length, actuator_velocity, sensordata` sau mỗi bước.
- **Căn cứ**: đây là cơ chế chính thức MuJoCo dùng để báo mất ổn định; chuyển cảnh báo thành tín hiệu số đếm được giúp báo cáo tất định (INV-002). Tự chốt trong spec đã nêu hướng này; chi tiết cách đọc chốt ở đây.
- **Phương án đã loại**: bắt qua `mju_user_warning` (callback toàn cục) — không an toàn đa luồng, khó gắn vào từng mẫu.

## Q5. Đo hiệu năng CPU (AC-3, NFR-PERF-001)

- **Quyết định** (tham số khởi tạo, chỉnh theo đo thực tế rồi ghi vào `configs/simulation.yaml`):
  - Mỗi kịch bản: 1 lần khởi động (warm-up, loại khỏi thống kê) + **7 lần lặp đo** (≥ 5 theo NFR), mỗi lần 100 000 bước `mj_step` (≈ 0,7 s ở tốc độ thăm dò — đủ dài để giảm nhiễu đồng hồ, đủ ngắn để chạy dưới 1 phút).
  - Hai kịch bản: `constant` (ctrl cố định 0,5) và `policy_like` (lấy mẫu ctrl ngẫu nhiên có seed, giữ 16 bước vật lý/lần — mô phỏng nhịp policy 25 Hz ở bước 0,0025 s của yêu cầu gốc).
  - Hai bước thời gian vật lý: mặc định của mô hình `0.002 s` và `0.0025 s` (gán `model.opt.timestep`); không sửa XML.
  - Thống kê báo cáo: trung vị (median), trung bình, min, max, độ lệch chuẩn, hệ số biến thiên (CV); đồng hồ `time.perf_counter()`.
  - Không đặt ngưỡng steps/s tối thiểu (Tự chốt trong spec).
- **Phương án đã loại**: dùng `timeit` mặc định (gộp lặp, mất phân tán); đo đa môi trường 1/2/4/8 (ngoài phạm vi M0).

## Q6. RAM đỉnh & GPU (AC-4)

- **Quyết định**: RAM đỉnh = `resource.getrusage(RUSAGE_SELF).ru_maxrss` (KB trên Linux/WSL2 → MB) đọc ở cuối benchmark; không thêm dependency `psutil`. GPU: `torch.cuda.is_available()`, tên GPU, `torch.cuda.mem_get_info()`, `torch.cuda.max_memory_allocated()` sau một phép nhân ma trận nhỏ, kèm `torch.cuda.get_arch_list()`; thêm đọc `nvidia-smi` nếu có (driver, CUDA version) — thiếu thì ghi "không dò được".
- **Căn cứ (ĐÃ ĐO)**: máy phát triển không có `nvidia-smi` ⇒ AC-4 ở máy này sẽ là **chưa đạt** với nguyên nhân ghi rõ (đúng Tự chốt của spec); cổng M0 chỉ đóng khi đo GPU thật chạy được trên máy đích.
- **CHƯA KIỂM (bắt buộc trên máy đích)**: GPU RTX 5060 là kiến trúc Blackwell (compute capability 12.0 / `sm_120`). Bản PyTorch cài phải có `sm_120` trong `torch.cuda.get_arch_list()` thì mới chạy được kernel; nếu bản mặc định trên PyPI thiếu, cài từ chỉ mục wheel CUDA ≥ 12.8 do PyTorch cung cấp. Task cài đặt phải ghi lại bản torch + CUDA runtime + arch list thực tế vào hồ sơ môi trường, không chọn số phiên bản từ trí nhớ. Dò phiên bản mới nhất trên PyPI ngày 2026-10-09 (`pip index`): torch 2.14.1, mujoco 3.15.0, numpy 2.5.3, pytest 9.1.1 — chỉ là ứng viên, lockfile mới là sự thật.
- **Phương án đã loại**: `pynvml`/`nvidia-ml-py` — thêm dependency chỉ để đọc thứ `torch` + `nvidia-smi` đã cho.

## Q7. Quản lý phụ thuộc & khoá phiên bản (FR-002, AC-5)

- **Quyết định**: `uv` + `pyproject.toml` + `uv.lock`; torch nằm ở extra `gpu` (không kéo ~GB khi chỉ chạy CPU/CI); `uv lock` chỉ chạy và commit **sau khi** `scripts/smoke_test.py` đạt (FR-002). Xung đột phiên bản làm `uv sync` dừng với thông điệp nêu cặp xung đột — đúng Edge Case, không tự hạ phiên bản.
- **Phương án đã loại**: `pip freeze` thủ công (không băm, không giải xung đột); conda (không có trên máy phát triển).

## Q8. Tính tất định (INV-002, NFR-REPRO-001)

- **Quyết định**: MuJoCo `mj_step` tất định với cùng trạng thái đầu và ctrl. Ngẫu nhiên chỉ đến từ `numpy.random.default_rng(seed)` sinh mẫu kích hoạt. Smoke test xuất `trajectory_fingerprint` (SHA-256 của qpos/qvel/actuator_force làm tròn float64 → bytes) để test hồi quy so hai lần chạy cùng seed.
- **Rủi ro biết trước**: khác biệt dấu phẩy động giữa máy/phiên bản MuJoCo ⇒ fingerprint chỉ so trong cùng môi trường khoá; báo cáo ghi phiên bản. Nếu hai lần cùng máy cho fingerprint khác ⇒ ghi giới hạn (Edge Case INV-002), không che.

## Q9. Quy mô tài liệu

- **Quyết định**: một bounded context duy nhất (mô phỏng cơ–xương) ⇒ không tạo `docs/02-strategic/`, `docs/03-tactical/`, `rbac.md` (không phân quyền); không có API mạng ⇒ hợp đồng là CLI + định dạng tệp báo cáo JSON ở `contracts/`. Không có `docs/` sẵn để đọc.

## Tổng kết

Không còn mục `NEEDS CLARIFICATION`. Hai việc CHƯA KIỂM được giao thành task bắt buộc có kết quả ghi vào báo cáo: (1) công thức ngưỡng lực (Q3), (2) torch có `sm_120` trên máy đích (Q6).
