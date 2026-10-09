---
id: "PLAN-005"
title: "M1 (4/4) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Implementation Plan: M1 (4/4) — Replay 3D và demo khuỷu tay do cơ điều khiển

**Branch**: `005-replay-3d-muscle-demo` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: `specs/005-replay-3d-muscle-demo/spec.md` (bản hiện tại, REQ-0104; không có `[NEEDS CLARIFICATION]`; Q-0001 thuộc `003-ppo-train-repro` — đã áp vào Clarifications như ranh giới, không đổi phạm vi con 4)

## Summary

Feature dựng **lớp hiển thị** cho M1: lệnh `python scripts/replay.py` có hai chế độ loại trừ nhau — `--episode <path>` **phát lại** một episode đã lưu trong MuJoCo Viewer (AC-1), và `--checkpoint <path>` **demo**: nạp policy của con 2 (chỉ đọc), chạy trọn một episode trên môi trường của con 1 rồi phát nó bằng đúng đường phát của replay, hiển thị mục tiêu và **6 activation có tên cơ** theo từng khung (AC-2). Có **định dạng episode** tự đủ (seed, hash XML, tên cơ, mục tiêu, nguồn) để con 3 hoặc người dùng đọc; có **chế độ `--headless`** kiểm dữ liệu và in tóm tắt máy đọc được (AC-3); **lệch hash XML** thì dừng, không phát sai ngầm (AC-4); **đường dẫn/tệp không dùng được** thì mã thoát khác 0 (AC-5).

Cách tiếp cận (chi tiết và số đo ở [research.md](research.md)):

- **Viewer thụ động + giao diện `FrameSink`** (Q1, Q9): `mujoco.viewer.launch_passive`; mục tiêu là hình cầu ở `user_scn`, 6 activation là bảng chữ `set_texts` (ĐÃ ĐO các API này có ở `mujoco 3.15.0`, chạy được ở `DISPLAY=:0`). Vòng phát (`play`) làm việc với `FrameSink` trừu tượng nên test khẳng định thứ tự khung, mục tiêu, HUD bằng một `RecordingSink` — chỉ thay *màn hình*, không thay vật lý.
- **Kiểm màn hình trước khi mở viewer** (Q2): `glfw.init()` trong tiến trình (ĐÃ ĐO: 0,03 s, trả 0 khi không có màn hình hoặc `DISPLAY` hỏng, không crash). Bỏ bước này, `launch_passive` kết thúc cả tiến trình bằng mã 1 và thông báo tiếng Anh từ mã C (ĐÃ ĐO ≈ 0,45 s) — không bắt được bằng Python.
- **Mã thoát không phụ thuộc dọn dẹp đồ hoạ** (Q3): ĐÃ ĐO viewer thụ động làm tiến trình sập `SIGSEGV` (139) hoặc treo lúc thoát ở 8/9 lần chạy; `os._exit(mã)` sau khi xả đầu ra đạt 3/3 lần mã 0. Chỉ `scripts/replay.py` làm việc đó và chỉ khi viewer đã mở.
- **Episode = một tệp JSON, một khung mỗi hành động** (Q4): hợp khuôn `episode.schema.json`, ≈ 379 byte/khung (ĐÃ ĐO) ⇒ vài chục KB; ghi nguyên tử, không ghi đè, không ghi ngầm; khi phát, nội suy tuyến tính `qpos`/`activation` giữa hai khung (hạn chế được ghi rõ).
- **Nhịp thời gian thực đo được** (Q5): `Pacer` với đồng hồ tiêm vào ⇒ NFR-PERF-001 kiểm tất định. Vì episode tới mục tiêu chỉ ≈ 0,16 s mô phỏng (ĐÃ ĐO ở 002), có **hệ số tốc độ** và **lặp**; khung trễ được đếm và báo, không bỏ âm thầm.
- **Lệch mô hình = dừng mặc định** (Q7): `check_model` so SHA-256 XML + `nq`/`nv`/6 tên cơ; chỉ `--allow-model-mismatch` mới đi tiếp (cấu trúc phải tương thích), kèm cảnh báo liên tục.
- **Không màn hình = kiểm dữ liệu, không xuất khung** (Q8): ĐÃ ĐO EGL và OSMesa không khởi tạo được, GLFW cần `DISPLAY`; `Xvfb` không có. Hứa xuất khung khi không có màn hình là hứa điều không kiểm được.
- **Không thêm phụ thuộc, không thêm extra** (Q10): `mujoco.viewer`/`glfw` đi kèm `mujoco`; đường `--episode` không cần `torch`. Phạm vi CHỈ M1: không giao diện web, không quay video, không đối thủ/arena, không M2–M9, không giao diện quan sát training (đã thuộc con 2).

