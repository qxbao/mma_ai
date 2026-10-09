---
id: "RES-003"
title: "M1 (2/4) — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Nghiên cứu Phase 0 — M1 (2/4): Huấn luyện PPO, checkpoint, hồ sơ tái lập & giao diện quan sát

Mọi mục "ĐÃ ĐO" là kết quả chạy thật ngày 2026-10-09 trên máy phát triển (Linux gốc, 12 luồng CPU, Python 3.11 do `uv` cấp, **chưa có NVIDIA**) trong môi trường ảo tạm: `torch 2.14.1+cpu`, `tensorboard 2.21.0`, `gymnasium 1.4.0`, `numpy 2.4.6`, `mujoco 3.15.0`, `myo-sim 0.2.3`. Mã thăm dò chạy ở thư mục tạm, KHÔNG nằm trong repo. Mục "CHƯA KIỂM" là việc phải xác minh ở bước triển khai — plan không giả định kết quả. Các con số hiệu năng ở đây là thăm dò sơ bộ, KHÔNG dùng để suy ra thời gian huấn luyện (master plan XI.10).

## Q1. Tự cài PPO hay dùng thư viện (Stable-Baselines3)? (FR-001…FR-009)

- **Quyết định**: **tự cài PPO tối giản trên PyTorch** (mô-đun `ppo.py` + `networks.py` + `normalizer.py`); KHÔNG thêm `stable-baselines3`.
- **Căn cứ (ĐÃ ĐO)**: `uv pip install --dry-run "gymnasium>=1.4,<1.5" stable-baselines3 tensorboard myo-sim==0.2.3 mujoco` giải được (51 gói: `stable-baselines3==2.9.0`, `gymnasium==1.4.0`, `torch==2.14.1`, `tensorboard==2.21.0`); không có `stable-baselines3` thì 50 gói. Nghĩa là **chi phí phụ thuộc không phải lý do loại** — SB3 cài được cùng `gymnasium 1.4`. Lý do loại là **toàn vẹn checkpoint và kiểm soát tất định**:
  1. INV-004 đòi MỘT checkpoint khứ hồi đủ policy, critic, bộ chuẩn hoá observation, optimizer, seed và trạng thái sinh số ngẫu nhiên. SB3 lưu `VecNormalize` ở tệp riêng và không lưu trạng thái RNG; bọc lại để ép vào một tệp là viết thêm mã quanh thư viện lớn — không rẻ hơn tự cài ~300 dòng.
  2. FR-010/FR-020 cần móc dữ liệu riêng (kích hoạt 6 cơ theo bước, snapshot tiến trình, đếm NaN/Inf) vào vòng lặp; tự cài thì vòng lặp là của dự án.
  3. Yêu cầu gốc đã đặt tên mô-đun `ppo.py` trong phạm vi.
- **Rủi ro của quyết định và cách chặn**: PPO tự cài dễ sai âm thầm. Test bắt buộc (tên kế hoạch ở `plan.md`): GAE khớp giá trị tính tay; mục tiêu clip đúng dấu; chuẩn gradient sau clipping ≤ ngưỡng; và **`test_learns_toy_env`** — PPO cải thiện return trên một môi trường Gymnasium đồ chơi tất định (tới điểm trên đoạn thẳng) trong số bước nhỏ, để phát hiện lỗi thuật toán mà không phụ thuộc môi trường cơ. SB3 chỉ dùng làm tham chiếu đọc khi viết, không là phụ thuộc.
- **Phương án đã loại**: (A) SB3 + callback + gói lại checkpoint — như trên; (B) CleanRL kiểu một tệp sao chép — không có giấy phép/bảo trì rõ trong repo và vẫn phải sửa tương đương.
- **Đóng việc CHƯA KIỂM của con 1 (Q1 của 002)**: *tương thích `gymnasium 1.4` với `torch`* — **ĐÃ ĐO**: cài thật `torch==2.14.1+cpu` + `tensorboard==2.21.0` + `gymnasium==1.4.0` + `numpy==2.4.6` + `myo-sim==0.2.3` + `mujoco==3.15.0` + `jsonschema` vào một venv sạch, không xung đột; không cần lùi `gymnasium`. Còn **CHƯA KIỂM**: bản `torch` CUDA có `sm_120` (Blackwell) trên máy đích — giao research Q6 của 001 (máy phát triển không có NVIDIA); dry-run bản mặc định kéo bánh xe CUDA 13 (`nvidia-*-cu13`) — pin cuối chọn sau khi 001 đo `arch_list`.

