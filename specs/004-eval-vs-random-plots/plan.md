---
id: "PLAN-004"
title: "M1 (3/4) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Implementation Plan: M1 (3/4) — Đánh giá policy so với random policy và biểu đồ loss/reward/activation

**Branch**: `004-eval-vs-random-plots` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/004-eval-vs-random-plots/spec.md` (bản hiện tại, REQ-0103; không có `[NEEDS CLARIFICATION]`; Q-0001 thuộc `003-ppo-train-repro` và không đổi phạm vi con 3)

## Summary

Feature dựng **đường đánh giá** cho checkpoint của con 2 (`003-ppo-train-repro`): lệnh `python scripts/evaluate.py --checkpoint <path>` nạp policy chỉ-đọc, chạy nó và một **random policy có seed** trên **tập mục tiêu kiểm thử** của con 1 (`002-elbow-muscle-env`; mỗi mục tiêu một episode cho mỗi policy), tính bảy nhóm chỉ số kèm khoảng tin cậy, đưa ra **kết luận "tốt hơn random" theo tiêu chí khai trước**, vẽ **ba biểu đồ headless** (loss, reward, activation 6 cơ) từ nhật ký của run, và **lưu kết quả cạnh run** mà không sửa tệp nào con 2 đã ghi.

Cách tiếp cận (chi tiết và số đo ở [research.md](research.md)):

- **Kết luận thống kê giải tích** (Q1): chỉ số chính là tỷ lệ tới mục tiêu; khoảng tin cậy từng tỷ lệ theo **Wilson**, khoảng tin cậy hiệu theo **Newcombe (Wilson hỗn hợp)**; "tốt hơn" ⇔ cận dưới > 0. Đã đo trên các ca có đáp án (50 vs 0 → [0,899 ; 1,000]; 20 vs 10 → [0,020 ; 0,364]; 0 vs 0 → [−0,071 ; 0,071]); bootstrap ghép cặp bị loại vì thoái hoá ở biên. Chỉ số liên tục dùng bootstrap có seed, không quyết định kết luận. Chỉ `numpy` — không `scipy`.
- **Phép kiểm giao rỗng chạy MỖI lần, trước episode đầu** (Q5, INV-001): dựng lại `TargetSetPair` của con 1 từ cấu hình môi trường của run, kiểm giao rỗng và khoảng cách tối thiểu bằng số liệu của con 1, kiểm seed episode/seed random policy không giao seed train (cả chuỗi run cha); không thiết lập được ⇒ từ chối, không đánh giá "không kiểm".
- **Ghi nguyên tử, không kết quả giả** (Q6, INV-004): kiểm đầu vào *trước* khi tạo thư mục; ghi vào `.tmp-<eval_id>` rồi đổi tên thành thư mục công bố; lỗi/ngắt ⇒ xoá tạm, mã thoát khác 0. Không sửa `manifest.json`/checkpoint/nhật ký của run (INV-005).
- **Biểu đồ từ nhật ký con 2** (Q2, Q3): đọc `metrics.jsonl` hoặc tfevents (chỉ cần `tensorboard`, không `torch`) vào bảng `pandas`; `matplotlib` backend `Agg`; thẻ chọn theo **tiền tố cấu hình được** (tên thẻ thật của con 2 CHƯA KIỂM). Thiếu một đại lượng ⇒ mã 6, kết quả số vẫn lưu, không ảnh rỗng.
- **Random policy tất định** (Q4, INV-007): một bộ sinh `default_rng(seed)` xuyên lượt, không nhìn observation; policy học được dùng hành động xác định; cả hai chạy bằng cùng một vòng `run_policy_on_targets` với cùng danh sách mục tiêu/thứ tự (INV-002).
- Một cấu hình duy nhất `configs/eval_elbow.yaml` (khuôn [eval-config.schema.json](contracts/eval-config.schema.json)) lưu nguyên văn vào báo cáo; tiêu chí kết luận chỉ đọc từ cấu hình, **không có cờ ghi đè khi chạy** (INV-006). Phạm vi CHỈ M1: không giao diện tương tác (đã thuộc con 2), không replay/demo (con 4), không baseline/chỉ số ngoài yêu cầu, không M2–M9.

## Technical Context

**Language/Version**: Python 3.11 (ghim `.python-version` và `requires-python = ">=3.11,<3.13"` của 001)

**Primary Dependencies**: kế thừa 001–003 (`mujoco` 3.15.0, `myo-sim==0.2.3`, `gymnasium>=1.4,<1.5`, `numpy`, `pyyaml`, extra `rl`: `torch`, `tensorboard`; extra `dev`: `pytest`, `jsonschema`); **mới, extra `eval`**: `pandas` (ĐÃ ĐO cài được 3.0.6), `matplotlib` (ĐÃ ĐO 3.11.2). `uv pip install --dry-run` của toàn bộ tập (gồm `gymnasium 1.4.0`, `torch 2.14.1`, `numpy 2.4.6`) giải được 64 gói, không xung đột (research Q8). **Không** `scipy`, `seaborn`, `statsmodels`, Plotly/Altair

**Storage**: tệp — cấu hình `configs/eval_elbow.yaml`; mỗi lượt đánh giá một thư mục `runs/<run_id>/eval/<eval_id>/` (`report.json`, `episodes.csv`, `charts/*.png`); không CSDL

**Testing**: `pytest` (`python -m pytest`); test hợp đồng bằng `jsonschema` (draft 2020-12); test thống kê so với đáp án tay; test đường chính dùng mô hình MuJoCo thật cho `test_evaluate_cli`, và policy kịch bản (tới mục tiêu / không bao giờ tới) qua giao diện `act` cho kết luận; nhật ký mẫu cùng định dạng cho `test_training_log`; mọi test chạy với `DISPLAY` bỏ đặt

**Target Platform**: Linux gốc / WSL2 Ubuntu; phần cứng đích RTX 5060 8GB · Ryzen 9 HX · 32GB RAM; đánh giá là suy luận 1 môi trường, không cần GPU; máy phát triển hiện CHƯA có NVIDIA ⇒ đường GPU CHƯA KIỂM

**Project Type**: thư viện + CLI nghiên cứu (không máy chủ, không giao diện tương tác)

**Performance Goals**: không đặt ngưỡng tốc độ (master plan XI.10 cấm giả định; spec không có NFR hiệu năng); thời gian chạy và episode/giây do máy đo, ghi trong `report.timing` — KHÔNG là cam kết. Chi phí vẽ 3 biểu đồ thăm dò ≈ 0,25 s và đọc 8 000 sự kiện tfevents ≈ 0,12 s (ĐÃ ĐO, chỉ để đặt cỡ độ lớn)

**Constraints**: headless; chỉ kích thích cơ `u ∈ [0,1]^6` (INV-003); chỉ tập kiểm thử và seed ngoài tập train (INV-001); chỉ đọc dữ liệu con 2 (INV-005); không đường dẫn tuyệt đối riêng của máy trong tài liệu hay báo cáo

**Scale/Scope**: 1 mô hình (1 DoF, 6 cơ); mặc định khởi đầu 50 mục tiêu kiểm thử × 1 lần × 2 policy = 100 episode; ≈ 10 mô-đun mới (`evaluation/`); 1 script; ≈ 14 tệp test; 1 tệp cấu hình

## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | Mọi AC có test chạy ngoài; số liệu đánh giá do `evaluate.py` sinh vào `report.json`, không viết tay; kết luận chất lượng policy chỉ lấy từ báo cáo; ví dụ ở `contracts/examples/` ghi rõ là minh hoạ khuôn |
| II. Test trước, sửa sau | Đạt | Mỗi mô-đun có test đặt tên sẵn ở bảng truy vết; task tạo test đỏ trước mã; không skip/xfail; cơ chế kết luận được chứng minh bằng policy chất lượng đã biết, không phụ thuộc may rủi huấn luyện |
| III. Lát cắt nhỏ, một vai một task | Đạt | Mỗi mô-đun một trách nhiệm một tệp; `evaluation/` không import `learning.trainer`/`learning.ppo`; tệp chung với 001–003 chỉ `pyproject.toml` (thêm extra `eval`), `scripts/evaluate.py` (thay stub), `tests/integration/test_unimplemented_cli.py` của 001 (bỏ `evaluate` khỏi danh sách "chưa triển khai") và accessor `target_index` ở `single_agent.py` của 002 — mỗi tệp một task chủ, đứng sau task của chủ sở hữu (Quy tắc thứ tự) |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…007 và NFR-REPRO/REL/HEADLESS/STAT khai ở `spec.md`; plan chỉ tham chiếu. **Không có INV/NFR mới phát hiện ở bước plan** (mã thoát, tên mô-đun, tên thẻ nhật ký là chi tiết hợp đồng ở `contracts/cli.md` và cấu hình) |
| V. Không đổi cái không được yêu cầu | Đạt | Không đổi môi trường/reward (con 1), không đổi trainer/checkpoint (con 2), không refactor; hai thay đổi nhỏ ở tệp của người khác là accessor đọc-chỉ (D-2) và cập nhật test stub (cùng nguyên tắc 003 đã áp); đề xuất ghi thêm trường vào hồ sơ run (D-1) ghi như **đề xuất riêng**, không làm lẫn vào task |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; đường dẫn trong báo cáo tương đối (kiểm bằng `test_repo_hygiene` của 001 và `test_report_paths_relative`) |
| VII. Nhánh bảo vệ | Đạt | Lượt spec không commit, không đổi nhánh |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số trong `research.md` gắn nhãn "ĐÃ ĐO"/"CHƯA KIỂM"; báo cáo ghi mỗi con số lấy từ phép đo; không khẳng định policy tốt |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Data model/hợp đồng CHỈ ở `specs/004-…/`; `docs/` mới chỉ có `00-input/` ⇒ không có `context-map`/`docs/03-tactical/*` để đồng bộ; không tạo tài liệu rỗng |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm phụ thuộc ngoài danh sách; không có vi phạm cần ghi ở Complexity Tracking.

**Quy mô tài liệu & kiến trúc**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, gói `mma_ai`) như 001–003 ⇒ KHÔNG ghi `docs/02-strategic/context-map.md`, `docs/03-tactical/*` hay `docs/01-intent/overview.md`; **không có phân quyền** (lệnh dòng lệnh cục bộ, không vai/khoá/token) ⇒ không `rbac.md`. Hợp đồng dây (một CLI + tệp báo cáo JSON) có schema và ví dụ ở `contracts/`. Stack không đổi (`python-mujoco-cli`); `.ai/stack-proposal.yml` chỉ thêm một dòng căn cứ.

## Phụ thuộc vào 001, 002 và 003

001–003 mới có spec + plan, **chưa có mã**. 004 dựa vào giao diện theo hợp đồng đã công bố của chúng (giả định CHƯA KIỂM — research Q11):

| Mã | Thành phần | Dùng để | Ghi chú |
|---|---|---|---|
| D-1 | 003: `manifest.json` (`seed`, `config.env_config`, `model.sha256`, `status`, `resumed_from`, `model.muscle_names`) | seed train (cả chuỗi cha), dựng lại tập train, hash XML, trạng thái run | trường đề xuất `env.target_fingerprint_sha256` **chưa có**: thiếu ⇒ `provenance = rebuilt_from_config` + cảnh báo; đề xuất giao 003, không làm trong 004 |
| D-2 | 002: `reset(seed, options={"split": "test", "target_index": i})` | mỗi mục tiêu đúng một lần, cùng thứ tự cho hai policy | `options["target_index"]` **chưa có** trong hợp đồng 002 ⇒ một task nhỏ đọc-chỉ ở `single_agent.py` của 002 (sau task của 002), không đổi hành vi mặc định |
| D-3 | 003: `load_checkpoint`, `load_policy(...).act_deterministic(obs_raw)` | nạp policy chỉ-đọc, kiểm checkpoint | lỗi ⇒ `CheckpointUnusable` ⇒ mã 4 |
| D-4 | 002: `TargetGenerator`, `TargetSetPair{train,test,min_cross_distance_m,fingerprint_sha256}`, `make_env`, `model_record()`, `ObservationLayout` (kích hoạt 6 cơ ở chỉ số 2–7), `info{distance_m, reached, reward_dist, reward_effort, ctrl_effective, end_reason, target_index}`, lỗi `PhysicsInstabilityError` | tập đánh giá, giao rỗng, chỉ số episode | nếu `ObservationLayout` không công khai lát cắt kích hoạt: dùng `info["ctrl_effective"]` (đã có trong `step-info`) cho mức kích hoạt/nỗ lực — không cần thêm accessor |
| D-5 | 003: nhật ký `metrics.jsonl` / `tb/` với thẻ `loss…`, `reward…`, `activation/<tên cơ>` | biểu đồ | tên thật CHƯA KIỂM ⇒ `logs.tags` là cấu hình |
| D-6 | 001: `mma_ai.config`, `mma_ai.diagnostics.environment`, `mma_ai.reporting.runlog`; stub `scripts/evaluate.py` (thoát 3) | phiên bản thư viện, ghi JSON an toàn, nền cho CLI | 004 thay nội dung stub; test `test_unimplemented_cli` của 001 cập nhật để không còn đòi `evaluate` thoát 3 |

**Quy tắc thứ tự** (cho bước tasks): mọi task của 004 chạm mã đứng SAU task tương ứng của 001–003 (`depends_on`); `pyproject.toml` (thêm extra `eval`) do một task riêng, sau task thêm extra `rl` của 003; task accessor `target_index` ở `single_agent.py` của 002 đứng sau task `single_agent.py` của 002 và TRƯỚC `rollout`. Lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu, 004 không sao chép.

## Kiến trúc & tách trách nhiệm

Phụ thuộc một chiều: `evaluation → learning.checkpoint (003, chỉ nạp) → environment (002) → physics (001) → config`. `evaluation` không import `learning.trainer`/`learning.ppo`. Mô-đun mới:

| Mô-đun | Trách nhiệm | FR / INV |
|---|---|---|
| `evaluation/eval_config` | `EvalConfig.load`, kiểm khoá/giá trị (≤ 0, mức tin cậy ngoài (0,1), thiếu khoá); ném `EvalConfigError` | FR-007, FR-018 |
| `evaluation/policies` | `RandomPolicy` (bộ sinh có seed, không nhìn observation), `LearnedPolicy` (bọc `load_policy` của 003) | FR-003, INV-003, INV-007 |
| `evaluation/split_guard` | `check_disjoint`: dựng lại `TargetSetPair`, đi ngược chuỗi run cha lấy seed train, kiểm giao rỗng/khoảng cách/seed, ghi `provenance` | FR-008, FR-009, INV-001 |
| `evaluation/rollout` | `run_policy_on_targets`: mỗi mục tiêu `i` × `repeats`, kiểm hành động trước `step`, bắt `PhysicsInstabilityError`, sinh `EpisodeRecord` | FR-002, FR-016, INV-002 |
| `evaluation/metrics` | `summarize` (bảy nhóm chỉ số, `null`+`reason`), `read_training_log` (jsonl/tfevents → bảng dài) | FR-004, FR-010, FR-016, FR-017 |
| `evaluation/stats` | Wilson, Newcombe, bootstrap có seed, `decide` | FR-005, FR-006, NFR-STAT-001, INV-006 |
| `evaluation/charts` | `render_charts` (Agg, 3 PNG, `ChartData`, bỏ điểm không hữu hạn) | FR-010…FR-012 |
| `evaluation/report` | `build_report` (theo schema, từ chối NaN/Inf), `write_report`, `publish_report` (đổi tên thư mục tạm) | FR-013, FR-014, FR-017, FR-019, INV-004, INV-005 |
| `evaluation/runner` | `evaluate_checkpoint`: điều phối đúng thứ tự, xử lý lỗi/ngắt, ánh xạ ngoại lệ → mã thoát | FR-001, FR-015, INV-004 |
| `evaluation/errors` | `EvalConfigError`, `CheckpointUnusable`, `LeakageError`, `TrainSetUnknown`, `LogMissing`, `EvalWriteError` | FR-015 |
| `scripts/evaluate.py` | lệnh CLI mỏng gọi `evaluate_checkpoint`, in tóm tắt tiếng Việt | FR-001 |

### Quyết định thiết kế

- **Hai policy, một vòng**: `run_policy_on_targets` nhận `policy` qua giao diện `act(obs_raw)`; không có nhánh riêng cho random/learned ngoài việc dựng policy (INV-002). Seed episode `episode_base + k` đếm tuần tự; hai policy dùng cùng dãy seed.
- **Hành động**: kiểm hữu hạn và trong `[0,1]^6` ngay trước `env.step`; vi phạm ⇒ đếm NaN/Inf, episode bất thường, không gọi `step`. Không có đường ghi lực, góc khớp hay toạ độ tay (INV-003).
- **Chỉ số từ `info`**: `reached`/`distance_m`/`ctrl_effective`/`reward_*` của con 1; reward episode = tổng reward các bước; nỗ lực = trung bình theo bước của trung bình 6 `ctrl_effective`; khoảng cách cuối lấy ở bước cuối của episode không bất thường.
- **Trạng thái `abnormal`**: chỉ do `PhysicsInstabilityError` hoặc hành động hỏng; tính là không tới mục tiêu; loại khỏi thống kê khoảng cách; đếm vào `abnormal_rate` (spec Tự chốt).
- **Báo cáo**: một tệp `report.json` theo schema + `episodes.csv` mức thấp; trạng thái công bố chỉ `done` / `done_charts_incomplete`; `limits` luôn có (độ rộng khoảng tin cậy thật, phạm vi kết luận).
- **Không mock vật lý**: test đường chính dùng mô hình thật; policy kịch bản chỉ thay *policy*, không thay môi trường; `monkeypatch` chỉ để tiêm lỗi ghi đĩa/hành động hỏng và được gọi tên rõ. Không tự viết validator an ninh riêng ngoài `jsonschema` và các kiểm tra theo spec; test assert thẳng trên sản phẩm.

## Project Structure

### Documentation (this feature)

```text
specs/004-eval-vs-random-plots/
├── plan.md
├── research.md          # Q1 thống kê · Q2 nhật ký · Q3 biểu đồ · Q5 giao rỗng · Q6 ghi nguyên tử
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md                          # CMD-EVL-0001, mã thoát
│   ├── python-api.md                   # API-EVL-0001…0010
│   ├── eval-config.schema.json
│   ├── eval-report.schema.json
│   └── examples/                       # ví dụ hợp schema (minh hoạ khuôn, không phải kết quả đo)
├── checklists/requirements.md
├── request.link
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

### Source Code (repository root) — chỉ phần 004 thêm vào cây của 001–003

```text
configs/
└── eval_elbow.yaml          # seeds.*, episodes.*, criterion.*, stats.*, logs.*, charts.*, paths.*
src/mma_ai/
└── evaluation/
    ├── __init__.py
    ├── eval_config.py   policies.py   split_guard.py   rollout.py
    ├── metrics.py       stats.py      charts.py        report.py
    └── runner.py        errors.py
scripts/
└── evaluate.py           # thay stub của 001 (mã thoát theo contracts/cli.md)
tests/
├── unit/        # test_eval_config, test_policies, test_metrics, test_stats, test_training_log,
│                # test_charts, test_split_guard, test_report
├── integration/ # test_evaluate_cli, test_verdict_known_policies, test_evaluate_headless,
│                # test_evaluate_storage, test_report_contract, test_evaluation_imports
└── regression/  # test_eval_determinism
```

**Structure Decision**: dự án đơn (single project), mở rộng cây `src/mma_ai/` của 001–003 bằng một gói con `evaluation/`. Gói `visualization/` (con 4) **chưa tạo**. Không thêm quy tắc `.gitignore` (thư mục `runs/` đã bỏ khỏi git theo 003).

## Lệnh build / test (cho task khung dựng đúng một lần)

| Việc | Lệnh |
|---|---|
| Dựng môi trường | `uv python install 3.11 && uv sync --extra dev --extra rl --extra eval` |
| Toàn bộ test | `uv run python -m pytest -q` |
| Test riêng feature | `uv run python -m pytest -q tests/unit/test_stats.py tests/unit/test_split_guard.py tests/integration/test_evaluate_cli.py` |
| Chạy đánh giá | `uv run python scripts/evaluate.py --checkpoint runs/<run_id>/checkpoints/latest.json` |
| Đánh giá với số lần lặp khác | `uv run python scripts/evaluate.py --checkpoint <ckpt> --repeats 3` |
| Khoá phiên bản | `uv lock` — CHỈ sau khi smoke test đạt; commit `uv.lock` |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng / Test |
|---|---|---|
| FR-001, AC-1 | `runner`, `scripts/evaluate.py` | `test_evaluate_cli::test_both_policies_same_targets` |
| FR-002, INV-002 | `rollout`, `runner` | `test_evaluate_cli::test_both_policies_same_targets`, `test_report_contract::test_n_episodes_equal_targets_times_repeats`, `::test_hash_consistency` |
| FR-003, INV-003, INV-007 | `policies`, `rollout` | `test_evaluate_cli::test_actions_in_unit_interval`, `test_policies::test_random_policy_seeded_and_in_unit_interval`, `::test_random_ignores_observation` |
| FR-004 | `metrics` | `test_metrics::test_summarize_all_groups`, `test_evaluate_cli::test_all_metrics_present_with_ci` |
| FR-005, NFR-STAT-001 | `stats` | `test_stats::test_wilson_matches_hand_values`, `::test_newcombe_matches_hand_values`, `::test_edge_counts_0_and_n_finite`, `::test_bootstrap_seeded_reproducible` |
| FR-006, FR-007, INV-006 | `stats`, `eval_config`, `report` | `test_stats::test_verdict_rule_ci_lower_gt_zero`, `test_verdict_known_policies::test_scripted_reaching_policy_is_better`, `::test_always_zero_policy_is_not_better`, `::test_identical_policies_not_better`, `test_evaluate_cli::test_criterion_in_report_and_no_override_flag` |
| FR-008, FR-009, INV-001 | `split_guard` | `test_split_guard::test_disjoint_targets_and_min_distance_ok`, `::test_seed_equal_train_seed_rejected`, `::test_seed_range_overlap_rejected`, `::test_target_within_min_distance_rejected`, `::test_unknown_train_set_refused`, `::test_resume_chain_seeds_collected`, `::test_fingerprint_mismatch_rejected`, `test_evaluate_cli::test_leak_exits5_no_episode_run` |
| FR-010, FR-011 | `metrics` (`read_training_log`), `charts` | `test_training_log::test_reads_jsonl_and_tfevents`, `::test_missing_group_names_available_tags`, `test_charts::test_three_files_valid_png`, `::test_activation_has_six_named_lines`, `::test_points_match_log`, `test_evaluate_headless::test_missing_activation_series_exit6_results_saved` |
| FR-012 | `charts` | `test_charts::test_nonfinite_points_dropped_and_counted` |
| FR-013, KQ-4 | `report`, `runner` | `test_evaluate_storage::test_report_names_seed_and_checkpoint_hash`, `::test_two_evals_two_dirs_first_unchanged`, `::test_checkpoint_outside_run_requires_out` |
| FR-014, INV-005 | `runner`, `report` | `test_evaluate_storage::test_run_files_unchanged_by_evaluation`, `test_evaluation_imports::test_evaluation_has_no_training_imports` |
| FR-015, INV-004 | `runner`, `report` | `test_evaluate_cli::test_missing_checkpoint_exit4_no_output`, `::test_corrupt_checkpoint_exit4_names_cause`, `::test_missing_component_exit4`, `::test_xml_hash_mismatch_exit4`, `::test_no_eval_dir_after_checkpoint_error`, `test_evaluate_storage::test_no_partial_dir_on_interrupt`, `::test_unwritable_eval_dir_exit7` |
| FR-016 | `rollout`, `metrics` | `test_evaluate_cli::test_abnormal_episode_counted_not_fatal`, `test_metrics::test_abnormal_excluded_from_distance` |
| FR-017, NFR-REL-001 | `metrics`, `report` | `test_metrics::test_all_abnormal_distance_is_null_with_reason`, `test_report_contract::test_report_schema_and_no_nonfinite` |
| FR-018 | `eval_config` | `test_eval_config::test_invalid_values_raise`, `::test_defaults_load` |
| FR-019 | `report` | `test_report::test_limits_present_and_no_quality_claim`, `test_report_contract::test_contract_examples_eval` |
| FR-020 | toàn bộ bộ test trên | `python -m pytest` |
| NFR-REPRO-001 | `policies`, `stats`, `runner` | `test_eval_determinism::test_same_seed_same_actions_and_metrics`, `::test_diff_seed_diff_random_actions` |
| NFR-HEADLESS-001 | `charts`, `runner` | `test_evaluate_headless::test_evaluate_with_display_unset_exit0` |

## Rủi ro & việc CHƯA KIỂM

1. **001–003 chưa có mã** — 004 dựa vào hợp đồng đã công bố (D-1…D-6); lệch ⇒ sửa ở nơi chủ sở hữu, 004 chỉ thêm accessor đọc-chỉ.
2. **`options["target_index"]` của 002 chưa có (D-2)** — thiếu nó thì "mỗi mục tiêu một lần, cùng thứ tự" không đạt; task bổ sung là bắt buộc và đứng trước `rollout`.
3. **Trượt cấu hình môi trường (D-1)** — hồ sơ run chưa lưu băm tập mục tiêu; đánh giá dựng lại tập train từ cấu hình hiện tại và ghi `provenance`; nếu cấu hình bị sửa sau khi train, phép kiểm giao rỗng chỉ chắc chắn khi có băm trong hồ sơ hoặc người dùng ghim `expect_fingerprint_sha256`. Đề xuất ghi thêm hai trường vào hồ sơ run thuộc 003.
4. **Sức mạnh kiểm định thấp với 50 mục tiêu** — hiệu quanh 0,14 chưa đủ kết luận (ĐÃ ĐO trên đáp án giải tích); kết luận "không tốt hơn" có thể vừa do policy chưa tốt vừa do ít mẫu; báo cáo ghi độ rộng khoảng tin cậy thật trong `limits`. Tăng số mục tiêu là đổi cấu hình của con 1, không phải việc của 004.
5. **`repeats > 1` là xấp xỉ** (research Q1) — mặc định 1; báo cáo gắn `approximate = true`; không là điều kiện nghiệm thu.
6. **Tên thẻ nhật ký thật của con 2 (D-5)** — cấu hình `logs.tags`; test dùng nhật ký mẫu; chỉnh khi con 2 có mã.
7. **Kết quả đo trên checkpoint thật chưa biết** — một checkpoint train ngắn có thể "không tốt hơn random"; đó là kết quả hợp lệ, không phải lỗi hệ thống (mã thoát 0).
8. **`test_unimplemented_cli` của 001 hiện đòi `evaluate.py` thoát 3** — task chủ của 004 cập nhật đúng tệp test đó (bỏ `evaluate` khỏi danh sách), sau khi `scripts/evaluate.py` được thay.

## Phản biện plan_lint

- Cạnh tranh phương pháp khoảng tin cậy: bootstrap ghép cặp bị loại vì thoái hoá ([1,0 ; 1,0] cho 50 vs 0; [0 ; 0] khi ghép cặp giống hệt — ĐÃ ĐO); Wald z-test vỡ ở tỷ lệ 0/1; Fisher/z chính xác cần `scipy`. Newcombe đủ tốt, giải tích, kiểm được bằng đáp án tay.
- Dựng lại tập train từ cấu hình thay vì tin mù hồ sơ: chấp nhận rủi ro trượt cấu hình (rủi ro 3) đổi lấy việc không tự tạo nguồn sự thật thứ hai về tập train; ghi `provenance` để người đọc biết mức chắc chắn.
- Ghi nguyên tử bằng đổi tên thư mục: thêm một bước công bố đổi lấy bảo đảm không có kết quả dở dang (INV-004); chi phí tối thiểu.
- Chưa có số đo thật nào về kết quả đánh giá hay thời gian chạy: mọi con số trong plan là thiết kế hoặc thăm dò; nghiệm thu dựa vào `report.json` và test, không dựa vào plan.

## Complexity Tracking

Không có vi phạm hiến chương cần biện minh. Độ phức tạp thêm vào (kiểm giao rỗng bằng dựng lại tập train, thư mục tạm công bố bằng đổi tên) được biện minh trực tiếp bởi AC-4/INV-001 (đánh giá giả nếu rò rỉ) và AC-5/INV-004 (không kết quả giả); phương án đơn giản hơn (tin hồ sơ không kiểm, ghi thẳng vào thư mục đích) không đáp ứng các tiêu chí đó.