## Technical Context

**Language/Version**: Python 3.11 (ghim `.python-version` và `requires-python = ">=3.11,<3.13"` của 001)

**Primary Dependencies**: kế thừa 001–003 (`mujoco` 3.15.0 — gồm `mujoco.viewer` và `glfw`; `myo-sim==0.2.3`; `gymnasium>=1.4,<1.5`; `numpy`; `pyyaml`; extra `rl`: `torch` — chỉ cho `--checkpoint`; extra `dev`: `pytest`, `jsonschema`). **Mới: không có.** `pyproject.toml` không đổi (research Q10). **Không** Open3D/PyVista/Plotly, **không** `imageio`/`ffmpeg` (không quay video)

**Storage**: tệp — cấu hình `configs/replay.yaml`; episode do người dùng chỉ định (khuyến nghị `runs/<run_id>/replays/*.episode.json`); không CSDL

**Testing**: `pytest` (`python -m pytest`); test hợp đồng bằng `jsonschema` (draft 2020-12); bộ lập nhịp bằng đồng hồ giả; HUD/thứ tự khung bằng `RecordingSink`; đường demo dùng mô hình MuJoCo thật và policy kịch bản qua giao diện `act_deterministic`; **một** test rẽ nhánh theo `display_available()` cho viewer thật (research Q9) — không `skip`/`xfail`; mọi test khác chạy với `DISPLAY` bỏ đặt

**Target Platform**: Linux gốc (ĐÃ ĐO có màn hình `DISPLAY=:0`) / WSL2 Ubuntu (CHƯA KIỂM, kể cả WSLg); phần cứng đích RTX 5060 8GB · Ryzen 9 HX · 32GB RAM; replay không cần GPU riêng; máy phát triển hiện CHƯA có NVIDIA

**Project Type**: thư viện + CLI nghiên cứu có một cửa sổ đồ hoạ tuỳ chọn (không máy chủ)

**Performance Goals**: không đặt ngưỡng khung/giây tuyệt đối (spec Clarifications; master plan XI.10); mục tiêu đo được là nhịp: thời gian phát / thời gian mô phỏng ∈ [0,95 ; 1,05] ở tốc độ 1,0 (NFR-PERF-001). Số đo thăm dò để đặt cỡ: mở viewer ≈ 0,53 s; chi phí một vòng đồng bộ ≈ 7–8 ms; mô phỏng 100 hành động ≈ 0,011 s (ĐÃ ĐO, không là cam kết)

**Constraints**: chỉ kích thích cơ `u ∈ [0,1]^6` trong demo (INV-002); replay chỉ đặt trạng thái đã ghi; chỉ đọc dữ liệu con 2 (INV-005); không import `learning.trainer`/`learning.ppo`; không đường dẫn tuyệt đối riêng của máy trong tài liệu hay bản ghi; replay là tiến trình riêng, không nằm trong vòng train (master plan XI.8)

**Scale/Scope**: 1 mô hình (1 DoF, 6 cơ); episode ≤ 100 hành động ≈ 4 s mô phỏng (≈ 38 KB); 12 tệp mô-đun mới trong `visualization/`; 1 script; 19 tệp test; 1 tệp cấu hình

## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | Mọi AC có test chạy ngoài; mã thoát và tóm tắt do `replay.py` sinh; phần "viewer thật" có bằng chứng từ lần chạy trên máy có màn hình ghi vào `evidence/` do cổng sinh, không do tay viết; ví dụ ở `contracts/examples/` ghi rõ là minh hoạ khuôn (hash giả) |
| II. Test trước, sửa sau | Đạt | Mỗi mô-đun có test đặt tên sẵn ở bảng truy vết; task tạo test đỏ trước mã; **không** skip/xfail — phần cần màn hình dùng test rẽ nhánh theo môi trường (cả hai nhánh là khẳng định thật) |
| III. Lát cắt nhỏ, một vai một task | Đạt | Mỗi mô-đun một trách nhiệm một tệp; `visualization/` không import `learning.trainer`/`learning.ppo`; tệp chung với 001–003 chỉ `scripts/replay.py` (thay stub), `tests/integration/test_unimplemented_cli.py` của 001 (bỏ `replay` khỏi danh sách "chưa triển khai") và accessor `read_state()` (cùng `target_index`) ở `single_agent.py` của 002 — mỗi tệp một task chủ, đứng sau task của chủ sở hữu (Quy tắc thứ tự). `pyproject.toml` KHÔNG đổi |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…006 và NFR-PERF/HEADLESS/REPRO/REL-001 khai ở `spec.md`; plan chỉ tham chiếu. **Không có INV/NFR mới phát hiện ở bước plan** (mã thoát, tên mô-đun, `os._exit` là chi tiết hợp đồng ở `contracts/cli.md` và research Q3) |
| V. Không đổi cái không được yêu cầu | Đạt | Không đổi môi trường/reward (con 1), trainer/checkpoint/`viewer3d` (con 2); không refactor; không phụ thuộc mới; hai thay đổi nhỏ ở tệp của người khác là accessor đọc-chỉ (D-2) và cập nhật test stub (cùng nguyên tắc 003/004 đã áp); đề xuất chuyển HUD dùng chung cho `viewer3d` (research Q10) ghi như **đề xuất riêng**, không làm lẫn vào task |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; đường dẫn trong episode và tóm tắt là tương đối (kiểm bằng `test_repo_hygiene` của 001 và `test_summary::test_paths_relative`) |
| VII. Nhánh bảo vệ | Đạt | Lượt spec không commit, không đổi nhánh |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số trong `research.md` gắn nhãn "ĐÃ ĐO"/"CHƯA KIỂM"; tóm tắt ghi mỗi con số lấy từ phép đo; không khẳng định policy tốt |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Data model/hợp đồng CHỈ ở `specs/005-…/`; `docs/` mới chỉ có `00-input/` ⇒ không có `context-map`/`docs/03-tactical/*` để đồng bộ; không tạo tài liệu rỗng |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm phụ thuộc; không có vi phạm cần ghi ở Complexity Tracking.

**Quy mô tài liệu & kiến trúc**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, gói `mma_ai`) như 001–004 ⇒ KHÔNG ghi `docs/02-strategic/context-map.md`, `docs/03-tactical/*` hay `docs/01-intent/overview.md`; **không có phân quyền** (lệnh dòng lệnh cục bộ, không vai/khoá/token) ⇒ không `rbac.md`. Hợp đồng dây (một CLI + ba khuôn JSON) có schema và ví dụ ở `contracts/`. Stack không đổi (`python-mujoco-cli`); `.ai/stack-proposal.yml` chỉ thêm một dòng căn cứ.

## Phụ thuộc vào 001, 002 và 003

001–003 mới có spec + plan, **chưa có mã**. 005 dựa vào giao diện theo hợp đồng đã công bố của chúng (giả định CHƯA KIỂM — research Q11):

