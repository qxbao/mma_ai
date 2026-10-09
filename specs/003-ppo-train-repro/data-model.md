---
id: "DM-003"
title: "M1 (2/4) — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Mô hình dữ liệu — M1 (2/4)

- [Thực thể → đối tượng / tệp](#thuc-the-doi-tuong-tep)
- [Cấu trúc thư mục một run](#cau-truc-thu-muc-mot-run)
- [Máy trạng thái của run](#may-trang-thai-cua-run)
- [Luật hợp lệ chéo (schema không diễn đạt hết — kiểm bởi mã/test)](#luat-hop-le-cheo-schema-khong-dien-dat-het-kiem-boi-matest)
- [Bố cục checkpoint (nội dung tệp `.pt`)](#bo-cuc-checkpoint-noi-dung-tep-pt)
- [Bất biến liên quan (khai ở spec.md, chỉ tham chiếu mã)](#bat-bien-lien-quan-khai-o-specmd-chi-tham-chieu-ma)
- [Cấu hình (đọc, không phải bản ghi báo cáo)](#cau-hinh-doc-khong-phai-ban-ghi-bao-cao)


Cập nhật theo `spec.md` hiện tại (có Q-0001 đã trả lời, AC-7). Không có cơ sở dữ liệu ⇒ không có bảng `TBL-*`, không có index; không có `EVT-*`. Dữ liệu là đối tượng trong bộ nhớ và **tệp** trong thư mục run (JSON theo `contracts/*.schema.json`, `.pt`, tfevents, JSONL). Tên trường KHÔNG chép lại ở đây — xem schema; chỉ ghi luật và quan hệ. Mọi tệp trong `contracts/examples/` là **ví dụ minh hoạ khuôn**, không phải kết quả đo.

<a id="thuc-the-doi-tuong-tep"></a>
## Thực thể → đối tượng / tệp

| Thực thể (spec) | Đối tượng | Khuôn dây / tệp | Người ghi | Người đọc |
|---|---|---|---|---|
| Lần chạy huấn luyện (Run) | `RunDir` | thư mục `runs/<run_id>/` | `train.py` (một lần, loại trừ) | con 3, con 4, giao diện, test |
| Hồ sơ thí nghiệm | `RunManifest` (dict) | `manifest.json` — [run-manifest.schema.json](contracts/run-manifest.schema.json) | trainer (đầu run + thay thế nguyên tử cuối run) | con 3, `compare_runs.py`, test |
| Checkpoint | `Checkpoint` | `checkpoints/ckpt_uNNNNNN[_final].pt` + `.meta.json` ([checkpoint-meta.schema.json](contracts/checkpoint-meta.schema.json)) + `checkpoints/latest.json` | trainer | trainer (resume), con 3, con 4, `viewer3d` |
| Cấu hình huấn luyện | `TrainConfig` | `configs/train_elbow*.yaml` ([train-config.schema.json](contracts/train-config.schema.json)); bản đã phân giải `config.yaml` trong run | người dùng / `TrainConfig.load` | mọi mô-đun `learning`, hồ sơ |
| Nhật ký huấn luyện | `MetricsLogger` | `tb/` (tfevents) + `metrics.jsonl` | trainer | TensorBoard, con 3 |
| Ảnh chụp tiến trình | `ProgressSnapshot` | `progress.json` ([progress-snapshot.schema.json](contracts/progress-snapshot.schema.json)) | trainer (thay thế nguyên tử, ≥ 1 s/lần) | giao diện (qua `API-TRN-0001`), test |
| Kết quả đo chi phí giao diện | `TrainBenchmark` | `logs/m1/benchmark_train.json` ([train-benchmark.schema.json](contracts/train-benchmark.schema.json)) | `scripts/benchmark_train.py` | hồ sơ nghiệm thu, người duyệt |

<a id="cau-truc-thu-muc-mot-run"></a>
## Cấu trúc thư mục một run

```text
runs/<run_id>/
├── manifest.json            # status: running → done | error | interrupted
├── config.yaml              # cấu hình đã phân giải (cũng nhúng nguyên văn vào manifest.config)
├── checkpoints/
│   ├── ckpt_u000010.pt      # + ckpt_u000010.meta.json
│   ├── ckpt_u000020_final.pt
│   └── latest.json          # con trỏ tới checkpoint hợp lệ mới nhất (thay thế nguyên tử)
├── tb/                      # tfevents: loss, reward, activation/<tên cơ>, throughput
├── metrics.jsonl            # một dòng mỗi lượt cập nhật
├── progress.json            # snapshot cho giao diện
└── ui.json                  # {url, pid} do TIẾN TRÌNH GIAO DIỆN ghi (không phải trainer)
```

`run_id = <UTC YYYYMMDDTHHMMSSZ>_<stage>_s<seed>[-n]` (mẫu regex ở schema). Thư mục gốc `runs/` cấu hình được (`paths.runs_dir`), nằm trên SSD, bỏ khỏi git.

<a id="may-trang-thai-cua-run"></a>
## Máy trạng thái của run

```text
(không có thư mục) ──mkdir loại trừ──▶ running
running ──hết total_timesteps, ghi checkpoint final──▶ done
running ──NaN/Inf | PhysicsInstabilityError | lỗi ghi đĩa──▶ error       (mã thoát 1, không ghi checkpoint mới)
running ──KeyboardInterrupt──▶ interrupted                              (mã thoát 130)
done | error | interrupted ──────▶ (bất biến: không sửa nữa, INV-001)
```

Train tiếp (`--resume`) **không** đổi trạng thái run cha; nó tạo run con mới có `resumed_from`.

<a id="luat-hop-le-cheo-schema-khong-dien-dat-het-kiem-boi-matest"></a>
## Luật hợp lệ chéo (schema không diễn đạt hết — kiểm bởi mã/test)

| Luật | Nơi kiểm | Mã |
|---|---|---|
| `batch_size ≤ n_steps ≤ total_timesteps` | `TrainConfig.load` ⇒ `TrainConfigError` | FR-018 |
| `ui.host` thuộc loopback (`127.0.0.1`, `::1`, `localhost`) | schema + `TrainConfig.load` | INV-005 |
| `manifest.model.sha256` = `env.model_record()["sha256"]` | `test_manifest_hash_matches_env_model_record` | AC-3 |
| `checkpoint.model_sha256` = hash mô hình của run khi `--resume` (khác ⇒ từ chối train tiếp) | `load_checkpoint(..., for_training=True)` | AC-2 |
| `reward_metrics.head_mean_return` có đúng K = min(`head_updates`, `n_updates`) phần tử | `build_manifest` + test | AC-4 |
| `components` của checkpoint đủ 6 phần tử; `finite = true` | `save_checkpoint` | INV-004 |
| Trường không áp dụng ghi `null` tường minh (GPU/VRAM khi không có GPU, `finished_utc` khi `running`) | schema (`required` + `["…","null"]`) | AC-3 |
| `progress.timestamp_utc` đơn điệu không giảm | `test_snapshot_atomic_and_schema` | AC-7 |

<a id="bo-cuc-checkpoint-noi-dung-tep-pt"></a>
## Bố cục checkpoint (nội dung tệp `.pt`)

| Khoá | Nội dung | Ghi chú |
|---|---|---|
| `actor`, `critic` | `state_dict` | cấu trúc suy ra từ `config.network` |
| `obs_normalizer` | `mean`, `var`, `count` | thống kê chạy (research Q3) |
| `optimizer` | `state_dict` Adam | |
| `seed` | số nguyên | seed gốc của chuỗi run |
| `rng_state` | numpy bit-generator, torch CPU (+ CUDA nếu có), `np_random` của môi trường | nạp bằng `weights_only=True` (research Q5) |
| `update_idx`, `env_steps` | số nguyên | bộ đếm tiếp nối khi train tiếp |
| `model_sha256`, `library_versions`, `config` | chuỗi / từ điển | đối chiếu khi nạp |

<a id="bat-bien-lien-quan-khai-o-specmd-chi-tham-chieu-ma"></a>
## Bất biến liên quan (khai ở spec.md, chỉ tham chiếu mã)

INV-001 (thư mục run duy nhất, không ghi đè) · INV-002 (hành động ∈ [0,1]^6) · INV-003 (chỉ tập train) · INV-004 (checkpoint khứ hồi đủ trạng thái, không NaN/Inf) · INV-005 (giao diện chỉ đọc).

<a id="cau-hinh-doc-khong-phai-ban-ghi-bao-cao"></a>
## Cấu hình (đọc, không phải bản ghi báo cáo)

| Tệp | Khoá chính | Dùng bởi |
|---|---|---|
| `configs/train_elbow.yaml` | `ppo.*`, `network.*`, `normalization.*`, `schedule.*`, `checkpoint.every_updates`, `reproducibility.*`, `paths.runs_dir`, `ui.*` | `TrainConfig` → toàn bộ gói `learning` và `monitoring` |
| `configs/train_elbow_smoke.yaml` | như trên, `total_timesteps: 4096`, `every_updates: 1`, `ui.mode: none` | test smoke, quickstart |
| `configs/elbow_env.yaml` (002) | tham số môi trường | `make_env` |
