---
id: "PLAN-003"
title: "M1 (2/4) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Implementation Plan: M1 (2/4) — Huấn luyện PPO, checkpoint, hồ sơ tái lập & giao diện quan sát huấn luyện

**Branch**: `003-ppo-train-repro` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/003-ppo-train-repro/spec.md` (bản hiện tại, REQ-0102 + bổ sung C-0009; Q-0001 đã được người dùng trả lời và áp vào `## Clarifications`)

## Summary

Feature dựng **đường huấn luyện PPO** cho môi trường khuỷu tay của con 1 (`002-elbow-muscle-env`): lệnh `python scripts/train.py --stage elbow --seed 42`, **PPO tự cài trên PyTorch** (`ppo.py`; actor và critic MLP 2×256, chuẩn hoá observation, gradient clipping), **checkpoint một tệp khứ hồi** (policy, critic, bộ chuẩn hoá, optimizer, seed, trạng thái RNG), **hồ sơ thí nghiệm** (run manifest) mỗi run một thư mục không ghi đè, phép so sánh tái lập theo seed/dung sai, báo cáo env steps/s + wall-clock, và **giao diện quan sát thời gian thực** (C-0009, AC-7).

Cách tiếp cận (chi tiết và số đo ở [research.md](research.md)):

- **PPO tự cài, không Stable-Baselines3** (Q1): SB3 cài được cùng `gymnasium 1.4` (đã đo) nên lý do loại là toàn vẹn checkpoint (INV-004) và quyền móc dữ liệu vào vòng lặp; rủi ro "PPO sai âm thầm" được chặn bằng test GAE, mục tiêu clip, chuẩn gradient và `test_learns_toy_env`.
- **Hành động** `u = sigmoid(a)` với `a` là đầu ra Gauss thô ⇒ luôn trong (0,1)^6 (Q2, INV-002).
- **Giao diện quan sát — quyết định của plan (FR-024, Q-0001)**: xem mục riêng bên dưới. Tóm tắt: **TensorBoard (lịch sử, bắt buộc theo FR-010) + bảng điều khiển web nhẹ bằng `http.server` ở tiến trình riêng (đáp ứng AC-7, mặc định bật) + MuJoCo Viewer 3D tuỳ chọn (`--view3d`, mặc định tắt)**; trainer chỉ ghi tệp, giao diện chỉ đọc.
- Tái lập: một seed gốc điều khiển torch, numpy, môi trường; `use_deterministic_algorithms`, 1 luồng torch; dung sai 1×10⁻⁶ chỉ giữa hai run cùng loại thiết bị (Q7).
- Một cấu hình duy nhất `configs/train_elbow.yaml` (khuôn [train-config.schema.json](contracts/train-config.schema.json)) lưu nguyên văn vào hồ sơ (FR-018). Phạm vi CHỈ M1: không đánh giá/biểu đồ (con 3), không replay/demo (con 4), không môi trường song song, không M2–M9.

## Technical Context

**Language/Version**: Python 3.11 (ghim `.python-version` và `requires-python = ">=3.11,<3.13"` của 001)

**Primary Dependencies**: kế thừa 001/002 (`mujoco` 3.15.0, `myo-sim==0.2.3`, `gymnasium>=1.4,<1.5`, `numpy`, `pyyaml`); **mới, extra `rl`**: `torch` (ĐÃ ĐO cài được 2.14.1+cpu cùng `gymnasium 1.4.0`; bản CUDA có `sm_120` CHƯA KIỂM trên máy đích — research Q1), `tensorboard` (ĐÃ ĐO 2.21.0); extra `dev`: `pytest`, `jsonschema`. **Không** `stable-baselines3`, **không** `myosuite`, **không** Streamlit/Flask/Gradio/`psutil`/`pynvml`.

**Storage**: tệp — cấu hình `configs/train_elbow*.yaml`; mỗi run một thư mục `runs/<run_id>/` (hồ sơ JSON, checkpoint `.pt` + `.meta.json`, tfevents, `metrics.jsonl`, `progress.json`); log đo ở `logs/m1/`; không CSDL