| Mã | Thành phần | Dùng để | Ghi chú |
|---|---|---|---|
| D-1 | 003: `load_checkpoint`, `load_policy(path).act_deterministic(obs_raw)`, `checkpoints/latest.json`, `manifest.json` (`run_id`, `model.sha256`) | nạp policy chỉ-đọc cho demo; điền `episode.source` | lỗi ⇒ `CheckpointUnusable` ⇒ mã 4; nhập lười để `--episode` không cần `torch` |
| D-2 | 002: `make_env(split)`, `reset(seed, options={"split", "target_index"})`, `step`, `info`, `model_record()`, `PhysicsInstabilityError` **và một accessor đọc-chỉ mới** `ElbowReachEnv.read_state()` (bản sao `qpos`, `qvel`, `act`, `fingertip_position_m`, `target_position_m`, `time_s`) | chạy demo, ghi khung | `options["target_index"]` đã được 004 xin (D-2 của 004) — **một chủ một tệp**: nếu task của 004 đã giao thì 005 chỉ phụ thuộc; `read_state()` **chưa có** trong hợp đồng 002 ⇒ một task nhỏ đọc-chỉ ở `single_agent.py` của 002 (sau task của 002), không đổi hành vi mặc định |
| D-3 | 001: `load_muscle_model` / `MuscleModelInfo` (SHA-256, tên cơ, `nq`, `nv`), `mma_ai.reporting.runlog` (ghi JSON an toàn), stub `scripts/replay.py` (thoát 3) | kiểm hash/cấu trúc, nạp `MjModel` cho viewer, nền cho CLI | 005 thay nội dung stub; `test_unimplemented_cli` của 001 cập nhật để không còn đòi `replay` thoát 3 |
| D-4 | `mujoco` 3.15.0: `mujoco.viewer.launch_passive` (`user_scn`, `set_texts`, `sync`, `is_running`, `close`) và `glfw` | viewer, kiểm màn hình | ĐÃ ĐO (research Q1, Q2); đổi phiên bản `mujoco` ⇒ chạy lại thăm dò |
| D-5 | 003: `monitoring/viewer3d.py` | **không phụ thuộc** | là giao diện quan sát training của con 2 (Q-0001); 005 không import, không sửa (research Q10) |

**Quy tắc thứ tự** (cho bước tasks): mọi task của 005 chạm mã đứng SAU task tương ứng của 001–003 (`depends_on`); task accessor `read_state()` ở `single_agent.py` của 002 đứng sau task `single_agent.py` của 002 (và cùng task với `target_index` nếu 004 chưa giao) và TRƯỚC `recorder`; `scripts/replay.py` và `test_unimplemented_cli` mỗi tệp một task chủ. Lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu, 005 không sao chép.

## Kiến trúc & tách trách nhiệm

Phụ thuộc một chiều: `visualization → learning.checkpoint (003, chỉ nạp, nhập lười) → environment (002) → physics (001) → config`. `visualization` không import `learning.trainer`/`learning.ppo`. Chỉ `viewer.py` nhập `mujoco.viewer`, chỉ `display.py` nhập `glfw`; cả hai nhập lười nên `--headless` không đụng đồ hoạ. Mô-đun mới:

| Mô-đun | Trách nhiệm | FR / INV |
|---|---|---|
| `visualization/replay_config` | `ReplayConfig.load`, kiểm khoá/giá trị; ném `ReplayConfigError` | FR-006, FR-017 |
| `visualization/episode` | `Episode`/`Frame`, `read_episode` (khuôn + luật R1–R7), `write_episode` (nguyên tử, không ghi đè) | FR-007…FR-009, INV-003, INV-005 |
| `visualization/recorder` | `record_episode`: chạy một episode bằng policy, kiểm hành động trước `step`, đọc trạng thái qua `env.read_state()` | FR-002, FR-003, INV-002 |
| `visualization/model_check` | `check_model`, `enforce` (INV-001) | FR-012, INV-001 |
| `visualization/summary` | `summarize_episode` (thống kê activation, từ chối NaN/Inf) | FR-010, NFR-REL-001 |
| `visualization/pacing` | `Pacer`, `frame_at` (nội suy), `PlaybackStats` | FR-006, NFR-PERF-001 |
| `visualization/hud` | `hud_lines` (tên cơ + giá trị + thanh; làm tròn chỉ ở đây) | FR-005, INV-006 |
| `visualization/playback` | `FrameSink`, `play` (thứ tự khung, lặp, giữ khung cuối) | FR-001, FR-004…FR-006 |
| `visualization/display` | `display_available` (glfw, nhập lười) | FR-011, NFR-HEADLESS-001 |
| `visualization/viewer` | `ViewerSink` bọc `launch_passive` | FR-001, FR-004, FR-005 |
| `visualization/replay` | `run_replay(args) -> int`: điều phối đúng thứ tự, ánh xạ ngoại lệ → mã thoát | FR-001, FR-002, FR-010…FR-014 |
| `visualization/errors` | `ReplayConfigError`, `EpisodeNotFound`, `EpisodeInvalid`, `EpisodeWriteError`, `CheckpointUnusable`, `ModelMismatch`, `DisplayUnavailable`, `DemoUnstable` | FR-013 |
| `scripts/replay.py` | CLI mỏng gọi `run_replay`, xả đầu ra rồi `os._exit` khi viewer đã mở | FR-014 |

