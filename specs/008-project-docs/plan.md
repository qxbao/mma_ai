---
id: "PLAN-008"
title: "Bộ tài liệu dự án mma_ai — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Implementation Plan: Bộ tài liệu dự án mma_ai

- [Summary](#summary)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Kiến trúc & quyết định thiết kế](#kien-truc-quyet-dinh-thiet-ke)
  - [Quyết định thiết kế](#quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 008 chạm tới](#source-code-repository-root-chi-phan-008-cham-toi)
- [Lệnh build / test](#lenh-build-test)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks)
- [Phản biện plan_lint](#phan-bien-plan-lint)
- [Complexity Tracking](#complexity-tracking)

**Branch**: `008-project-docs` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: `specs/008-project-docs/spec.md` (bản hiện tại; không còn `[NEEDS CLARIFICATION]`; Q-0001/Q-0002 không áp dụng — xem Clarifications của spec).

<a id="summary"></a>
## Summary

Feature chỉ thêm tài liệu Markdown và một tệp giấy phép ở gốc repo; **không đổi mã, CI, `pyproject.toml`, `deliverables/`** (INV-002). Cách làm: mỗi câu trong tài liệu truy được về một nguồn thật (cờ `--help`, `pyproject.toml`, cây thư mục, spec 001–006) — nguồn đã gom ở [research.md](research.md) và [contracts/cli-commands.md](contracts/cli-commands.md) để vai `docs` chép đúng, không bịa (INV-001). Bố cục 3 task theo yêu cầu gốc:

1. Task 1 (vai `docs`): `README.md` + `LICENSE` + `CONTRIBUTING.md` (AC-1, AC-2, AC-3).
2. Task 2 (vai `docs`): `CHANGELOG.md` + `docs/guides/**` (AC-4, AC-5).
3. Task 3 (vai `reviewer`): đối chiếu từng lệnh/cờ trong tài liệu với `--help` và mã, ghi báo cáo (FR-011, NFR-DOC-001).

Không dùng QA/challenger (ràng buộc yêu cầu gốc; tài liệu không có hành vi để QA chạy E2E).

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Markdown (GitHub-flavored) + văn bản giấy phép MIT; mã dự án Python theo `requires-python = ">=3.11,<3.13"` (chỉ đọc).

**Primary Dependencies**: không thêm phụ thuộc. Công cụ chỉ để kiểm: `uv`, `python`, `pytest`, `ruff`, `mypy` (chạy qua `uv run --isolated --with …` như cổng của dự án).

**Storage**: N/A (tệp văn bản).

**Testing**: không có test tự động mới (không đổi mã, hiến chương V). Kiểm bằng: (a) `--help` của 4 lệnh; (b) quét liên kết tương đối + UTF-8 + `wc -l` (NFR-DOC-003/004) — lệnh ở [quickstart.md](quickstart.md); (c) báo cáo đối chiếu của reviewer ở Task 3.

**Target Platform**: người đọc trên Linux/WSL2 (hiện trạng mã); Windows/macOS ghi "đang làm ở spec 006".

**Project Type**: thư viện + CLI nghiên cứu (đã có); feature là tài liệu.

**Performance Goals**: NFR-DOC-002 — từ đọc README tới lệnh đầu tiên ≤ 10 phút (không kể tải phụ thuộc).

**Constraints**: vùng ghi = `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/**`; tiếng Việt, thuật ngữ song ngữ ở lần đầu mỗi tài liệu; không số liệu viết tay (hiến chương VIII); không đường dẫn tuyệt đối của máy riêng (hiến chương VI); `CONTRIBUTING.md` ≤ 100 dòng, mỗi guide ≤ 120 dòng.

**Scale/Scope**: 7 tệp mới (README, LICENSE, CONTRIBUTING, CHANGELOG, 3 guide) + 1 báo cáo đối chiếu.

<a id="constitution-check"></a>
## Constitution Check

*Cổng: qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | "Lệnh đúng" chỉ khi `--help` thật chạy và reviewer (vai khác vai viết) ghi báo cáo; lệnh chưa chạy được ghi "CHƯA KIỂM", không ghi "đạt" (NFR-DOC-001). |
| II. Test trước, sửa sau | Đạt (không áp dụng cho mã) | Không có bug/mã mới; kiểm tra tài liệu là bước đối chiếu có sẵn ở Task 3. Không thêm/giảm test nào. |
| III. Lát cắt nhỏ, một vai một task | Đạt | 3 task, mỗi tệp một chủ; Task 3 do vai reviewer, khác vai `docs`. |
| IV. Bất biến và NFR có mã | Đạt | INV-001…004 và NFR-DOC-001…004 khai ở spec, có ngưỡng số và cách đo; bảng truy vết bên dưới. |
| V. Không đổi cái không được yêu cầu | Đạt | Không đổi `pyproject.toml` (kể cả thiếu trường `license`/`readme`: ghi đề xuất ở Rủi ro, không làm), không lockfile, không CI. |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; ví dụ lệnh dùng đường dẫn tương đối hoặc `<ckpt>`; không `~/…` của một máy cụ thể. |
| VII. Nhánh bảo vệ | Đạt | Làm trên nhánh task; không push/merge vào nhánh bảo vệ. |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt, có điều kiện | README/CHANGELOG KHÔNG viết tay số test, số bước, tốc độ; tên nhóm cài đặt, cờ, mã thoát lấy từ nguồn trong `contracts/cli-commands.md`. Ngày/phiên bản `0.1.0` lấy từ `pyproject.toml`. |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | README là chỗ gốc của lệnh nhanh, nhóm cài đặt, trạng thái nền tảng; CONTRIBUTING/guides trỏ về README thay vì chép lệch (INV-004). Không đổi aggregate/INV/NFR của bounded context ⇒ không đụng `docs/02-strategic`, `docs/03-tactical`. Chi tiết dùng lệnh sâu ở `docs/guides/`, không chép sang `docs/` thêm. |

Kiểm lại sau Phase 1: không phát sinh vi phạm; Complexity Tracking trống.

<a id="kien-truc-quyet-dinh-thiet-ke"></a>
## Kiến trúc & quyết định thiết kế

Không có thành phần sản phẩm. Mỗi tệp tài liệu có một chủ và một nguồn sự thật:

| Tệp | Chủ (task) | Nguồn sự thật để chép | Mục bắt buộc (AC) |
|---|---|---|---|
| `LICENSE` | T1 | văn bản MIT chuẩn + dòng bản quyền của yêu cầu | AC-1 |
| `README.md` | T1 | `pyproject.toml`; `contracts/cli-commands.md`; cây thư mục; `specs/006` | AC-2; khung mục ở [data-model.md](data-model.md) |
| `CONTRIBUTING.md` | T1 | cổng của dự án (pytest/ruff/mypy), hiến chương, `docs/MAP.md` | AC-3 |
| `CHANGELOG.md` | T2 | `specs/001…005/spec.md`, `pyproject.toml` (`version`) | AC-4 |
| `docs/guides/training.md` | T2 | `contracts/cli-commands.md` §train | AC-5 |
| `docs/guides/evaluation.md` | T2 | `contracts/cli-commands.md` §evaluate | AC-5 |
| `docs/guides/replay-demo.md` | T2 | `contracts/cli-commands.md` §replay | AC-5 |
| báo cáo đối chiếu | T3 | `--help` thật của từng lệnh | FR-011 |

<a id="quyet-dinh-thiet-ke"></a>
### Quyết định thiết kế

- **D1 — Đặt tên guide bằng tiếng Anh, không dấu**: `training.md`, `evaluation.md`, `replay-demo.md` — phù hợp tên tệp ở `docs/` (không dấu, kebab-case), liên kết tương đối không phải mã hoá. Tiêu đề bên trong bằng tiếng Việt.
- **D2 — Frontmatter cho `docs/guides/*.md`**: các tệp dưới `docs/` được cổng `docs_gate` đọc nên có frontmatter `id`, `title`, `doc_type: guide`, `owner_agent: docs`, `status: draft`, `updated` (khuôn như `docs/MAP.md`). Tệp gốc repo (`README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`) KHÔNG có frontmatter (GitHub hiển thị và công cụ giấy phép nhận diện đúng khi không có).
- **D3 — Lệnh dùng `python …` kèm một dòng chạy trong môi trường uv**: README nêu "chạy trong môi trường đã `uv sync` (kích hoạt `.venv` hoặc đặt tiền tố `uv run`)" một lần; các lệnh vẫn viết `python …` đúng bốn lệnh của yêu cầu (FR-004).
- **D4 — Lint/mypy theo cổng của dự án**: CONTRIBUTING dùng `uv run --isolated --with ruff ruff check .` và `uv run --isolated --with mypy mypy --strict .` (cổng trong cấu hình dự án), vì nhóm `dev` không chứa hai công cụ này (khảo sát). Không đề xuất sửa `pyproject.toml` trong feature này.
- **D5 — Nền tảng**: một đoạn gốc ở README mục Tình trạng nền tảng; nơi khác chỉ trỏ (INV-003, INV-004). Căn cứ: `src/mma_ai/learning/resources.py` nhập `resource` theo POSIX (khảo sát), spec 006 đang làm. Hiện trạng thật của spec 006 được đọc lại lúc viết để câu chữ không lệch.
- **D6 — Nguồn CHANGELOG 0.1.0 chỉ là cái có trong mã**: spec 001 nhắc nhiều `scripts/*.py` của M0, nhưng thư mục `scripts/` hiện chỉ có `train.py`; CHANGELOG ghi M0 theo mô-đun `src/mma_ai/physics` (mô phỏng, kiểm sức khoẻ số học), không nêu script không còn tồn tại (research.md Q3).
- **D7 — Huy hiệu tĩnh**: hai badge (Python 3.11–3.12, MIT) dạng ảnh tĩnh trỏ về `LICENSE`; không badge CI/coverage (không có CI trong phạm vi).
- **D8 — Đối chiếu độc lập**: Task 3 do vai `reviewer` chạy `--help` từng lệnh (và cờ nêu trong guide), điền bảng đối chiếu theo khuôn ở quickstart; không sửa tệp tài liệu — phát hiện lệch thì trả lại cho vai `docs` (hiến chương I: người viết không tự chấm).

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/008-project-docs/
├── plan.md                      # tệp này
├── research.md                  # Phase 0
├── data-model.md                # Phase 1 — khung mục tài liệu (không phải thực thể dữ liệu)
├── quickstart.md                # Phase 1 — kịch bản kiểm
├── contracts/
│   └── cli-commands.md          # Phase 1 — hợp đồng lệnh ↔ cờ ↔ nguồn ↔ mã thoát
├── checklists/requirements.md   # chất lượng spec
└── tasks.md                     # Phase 2 (/speckit-tasks — KHÔNG tạo ở lượt này)
```

<a id="source-code-repository-root-chi-phan-008-cham-toi"></a>
### Source Code (repository root) — chỉ phần 008 chạm tới

```text
README.md                       # mới (T1)
LICENSE                         # mới (T1)
CONTRIBUTING.md                 # mới (T1)
CHANGELOG.md                    # mới (T2)
docs/guides/
├── training.md                 # mới (T2)
├── evaluation.md               # mới (T2)
└── replay-demo.md              # mới (T2)
.ai/runs/<pha>/reports/reviewer-docs-check.md   # báo cáo đối chiếu (T3)
```

Không tệp nào trong `src/`, `scripts/`, `tests/`, `pyproject.toml`, CI, `deliverables/` bị đổi.

**Structure Decision**: tài liệu phẳng ở gốc cho bốn tệp chuẩn cộng đồng; ba hướng dẫn gom ở `docs/guides/` (một thư mục, không lồng thêm). Không `docs/MAP.md` sửa tay: MAP do máy sinh, sẽ tự thêm dòng phân hệ 008 khi có `tasks.md`.

<a id="lenh-build-test"></a>
## Lệnh build / test

Không có bước build. Lệnh kiểm theo từng phía:

| Việc | Lệnh | Ngưỡng |
|---|---|---|
| Trợ giúp bốn lệnh | `uv run --isolated python scripts/train.py --help` · `uv run --isolated python -m mma_ai.evaluation.cli --help` · `uv run --isolated python -m mma_ai.visualization.cli --help` · `uv run --isolated python -m mma_ai.learning.benchmark --help` | thoát 0, có đủ cờ tài liệu dùng (NFR-DOC-001) |
| Độ dài | `wc -l CONTRIBUTING.md docs/guides/*.md` | ≤ 100 / ≤ 120 dòng (NFR-DOC-003) |
| Liên kết + UTF-8 | xem [quickstart.md](quickstart.md) kịch bản 4 | 0 gãy, 100% UTF-8 (NFR-DOC-004) |
| Cổng chung | cổng `tests`, `lint`, `typecheck` của dự án | xanh không đổi (không đổi mã) |
| Cổng tài liệu | `ai-sdlc check docs .` | sạch |

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thiết kế / nơi thực hiện | Kiểm |
|---|---|---|
| AC-1 · FR-001 | `LICENSE` (T1) | quickstart KB-1 |
| AC-2 · FR-002…FR-007, FR-012 | `README.md` (T1), khung ở data-model.md | quickstart KB-2, KB-3 |
| AC-3 · FR-008 | `CONTRIBUTING.md` (T1), D4 | quickstart KB-5 |
| AC-4 · FR-009 | `CHANGELOG.md` (T2), D6 | quickstart KB-6 |
| AC-5 · FR-010 | `docs/guides/*.md` (T2), contracts/cli-commands.md | quickstart KB-3, KB-7 |
| FR-011 · NFR-DOC-001 · INV-001 | T3 reviewer, D8 | quickstart KB-3 |
| NFR-DOC-002 | README mục Cài đặt + Bắt đầu nhanh | quickstart KB-2 |
| NFR-DOC-003 | giới hạn dòng | quickstart KB-4 |
| NFR-DOC-004 · FR-012 | liên kết tương đối, UTF-8 | quickstart KB-4 |
| INV-002 · SC-008 | vùng ghi tasks.md | quickstart KB-8 |
| INV-003 | D5 | quickstart KB-2 |
| INV-004 | D3, D5, mục Kiến trúc | quickstart KB-3 |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

- **Lệnh không chạy được tại máy đo** (thiếu `torch`/`pandas`/`matplotlib`, không có màn hình): `--help` cần nhập mô-đun nên có thể lỗi khi thiếu nhóm `rl`/`eval`; reviewer ghi "CHƯA KIỂM" kèm lỗi thật, không ghi "đạt". Ở máy phát triển hiện tại `.venv` chưa đủ phụ thuộc (đã thử lúc lập plan: thiếu `yaml`, `gymnasium`) nên phép đo cần `uv run --isolated`/`uv sync` (CHƯA KIỂM ở lượt plan này; chỉ benchmark `--help` đã chạy được và in đủ cờ `--seed`, `--repeats`).
- **Đề xuất ngoài phạm vi (không làm)**: `pyproject.toml` chưa khai `license`, `readme`, `authors`, và nhóm `dev` chưa có `ruff`/`mypy`; đề xuất tách thành yêu cầu riêng (hiến chương V).
- **Lệch với spec 006 khi nó hoàn thành**: câu "Windows/macOS đang làm" sẽ lỗi thời; ghi ở một chỗ (README) để sửa một lần (INV-004).
- **Cổng `ai-sdlc check docs .` có thể đòi frontmatter/TOC** cho `docs/guides/*`: dùng khuôn `docs/MAP.md`; TOC (nếu cần) sinh/đối chiếu bằng cổng, không viết tay số (hiến chương VIII).

<a id="quyet-dinh-o-buoc-tasks"></a>
## Quyết định ở bước tasks

Bước tasks (máy chạy sau) khai: T1 outputs `README.md LICENSE CONTRIBUTING.md`; T2 outputs `CHANGELOG.md docs/guides/**`, `depends_on` T1 (guide/CHANGELOG trỏ về README); T3 vai `reviewer`, `depends_on` T1, T2, outputs là báo cáo đối chiếu dưới `.ai/runs/`. Không task QA/challenger. Mỗi task ≤ 600 LoC (tổng 7 tệp ngắn). Không có task khung (không có manifest hay build).

**Quyết định về vai `challenger`**: KHÔNG DÙNG. Bốn bất biến `INV-001…004` là bất biến về nội dung và vùng ghi của tài liệu (lệnh khớp `--help`, không đổi mã, không hứa nền tảng chưa hỗ trợ, một chỗ gốc cho mỗi sự thật), không có đầu vào người dùng để dựng vector/fuzz đánh sập; chúng được kiểm tất định bằng đối chiếu `--help` của reviewer (Task 3) và so `git diff --name-only` với vùng ghi. Dùng challenger chỉ thêm một lượt, đổi cổng review thành nhất trí hai vai, và yêu cầu gốc cấm QA/challenger.

<a id="phan-bien-plan-lint"></a>
## Phản biện plan_lint

- **Phản biện**: "Tài liệu nhập môn bằng tay thì số liệu (tốc độ, số test) sẽ lệch." → gốc: plan cấm số viết tay (hiến chương VIII); README chỉ nêu tính năng bằng văn xuôi và tên nhóm/cờ lấy từ mã. lý do: số lệch ngay lần sửa kế tiếp.
- **Phản biện**: "Thiếu task QA cho tài liệu?" → gốc: yêu cầu gốc cấm QA/challenger; kiểm do reviewer đối chiếu lệnh (FR-011) đã đủ cho tài liệu không có hành vi. lý do: không có luồng người dùng để chạy E2E.
- **Phản biện**: "README đứng độc lập hay guide chép lại lệnh?" → gốc: một chỗ gốc (README) cho bốn lệnh nhanh; guide chỉ đi sâu cờ và lỗi, nêu lệnh đúng cú pháp rồi trỏ README. lý do: INV-004.

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