**Testing**: `pytest` (`python -m pytest`); test hợp đồng bằng `jsonschema` (draft 2020-12, có registry cho `$ref`); test dùng mô hình MuJoCo thật cho đường chính và một môi trường Gymnasium đồ chơi tất định cho `test_learns_toy_env`; test smoke chạy với `DISPLAY` bỏ đặt

**Target Platform**: Linux gốc / WSL2 Ubuntu; phần cứng đích RTX 5060 8GB · Ryzen 9 HX · 32GB RAM; train headless một môi trường, mạng nhỏ; máy phát triển hiện CHƯA có NVIDIA ⇒ đường GPU CHƯA KIỂM

**Project Type**: thư viện + CLI nghiên cứu, kèm một tiến trình giao diện web loopback chỉ đọc

**Performance Goals**: không đặt ngưỡng tốc độ train (master plan XI.10 cấm giả định); ngưỡng duy nhất là chi phí giao diện: NFR-PERF-001 (≥ 90% env steps/s) và NFR-PERF-002 (≤ 5 s độ trễ). Số thăm dò ≈ 7,35 nghìn bước môi trường/s và ≈ 0,6–0,8 s/lượt cập nhật (CPU phát triển, 1 luồng; research Q4) chỉ để đặt cỡ độ lớn, KHÔNG là cam kết hay dự báo thời gian huấn luyện

**Constraints**: headless mặc định; chỉ kích thích cơ `u ∈ [0,1]^6` (INV-002); chỉ tập train (INV-003); giao diện chỉ đọc và loopback (INV-005); logs/checkpoint trên SSD, đường dẫn gốc cấu hình được; không đường dẫn tuyệt đối riêng của máy trong tài liệu hay hồ sơ

**Scale/Scope**: 1 mô hình (1 DoF, 6 cơ), 1 môi trường, actor/critic ≈ 2×256; ≈ 12 mô-đun mới (`learning/` 10, `monitoring/` 2); 4 script; ≈ 20 tệp test; 2 tệp cấu hình

## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | Mọi AC có test chạy ngoài; số đo (env steps/s, chi phí giao diện, tái lập) do `benchmark_train.py`/`pytest` sinh vào `logs/m1/` và hồ sơ run; ví dụ ở `contracts/examples/` ghi rõ là minh hoạ khuôn, không phải kết quả đo |
| II. Test trước, sửa sau | Đạt | Mỗi mô-đun có test đặt tên sẵn ở bảng truy vết; task tạo test đỏ trước mã; không skip/xfail |
| III. Lát cắt nhỏ, một vai một task | Đạt | Mỗi mô-đun một trách nhiệm một tệp; `monitoring/` tách hẳn `learning/` (không import chéo trainer); tệp chung với 001/002 chỉ `pyproject.toml` (thêm extra `rl`) và `scripts/train.py` (thay stub) — mỗi tệp một task chủ |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…005 và NFR-REL/REPRO/PERF×2/RES/HEADLESS khai ở `spec.md`; plan chỉ tham chiếu. **Không có INV/NFR mới phát hiện ở bước plan** (mã thoát 3/4/130 và chu kỳ snapshot là chi tiết hợp đồng ở `contracts/cli.md`) |
| V. Không đổi cái không được yêu cầu | Đạt | Không đổi môi trường/reward (con 1), không refactor 001/002; chỉ thêm accessor đọc-chỉ vào chủ sở hữu nếu giao diện thiếu (Rủi ro 1); giao diện không điều khiển train (FR-021) |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; giao diện chỉ nghe loopback, không xác thực vì không ra ngoài máy; đường dẫn trong hồ sơ tương đối (kiểm bằng `test_repo_hygiene` của 001) |
| VII. Nhánh bảo vệ | Đạt | Lượt spec không commit, không đổi nhánh |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số trong `research.md` gắn nhãn "ĐÃ ĐO"/"CHƯA KIỂM"; số nghiệm thu sinh từ script, không viết tay |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Data model/hợp đồng CHỈ ở `specs/003-…/`; `docs/` mới chỉ có `00-input/` ⇒ không có `context-map`/`docs/03-tactical/*` để đồng bộ; không tạo tài liệu rỗng |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm phụ thuộc ngoài danh sách; không có vi phạm cần ghi ở Complexity Tracking.