## Q2. Tham số hoá policy và đảm bảo `u ∈ [0,1]^6` (FR-005, INV-002)

- **Quyết định**: actor xuất trung bình của phân phối Gauss **thô** `a ∈ ℝ⁶` với `log_std` là tham số học độc lập với observation; hành động đưa vào môi trường là `u = sigmoid(a)`; `log_prob` tính trên `a`. Hành động xác định (đánh giá, kiểm khứ hồi checkpoint) là `sigmoid(mean)`. Kích hoạt tanh, khởi tạo trực giao, critic cùng cấu trúc xuất 1 giá trị.
- **Căn cứ**: `sigmoid` trả giá trị trong (0,1) nên luôn qua `validate_activation` của 001 (không bao giờ bị từ chối), không thêm hiệu chỉnh mật độ như tanh-squash, và vẫn khả vi. Từ góc nhìn PPO, `sigmoid` là một phần của môi trường — ratio và KL dùng `a`, nên đúng toán.
- **Phương án đã loại**: kẹp `clip(a,0,1)` — gradient bằng 0 ngoài [0,1], dồn khối lượng tại biên; phân phối Beta — biên rõ nhưng khó khởi tạo/ổn định hơn cho baseline; tanh-squash có hiệu chỉnh log-det — thêm phức tạp không cần thiết khi chỉ cần miền [0,1].
- **Lưu ý đã biết**: MuJoCo kẹp ctrl về `[0.001, 1]` (001); môi trường ghi `ctrl_effective`. Không phải việc của feature này.

## Q3. Chuẩn hoá observation (FR-003)

- **Quyết định**: ước lượng trung bình/phương sai chạy (gộp song song kiểu Welford) trên observation THÔ của môi trường (đã có cận hữu hạn từ con 1), cập nhật CHỈ khi thu rollout; áp `(x − mean) / sqrt(var + ε)` rồi kẹp `±clip_obs` (mặc định 10) trước actor và critic. Thống kê (`mean`, `var`, `count`) nằm trong checkpoint. Không chuẩn hoá reward (ngoài yêu cầu).
- **Căn cứ**: nghiên cứu Phase 0 của con 1 (Q4) đã loại chuẩn hoá chạy khỏi môi trường và giao con 2. Cập nhật chỉ lúc thu mẫu giữ cho cùng seed ⇒ cùng thống kê (tất định).
- **Phương án đã loại**: chuẩn hoá bằng hằng số cố định — môi trường đã làm; BatchNorm — lệ thuộc kích thước batch, phá tính tất định khi suy luận một mẫu.

## Q4. Siêu tham số khởi đầu và tốc độ thăm dò (FR-018) — KHÔNG phải benchmark

- **Quyết định** (khởi đầu, chưa tinh chỉnh; nằm ở `configs/train_elbow.yaml`): `learning_rate 3e-4`, `clip_range 0,2`, `gamma 0,99`, `gae_lambda 0,95`, `entropy_coef 0`, `value_coef 0,5`, `max_grad_norm 0,5`, `n_steps 2048`, `batch_size 64`, `n_epochs 10`, `log_std_init −0,5`, `checkpoint.every_updates 10`, `total_timesteps 100 000` (**giá trị giữ chỗ để chạy được, không phải ngân sách huấn luyện** — master plan XI.10), `rel_tolerance 1e-6`, `head_updates 10`, `torch_threads 1`. Cấu hình smoke `configs/train_elbow_smoke.yaml`: `total_timesteps 4096`, `every_updates 1`.
- **Căn cứ**: bộ mặc định PPO thông dụng cho điều khiển liên tục (Schulman và cộng sự 2017; mặc định của các thư viện PPO phổ biến). Không có bằng chứng ở đây rằng chúng hội tụ trên khuỷu tay — con 3 đo; con 2 chỉ đảm bảo đường train, lưu/nạp, tái lập và quan sát.
- **Số thăm dò (ĐÃ ĐO, sơ bộ, CPU phát triển, 1 luồng torch, mô hình thật)**: một lượt cập nhật (2048 mẫu × 10 epoch × minibatch 64 = 320 bước tối ưu) mất 0,60–0,80 s; thu mẫu gồm suy luận actor + 16 `mj_step`/hành động chạy ≈ 7,35 nghìn bước môi trường/s; checkpoint (actor, tối ưu, RNG) ≈ 1,4 MB; 1000 scalar TensorBoard ghi trong 0,033 s; RSS đỉnh ≈ 591 MB. Đây là cỡ độ lớn để đặt tần số snapshot và kích thước checkpoint, **không** là thời gian huấn luyện; benchmark chính thức do `scripts/benchmark_train.py` đo trên máy đích.
- **Hệ quả**: một chu kỳ thu mẫu + cập nhật cỡ giây ⇒ snapshot giao diện ghi mỗi ≥ 1 s (kể cả giữa lúc thu mẫu) mới thoả độ trễ 5 s (Q8).