### Quyết định thiết kế

- **Demo = chạy trọn rồi phát**: `record_episode` hoàn tất (≪ 1 s, ĐÃ ĐO 0,011 s cho 100 hành động vật lý thuần; chi phí suy luận policy CHƯA KIỂM) rồi `play` phát chính `Episode` đó — một đường phát duy nhất cho replay và demo; cái thấy khi demo ≡ tệp lưu; đóng cửa sổ giữa chừng không làm cụt dữ liệu (Edge Case của spec được thoả bằng thiết kế).
- **Ghi trước, mở cửa sổ sau**: `--save-episode` ghi nguyên tử *trước* khi mở viewer; Ctrl-C hay đóng cửa sổ về sau không mất tệp và không để tệp dở dang (INV-004).
- **HUD**: bảng chữ 6 dòng (tên cơ, giá trị làm tròn `hud.decimals`, thanh `hud.bar_width`) + một dòng trạng thái (khung k/n, tỷ lệ thời gian) + dòng "MÔ HÌNH LỆCH" khi cần. Giá trị lấy từ `Frame` (đã nội suy khi hiển thị giữa hai khung; ở khung gốc là đúng giá trị ghi).
- **Hành động**: demo chỉ qua `policy.act_deterministic(obs_raw)` → kiểm hữu hạn và `[0,1]^6` ngay trước `env.step`; vi phạm ⇒ episode `abnormal`, không gọi `step` với giá trị sai. Không có đường ghi lực, góc khớp hay toạ độ tay; `recorder` không ghi vào `MjData` (INV-002).
- **Không mock vật lý**: test dùng mô hình thật; `RecordingSink` chỉ thay màn hình; `monkeypatch` chỉ để tiêm lỗi ghi đĩa, chặn `os._exit` và đồng hồ giả, được gọi tên rõ. Không tự viết trình kiểm an ninh riêng ngoài `jsonschema` và các kiểm tra theo spec; test assert thẳng trên sản phẩm.

## Project Structure

### Documentation (this feature)

```text
specs/005-replay-3d-muscle-demo/
├── plan.md
├── research.md          # Q1 viewer · Q2 màn hình · Q3 mã thoát · Q4 episode · Q5 nhịp · Q6 trạng thái · Q7 lệch mô hình · Q8 headless · Q9 kiểm thử · Q10 phụ thuộc
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md                          # CMD-VIS-0001, mã thoát
│   ├── python-api.md                   # API-VIS-0001…0012
│   ├── episode.schema.json
│   ├── replay-summary.schema.json
│   ├── replay-config.schema.json
│   └── examples/                       # ví dụ hợp schema (minh hoạ khuôn, không phải kết quả đo)
├── checklists/requirements.md
├── request.link
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

### Source Code (repository root) — chỉ phần 005 thêm vào cây của 001–004

```text
configs/
└── replay.yaml              # playback.*, demo.*, hud.*, target_marker.*
src/mma_ai/
└── visualization/
    ├── __init__.py
    ├── replay_config.py   episode.py     recorder.py   model_check.py
    ├── summary.py         pacing.py      hud.py        playback.py
    ├── display.py         viewer.py      replay.py     errors.py
