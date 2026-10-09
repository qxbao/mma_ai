---
id: "RES-002"
title: "M1 (1/4) — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Nghiên cứu Phase 0 — M1 (1/4): Môi trường khuỷu tay điều khiển bằng cơ & tập mục tiêu

- [Q1. Ghim `gymnasium<1.3` theo MyoSuite hay bỏ MyoSuite? (FR-015, FR-016, AC-5)](#q1-ghim-gymnasium13-theo-myosuite-hay-bo-myosuite-fr-015-fr-016-ac-5)
- [Q2. Mô hình và đầu mút tay (FR-001, FR-005, FR-010)](#q2-mo-hinh-va-dau-mut-tay-fr-001-fr-005-fr-010)
- [Q3. Hình học tầm với & bộ sinh mục tiêu (FR-010, FR-011, FR-012, INV-001, INV-002)](#q3-hinh-hoc-tam-voi-bo-sinh-muc-tieu-fr-010-fr-011-fr-012-inv-001-inv-002)
- [Q4. Observation: bố cục, chuẩn hoá, cận (FR-005, FR-006, INV-004)](#q4-observation-bo-cuc-chuan-hoa-can-fr-005-fr-006-inv-004)
- [Q5. Action, kích thích và kẹp ctrl (FR-003, FR-004, INV-003)](#q5-action-kich-thich-va-kep-ctrl-fr-003-fr-004-inv-003)
- [Q6. Reward, kết thúc episode (FR-008, FR-009)](#q6-reward-ket-thuc-episode-fr-008-fr-009)
- [Q7. Tần số, bước vật lý, tái lập (FR-014, INV-002)](#q7-tan-so-buoc-vat-ly-tai-lap-fr-014-inv-002)
- [Q8. Quy mô tài liệu & stack](#q8-quy-mo-tai-lieu-stack)
- [Tổng kết](#tong-ket)


Mọi mục "ĐÃ ĐO" là kết quả chạy thật ngày 2026-10-09 trên máy phát triển (Linux gốc, 12 luồng CPU, Python 3.11.15 do `uv` cấp, chưa có NVIDIA) trong hai môi trường ảo tạm: **A** = `myosuite==3.0.0`, **B** = `myo-sim==0.2.3` + `gymnasium` mới nhất. Mã thăm dò chạy ở thư mục tạm, KHÔNG nằm trong repo. Mục "CHƯA KIỂM" là việc phải xác minh ở bước triển khai — plan không giả định kết quả. Các con số hiệu năng ở đây là thăm dò sơ bộ, KHÔNG dùng để suy ra thời gian huấn luyện (master plan XI.10).

<a id="q1-ghim-gymnasium13-theo-myosuite-hay-bo-myosuite-fr-015-fr-016-ac-5"></a>
## Q1. Ghim `gymnasium<1.3` theo MyoSuite hay bỏ MyoSuite? (FR-015, FR-016, AC-5)

- **Quyết định**: **bỏ MyoSuite** ở feature này; dùng `myo-sim==0.2.3` + `mujoco` + `gymnasium>=1.4,<1.5` (ĐÃ ĐO: 1.4.0). `myosuite` KHÔNG nằm trong `pyproject.toml`; `uv.lock` khoá phiên bản chính xác chỉ sau khi smoke test của môi trường đạt (FR-016).
- **Căn cứ (ĐÃ ĐO)**:
  - `uv pip install --dry-run myosuite==3.0.0 gymnasium==1.4.0` → "No solution found": `myosuite==3.0.0` yêu cầu `gymnasium<1.3`; cặp này không cùng tồn tại.
  - Môi trường A (`myosuite==3.0.0`) cài được và `import myosuite` chạy headless, nhưng kéo `gymnasium==1.2.3`, `onnxruntime==1.20.1`, `mjviser` và **≈ 76 gói**, ≈ 717 MB.
  - Môi trường B cài **20 gói** (kể cả `pytest`, `pyyaml`): `gymnasium==1.4.0`, `mujoco==3.15.0`, `myo-sim==0.2.3`, `numpy==2.4.6`, `glfw`, `pyopengl`…; `import mujoco, myo_sim, gymnasium` chạy khi không đặt `DISPLAY`; `gymnasium.utils.env_checker.check_env` qua trên một môi trường thăm dò bọc đúng `myoelbow_1dof6muscles.xml` (không lỗi; chỉ cảnh báo cận `±inf` của observation — thiết kế dưới đây dùng cận hữu hạn nên sẽ hết cảnh báo).
  - Feature này tự viết môi trường theo giao diện Gymnasium (yêu cầu gốc: `single_agent.py`) và chỉ cần mô hình XML của `myo-sim`; không dùng lớp môi trường, bộ sinh task hay trình xem của MyoSuite. Replay (con 4) dùng `mujoco.viewer` — có sẵn trong `mujoco` (import được ở B).
- **Phương án đã loại**: (A) ghim `gymnasium<1.3` theo MyoSuite — kéo ≈ 56 gói thừa và một bản `gymnasium` cũ để lấy những thứ không dùng, thêm bề mặt xung đột cho PyTorch/con 2; (C) `myosuite` + `gymnasium` mới bằng `override-dependencies` — lách ràng buộc đã khai của tác giả, không có bằng chứng tương thích.
- **CHƯA KIỂM (giao con 2)**: tương thích `gymnasium 1.4` với thư viện PPO/`torch` sẽ chọn ở con 2 — con 2 phải đo và ghi vào plan của nó; nếu con 2 buộc lùi `gymnasium`, đổi ghim ở `pyproject.toml` và chạy lại `verify_clean_install` (AC-5).
- **Cách chứng minh AC-5**: script `scripts/verify_clean_install.py` tạo môi trường ảo mới trong thư mục tạm, cài theo `uv.lock` (`uv sync --frozen`), chạy bộ test của môi trường, trả mã thoát; đầu ra được ghi vào `logs/m1/verify_clean_install.json` (chạy khi triển khai, không phải bây giờ).

<a id="q2-mo-hinh-va-dau-mut-tay-fr-001-fr-005-fr-010"></a>
## Q2. Mô hình và đầu mút tay (FR-001, FR-005, FR-010)

- **Quyết định**: dùng lại `load_muscle_model` của 001 (`mma_ai.physics.body_model`) để nạp `myoelbow_1dof6muscles.xml` và tính `MuscleModelInfo` (số cơ, số actuator không phải cơ, SHA-256, tên cơ). Đầu mút tay = site **`wrist`** (`site_xpos`), tên site đặt trong cấu hình `configs/elbow_env.yaml`.
- **Căn cứ (ĐÃ ĐO)**: `nu = 6`, `nq = nv = 1`, khớp `r_elbow_flex` giới hạn `[0, 2.26893]` rad, 6 tendon, `nsensor = 0` (không có sensor sẵn ⇒ observation đọc thẳng `qpos/qvel/act/site_xpos`), site `wrist` tồn tại, cả 6 actuator `gaintype = muscle (2)`, `actuator_ctrlrange = [0.001, 1]`, `jnt_margin = 0`, khớp có `damping = 0,5`. SHA-256 tệp XML bắt đầu `384dcb555561287f…`.
- **Phát hiện quan trọng #1 (giới hạn mềm)**: dù khớp có `limited`, trong rollout ngẫu nhiên `qpos` đo được trong `[-0,1106; 2,2273]` rad — khớp **vượt nhẹ giới hạn dưới** (mềm). Cận chuẩn hoá của góc khớp vì vậy phải rộng hơn `[-1,1]` (xem Q4).
- **Phát hiện quan trọng #2 (rất nhanh)**: dưới kích thích tối đa của nhóm gập (BIClong/BICshort/BRA = 1, còn lại 0), khuỷu đi từ 0 tới 2,0 rad chỉ trong **4 hành động** (16 bước × 0,0025 s = 0,04 s mỗi hành động ⇒ ≈ 0,16 s); vận tốc khớp đỉnh quan sát được `|qvel|` ≈ 20,9 rad/s (random: `[-18,6; 14,5]`). Hệ quả: dung sai 0,02 m và bước 25 Hz là bài toán điều khiển tinh; số hành động tối đa 100 (≈ 4 s) dư rộng để tới mục tiêu.
- **Phát hiện quan trọng #3 (tất định)**: cùng seed, cùng chuỗi hành động ⇒ cùng `qpos/qvel/act` (SHA-256 trùng giữa hai lần chạy) — nền cho INV-002.

<a id="q3-hinh-hoc-tam-voi-bo-sinh-muc-tieu-fr-010-fr-011-fr-012-inv-001-inv-002"></a>
## Q3. Hình học tầm với & bộ sinh mục tiêu (FR-010, FR-011, FR-012, INV-001, INV-002)

- **Quyết định**:
  1. Mục tiêu = vị trí site `wrist` ở một góc khớp θ trong `[θ_lo + m, θ_hi − m]` (m = `angle_margin_rad`, khởi đầu 0,05) tính bằng động học thuận trên một `MjData` **riêng** (không phải `MjData` của mô phỏng ⇒ không chạm trạng thái episode, INV-003). Mọi mục tiêu vì thế với tới được (FR-010).
  2. **Tách theo khối cung (arc-block split)**: tham số hoá cung theo độ dài cung `s`, chia đoạn khả dụng thành các khối bề rộng `split_block_m` (khởi đầu 0,05 m); seed xáo trộn rồi gán khối cho train hoặc test theo tỉ lệ `n_test/(n_train+n_test)` (làm tròn lên, mỗi vai ≥ 1 khối); thu hẹp mỗi khối `min_separation_m/2` ở hai biên ⇒ mọi cặp (train, test) cách nhau ≥ `min_separation_m` (INV-001) mà không cần rejection sampling.
  3. Trong mỗi vai, đặt mục tiêu bằng lấy mẫu phân tầng (đều theo `s` có nhiễu theo seed) trên các khối của vai đó — phủ đều, không trùng điểm; sinh bằng `numpy.random.default_rng(seed)` (INV-002).
  4. **Khoảng cách tối thiểu đo Euclid 3D** (cùng thước với dung sai tới đích); dây cung ≤ cung nên biên thu hẹp mỗi khối là `1,1 · min_separation_m / 2` (hệ số an toàn 1,1) và cấu hình phải thoả `split_block_m > 1,1 · min_separation_m`. Nguyên mẫu thăm dò (thư mục tạm) với seed 42: 200/50 mục tiêu ⇒ khối train `[1,2,3,4,5,8,9,10]`, khối test `[0,6,7]`, khoảng cách Euclid nhỏ nhất train–test **0,02285 m ≥ 0,02** (ĐÃ ĐO), 200 điểm train phân biệt, hai lần sinh cùng seed giống nhau.
  5. Sau sinh, bộ sinh TỰ KIỂM giao rỗng + khoảng cách tối thiểu và ném `TargetConfigError` nếu vi phạm (phòng hồi quy); cấu hình bất khả thi (xem Edge Case) cũng ném lỗi nêu giới hạn.
- **Căn cứ (ĐÃ ĐO)**: do khớp 1 bậc tự do, đầu mút tay chạy trên một cung 1 chiều: độ dài cung toàn dải ≈ 0,597 m (dây cung 0,477 m), hộp bao `x ∈ [-0,223; -0,197]`, `y ∈ [-0,175; 0,084]`, `z ∈ [0,842; 1,277]`; đoạn khả dụng sau lề 0,05 rad ≈ 0,571 m. Với khối 0,05 m ⇒ 11 khối; tỉ lệ 50/250 ⇒ 3 khối test, 8 khối train. Mỗi khối còn bề rộng khả dụng `0,05 − 0,02 = 0,03` m.
- **Hệ quả cần ghi**: với dung sai 0,02 m, số vị trí "phân biệt về mặt điều khiển" chỉ cỡ 0,571/0,04 ≈ 14 — 200 train/50 test mục tiêu mật độ dày hơn nhiều so với độ phân giải đích; con số 200/50 vẫn giữ (Tự chốt trong spec, cấu hình được) để thống kê đánh giá có nhiều mẫu, nhưng con 3 KHÔNG được diễn giải 50 mục tiêu test như 50 tình huống độc lập. Ghi vào báo cáo của con 3 (nhắc ở đây để không mất).
- **Phương án đã loại**: (a) rejection sampling train rồi test với khoảng cách tối thiểu — với 200 điểm dày trên cung 0,57 m, test hầu như không có chỗ (khoảng cách trung bình 2,9 mm ≪ 0,02 m) ⇒ vòng lặp vô hạn; (b) chia theo chỉ số (xen kẽ) — test nằm sát train, không đạt khoảng cách tối thiểu; (c) mục tiêu 3D tuỳ ý trong khối hộp — không với tới được với khuỷu 1 bậc tự do (Tự chốt trong spec).
- **Mở rộng nằm ngoài feature (không làm)**: tập test "ngoài vùng" (extrapolation) — là câu hỏi đánh giá của con 3.

<a id="q4-observation-bo-cuc-chuan-hoa-can-fr-005-fr-006-inv-004"></a>
## Q4. Observation: bố cục, chuẩn hoá, cận (FR-005, FR-006, INV-004)

- **Quyết định**: vector 14 chiều `float32`, thứ tự cố định:

  | Chỉ số | Thành phần | Số chiều | Chuẩn hoá | Cận khai báo |
  |---|---|---|---|---|
  | 0 | góc khớp `qpos` | 1 | `(q − q_mid) / q_half`, với `q_mid, q_half` từ `jnt_range` | `[-1,5; 1,5]` |
  | 1 | vận tốc khớp `qvel` | 1 | `qvel / qvel_scale` (khởi đầu `qvel_scale = 25 rad/s`), **kẹp** về cận | `[-1; 1]` |
  | 2–7 | kích hoạt cơ `act` (6) | 6 | giữ nguyên (đã trong [0,1] do động học kích hoạt cơ Hill) | `[0; 1]` |
  | 8–10 | vị trí đầu mút tay (`site_xpos` `wrist`) | 3 | `(p − c) / h` (c = tâm hộp bao cung, h = nửa cạnh dài nhất, đẳng hướng) | `[-1,5; 1,5]` |
  | 11–13 | vị trí mục tiêu | 3 | cùng phép chuẩn hoá vị trí | `[-1,5; 1,5]` |

  Tổng 1 + 1 + 6 + 3 + 3 = **14** (khớp spec). `c, h, q_mid, q_half` tính từ mô hình lúc khởi tạo (quét cung) và ghi vào hồ sơ; không hằng số rải trong mã (FR-014).
- **Căn cứ**: qpos vượt −0,11 rad (Q2 #1) ⇒ cận ±1,5 dư cho chuẩn hoá `/q_half ≈ 1,134`: giá trị tối thiểu ≈ −1,097; `qvel` đỉnh 20,9 rad/s ⇒ `qvel_scale = 25` kẹp hiếm khi, nhưng phải kẹp để đảm bảo INV-004 khi có xung đột va chạm bất thường. Vị trí chuẩn hoá đẳng hướng vì trục x của cung chỉ rộng 2,6 cm — chuẩn hoá theo từng trục sẽ phóng đại.
- **Quy tắc kiểm** (FR-006): `validate_observation` kiểm chiều, hữu hạn, nằm trong cận; chỉ `qvel` được kẹp (có ghi `info["qvel_clipped"]`), các thành phần khác ngoài cận ⇒ `ObservationError` (không trả ra). Mất ổn định số (NaN/Inf ở `qpos/qvel/act/actuator_force` hoặc `data.warning` > 0) ⇒ `PhysicsInstabilityError` (tái dùng `numeric_health` của 001).
- **Phương án đã loại**: chuẩn hoá chạy (running mean/std) trong môi trường — việc của PPO (con 2, "chuẩn hoá observation"); cận `±inf` — `check_env` cảnh báo và không "xác định miền giá trị" (KQ-2).

<a id="q5-action-kich-thich-va-kep-ctrl-fr-003-fr-004-inv-003"></a>
## Q5. Action, kích thích và kẹp ctrl (FR-003, FR-004, INV-003)

- **Quyết định**: `action_space = Box(0, 1, (6,), float32)`. Mỗi `step` gọi `validate_activation` của 001 (ném `ActivationError` nêu giá trị vi phạm khi sai kích thước/NaN/Inf/ngoài [0,1]) rồi `HeadlessSimulator.step(activation, n_steps=16)` — đường ghi duy nhất là `data.ctrl`. `info["ctrl_effective"]` ghi giá trị sau khi MuJoCo kẹp về `[0.001, 1]` bên cạnh giá trị yêu cầu (đã nêu ở 001 research Q3 #1).
- **Căn cứ**: tái dùng thay vì viết lại — giữ một chủ cho mã "ghi ctrl" và kiểm tra hợp lệ (constitution IX: mỗi thứ MỘT chỗ).
- **Kiểm cấu trúc** (AC-4): test khẳng định `model.nu == 6`, mọi `actuator_gaintype == muscle`, `actuator_biastype == muscle`, `actuator_dyntype == muscle`, không có motor/position actuator; test khẳng định `qpos/qvel/site_xpos` không bị ghi ngoài `mj_step` (theo dõi: so sánh trạng thái trước/sau `reset` hoặc chạy bước 0 hành động không đổi hình học… cách cụ thể do task chọn, assert thẳng trên sản phẩm).
- **Phương án đã loại**: tạo lớp ghi `ctrl` mới trong `environment/` — trùng chức năng với `HeadlessSimulator`; cho phép action ngoài [0,1] rồi kẹp âm thầm — vi phạm FR-003.
- **Giả định giao diện với 001 (CHƯA KIỂM — 001 chưa có mã)**: `HeadlessSimulator` cho đọc (chỉ đọc) `model`/`data` và `LoadedModel` có `info: MuscleModelInfo`; nếu khi triển khai 001 chưa cung cấp, task của 002 chỉ ĐƯỢC thêm accessor đọc-chỉ vào đúng tệp đó (sau task của 001), không sao chép mã.

<a id="q6-reward-ket-thuc-episode-fr-008-fr-009"></a>
## Q6. Reward, kết thúc episode (FR-008, FR-009)

- **Quyết định** (tham số khởi tạo trong `configs/elbow_env.yaml`, CHƯA KIỂM bằng huấn luyện — con 2 sẽ chỉnh):
  - `reward = − w_dist · (d / d_ref) − w_effort · mean(u²)` với `d` = khoảng cách Euclid đầu mút tay–mục tiêu (m), `d_ref = 0,5` m, `w_dist = 1,0`, `w_effort = 0,01`, `u` = action yêu cầu đưa vào bước. Hai thành phần được trả riêng trong `info` (`reward_dist`, `reward_effort`).
  - `terminated` khi `d ≤ tolerance_m` (khởi đầu 0,02); `truncated` khi số hành động ≥ `max_actions` (khởi đầu 100); khi cả hai xảy ra cùng bước thì `terminated=True` (tới mục tiêu thắng).
- **Căn cứ**: reward dày, hữu hạn, đơn điệu theo khoảng cách ⇒ đủ cho AC-2 (hữu hạn) và Story 4; thành phần "tiến tới mục tiêu" biểu diễn bằng −khoảng cách (dày) thay vì hiệu khoảng cách giữa hai bước để không phụ thuộc trạng thái bước trước. `d_ref` bằng cỡ cung để thành phần ~ O(1).
- **Phương án đã loại**: thưởng thưa (chỉ +1 khi tới) — PPO khó học ở M1; thêm thưởng tới đích/phạt thời gian — thành phần thứ ba, ngoài hai thành phần của yêu cầu.

<a id="q7-tan-so-buoc-vat-ly-tai-lap-fr-014-inv-002"></a>
## Q7. Tần số, bước vật lý, tái lập (FR-014, INV-002)

- **Quyết định**: `physics_timestep_s = 0,0025` gán qua `model.opt.timestep` (không sửa XML; mặc định mô hình 0,002), `substeps_per_action = 16`. Trạng thái đầu episode cố định: `mj_resetData` (qpos = 0, act = 0); độ ngẫu nhiên của một episode chỉ đến từ việc chọn mục tiêu bằng `self.np_random` của Gymnasium (`reset(seed)`).
- **Căn cứ (ĐÃ ĐO, sơ bộ — không phải benchmark)**: bước vật lý 0,0025 s + 16 bước/hành động ⇒ ≈ 9,1 nghìn hành động/s ≈ 1,46×10⁵ bước vật lý/s trên CPU phát triển (một môi trường, Python thuần). KHÔNG dùng để suy thời gian huấn luyện; số chính thức thuộc benchmark 001/con 2.
- **Hệ quả**: ở nhịp 25 Hz, 100 hành động ≈ 4 s mô phỏng; thời gian thực tế một episode ≈ 11 ms CPU (thăm dò).

<a id="q8-quy-mo-tai-lieu-stack"></a>
## Q8. Quy mô tài liệu & stack

- **Quyết định**: một bounded context duy nhất (mô phỏng cơ–xương, cùng 001) ⇒ không tạo `docs/02-strategic/`, `docs/03-tactical/`, `rbac.md` (không phân quyền); không có API mạng ⇒ hợp đồng là API Python + định dạng JSON ở `contracts/`. `docs/` hiện chỉ có `00-input/`; không có tệp chiến lược/chiến thuật để đồng bộ. Stack không đổi so với `.ai/stack-proposal.yml` đã ghi ở 001 (`python-mujoco-cli`) ⇒ chỉ bổ sung một dòng `evidence`, không tạo preset mới.
- **Phương án đã loại**: tách `mma_ai.environment` thành gói riêng/repo riêng — chưa có lý do.

<a id="tong-ket"></a>
## Tổng kết

Không còn câu hỏi chưa giải quyết. Việc CHƯA KIỂM được giao thành bước triển khai bắt buộc có kết quả ghi lại: (1) tương thích `gymnasium 1.4` với thư viện PPO/`torch` — con 2; (2) chạy `verify_clean_install` trên môi trường ảo sạch — AC-5 của feature này; (3) giao diện đọc-chỉ `model`/`data` của `HeadlessSimulator` từ 001 (Q5); (4) giá trị mặc định reward/dung sai được chốt lại sau khi con 2 chạy PPO thử.