## Q5. Định dạng checkpoint & ghi an toàn (FR-006…FR-009, INV-004)

- **Quyết định**: mỗi checkpoint là MỘT tệp `torch.save` chứa từ điển các giá trị nguyên thuỷ/tensor: `actor`, `critic` (state_dict), `obs_normalizer`, `optimizer`, `seed`, `rng_state` (numpy `bit_generator.state`, `torch.get_rng_state()`, trạng thái RNG của GPU nếu có, `np_random` của môi trường), `update_idx`, `env_steps`, `model_sha256`, `library_versions`, `config`. Kèm `*.meta.json` theo [checkpoint-meta.schema.json](contracts/checkpoint-meta.schema.json) và con trỏ `checkpoints/latest.json`. Nạp bằng `torch.load(..., weights_only=True)`.
- **Ghi an toàn**: ghi ra `*.tmp` → quét hữu hạn mọi tensor → `fsync` → `os.replace` sang tên cuối → cập nhật `latest.json` (cũng bằng thay thế nguyên tử). Tên có chỉ số lượt (`ckpt_u000010.pt`) nên KHÔNG bao giờ ghi đè checkpoint cũ cùng run (FR-007). Cuối run luôn ghi thêm checkpoint `final` (để smoke ngắn hơn chu kỳ vẫn có ≥ 1 checkpoint — SC-001).
- **Căn cứ (ĐÃ ĐO)**: từ điển chứa `np.random.default_rng(...).bit_generator.state` (số nguyên > 2⁶⁴), tensor và chuỗi **nạp được bằng `weights_only=True`** (không cần `pickle` tuỳ ý) và RNG tiếp tục cho cùng dãy sau nạp; nạp lại `state_dict` actor cho **sai khác tuyệt đối tối đa 0,0** trên lô 64 observation (CPU) — dư rộng so với dung sai 1×10⁻⁶.
- **Phương án đã loại**: `pickle` nguyên đối tượng — nạp mã tuỳ ý từ tệp, vi phạm tinh thần an toàn dữ liệu và gãy khi đổi tên lớp; lưu nhiều tệp rời (actor, normalizer…) — mất tính nguyên tử, dễ lệch phiên bản giữa các tệp.
- **Hash XML**: checkpoint ghi `model_sha256`; train tiếp từ checkpoint có hash khác hash hiện tại ⇒ từ chối (Edge Case), chỉ cho nạp suy luận kèm cảnh báo.

## Q6. Thư mục run, hồ sơ và train tiếp (FR-009, FR-011, FR-012, INV-001)

- **Quyết định**: `runs/<run_id>/` với `run_id = <UTC YYYYMMDDTHHMMSSZ>_<stage>_s<seed>[-n]`; tạo bằng `os.mkdir` loại trừ (lỗi nếu đã có ⇒ thử hậu tố `-2`, `-3`… tới 100 rồi báo lỗi) — không ghi đè (INV-001). Cấu trúc: `manifest.json` · `config.yaml` (cấu hình đã phân giải) · `checkpoints/` · `tb/` · `metrics.jsonl` (một dòng/lượt cập nhật) · `progress.json` · `ui.json`. Hồ sơ [run-manifest.schema.json](contracts/run-manifest.schema.json) ghi lúc bắt đầu (`status: running`) và thay thế nguyên tử lúc kết thúc (`done`/`error`/`interrupted`); đây là tệp của chính run nên không vi phạm INV-001.
- **Train tiếp**: `--resume <đường dẫn checkpoint>` tạo run MỚI, khôi phục optimizer/normalizer/RNG, ghi `resumed_from {run_id, checkpoint, checkpoint_sha256}`; bộ đếm `update_idx`/`env_steps` tiếp nối từ checkpoint; `total_timesteps` tính theo bộ đếm tiếp nối. Không hứa hẹn rằng train tiếp trùng từng bit với chạy liền một mạch (episode đang dở bị bỏ khi dừng); hứa hẹn là **trạng thái học được và thống kê chuẩn hoá liên tục**.
- **Reward metrics** trong hồ sơ: `n_updates`, `n_episodes`, `head_mean_return` (K lượt đầu — đầu vào so sánh tái lập), `first/last_mean_return`, `success_rate` (tỉ lệ episode terminated). Chuỗi đầy đủ ở `metrics.jsonl` và TensorBoard.
- **Phương án đã loại**: cho phép `--run-id` tự đặt — dễ trùng và ghi đè; ghi checkpoint vào thư mục dùng chung — mất tính cô lập từng run.