**Quy mô tài liệu & kiến trúc**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, cùng gói `mma_ai`) như 001/002 ⇒ KHÔNG ghi `docs/02-strategic/context-map.md` hay `docs/03-tactical/*`; yêu cầu không vượt một trang cần `docs/01-intent/overview.md`; **không có phân quyền** (giao diện loopback chỉ-đọc, không vai/khoá/token) ⇒ không `rbac.md`. Hợp đồng dây (CLI + một điểm HTTP đọc-chỉ + bản ghi tệp) có schema và ví dụ ở `contracts/`. Stack không đổi (`python-mujoco-cli`); `.ai/stack-proposal.yml` đã khớp.

## Giao diện quan sát — phương án chọn, lý do, chi phí (FR-024, AC-7)

Câu hỏi giao cho plan (Q-0001): TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai? Căn cứ và phương án đã loại đầy đủ ở [research.md](research.md) Q8; tóm tắt quyết định:

| Thành phần | Quyết định | Lý do | Chi phí (đo ở `benchmark_train.py`; CHƯA KIỂM đến khi chạy) |
|---|---|---|---|
| TensorBoard | **Có, luôn ghi** (`tb/`); người dùng tự mở `tensorboard --logdir runs` khi cần | FR-010 bắt buộc; con 3 đọc để vẽ biểu đồ; xem được lịch sử chi tiết | ≈ 33 ms/1000 scalar (ĐÃ ĐO thăm dò); tiến trình TensorBoard tách rời |
| Bảng điều khiển web nhẹ | **Có, mặc định bật** (`--ui web`, tắt bằng `--ui none`); tiến trình riêng `scripts/watch_train.py` bằng `http.server` thư viện chuẩn, loopback, chỉ GET, một trang tĩnh thăm dò `/api/progress` mỗi 2 s | Duy nhất đáp ứng cùng lúc 6 mục của AC-7 trên một màn (reward, loss, 6 cơ, env steps/s, số bước / tổng, trạng thái checkpoint); không thêm phụ thuộc | trainer: một lần ghi JSON nhỏ mỗi ≥ 1 s; giao diện: một luồng CPU cho vài yêu cầu HTTP/2 s; không dùng GPU/VRAM; độ trễ thiết kế ≤ 1 s + 2 s = 3 s < 5 s |
| MuJoCo Viewer 3D | **Tuỳ chọn, mặc định TẮT** (`--view3d`); tiến trình riêng, `launch_passive` trên `MjData` riêng, nạp `latest.json` mỗi vài giây | AC-7 cho phép; master plan XI.8 cấm đồ hoạ nặng cùng lúc ⇒ không bật mặc định; cần màn hình | CPU/GPU/VRAM của 3D đo riêng khi có màn hình, nếu không ghi `measured:false` kèm lý do; không dùng khi benchmark thường lệ |

Ràng buộc kiến trúc: trainer chỉ GHI (`progress.json`, `metrics.jsonl`, tfevents); `monitoring.*` chỉ ĐỌC và **không import** `learning.trainer`/`learning.ppo` (INV-005, kiểm bằng `test_monitoring_has_no_training_imports`); cổng bị chiếm hoặc giao diện lỗi ⇒ cảnh báo, train vẫn chạy; đóng giao diện giữa chừng không ảnh hưởng train. Quy tắc này là **ràng buộc cho mọi stage train sau này** (M2–M9 dùng lại `monitoring/` và `ProgressWriter`, không đặc tả ở đây).

## Phụ thuộc vào 001 và 002

001 và 002 mới có spec + plan, **chưa có mã**. 003 dựa vào giao diện theo plan của chúng (giả định CHƯA KIỂM — research Q12):

| Thành phần | Dùng để | Ghi chú |
|---|---|---|
| 002: `make_env(config_path, split="train")` · `env.reset(seed)` → `info{target_split, target_index, seed, model_sha256}` · `env.step(u)` → `info{reward_dist, reward_effort, end_reason, ctrl_effective}` · `env.model_record()` · `ObservationLayout` (kích hoạt 6 cơ ở chỉ số 2–7) | thu mẫu, INV-003, hash XML, snapshot kích hoạt cơ | nếu `ObservationLayout` không công khai lát cắt kích hoạt: một task nhỏ thêm accessor đọc-chỉ vào đúng tệp của 002 (sau task của 002) |
| 001: `mma_ai.config` · `mma_ai.diagnostics.{environment,memory,gpu,stats}` · `mma_ai.reporting.runlog` | phiên bản thư viện, RAM đỉnh, dò GPU, ghi JSON an toàn | tái dùng, không sao chép |
| 001: stub `scripts/train.py` (thoát 3) | nền cho CLI | 003 thay nội dung stub, **giữ mã thoát 3** cho stage chưa hỗ trợ |

