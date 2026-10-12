---
id: "PLAN-009"
title: "Năng lực requires_git_history — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Implementation Plan: Năng lực `requires_git_history` cho cổng năng lực

- [Summary](#summary)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Kiến trúc & quyết định thiết kế](#kien-truc-quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 009 chạm tới](#source-code-repository-root-chi-phan-009-cham-toi)
- [Lệnh build / test](#lenh-build-test)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks)
- [Complexity Tracking](#complexity-tracking)


**Branch**: `009-git-history-capability` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: `specs/009-git-history-capability/spec.md` (bản hiện tại, 1.0.0; không còn `[NEEDS CLARIFICATION]`; Q-0001/Q-0002 không áp dụng — xem Clarifications của spec).

<a id="summary"></a>
## Summary

Cổng toàn hệ chạy trên bản archive không có `.git` nên test INV-002 của 008 đỏ (git thoát 128). Hướng đã chốt: dùng cổng năng lực của 006 — test thiếu năng lực bị **loại khi thu thập, có báo cáo**, không skip/xfail, ngưỡng 5% giữ nguyên. Mã năng lực `requires_git_history` **đã có** ở `tests/unit/capability_gate.py` (nhánh tích hợp @ffea840). Feature chỉ thêm **hai thay đổi test**, test trước mã:

1. **W-1 (builder)** — `tests/unit/test_capability_gate.py`: bốn test đơn vị thay `subprocess.run` trong mô-đun `capability_gate` (mã 0 ⇒ `True`; mã 128 ⇒ `False`; `OSError` ⇒ `False`; `TimeoutExpired` ⇒ `False`, kiểm `timeout` ≤ 5) và một test chạy pytest thật trong cây tạm không có `.git` cho thấy test gắn dấu bị loại có báo cáo (FR-001…FR-003).
2. **W-2 (qa)** — `tests/e2e/test_008_docs_entrypoints.py`: thêm đúng một dòng `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` lên `test_inv002_document_commits_keep_product_code_untouched`; thân hàm, assert, test khác giữ nguyên (FR-005, FR-006).

Không đổi `capability_gate.py` trừ khi W-1 chứng minh lỗi (FR-004: task riêng, test đỏ trước sửa). Không `pyproject.toml`/`uv.lock`, không nới 5%, không nhánh dự phòng PASS (INV-001…INV-003). Giới hạn phải ghi trong báo cáo: INV-002 của 008 chỉ chứng minh được ở môi trường có git (FR-010).

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Python ≥ 3.11, < 3.13 (`pyproject.toml`; `target-version = py312` cho `ruff`/`mypy`)

**Primary Dependencies**: `pytest` (cổng kiểm thử, dấu năng lực qua plugin `capability_gate`); không thêm phụ thuộc

**Storage**: N/A — chỉ thư mục tạm (`tmp_path`) và tệp báo cáo JSON tạm

**Testing**: `pytest` (đơn vị + e2e); `ruff check`, `mypy --strict`

**Target Platform**: Linux (nhánh tích hợp/cổng); test W-1 viết theo cách chạy được cả Windows/macOS (dùng `sys.executable`, `pathlib`, `shutil`, không giả định `/`)

**Project Type**: thư viện + CLI (`python-mujoco-cli`, stack đã có ở `.ai/stack-proposal.yml`; không ghi lại)

**Performance Goals**: không có; test W-1 mỗi test ≲ 1 s (một tiến trình con pytest ≲ 5 s)

**Constraints**: phép dò ≤ 5 s và không ném ngoại lệ (NFR-REL-001); tỉ lệ loại ≤ 5% (NFR-GATE-001); `ruff` + `mypy --strict` xanh (NFR-QUAL-001); vùng ghi đúng hai tệp test (FR-011)

**Scale/Scope**: 2 tệp test; ≈ 5 test mới và 1 dòng decorator

<a id="constitution-check"></a>
## Constitution Check

| Nguyên tắc | Đạt? | Căn cứ |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | AC-3 chứng minh bằng cổng `ai-sdlc verify`; AC-2 bằng test pytest thật + `--capability-report`; báo cáo tự viết chỉ là lời giải thích |
| II. Test trước, sửa sau | Đạt | W-1 là test; nếu lộ lỗi ở `capability_gate.py`, task sửa riêng có test đỏ trước (FR-004); không thêm skip/xfail (INV-001) |
| III. Lát cắt nhỏ, một vai một task | Đạt | hai task chính (builder: 1 tệp; qa: 1 tệp), mỗi tệp một chủ |
| IV. INV/NFR có mã và ngưỡng | Đạt | INV-001…003, NFR-REL-001/GATE-001/QUAL-001 khai ở `spec.md`, mỗi NFR có `Ngưỡng:`/`Đo bằng:` |
| V. Không đổi cái không được yêu cầu | Đạt | không đụng `pyproject.toml`/`uv.lock`/ngưỡng/test 008 khác (INV-002, INV-003) |
| VI. Bí mật qua biến môi trường | Đạt | không bí mật; test không ghi đường dẫn tuyệt đối riêng của máy |
| VII. Nhánh bảo vệ | Đạt | không commit/đổi nhánh ở lượt đặc tả; thi công qua nhánh task |
| VIII–IX. Tài liệu sinh từ mã; mỗi tài liệu một chỗ | Đạt | chi tiết chỉ ở `specs/009-…/`; không chép sang `docs/` (chỉ một bounded context ⇒ chỉ `plan.md`) |

Không vi phạm ⇒ bảng Complexity Tracking trống.

<a id="kien-truc-quyet-dinh-thiet-ke"></a>
## Kiến trúc & quyết định thiết kế

Một bounded context (hạ tầng kiểm thử); không có `docs/02-strategic/context-map.md` mới, không `docs/03-tactical/*`, không `rbac.md`, không `contracts/` (không có API/wire mới; báo cáo năng lực JSON là hợp đồng của 006, feature chỉ đọc — xem [data-model.md](data-model.md)).

| # | Quyết định | Lý do | Căn cứ |
|---|---|---|---|
| D-1 | Bản giả bằng `monkeypatch.setattr(capability_gate.subprocess, "run", giả)`, một test mỗi nhánh | thay đúng tên mà phép dò gọi, tự khôi phục sau test (INV-001); mỗi nhánh một test để đỏ chỉ ra đúng nhánh | [research.md Q1](research.md#q1-thay-subprocess-run-o-dau-de-chung-minh-bon-nhanh-fr-001-fr-002) |
| D-2 | Test pytest thật dùng **cây tạm có bản sao `capability_gate.py` ở `gốc/tests/unit/`**, chạy `-p capability_gate` | phép dò neo `cwd` ở `parents[2]` của tệp plugin; chỉ đổi `cwd` sẽ đo nhầm `.git` của dự án thật | ĐÃ ĐO, [research.md Q2](research.md#q2-dung-phep-chay-pytest-khong-co-git-the-nao-cho-do-dung-fr-003) |
| D-3 | Môi trường con của D-2: xoá `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`, đặt `GIT_CEILING_DIRECTORIES` là cha của cây tạm | `git` không leo lên kho cha / không bị hook của git ép vào kho khác | Edge Case "kho cha" |
| D-4 | Cấu hình test D-2: 1 test gắn dấu + 19 test thường ⇒ `1/20 = 0,05` | khớp khuôn `_run_pytest` hiện có (1 + 19); không vượt ngưỡng vì cổng so `>` | ĐÃ ĐỌC, research Q3 |
| D-5 | Dấu ở mức **hàm**, kèm `reason="Máy không có lịch sử git"` | đúng một test bị loại; thiếu `reason` là lỗi thu thập | spec Clarifications |
| D-6 | Không đổi `capability_gate.py`; test bám đúng hành vi hiện có | ràng buộc yêu cầu; sửa chỉ qua task riêng khi test chứng minh lỗi | FR-004 |
| D-7 | AC-3 kiểm bằng lần chạy cổng máy, không bằng test trong repo | `ai-sdlc verify` là lệnh của khung điều phối, chạy ngoài repo | spec Clarifications |

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/009-git-history-capability/
├── spec.md              # đặc tả (AC-1…AC-3, FR-001…FR-011, NFR-*, INV-001…003)
├── plan.md              # tệp này
├── research.md          # Phase 0 — cách chứng minh phép dò, đo cây tạm, ngân sách 5%
├── data-model.md        # Phase 1 — đối tượng tạm của test, khuôn báo cáo năng lực (chỉ đọc)
├── quickstart.md        # Phase 1 — bốn kịch bản kiểm chứng gắn mã AC/INV/NFR
├── request.link         # trỏ tới .ai/chat/request-git-history-gate.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 — KHÔNG do plan tạo (máy chạy /speckit-tasks sau)
```

<a id="source-code-repository-root-chi-phan-009-cham-toi"></a>
### Source Code (repository root) — chỉ phần 009 chạm tới

Mã nguồn nằm trên nhánh tích hợp `ai-sdlc/integration`; nhánh hiện hành chỉ có `specs/`, `docs/`.

```text
tests/
├── unit/
│   ├── capability_gate.py          # ĐÃ CÓ (F022) — KHÔNG sửa trừ khi test chứng minh lỗi (FR-004)
│   └── test_capability_gate.py     # W-1 (builder): thêm 5 test, giữ nguyên các test hiện có
└── e2e/
    └── test_008_docs_entrypoints.py  # W-2 (qa): thêm đúng 1 dòng decorator lên 1 hàm
conftest.py                          # KHÔNG sửa (đã khai pytest_plugins = ["capability_gate"])
```

Không có thư mục khung mới, không manifest mới, không FE/BE tách phía (đồ án một gói Python quản lý bằng `uv`).

<a id="lenh-build-test"></a>
## Lệnh build / test

Theo `.ai/profile.yml` (chạy trong worktree của task; `${AI_SDLC_PROJECT_ROOT}` là gốc dự án):

| Mục đích | Lệnh |
|---|---|
| Test W-1 | `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/unit/test_capability_gate.py` |
| Test W-2 trên máy có git (AC-1) | `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --capability-report=<tệp>` |
| Cổng e2e (khi đổi `tests/e2e/**`) | `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e` |
| Cổng tests | `uv run --isolated --with pytest --with pytest-xdist pytest -q -p no:cacheprovider -n auto --ignore=tests/e2e` |
| lint | `uv run --isolated --with ruff ruff check .` |
| typecheck | `uv run --isolated --with mypy mypy --strict .` |
| Toàn hệ (AC-3) | `ai-sdlc verify --branch ai-sdlc/integration` |

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Mã | Thiết kế | Test / cổng đề xuất | Mức |
|---|---|---|---|
| AC-1 | D-1 (nhánh mã 0), D-5, W-2 | `test_capability_gate.py::test_ac1_git_history_probe_true_when_git_exits_zero`; `test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` chạy ở môi trường có git | entrypoint (e2e) |
| AC-2 | D-1 (ba nhánh sai), D-2…D-4, D-5, W-2 | `test_ac2_git_history_probe_false_when_git_exits_128`, `…_on_oserror`, `…_on_timeout`, `test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git`; archive thật ở quickstart kịch bản 2 | entrypoint (pytest tiến trình con) |
| AC-3 | D-7 | cổng `ai-sdlc verify --branch ai-sdlc/integration` (5 cổng) | cổng |
| FR-001, FR-002 | D-1 | bốn test đơn vị ở trên | đơn vị |
| FR-003 | D-2…D-4 | `test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git` | entrypoint |
| FR-004 | D-6 | `git diff --name-only` (không có `capability_gate.py` khi không có lỗi) | cổng |
| FR-005, FR-006 | D-5 | `git diff -U0` tệp e2e (đúng một dòng thêm); e2e ở môi trường có git | cổng + entrypoint |
| FR-007 | — | quét `skip`/`skipif`/`xfail`/`importorskip` trong diff | cổng |
| FR-008 | D-5 | quickstart kịch bản 2 bước 3 (`--capability-report` trên archive) | entrypoint |
| FR-009 | D-7 | `ai-sdlc verify` | cổng |
| FR-010 | — | báo cáo QA/review có câu giới hạn (quickstart kịch bản 3 bước 3) | cổng |
| FR-011 | — | `git diff --name-only` thuộc vùng ghi | cổng |
| NFR-REL-001 | D-1 | `test_ac2_git_history_probe_false_on_timeout` (kiểm `timeout` ≤ 5) | đơn vị |
| NFR-GATE-001 | D-4 | test D-2 (`ratio == 0.05`); `--capability-report` trên archive | entrypoint |
| NFR-QUAL-001 | — | cổng `lint`, `typecheck` | cổng |
| INV-001 | D-1, D-6 | quét diff; `pytest --collect-only` số test không giảm | cổng |
| INV-002 | D-5 | `git diff -U0` tệp e2e | cổng |
| INV-003 | D-6 | `git diff --name-only` (không `pyproject.toml`/`uv.lock`); `grep default=0.05` ở `capability_gate.py` | cổng |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

| # | Rủi ro / việc | Mức | Xử lý |
|---|---|---|---|
| R-1 | Mẫu số `e2e` thực < 20 ⇒ 1 test bị loại vượt 5% | thấp (ước lượng ≥ 54, ĐÃ ĐỌC) | QA đếm `--collect-only` (O-1); nếu < 20, báo cáo — KHÔNG nới ngưỡng (INV-003) |
| R-2 | Bản archive của cổng nằm trong một cây làm việc git khác ⇒ phép dò trả `True`, test chạy trên lịch sử kho cha | thấp, CHƯA KIỂM (O-2) | ghi giới hạn ở báo cáo (FR-010); không che |
| R-3 | Test D-2 phụ thuộc pytest tiến trình con nạp được `capability_gate` bằng `PYTHONPATH` | thấp | ĐÃ ĐO ở cây tạm; builder chạy lại trên worktree thật |
| R-4 | W-1 lộ lỗi của `capability_gate.py` (ví dụ không bắt một ngoại lệ) | thấp | FR-004: dừng, task sửa riêng có test đỏ trước |
| R-5 | Feature khác thêm test e2e có dấu năng lực làm cạn ngân sách 5% của phiên `e2e` | trung bình về sau | ngoài phạm vi; báo cáo năng lực của cổng cho thấy ngay |
| R-6 | Hai lần giao việc trước của loại "sửa cổng" từng không để lại thay đổi | thấp | feature nhỏ, hai tệp, test bám hành vi đã đọc; QA đo bằng chứng thật trên archive (quickstart kịch bản 2) |

Việc CHƯA KIỂM của lượt đặc tả: không chạy `ai-sdlc verify`, không chạy test e2e 008 (nhánh hiện hành không có mã); chỉ có phép đo cây tạm ở research Q2 (ĐÃ ĐO).

<a id="quyet-dinh-o-buoc-tasks"></a>
## Quyết định ở bước tasks

Gợi ý cho `/speckit-tasks` (do máy chạy sau; plan không tạo `tasks.md`). Feature nhỏ: tối đa 2–3 task + task QA/review nếu quy trình đòi.

| Task gợi ý | Vai | `outputs` (vùng ghi) | Phụ thuộc | Mã phủ |
|---|---|---|---|---|
| A. Test chứng minh phép dò + pytest thật không có `.git` | builder | `tests/unit/test_capability_gate.py` | — | AC-1, AC-2, FR-001…FR-004, NFR-REL-001, NFR-GATE-001, INV-001 |
| B. Gắn dấu `requires_git_history` lên test INV-002 của 008 | qa | `tests/e2e/test_008_docs_entrypoints.py` | — (A song song được: hai tệp khác nhau; dấu đã có ở plugin) | AC-1, AC-2, FR-005…FR-008, INV-002 |
| C. Review/QA: đo trên archive, quét diff, ghi giới hạn | reviewer/qa | `evidence/reviews/**` | A, B | AC-3, FR-009…FR-011, NFR-QUAL-001, INV-001…INV-003 |

- `tdd_red`: cả hai task chỉ đổi test nên được miễn (gate `tdd_red` miễn task chỉ đổi test); test của A đều xanh trên mã hiện có vì phép dò đã đúng — đỏ chỉ xảy ra nếu R-4 xảy ra.
- Không có cờ UI/hạ tầng (`has_ui=false`, `has_infra=false`): không màn mẫu, không `ui_task_walk`.
- Task sửa `capability_gate.py` KHÔNG có sẵn trong danh sách: chỉ thêm nếu A chứng minh lỗi (FR-004).
- Không cần vai `challenger` (không có bất biến kiểu bảo mật chống đầu vào cố tình phá; test assert thẳng trên sản phẩm).

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