scripts/
└── replay.py                # thay stub của 001 (mã thoát theo contracts/cli.md)
tests/
├── unit/        # test_replay_config, test_episode, test_recorder, test_model_check, test_summary,
│                # test_pacing, test_hud, test_playback, test_display, test_script_exit
├── integration/ # test_demo_cli, test_replay_headless, test_replay_nodisplay, test_replay_model_mismatch,
│                # test_replay_bad_input, test_replay_viewer_real, test_replay_readonly,
│                # test_visualization_imports, test_contract_examples_replay
```

**Structure Decision**: dự án đơn (single project), mở rộng cây `src/mma_ai/` của 001–004 bằng một gói con `visualization/` (đúng tên mô-đun kiến trúc `visualization/replay.py` và `scripts/replay.py` của master plan). Không thêm quy tắc `.gitignore` mới (`runs/` đã bỏ khỏi git theo 003; episode ghi vào `runs/…/replays/` theo khuyến nghị).

## Lệnh build / test (cho task khung dựng đúng một lần)

| Việc | Lệnh |
|---|---|
| Dựng môi trường | `uv python install 3.11 && uv sync --extra dev --extra rl` (không extra mới) |
| Toàn bộ test | `uv run python -m pytest -q` |
| Test riêng feature | `uv run python -m pytest -q tests/unit/test_episode.py tests/unit/test_pacing.py tests/integration/test_replay_headless.py tests/integration/test_replay_nodisplay.py` |
| Sinh episode không màn hình | `uv run python scripts/replay.py --checkpoint runs/<run_id>/checkpoints/latest.json --headless --save-episode runs/<run_id>/replays/test0.episode.json` |
| Xem lại (có màn hình) | `uv run python scripts/replay.py --episode runs/<run_id>/replays/test0.episode.json --speed 0.1` |
| Khoá phiên bản | `uv lock` — không đổi vì không thêm phụ thuộc |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng / Test |
|---|---|---|
| FR-001, AC-1 | `playback`, `viewer`, `replay` | `test_playback::test_frames_in_recorded_order`, `test_replay_viewer_real::test_real_viewer_plays_or_reports_no_display` |
| FR-002, AC-2 | `replay`, `recorder` | `test_demo_cli::test_demo_saves_episode_headless`, `test_replay_bad_input::test_both_or_neither_mode_exit2` |
| FR-003, INV-002 | `recorder` | `test_demo_cli::test_demo_only_muscle_excitation_in_unit_interval`, `test_recorder::test_actions_checked_before_step`, `::test_recorder_never_writes_env_state` |
| FR-004 | `playback`, `viewer` | `test_playback::test_target_marker_at_recorded_position` |
| FR-005, INV-006 | `hud`, `playback` | `test_playback::test_hud_shows_recorded_activation_each_frame`, `::test_hud_names_match_muscle_names`, `test_hud::test_rounding_only_in_display` |
| FR-006, NFR-PERF-001 | `pacing`, `playback`, `replay` | `test_pacing::test_ratio_within_5pct_at_speed_1`, `::test_late_frames_reported_not_dropped`, `::test_single_frame_episode_no_zero_division`, `::test_loop_repeats_until_sink_closed`, `test_replay_headless::test_short_episode_hint_on_stderr` |
| FR-007, INV-003 | `episode` | `test_episode::test_write_read_roundtrip_and_schema`, `::test_required_provenance_fields`, `test_contract_examples_replay::test_examples_match_schemas` |
| FR-008, INV-005 | `episode`, `replay` | `test_episode::test_refuse_overwrite`, `::test_atomic_write_no_partial`, `test_demo_cli::test_no_file_written_without_save_flag`, `test_replay_bad_input::test_existing_save_path_exit8_not_overwritten` |
| FR-009 | `episode` | `test_episode::test_n_actions_matches_frames`, `::test_time_monotonic`, `::test_state_dims_match_model`, `::test_first_frame_has_no_action`, `::test_muscle_names_unique`, `::test_outcome_consistent`, `test_replay_bad_input::test_corrupt_json_exit5_names_field` |
| FR-010 | `replay`, `summary` | `test_replay_headless::test_summary_has_all_fields`, `test_summary::test_activation_stats_match_hand_values`, `test_demo_cli::test_demo_saves_episode_headless` |
| FR-011, NFR-HEADLESS-001 | `display`, `replay` | `test_replay_nodisplay::test_no_display_exits_7_fast_with_hint`, `::test_headless_exit0_with_summary`, `::test_bogus_display_handled_like_no_display`, `test_display::test_unavailable_reports_reason_without_crash` |
| FR-012, INV-001 | `model_check`, `replay` | `test_model_check::test_hash_and_structure_cases`, `test_replay_model_mismatch::test_mismatch_stops_names_both_hashes`, `::test_mismatch_allowed_warns_persistently`, `::test_incompatible_structure_always_refused` |
| FR-013, INV-004 | `replay`, `episode` | `test_replay_bad_input::test_missing_episode_exit5`, `::test_missing_checkpoint_exit4_no_viewer_no_file`, `::test_interrupt_leaves_no_partial_episode`, `::test_checkpoint_xml_hash_mismatch_exit4` |
| FR-014 | `replay`, `scripts/replay.py` | `test_script_exit::test_os_exit_only_when_viewer_opened`, `::test_exit_code_is_result_not_teardown`, `test_replay_viewer_real::test_real_viewer_plays_or_reports_no_display` |
| FR-015 | toàn gói | `test_visualization_imports::test_visualization_has_no_training_imports`, `::test_episode_path_does_not_import_torch`, `::test_headless_never_imports_viewer` |
| FR-016 | `replay`, `recorder` | `test_demo_cli::test_demo_selects_requested_target`, `test_replay_bad_input::test_target_index_out_of_range_exit2` |
| FR-017 | `replay_config` | `test_replay_config::test_invalid_values_raise`, `::test_defaults_load` |
| FR-018 | `replay`, `summary`, `episode` | `test_replay_bad_input::test_errors_are_vietnamese_with_context`, `test_summary::test_paths_relative` |
| FR-019 | toàn bộ bộ test trên | `python -m pytest` |
| NFR-REPRO-001 | `recorder` | `test_demo_cli::test_demo_same_seed_same_episode` |
| NFR-REL-001 | `episode`, `summary` | `test_episode::test_nonfinite_rejected`, `test_contract_examples_replay::test_no_nonfinite_values`, `test_replay_bad_input::test_nonfinite_values_exit5` |
| INV-005 (chỉ đọc) | toàn gói | `test_replay_readonly::test_run_files_unchanged_by_replay_and_demo` |

## Rủi ro & việc CHƯA KIỂM

1. **001–003 chưa có mã** — 005 dựa vào hợp đồng đã công bố (D-1…D-5); lệch ⇒ sửa ở nơi chủ sở hữu, 005 chỉ thêm accessor đọc-chỉ.
2. **`ElbowReachEnv.read_state()` và `options["target_index"]` của 002 chưa có (D-2)** — thiếu `read_state()` thì không ghi được `qpos`/`act`/đầu mút; task bổ sung là bắt buộc và đứng trước `recorder`. Hai feature (004, 005) cùng chạm `single_agent.py`: một chủ một tệp, task đứng đầu giao cả hai accessor.
3. **Viewer sập/treo lúc thoát tiến trình (research Q3)** — ĐÃ ĐO 8/9 lần ở máy phát triển; `os._exit` giải quyết 3/3 lần nhưng nguyên nhân gốc và hành vi trên WSLg/RTX 5060 CHƯA KIỂM; nếu một ngày `launch_passive` kết thúc tiến trình từ mã C khi khởi tạo thất bại dù `glfw.init()` thành công (driver GL hỏng) thì không bắt được trong tiến trình (Q2).
4. **Viewer thật không chạy trong CI không màn hình** — test rẽ nhánh theo môi trường chỉ chạy nhánh AC-3 ở đó; nhánh phát thật cần lần chạy trên máy có màn hình, bằng chứng ghi ở `evidence/`. Không có cách tự động hoá ở máy đo (`Xvfb` không có; EGL/OSMesa không khởi tạo).
5. **Nội suy giữa hai khung hành động** — hình giữa hai khung 25 Hz là nội suy tuyến tính, không phải trạng thái vật lý thật (research Q4); khi cần chính xác, dùng các khung gốc; không là điều kiện nghiệm thu.
6. **Episode ngắn (≈ 0,16–0,5 s)** — phát 1,0× gần như không nhìn được; cần `--speed`/`--loop` (đã đưa vào spec); chưa biết policy thật tới mục tiêu sau bao nhiêu hành động — số đo thật chỉ có khi 002/003 có mã.
7. **Hai nơi vẽ mục tiêu + activation** (`viewer3d` của 003 và `viewer` của 005) — trùng việc nhưng không thể chung mã vì 005 sau 003; đề xuất riêng ghi ở research Q10, không làm trong 005.
8. **Chi phí suy luận policy trong demo CHƯA KIỂM** (cần `torch` và checkpoint thật); đã đo chỉ phần mô phỏng thuần.
9. **`test_unimplemented_cli` của 001 hiện đòi `replay.py` thoát 3** — task chủ của 005 cập nhật đúng tệp test đó (bỏ `replay` khỏi danh sách) sau khi `scripts/replay.py` được thay; phải đồng bộ với task tương tự của 003 (`train`) và 004 (`evaluate`) — cùng một tệp, mỗi lần một task chủ theo thứ tự.

## Phản biện plan_lint

- Chạy viewer trong tiến trình con để bắt cái chết của nó: loại — tăng độ phức tạp (truyền episode, đồng bộ) đổi lấy một ca hiếm chưa quan sát được; `glfw.init()` trong tiến trình đã bắt được ca không có/hỏng màn hình (ĐÃ ĐO), `os._exit` đã giải quyết ca thoát (ĐÃ ĐO).
- Dùng `os._exit` có che lỗi thật không: mã thoát được tính từ kết quả phát và chỉ áp dụng sau khi viewer đã mở và handle đã đóng; các lỗi trước đó (tham số, nguồn, mô hình, màn hình, ghi) đều thoát bằng đường bình thường với mã riêng.
- Demo chạy trọn rồi phát thay vì phát khi đang chạy: bớt "trực tiếp" theo nghĩa đen nhưng chỉ chậm ≪ 1 s (ĐÃ ĐO phần mô phỏng), đổi lấy một đường phát duy nhất, tệp lưu trùng cái đã xem, và nội suy không cần chờ hành động kế.
- Không xuất khung ảnh: ghi rõ trong spec và Out of Scope là do đo được EGL/OSMesa không khả dụng; nếu sau này có máy dựng hình được, thêm là việc của feature khác.
- Chưa có số đo thật nào về hành vi policy hay FPS trên phần cứng đích: mọi con số trong plan là thiết kế hoặc thăm dò; nghiệm thu dựa vào tóm tắt, mã thoát và test, không dựa vào plan.

## Complexity Tracking

Không có vi phạm hiến chương cần biện minh. Độ phức tạp thêm vào (giao diện `FrameSink`, bước kiểm màn hình trước khi mở viewer, `os._exit` có điều kiện) được biện minh trực tiếp bởi số đo: không có `FrameSink` thì AC-1/AC-2 không kiểm tự động được ở môi trường không màn hình; không có bước kiểm màn hình thì AC-3 chết tiến trình bằng thông báo tiếng Anh (ĐÃ ĐO); không có `os._exit` thì AC-1 ("không lỗi") sai ở 8/9 lần chạy (ĐÃ ĐO). Phương án đơn giản hơn (gọi thẳng viewer, thoát bình thường) không đáp ứng các tiêu chí đó.