**Quy tắc thứ tự** (cho bước tasks): mọi task của 003 chạm mã đứng SAU task tương ứng của 001/002 (`depends_on`); `pyproject.toml` (thêm extra `rl`) do một task riêng, sau task khung của 001 và task thêm `gymnasium` của 002. Lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu.

## Kiến trúc & tách trách nhiệm

Phụ thuộc một chiều: `learning → environment (002) → physics (001) → config`; `monitoring → (chỉ đọc tệp run)`; `monitoring` không phụ thuộc `learning.trainer`/`learning.ppo`. Mô-đun mới:

| Mô-đun | Trách nhiệm | FR / INV |
|---|---|---|
| `learning/train_config` | `TrainConfig.load`, kiểm khoá/giá trị (≤ 0, thiếu khoá, `batch_size > n_steps`, `ui.host` không loopback); ném `TrainConfigError` | FR-018 |
| `learning/networks` | `ActorCritic`: actor/critic MLP theo `network` (mặc định 2×256), `log_std` học, `u = sigmoid(a)` | FR-002, FR-005, INV-002 |
| `learning/normalizer` | `RunningNorm`: trung bình/phương sai chạy kiểu Welford, kẹp `±clip_obs`, `state_dict` | FR-003 |
| `learning/ppo` | `PPOAgent`: GAE, mục tiêu clip, cập nhật, gradient clipping, `UpdateStats` (chuẩn gradient sau clipping) | FR-002, FR-004 |
| `learning/checkpoint` | `save_checkpoint` (ghi nguyên tử, quét hữu hạn), `load_checkpoint`, `load_policy` (chỉ đọc cho con 3/4), `latest.json` | FR-006…FR-009, INV-004 |
| `learning/run_dir` | `create_run_dir` bằng `os.mkdir` loại trừ, hậu tố `-n`, tối đa 100 lần | FR-011, INV-001 |
| `learning/manifest` | `build_manifest`/`write_manifest` theo [run-manifest.schema.json](contracts/run-manifest.schema.json); từ chối NaN/Inf | FR-011, FR-012 |
| `learning/resources` | CPU/RAM/GPU/VRAM, env steps/s, wall-clock (tái dùng `diagnostics` của 001) | FR-012, FR-013 |
| `learning/repro` | `seed_everything`, `compare_runs` theo dung sai của hồ sơ, `comparable=False` khi khác thiết bị/phiên bản/số luồng | FR-001, FR-014 |
| `learning/progress` | `ProgressWriter` ghi `progress.json` nguyên tử, ≥ 1 s/lần, cắt `history` | FR-020 |
| `learning/trainer` | `Trainer.run`: thu mẫu → GAE → cập nhật; quét NaN/Inf; TensorBoard, `metrics.jsonl`, snapshot; checkpoint định kỳ + `final`; xử lý lỗi/ngắt | FR-001, FR-010, FR-016, FR-017 |
| `monitoring/dashboard` | `serve`: `http.server` loopback đọc-chỉ (`API-TRN-0001`, `API-TRN-0002`) | FR-020, FR-021, INV-005 |
| `monitoring/viewer3d` | `View3D`: tiến trình riêng, thiếu `DISPLAY` ⇒ "3D không khả dụng" | FR-022 |
| `scripts/train.py` · `watch_train.py` · `compare_runs.py` · `benchmark_train.py` | bốn lệnh CLI mỏng gọi thư viện | FR-001, FR-013…FR-015, FR-020, FR-023 |

### Quyết định thiết kế

