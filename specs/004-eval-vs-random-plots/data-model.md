---
id: "DM-004"
title: "M1 (3/4) — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Mô hình dữ liệu — M1 (3/4)

- [Thực thể → đối tượng / tệp](#thuc-the-doi-tuong-tep)
- [Cấu trúc thư mục một lượt đánh giá](#cau-truc-thu-muc-mot-luot-danh-gia)
- [Máy trạng thái của một lượt đánh giá](#may-trang-thai-cua-mot-luot-danh-gia)
- [Luật hợp lệ chéo (schema không diễn đạt hết — kiểm bởi mã/test)](#luat-hop-le-cheo-schema-khong-dien-dat-het-kiem-boi-matest)
- [Ánh xạ nhãn ↔ khoá](#anh-xa-nhan-khoa)
- [Bất biến liên quan (khai ở spec.md, chỉ tham chiếu mã)](#bat-bien-lien-quan-khai-o-specmd-chi-tham-chieu-ma)
- [Cấu hình (đọc, không phải bản ghi báo cáo)](#cau-hinh-doc-khong-phai-ban-ghi-bao-cao)


Cập nhật theo `spec.md` hiện tại. Không có cơ sở dữ liệu ⇒ không có bảng `TBL-*`, không có index; không có `EVT-*`. Dữ liệu là đối tượng trong bộ nhớ và **tệp** trong thư mục `eval` của run (JSON theo `contracts/*.schema.json`, CSV, PNG). Tên trường KHÔNG chép lại ở đây — xem schema; chỉ ghi luật và quan hệ. Mọi tệp trong `contracts/examples/` là **ví dụ minh hoạ khuôn**, không phải kết quả đo.

<a id="thuc-the-doi-tuong-tep"></a>
## Thực thể → đối tượng / tệp

| Thực thể (spec) | Đối tượng | Khuôn dây / tệp | Người ghi | Người đọc |
|---|---|---|---|---|
| Lượt đánh giá | `EvalResult` | thư mục `runs/<run_id>/eval/<eval_id>/` | `evaluate.py` (một lần, công bố bằng đổi tên) | con 4 (tuỳ chọn), người dùng, test |
| Tập đánh giá | `DisjointnessReport` + `pair.test` | khối `disjointness` trong `report.json` | `split_guard` | người duyệt, test |
| Kết quả theo policy | `PolicyResult` | khối `policies.learned` / `policies.random` trong `report.json` | `metrics.summarize` | người dùng, test |
| Kết luận so sánh | `Verdict` | khối `comparison` + `criterion` trong `report.json` | `stats.decide` | người dùng, test |
| Báo cáo đánh giá | dict | `report.json` — [eval-report.schema.json](contracts/eval-report.schema.json) | `report.build_report` | người dùng, test, hồ sơ nghiệm thu |
| Bộ biểu đồ | `ChartResult` | `charts/{loss,reward,activation}.png` + khối `charts` trong `report.json` | `charts.render_charts` | người dùng |
| Cấu hình đánh giá | `EvalConfig` | `configs/eval_elbow.yaml` ([eval-config.schema.json](contracts/eval-config.schema.json)); bản nhúng nguyên văn trong `report.config` | người dùng / `EvalConfig.load` | mọi mô-đun `evaluation`, báo cáo |
| Bản ghi episode (mức thấp) | `EpisodeRecord` | `episodes.csv` (một dòng mỗi episode, cột liệt kê dưới) | `rollout` | `metrics`, người dùng |

<a id="cau-truc-thu-muc-mot-luot-danh-gia"></a>
## Cấu trúc thư mục một lượt đánh giá

```text
runs/<run_id>/eval/<eval_id>/
├── report.json        # status: done | done_charts_incomplete
├── episodes.csv       # policy, episode, target_index, seed, reached, end_reason, abnormal, final_distance_m,
│                      # return, effort, act_m0..act_m5, n_steps, nan_count, inf_count
└── charts/
    ├── loss.png
    ├── reward.png
    └── activation.png
runs/<run_id>/eval/.tmp-<eval_id>/   # chỉ tồn tại LÚC chạy; bị đổi tên (công bố) hoặc xoá (lỗi/ngắt)
```

`eval_id = <UTC YYYYMMDDTHHMMSSZ>_e<seed episode đầu>[-n]` (mẫu regex ở schema). Các tệp của run (`manifest.json`, `checkpoints/`, `tb/`, `metrics.jsonl`, `progress.json`) **không bao giờ** bị sửa (INV-005).

<a id="may-trang-thai-cua-mot-luot-danh-gia"></a>
## Máy trạng thái của một lượt đánh giá

```text
(không có gì) ──kiểm cấu hình/checkpoint/giao rỗng đạt──▶ chạy episode (chỉ có thư mục .tmp)
chạy episode ──tính chỉ số, kết luận, vẽ đủ ba biểu đồ──▶ done              (đổi tên .tmp → eval_id, mã 0)
chạy episode ──thiếu/hỏng nhật ký nên thiếu biểu đồ──▶ done_charts_incomplete (đổi tên, mã 6)
bất kỳ bước ──lỗi / Ctrl-C──▶ (xoá .tmp, KHÔNG có bản ghi)                  (mã ≠ 0)
done | done_charts_incomplete ──▶ (bất biến: không sửa nữa, INV-005)
```

Lỗi checkpoint, cấu hình, giao rỗng xảy ra **trước** khi tạo `.tmp`; ngoài `done` và `done_charts_incomplete` không có trạng thái nào được công bố (INV-004).

<a id="luat-hop-le-cheo-schema-khong-dien-dat-het-kiem-boi-matest"></a>
## Luật hợp lệ chéo (schema không diễn đạt hết — kiểm bởi mã/test)

| Luật | Nơi kiểm | Mã |
|---|---|---|
| `report.model.sha256` = `checkpoint.model_sha256` = `manifest.model.sha256` của run (một hash XML cho cả ba) | `runner` + `test_hash_consistency` | INV-002 |
| `comparison.better` ⇔ `comparison.ci_low > 0` | `stats.decide` + `test_verdict_rule` | INV-006 |
| `comparison.difference` = `policies.learned.success_rate.value − policies.random.success_rate.value` (sai khác ≤ 1×10⁻⁹) | `report.build_report` + test | AC-2 |
| `policies.*.n_episodes` bằng nhau và bằng `disjointness.n_eval_targets × config.episodes.repeats` | `runner` + test | INV-002 |
| `disjointness.passed = true` luôn (vi phạm ⇒ không công bố); `min_cross_distance_m ≥ min_required_m` | `split_guard` + test | INV-001 |
| `disjointness.eval_seed_range` và `random_policy_seed` không giao `run.train_seeds` | `split_guard` + test | INV-001 |
| `charts.status = complete` ⇔ cả ba tệp ảnh khác `null` và `reason = null`; `incomplete` ⇒ `status` báo cáo = `done_charts_incomplete` | `report.build_report` + test | AC-3 |
| `stat.value = null` ⇒ `reason` khác `null`; khi có số thì `reason = null` | schema + test | FR-017 |
| Không giá trị nào là NaN/Infinity trong `report.json` (từ chối khi ghi) | `report.build_report` + `test_report_has_no_nonfinite` | NFR-REL-001 |
| `run.train_seeds` gồm `run.seed` và seed mọi run cha; chuỗi cha ≤ 100 bậc | `split_guard` + test | INV-001 |
| `checkpoint.sha256` = SHA-256 nội dung tệp `.pt` được dùng | `runner` + test | KQ-4 |

<a id="anh-xa-nhan-khoa"></a>
## Ánh xạ nhãn ↔ khoá

Yêu cầu không có bảng ánh xạ nhãn hiển thị ↔ khoá dữ liệu cho dây; báo cáo chỉ mang **khoá** (`success_rate`, `final_distance_m`, `mean_return`, `effort`, `activation_per_muscle`, `abnormal_rate`, `nan_count`, `inf_count`). Nhãn tiếng Việt chỉ sinh ở bước in `stdout` và nhãn trục biểu đồ:

| Khoá (dây) | Nhãn (stdout / trục biểu đồ) |
|---|---|
| `success_rate` | Tỷ lệ tới mục tiêu |
| `final_distance_m` | Khoảng cách cuối episode (m) |
| `mean_return` | Reward trung bình mỗi episode |
| `effort` | Mức kích hoạt/nỗ lực |
| `activation_per_muscle` | Kích hoạt từng cơ |
| `abnormal_rate` | Tỷ lệ episode kết thúc bất thường |
| `nan_count`, `inf_count` | Số NaN, số Inf |

<a id="bat-bien-lien-quan-khai-o-specmd-chi-tham-chieu-ma"></a>
## Bất biến liên quan (khai ở spec.md, chỉ tham chiếu mã)

INV-001 (tập đánh giá không giao tập train) · INV-002 (cùng tập, thứ tự, cấu hình, hash XML) · INV-003 (hành động ∈ [0,1]^6, chỉ kích thích cơ) · INV-004 (lỗi không để lại kết quả hợp lệ giả) · INV-005 (chỉ đọc đối với dữ liệu con 2) · INV-006 (tiêu chí khai trước) · INV-007 (tái lập theo seed).

<a id="cau-hinh-doc-khong-phai-ban-ghi-bao-cao"></a>
## Cấu hình (đọc, không phải bản ghi báo cáo)

| Tệp | Khoá chính | Dùng bởi |
|---|---|---|
| `configs/eval_elbow.yaml` | `seeds.*`, `episodes.*`, `criterion.*`, `stats.*`, `logs.*`, `charts.*`, `paths.*` | `EvalConfig` → toàn bộ gói `evaluation` |
| `configs/elbow_env.yaml` (002) | tham số môi trường, kích thước tập mục tiêu, `min_separation_m` | `make_env`, `TargetGenerator` (qua `split_guard`) |
| hồ sơ run `manifest.json` (003) | `seed`, `config.env_config`, `model.sha256`, `status`, `resumed_from`, `model.muscle_names` | `evaluation.runner`, `split_guard` (chỉ đọc) |