## Q7. Tất định và dung sai tái lập (FR-001, FR-014, INV-004; KQ-4, AC-4)

- **Quyết định**: một seed gốc → (a) `torch.manual_seed`; (b) `numpy.random.default_rng(seed)` cho xáo minibatch; (c) `env.reset(seed=seed)` lần đầu rồi các lần sau `reset()` (luồng `np_random` của môi trường tiếp nối, tất định); `torch.set_num_threads(torch_threads)` (mặc định 1); `torch.use_deterministic_algorithms(True)` (và `CUBLAS_WORKSPACE_CONFIG=:4096:8` khi CUDA). Dung sai: lệch **tương đối ≤ 1×10⁻⁶** tại mỗi điểm của đường reward trung bình mỗi episode ở K = min(10, số lượt thực chạy) lượt đầu, **chỉ giữa hai run cùng loại thiết bị, cùng phiên bản thư viện, cùng số luồng**. Hồ sơ ghi dung sai, loại thiết bị, số luồng, cờ tất định.
- **Căn cứ (ĐÃ ĐO, thăm dò)**: hai lần huấn luyện cùng seed (2 mạng 2×256, 320 bước Adam có clipping gradient, xáo minibatch bằng RNG có seed, 1 luồng CPU) cho **hash SHA-256 trọng số trùng nhau**; seed khác cho hash khác. Mô hình MuJoCo cũng tất định theo seed (research Q2 của con 1). Vì vậy ngưỡng 1×10⁻⁶ chặt hơn mức cần (kỳ vọng sai khác = 0 trên CPU).
- **CHƯA KIỂM**: (1) sai khác thực tế GPU↔GPU (thứ tự cộng dồn có thể khác dù `deterministic`) — đo trên máy đích; nếu vượt 1×10⁻⁶ thì nới dung sai GPU bằng cấu hình và ghi số đo; (2) CPU↔GPU **không cam kết** (Tự chốt trong spec); (3) tác động của số luồng torch > 1.
- **Phương án đã loại**: cam kết trùng từng bit giữa CPU và GPU — không đạt được; cam kết "chỉ cùng hình dạng đường cong" — không kiểm được bằng máy.

## Q8. Hình thức giao diện quan sát khi train (FR-020…FR-024, AC-7, C-0009)