- **Hành động**: `Trainer` chuyển cho môi trường LUÔN `sigmoid(a)`; không có đường ghi lực, góc khớp hay toạ độ tay (INV-002). `log_prob` tính trên `a`.
- **Mục tiêu**: `Trainer` chỉ dùng môi trường tạo bằng `split="train"`; test khẳng định `info["target_split"] == "train"` ở mọi `reset` (INV-003).
- **Checkpoint**: MỘT tệp `torch.save` từ điển nguyên thuỷ/tensor, nạp `weights_only=True`; ghi `.tmp` → quét hữu hạn → `fsync` → `os.replace`; tên có chỉ số lượt ⇒ không ghi đè (Q5). Cuối run luôn ghi `final`.
- **Hồ sơ run**: ghi `status:running` lúc đầu, thay nguyên tử lúc cuối (`done`/`error`/`interrupted`); train tiếp (`--resume`) tạo run con ghi `resumed_from`, không sửa run cha (Q6).
- **Lỗi**: NaN/Inf ⇒ `NonFiniteError`, không ghi checkpoint mới; `PhysicsInstabilityError` của con 1 truyền nguyên văn; lỗi ghi đĩa ⇒ `CheckpointIOError`; Ctrl-C ⇒ `interrupted` mã 130 (Q10). Thông điệp hiển thị bằng tiếng Việt, nêu lượt/đại lượng/thành phần thiếu.
- **Siêu tham số khởi đầu** (chưa tinh chỉnh; `total_timesteps = 100 000` chỉ là giữ chỗ để chạy được, KHÔNG phải ngân sách huấn luyện): research Q4. Con 2 không khẳng định policy học được — việc của con 3.
- **Không mock vật lý**: test đường chính dùng mô hình thật; `monkeypatch` chỉ để tiêm NaN/lỗi ghi đĩa và được gọi tên rõ. Không tự viết validator an ninh riêng ngoài `jsonschema` và các kiểm tra theo spec; test assert thẳng trên sản phẩm.

## Project Structure

### Documentation (this feature)

```text
specs/003-ppo-train-repro/
├── plan.md
├── research.md          # Q1 PPO tự cài · Q8 hình thức giao diện quan sát
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md                          # CMD-TRN-0001…0004, API-TRN-0001/0002, mã thoát
│   ├── python-api.md
│   ├── train-config.schema.json
│   ├── run-manifest.schema.json
│   ├── checkpoint-meta.schema.json
│   ├── progress-snapshot.schema.json
│   ├── train-benchmark.schema.json
│   └── examples/                       # ví dụ hợp schema (minh hoạ khuôn, không phải kết quả đo)
├── checklists/requirements.md
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

### Source Code (repository root) — chỉ phần 003 thêm vào cây của 001/002

```text
configs/
├── train_elbow.yaml          # ppo.*, network.*, normalization.*, schedule.*, checkpoint.every_updates,
│                             # reproducibility.*, paths.runs_dir, ui.*
└── train_elbow_smoke.yaml    # total_timesteps 4096, every_updates 1, ui.mode none
src/mma_ai/
├── learning/
│   ├── __init__.py
│   ├── train_config.py   networks.py   normalizer.py   ppo.py
│   ├── checkpoint.py     run_dir.py    manifest.py     resources.py
│   └── repro.py          progress.py   trainer.py      errors.py
└── monitoring/
    ├── __init__.py
    ├── dashboard.py      # http.server loopback, chỉ GET, trang tĩnh nội tuyến
    └── viewer3d.py       # tiến trình riêng, tuỳ chọn
scripts/
├── train.py              # thay stub của 001 (giữ mã thoát 3 cho stage chưa hỗ trợ)
├── watch_train.py   compare_runs.py   benchmark_train.py
tests/
├── unit/        # test_train_config, test_networks, test_normalizer, test_ppo, test_checkpoint,
│                # test_run_dir, test_manifest, test_repro, test_progress
├── integration/ # test_train_cli, test_train_headless, test_train_split, test_train_nan_guard, test_resume,
│                # test_manifest_contract, test_dashboard, test_monitoring_imports, test_viewer3d,
│                # test_benchmark_train, test_contract_examples_train, test_dependency_train
└── regression/  # test_train_determinism
runs/                     # đầu ra mỗi run (bỏ khỏi git; gốc cấu hình được, nên trên SSD)
logs/m1/                  # benchmark_train.json (bỏ khỏi git)
```

**Structure Decision**: dự án đơn (single project), mở rộng cây `src/mma_ai/` của 001/002 bằng hai gói con `learning/` và `monitoring/`. Các gói `evaluation/`, `visualization/` (con 3–4) **chưa tạo**. `.gitignore` thêm `runs/` (cùng task với cấu hình); `logs/` đã có theo plan của 001.

## Lệnh build / test (cho task khung dựng đúng một lần)

| Việc | Lệnh |
|---|---|
| Dựng môi trường | `uv python install 3.11 && uv sync --extra dev --extra rl` |
| Toàn bộ test | `uv run python -m pytest -q` |
| Test riêng feature | `uv run python -m pytest -q tests/unit/test_ppo.py tests/unit/test_checkpoint.py tests/integration/test_train_cli.py` |
| Chạy smoke | `uv run python scripts/train.py --stage elbow --seed 42 --config configs/train_elbow_smoke.yaml` |
| Chạy thật + giao diện | `uv run python scripts/train.py --stage elbow --seed 42` (in URL giao diện); `uv run tensorboard --logdir runs` |
| So sánh hai run | `uv run python scripts/compare_runs.py runs/<run_a> runs/<run_b>` |
| Benchmark chi phí giao diện | `uv run python scripts/benchmark_train.py --seed 42 --repeats 5` |
| Khoá phiên bản | `uv lock` — CHỈ sau khi smoke test đạt; commit `uv.lock` |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng / Test |
|---|---|---|
| FR-001, NFR-REL-001 | `trainer`, `repro`, `scripts/train.py` | `test_train_cli::test_smoke_train_exit0`, `::test_tensorboard_scalars_present` |
| FR-002, FR-004 | `networks`, `ppo` | `test_networks::test_actor_critic_2x256`, `test_ppo::test_grad_norm_after_clip_le_threshold`, `::test_gae_matches_hand_computed`, `::test_learns_toy_env` |
| FR-003 | `normalizer` | `test_normalizer::test_matches_numpy_stats` |
| FR-005, INV-002 | `networks`, `trainer` | `test_train_cli::test_actions_in_unit_interval`, `test_networks::test_action_always_in_unit_interval` |
| FR-006, FR-007, INV-004 | `checkpoint` | `test_checkpoint::test_atomic_write_no_partial`, `::test_nan_not_written`, `test_train_cli::test_periodic_and_final_checkpoint` |
| FR-008, NFR-REPRO-001 | `checkpoint` | `test_checkpoint::test_roundtrip_same_action`, `::test_missing_component_raises`, `::test_shape_mismatch_raises` |
| FR-009 | `checkpoint`, `trainer` | `test_resume::test_resume_creates_new_run_with_parent`, `::test_resume_restores_normalizer_optimizer_rng`, `::test_resume_refused_when_xml_hash_differs` |
| FR-010 | `trainer` | `test_train_cli::test_tensorboard_scalars_present` (loss, reward, `activation/<6 cơ>`) |
| FR-011, INV-001 | `run_dir`, `manifest` | `test_run_dir::test_unique_dirs_no_overwrite`, `test_manifest_contract::test_manifest_fields_and_schema`, `::test_two_runs_two_dirs`, `::test_manifest_hash_matches_env_model_record` |
| FR-012, NFR-RES-001 | `resources`, `manifest` | `test_manifest_contract::test_resources_fields_null_explicit` |
| FR-013 | `resources`, `trainer` | `test_manifest::test_throughput_and_wallclock_measured` |
| FR-014, NFR-REPRO-001 | `repro`, `scripts/compare_runs.py` | `test_train_determinism::test_same_seed_head_curve_within_tolerance`, `::test_diff_seed_differs`, `test_repro::test_compare_within_tolerance`, `::test_compare_outside` |
| FR-015 | `scripts/train.py` | `test_train_cli::test_stage_not_implemented_exit3`, `::test_no_run_dir_for_unimplemented` |
| FR-016, INV-003 | `trainer` | `test_train_split::test_training_only_uses_train_split` |
| FR-017 | `trainer`, `errors` | `test_train_nan_guard::test_nan_loss_stops_without_checkpoint` |
| FR-018 | `train_config` | `test_train_config::test_invalid_values_raise`, `::test_defaults_load` |
| FR-019 | toàn bộ bộ test trên | `python -m pytest` |
| FR-020, NFR-PERF-002 | `progress`, `dashboard` | `test_dashboard::test_progress_endpoint_matches_schema`, `::test_page_lists_required_panels`, `::test_snapshot_latency_le_5s`, `test_progress::test_snapshot_atomic_and_schema` |
| FR-021, INV-005 | `dashboard`, `monitoring` | `test_dashboard::test_dashboard_is_read_only`, `::test_dashboard_loopback_only`, `test_monitoring_imports::test_monitoring_has_no_training_imports` |
| FR-022, NFR-HEADLESS-001 | `viewer3d`, `scripts/train.py` | `test_viewer3d::test_view3d_off_by_default`, `::test_view3d_unavailable_without_display_does_not_break_train`, `test_train_headless::test_smoke_without_display` |
| FR-023, NFR-PERF-001, INV-005 | `scripts/benchmark_train.py` | `test_benchmark_train::test_benchmark_schema_and_ratio`, `test_dashboard::test_train_survives_ui_failure`; số đo thật ở `logs/m1/benchmark_train.json` |
| FR-024 | mục "Giao diện quan sát" của plan + `research.md` Q8 | rà soát tài liệu (không có mã) |

## Rủi ro & việc CHƯA KIỂM

1. **001 và 002 chưa có mã** — 003 dựa vào giao diện theo plan của chúng; lệch ⇒ sửa ở nơi chủ sở hữu, 003 chỉ thêm accessor đọc-chỉ (research Q12).
2. **`torch` CUDA có `sm_120` (Blackwell) trên máy đích** — máy phát triển không có NVIDIA; ghim cuối chọn sau khi 001 đo `arch_list`; đường GPU chưa kiểm.
3. **Tái lập GPU↔GPU** — thứ tự cộng dồn có thể lệch dù `deterministic`; đo trên máy đích, nếu vượt 1×10⁻⁶ thì nới dung sai GPU bằng cấu hình và ghi số đo. CPU↔GPU không cam kết (Clarifications).
4. **Ngưỡng chi phí giao diện ≤ 10% và độ trễ ≤ 5 s** — chỉ là thiết kế đến khi `benchmark_train.py` và `test_snapshot_latency_le_5s` chạy; lần train đầu của benchmark nhỏ có thể nhiễu ⇒ so trung vị ≥ 5 lần xen kẽ.
5. **PPO tự cài sai âm thầm** — chặn bằng test GAE/clip/chuẩn gradient/`test_learns_toy_env`; siêu tham số khởi đầu có đủ để học khuỷu tay hay không thuộc con 3, không là điều kiện của feature này.
6. **Hiển thị 3D** — cần màn hình, chi phí chỉ đo khi có; thiếu `DISPLAY` ⇒ không khả dụng nhưng không làm hỏng train.
7. **Train tiếp không trùng từng bit với chạy liền** (episode dở bị bỏ khi dừng) — chỉ cam kết trạng thái học được và thống kê chuẩn hoá liên tục.

## Phản biện plan_lint

- Cạnh tranh phương án giao diện: chỉ TensorBoard bị loại vì thiếu env steps/s, số bước / tổng, trạng thái checkpoint và 6 cơ trên một màn; Streamlit/Flask/Gradio bị loại vì thêm phụ thuộc nặng cho một trang số liệu; 3D mặc định bật bị loại theo master plan XI.8.
- Tự cài PPO đổi lấy rủi ro sai thuật toán; chấp nhận vì INV-004 cần checkpoint một tệp có RNG và quyền móc dữ liệu vào vòng lặp, rủi ro có test chặn riêng.
- Chưa có số đo thật nào về chi phí giao diện: mọi con số trong plan là thiết kế hoặc thăm dò; nghiệm thu phải dựa vào `logs/m1/benchmark_train.json`, không dựa vào plan.

## Complexity Tracking

Không có vi phạm hiến chương cần biện minh. Độ phức tạp thêm vào (một tiến trình giao diện riêng, hai gói con) được biện minh bởi yêu cầu AC-7/FR-022: giao diện ở tiến trình riêng để không kéo chậm vòng train và để lỗi giao diện không dừng train (INV-005); phương án đơn giản hơn (chỉ TensorBoard) không đủ 6 số liệu của AC-7.