- **Câu hỏi giao cho plan**: TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai? Phạm vi đã được người dùng xác nhận (Q-0001, C-0010): giao diện thuộc con 2, hình thức do plan quyết định, chỉ-đọc, tiến trình riêng, không kéo chậm vòng train; bảng tóm tắt phương án/lý do/chi phí nằm ở `plan.md` mục "Giao diện quan sát".
- **Quyết định**: **TensorBoard (chi tiết lịch sử, bắt buộc theo FR-010) + bảng điều khiển web nhẹ (đáp ứng danh sách AC-7)** là cấu hình MẶC ĐỊNH; **MuJoCo Viewer 3D là TUỲ CHỌN** (`--view3d`, mặc định tắt) chạy ở tiến trình riêng.
- **Cấu tạo**:
  - Trainer chỉ GHI: TensorBoard (`tb/`), `metrics.jsonl`, và `progress.json` (snapshot theo [progress-snapshot.schema.json](contracts/progress-snapshot.schema.json), thay thế nguyên tử, tối đa mỗi `snapshot_interval_s = 1,0` s, kể cả giữa lúc thu mẫu).
  - Bảng điều khiển là **tiến trình riêng** (`scripts/watch_train.py`, do `train.py` khởi chạy nền mặc định `--ui web`, tắt bằng `--ui none`) dùng `http.server` của thư viện chuẩn: `GET /api/progress` trả nguyên văn `progress.json`; `GET /` trả MỘT trang tĩnh (HTML + JS nội tuyến, không tải CDN) thăm dò mỗi `poll_interval_ms = 2000` ms và vẽ reward, loss, 6 thanh kích hoạt cơ, env steps/s, thanh `env_steps / total_steps`, trạng thái checkpoint. Chỉ nhận GET (các phương thức khác ⇒ 405); chỉ lắng nghe địa chỉ loopback (cấu hình bị từ chối nếu `host` không phải loopback); không import `trainer`/`ppo` (đọc-chỉ về cấu trúc, INV-005). Tiến trình giao diện tự ghi `ui.json` (URL, pid) để `train.py` in URL và ghi vào hồ sơ.
  - Chọn cổng 0 ⇒ hệ điều hành cấp cổng trống; cổng cố định bị chiếm ⇒ giao diện báo lỗi và thoát, `train.py` cảnh báo rồi **vẫn train** (INV-005).
  - Hiển thị 3D (`monitoring/viewer3d.py`): tiến trình riêng, `mujoco.viewer.launch_passive` trên `MjData` riêng; mỗi vài giây đọc `checkpoints/latest.json`, nạp policy mới nhất (xác định) và chạy episode trên bản sao môi trường ở tập train; cần màn hình — thiếu `DISPLAY` ⇒ in "3D không khả dụng" và thoát, không ảnh hưởng train. Không dùng khi benchmark thường lệ.
- **Độ trễ**: snapshot ≤ 1 s sau số liệu + thăm dò ≤ 2 s ⇒ ≤ 3 s < 5 s (NFR-PERF-002). **CHƯA KIỂM** bằng đo: test `test_snapshot_latency_le_5s`.
- **Chi phí (ĐO ở triển khai — CHƯA KIỂM)**: trainer tốn một lần ghi tệp JSON nhỏ mỗi ≥ 1 s (≪ 1 ms); tiến trình giao diện tốn CPU của một luồng cho vài yêu cầu HTTP/2 s. `scripts/benchmark_train.py` chạy ≥ 5 lần xen kẽ bật/tắt, cùng seed/cấu hình, so trung vị env steps/s (ngưỡng ≥ 0,90 — NFR-PERF-001) và ghi chênh lệch CPU/RAM/VRAM vào [train-benchmark.schema.json](contracts/train-benchmark.schema.json). Chi phí 3D chỉ đo khi có màn hình, nếu không thì ghi `measured:false` kèm lý do.
- **Phương án đã loại**: (a) chỉ TensorBoard — thiếu env steps/s, số bước / tổng, trạng thái checkpoint, 6 cơ cạnh nhau trên một màn; vẫn giữ như log chi tiết; (b) Streamlit/Gradio/Flask/Dash — thêm phụ thuộc nặng cho một trang số liệu, thêm bề mặt xung đột phiên bản; (c) giao diện terminal (TUI) — không phải "cổng/URL hoặc cửa sổ", khó xem từ xa qua trình duyệt; (d) cho giao diện điều khiển/dừng train — ngoài yêu cầu ("chỉ ĐỌC"); (e) 3D mặc định bật — trái master plan XI.8.

## Q9. Đo tài nguyên, thông lượng (FR-012, FR-013, NFR-RES-001)

- **Quyết định**: tái dùng `mma_ai.diagnostics` của 001 (phiên bản thư viện, `peak_ram_mb` bằng `resource.getrusage`, dò GPU/`nvidia-smi`); bổ sung trong `learning/resources.py`: `cpu_utilization_pct = process_time / (wall × số lõi logic) × 100`, `vram_peak_mb = torch.cuda.max_memory_allocated()/2²⁰` khi có CUDA, `gpu_utilization_pct` = trung bình các mẫu `nvidia-smi --query-gpu=utilization.gpu` lấy mỗi ≥ 5 s (null khi không có). `env_steps_per_second = env_steps / thời gian thu mẫu + cập nhật`; `wall_clock_seconds` đo bằng `time.perf_counter()`. Không thêm `psutil`/`pynvml` (cùng quyết định ở 001).
- **CHƯA KIỂM**: GPU trên máy đích; `nvidia-smi` không có ở máy phát triển ⇒ các trường GPU ghi `null`, hợp lệ theo schema.

## Q10. Bảo vệ số học & lỗi huấn luyện (FR-007, FR-017, NFR-REL-001)

- **Quyết định**: sau MỖI lượt cập nhật quét hữu hạn loss và mọi tham số; trước MỖI lần ghi checkpoint quét lại mọi tensor. Phát hiện NaN/Inf ⇒ `NonFiniteError` (nêu lượt, đại lượng, số phần tử), hồ sơ `status:error`, `numeric_health` ghi số đếm, mã thoát 1, **không ghi checkpoint mới**, checkpoint hợp lệ trước đó giữ nguyên. `PhysicsInstabilityError` của môi trường (con 1) truyền nguyên văn lên và cũng thành `status:error`. Lỗi ghi đĩa ⇒ `CheckpointIOError`. `KeyboardInterrupt` ⇒ ghi checkpoint hợp lệ cuối nếu có, `status:interrupted`, mã thoát 130.
- **Căn cứ**: constitution I (bằng chứng) — trạng thái lỗi được ghi bằng máy chứ không bằng lời khai.

## Q11. Quy mô tài liệu & stack

- **Quyết định**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, cùng gói `mma_ai`) như 001/002; nhãn `context:` trong cây tách (`training`, `evaluation`, `visualization`) là nhãn mô-đun trong cùng một gói, không phải dịch vụ riêng ⇒ không tạo `docs/02-strategic/`, `docs/03-tactical/`; không phân quyền ⇒ không `rbac.md` (giao diện chỉ loopback, chỉ đọc — INV-005; ghi ở `contracts/cli.md`). `docs/` hiện chỉ có `00-input/`, không có tệp chiến lược/chiến thuật để đồng bộ. Hợp đồng dây: API Python + CLI + một điểm HTTP đọc-chỉ (`API-TRN-0001`) ⇒ có schema và ví dụ ở `contracts/`.
- **Stack**: không đổi (`python-mujoco-cli`, `.ai/stack-proposal.yml`); thêm phụ thuộc `torch`, `tensorboard` (extra `rl`) — không có preset kit mới.
- **Phương án đã loại**: tách gói huấn luyện thành repo/dịch vụ riêng — chưa có lý do.

## Q12. Giả định giao diện với 001/002 (CHƯA KIỂM — cả hai chưa có mã)

- Từ 002: `make_env(config_path, split="train")`, `env.reset(seed)` → `info{target_split, target_index, seed, model_sha256}`, `env.step(u)` → `info{reward_dist, reward_effort, end_reason, ctrl_effective}`, `env.model_record()` (SHA-256, `muscle_names`), `observation_space`/`action_space`, bố cục 14 chiều có kích hoạt 6 cơ ở chỉ số 2–7 (`ObservationLayout`). Nếu `ObservationLayout` không công khai lát cắt kích hoạt, task của 003 chỉ thêm accessor đọc-chỉ vào đúng tệp đó (sau task của 002), không sao chép bố cục.
- Từ 001: `mma_ai.config`, `mma_ai.diagnostics.{environment,memory,gpu,stats}`, `mma_ai.reporting.runlog` (ghi JSON an toàn), stub `scripts/train.py` "chưa triển khai → thoát 3" (003 thay nội dung stub, giữ mã thoát 3 cho stage chưa hỗ trợ).
- Lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu (001/002), 003 chỉ thêm accessor đọc-chỉ.

## Tổng kết

Không còn câu hỏi chưa giải quyết. Việc CHƯA KIỂM giao thành bước triển khai bắt buộc có kết quả ghi lại: (1) `torch` CUDA có `sm_120` trên máy đích (001 Q6); (2) sai khác tái lập GPU↔GPU; (3) độ trễ giao diện ≤ 5 s và chi phí ≤ 10% bằng `benchmark_train.py` trên máy đích; (4) chi phí hiển thị 3D khi có màn hình; (5) giao diện đọc-chỉ của 002 (`ObservationLayout`, `make_env`); (6) siêu tham số khởi đầu có đủ để PPO học hay không — việc của con 3, không phải điều kiện của feature này.
