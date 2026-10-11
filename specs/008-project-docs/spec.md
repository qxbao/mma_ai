---
id: "SPEC-008"
title: "Bộ tài liệu dự án mma_ai (README · giấy phép · đóng góp · nhật ký thay đổi · hướng dẫn dùng) — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Feature Specification: Bộ tài liệu dự án mma_ai

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Người mới hiểu dự án và chạy được trong vài phút qua README (Priority: P1)](#user-story-1-nguoi-moi-hieu-du-an-va-chay-duoc-trong-vai-phut-qua-readme-priority-p1)
  - [User Story 2 - Giấy phép MIT rõ ràng ở gốc repo (Priority: P1)](#user-story-2-giay-phep-mit-ro-rang-o-goc-repo-priority-p1)
  - [User Story 3 - Mọi lệnh trong tài liệu khớp trợ giúp và mã thật (Priority: P1)](#user-story-3-moi-lenh-trong-tai-lieu-khop-tro-giup-va-ma-that-priority-p1)
  - [User Story 4 - Người đóng góp biết cách kiểm thử và quy ước (Priority: P2)](#user-story-4-nguoi-dong-gop-biet-cach-kiem-thu-va-quy-uoc-priority-p2)
  - [User Story 5 - Nhật ký thay đổi tóm tắt bản 0.1.0 (Priority: P2)](#user-story-5-nhat-ky-thay-doi-tom-tat-ban-010-priority-p2)
  - [User Story 6 - Ba hướng dẫn ngắn: huấn luyện, đánh giá, phát lại/demo (Priority: P2)](#user-story-6-ba-huong-dan-ngan-huan-luyen-danh-gia-phat-laidemo-priority-p2)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)

**Feature Branch**: `008-project-docs` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Bộ tài liệu dự án cho mma_ai (README, giấy phép, đóng góp, nhật ký thay đổi, hướng dẫn dùng)" — nguồn: `.ai/chat/request-docs.md` (đã kết luận không tách: `docs/00-input/split/request-docs/children.md`); khảo sát: `docs/00-survey/mma-ai-project-docs.md`.

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án đã có mã M0–M1: môi trường khuỷu tay cơ bắp MuJoCo, huấn luyện PPO, đánh giá so với chính sách ngẫu nhiên (random), phát lại/demo 3D. Nhưng gốc repo chưa có `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md` `[đo: git ls-files README.md LICENSE CONTRIBUTING.md CHANGELOG.md 'docs/guides/**' → 0 dòng, theo docs/00-survey/mma-ai-project-docs.md]`. Người lần đầu tới repo không biết dự án làm gì, cài thế nào, chạy lệnh nào.

Người dùng của feature là **nhà nghiên cứu / kỹ sư lần đầu tới repo**, cần hiểu dự án làm gì, cài và chạy được trong vài phút. Feature **chỉ thêm tài liệu Markdown và tệp giấy phép**; không đổi hành vi sản phẩm. Mọi lệnh trong tài liệu phải kiểm được bằng cờ trợ giúp (`--help`) hoặc đọc mã, không bịa tính năng (hiến chương I, V).

Mã tiêu chí chấp nhận: yêu cầu gốc nêu năm kết quả mong muốn (a)–(e) nhưng không đánh mã; spec đặt **AC-1 = (a) LICENSE · AC-2 = (b) README · AC-3 = (c) CONTRIBUTING · AC-4 = (d) CHANGELOG · AC-5 = (e) hướng dẫn trong `docs/guides/`**.

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Mã tiêu chí → AC-1…AC-5 theo thứ tự (a)…(e) của yêu cầu gốc — lý do: yêu cầu không đánh mã; ánh xạ một–một, không gộp, không bỏ kết quả nào.
- Tự chốt: Số hiệu feature → `008` — lý do: `specs/001`…`007` đã có; đánh số tuần tự kế tiếp.
- Tự chốt: Q-0001 và Q-0002 trong khối "Câu trả lời của người dùng" của lượt này → không áp dụng cho feature này: Q-0001 đã được ghi ở `specs/003-ppo-train-repro/spec.md`; Q-0002 thuộc `specs/006-cross-platform-support/spec.md` — lý do: không sao chép câu trả lời của người sang spec không bị chúng ảnh hưởng. Riêng ý "Windows native là môi trường chính, macOS phải chạy tốt" của Q-0002 là mục tiêu của spec 006, chưa hoàn thành; README ghi đúng hiện trạng (xem FR-008, INV-003).
- Tự chốt: Bản quyền LICENSE → `Copyright (c) 2026 Dương Quan Bao` — lý do: chính yêu cầu ghi "người dùng đã xác nhận tên và năm".
- Tự chốt: Cách viết lệnh Bắt đầu nhanh → giữ đúng 4 lệnh yêu cầu đưa, dạng `python …`, kèm một dòng nói chạy trong môi trường đã `uv sync` (kích hoạt venv hoặc đặt tiền tố `uv run`) — lý do: yêu cầu đòi đúng 4 lệnh; tiền tố môi trường là cách chạy được chứ không thêm lệnh thứ năm.
- Tự chốt: Lệnh lint/mypy trong CONTRIBUTING → theo cổng của dự án (`uv run --isolated --with ruff ruff check .`, `uv run --isolated --with mypy mypy --strict .`), không giả định `ruff`/`mypy` nằm trong nhóm `dev` — lý do: `pyproject.toml` nhóm `dev` chỉ có `pytest` và `jsonschema`; khảo sát đã ghi cạm bẫy này.
- Tự chốt: CHANGELOG 0.1.0 → ngày phát hành là ngày tài liệu được ghi, tóm tắt theo spec 001–005 (M0–M1); mục "Chưa phát hành" (Unreleased) trống hoặc chỉ ghi các việc đang làm đã có spec (006) — lý do: Keep a Changelog; `pyproject.toml` khai `version = "0.1.0"`.
- Kết luận phân loại: rà các điểm còn lại, không điểm nào cần người trả lời (mục "Chưa rõ" của yêu cầu: không); không thêm Key Entity, không thêm endpoint hay màn hình, không thêm hành vi sản phẩm — mọi mục đều nằm trong năm kết quả (a)–(e) nên không có quyết định mở rộng phạm vi.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-nguoi-moi-hieu-du-an-va-chay-duoc-trong-vai-phut-qua-readme-priority-p1"></a>
### User Story 1 - Người mới hiểu dự án và chạy được trong vài phút qua README (Priority: P1)

**Tần suất**: hiếm — mỗi người mới một lần khi tới repo (nhà nghiên cứu/kỹ sư), cộng vai reviewer đối chiếu một lần mỗi lượt sửa README.

Người lần đầu mở repo đọc `README.md` bằng tiếng Việt, thuật ngữ song ngữ ở lần xuất hiện đầu (ví dụ "chính sách ngẫu nhiên (random policy)"), chuẩn format và thân thiện. Họ hiểu dự án làm gì, cài bằng `uv`, chạy bốn lệnh thật và biết nền tảng nào hiện được nhắm tới.

**Why this priority**: README là cửa vào duy nhất; thiếu nó thì mọi tài liệu khác không được tìm thấy.

**Independent Test**: Người chưa biết dự án đọc README, làm theo mục Cài đặt và Bắt đầu nhanh; kiểm mỗi mục bắt buộc của AC-2 có mặt, mỗi lệnh có trợ giúp đúng.

**Acceptance Scenarios**:

1. **Given** gốc repo, **When** mở `README.md`, **Then** thấy tiêu đề và phần mô tả 2–3 dòng nêu dự án làm gì, rồi huy hiệu (badge) cho Python 3.11–3.12 và giấy phép MIT. (AC-2)
2. **Given** `README.md`, **When** đọc theo thứ tự, **Then** có đủ các mục: Tính năng; Yêu cầu hệ thống; Cài đặt bằng uv; Bắt đầu nhanh; Cấu trúc thư mục; cách chạy kiểm thử; Tình trạng nền tảng; Tài liệu; Đóng góp; Giấy phép. (AC-2)
3. **Given** mục Cài đặt, **When** đối chiếu với `pyproject.toml`, **Then** nêu `uv sync` và ba nhóm tuỳ chọn `rl`, `eval`, `dev` đúng như khai trong `pyproject.toml`, không nhóm nào khác. (AC-2)
4. **Given** mục Bắt đầu nhanh, **When** đếm lệnh, **Then** có đúng 4 lệnh thật: huấn luyện `python scripts/train.py --stage elbow --seed 42`; đánh giá `python -m mma_ai.evaluation.cli --checkpoint <ckpt>`; phát lại/demo 3D `python -m mma_ai.visualization.cli --episode <tệp>` hoặc `--checkpoint <ckpt>`; đo hiệu năng `python -m mma_ai.learning.benchmark --seed 42 --repeats 5`. (AC-2)
5. **Given** mục Cấu trúc thư mục, **When** đối chiếu với cây thư mục thật, **Then** liệt kê `src/mma_ai/{physics,environment,learning,monitoring,evaluation,visualization}`, `specs/`, `docs/`, `tests/`, mỗi mục tồn tại thật. (AC-2)
6. **Given** mục Tình trạng nền tảng, **When** đọc, **Then** nói thẳng hiện nhắm Linux/WSL2; Windows/macOS đang làm ở spec 006 — không hứa Windows/macOS chạy được. (AC-2)
7. **Given** mục Tài liệu, **When** đọc, **Then** trỏ tới `docs/MAP.md` và `specs/`, và tới ba hướng dẫn trong `docs/guides/`; mục Giấy phép trỏ tới `LICENSE`. (AC-2, AC-5)

---

<a id="user-story-2-giay-phep-mit-ro-rang-o-goc-repo-priority-p1"></a>
### User Story 2 - Giấy phép MIT rõ ràng ở gốc repo (Priority: P1)

**Tần suất**: hiếm — người dùng/tổ chức xét điều khoản sử dụng một lần khi cân nhắc dùng lại mã.

`LICENSE` ở gốc repo là giấy phép MIT chuẩn, bản quyền đúng tên và năm đã xác nhận.

**Why this priority**: không có giấy phép thì mặc định không ai được phép dùng lại mã; việc nhỏ nhưng chặn người dùng ngoài.

**Independent Test**: So `LICENSE` với văn bản MIT chuẩn; kiểm dòng bản quyền.

**Acceptance Scenarios**:

1. **Given** gốc repo, **When** mở `LICENSE`, **Then** nội dung là văn bản giấy phép MIT chuẩn với dòng bản quyền đúng `Copyright (c) 2026 Dương Quan Bao`. (AC-1)
2. **Given** `LICENSE` và huy hiệu/mục Giấy phép của README, **When** đối chiếu, **Then** cùng nêu giấy phép MIT, không mâu thuẫn. (AC-1, AC-2)

---

<a id="user-story-3-moi-lenh-trong-tai-lieu-khop-tro-giup-va-ma-that-priority-p1"></a>
### User Story 3 - Mọi lệnh trong tài liệu khớp trợ giúp và mã thật (Priority: P1)

**Tần suất**: hiếm — vai reviewer một lần cho mỗi bộ tài liệu, và một lần mỗi khi lệnh CLI đổi.

Reviewer đối chiếu từng lệnh và từng cờ xuất hiện trong `README.md`, `CONTRIBUTING.md`, `docs/guides/*` với trợ giúp (`--help`) thật của lệnh đó và với mã.

**Why this priority**: tài liệu sai lệnh còn tệ hơn không có tài liệu; yêu cầu cấm bịa tính năng.

**Independent Test**: Trích mọi lệnh/cờ từ các tệp tài liệu, chạy `--help` của từng lệnh, so tên cờ; báo cáo đối chiếu liệt kê từng lệnh với kết quả khớp/lệch.

**Acceptance Scenarios**:

1. **Given** bốn lệnh Bắt đầu nhanh, **When** chạy `--help` của từng lệnh, **Then** mỗi lệnh thoát mã 0 và liệt kê mọi cờ mà tài liệu dùng (`--stage`, `--seed`; `--checkpoint`; `--episode`, `--checkpoint`; `--seed`, `--repeats`). (AC-2)
2. **Given** mọi cờ khác được nêu trong ba hướng dẫn, **When** đối chiếu, **Then** mỗi cờ có trong `--help` của lệnh tương ứng; cờ không có thì tài liệu bị sửa, không sửa mã. (AC-5)
3. **Given** báo cáo đối chiếu, **When** đọc, **Then** nêu từng lệnh, lệnh trợ giúp đã chạy, kết quả và môi trường đo; lệnh chưa chạy được ghi "CHƯA KIỂM", không ghi "đạt". (AC-2, AC-5)

---

<a id="user-story-4-nguoi-dong-gop-biet-cach-kiem-thu-va-quy-uoc-priority-p2"></a>
### User Story 4 - Người đóng góp biết cách kiểm thử và quy ước (Priority: P2)

**Tần suất**: hiếm — mỗi người đóng góp mới một lần trước khi gửi thay đổi đầu tiên.

`CONTRIBUTING.md` ngắn gọn nêu cách chạy test, lint, mypy, quy ước tiếng Việt và luồng ai-sdlc.

**Why this priority**: giảm thay đổi sai quy ước; ít cấp thiết hơn README vì lượng người đóng góp nhỏ hơn người dùng.

**Independent Test**: Làm theo `CONTRIBUTING.md` chạy test/lint/mypy; kiểm ba nhóm nội dung có mặt và lệnh đúng cổng của dự án.

**Acceptance Scenarios**:

1. **Given** `CONTRIBUTING.md`, **When** đọc, **Then** có cách chạy test, lint và mypy với lệnh khớp cổng của dự án (pytest · ruff · mypy), ngắn gọn (không dài hơn README). (AC-3)
2. **Given** `CONTRIBUTING.md`, **When** đọc, **Then** nêu quy ước tiếng Việt: tài liệu, thông báo người dùng và chú thích bằng tiếng Việt, thuật ngữ song ngữ ở lần xuất hiện đầu. (AC-3)
3. **Given** `CONTRIBUTING.md`, **When** đọc, **Then** nêu luồng ai-sdlc: đặc tả → kế hoạch → task → triển khai, vùng ghi mỗi task theo `specs/*/tasks.md`, bản đồ `docs/MAP.md`. (AC-3)

---

<a id="user-story-5-nhat-ky-thay-doi-tom-tat-ban-010-priority-p2"></a>
### User Story 5 - Nhật ký thay đổi tóm tắt bản 0.1.0 (Priority: P2)

**Tần suất**: hiếm — mỗi lần phát hành bản mới, người duy trì cập nhật một lần.

`CHANGELOG.md` theo Keep a Changelog, có bản 0.1.0 tóm tắt M0–M1.

**Why this priority**: người dùng cần biết bản hiện tại gồm gì; ít cấp thiết hơn README và giấy phép.

**Independent Test**: Kiểm cấu trúc Keep a Changelog; mỗi ý trong 0.1.0 truy được về một spec hoặc mã.

**Acceptance Scenarios**:

1. **Given** `CHANGELOG.md`, **When** đọc, **Then** có tiêu đề và đoạn dẫn theo Keep a Changelog, mục `[Unreleased]` và mục bản `[0.1.0]` kèm ngày; các nhóm thay đổi dùng tên chuẩn (Added, Changed, Fixed…). (AC-4)
2. **Given** mục `[0.1.0]`, **When** đối chiếu với `specs/001`…`specs/005` và `pyproject.toml` (`version = "0.1.0"`), **Then** tóm tắt M0–M1: mô phỏng vật lý và benchmark M0; môi trường khuỷu tay cơ bắp; huấn luyện PPO; đánh giá so với random; phát lại/demo 3D — mỗi ý có trong mã hoặc spec. (AC-4)

---

<a id="user-story-6-ba-huong-dan-ngan-huan-luyen-danh-gia-phat-laidemo-priority-p2"></a>
### User Story 6 - Ba hướng dẫn ngắn: huấn luyện, đánh giá, phát lại/demo (Priority: P2)

**Tần suất**: hiếm — mỗi người mới một lần cho mỗi bước (huấn luyện → đánh giá → phát lại).

`docs/guides/` gồm 3 hướng dẫn ngắn đi sâu hơn README cho ba việc chính.

**Why this priority**: README chỉ cho lệnh nhanh; người dùng cần biết cờ chính, đầu vào/đầu ra và lỗi thường gặp.

**Independent Test**: Làm theo từng hướng dẫn theo thứ tự (huấn luyện → đánh giá → phát lại) và kiểm lệnh, cờ, đường dẫn đầu ra khớp mã.

**Acceptance Scenarios**:

1. **Given** thư mục `docs/guides/`, **When** liệt kê, **Then** có đúng 3 hướng dẫn: huấn luyện, đánh giá, phát lại/demo; mỗi hướng dẫn ngắn (đọc xong trong vài phút) và có liên kết ngược về README. (AC-5)
2. **Given** hướng dẫn huấn luyện, **When** đọc, **Then** nêu lệnh `python scripts/train.py --stage elbow --seed 42`, các cờ chính có trong `--help` (như `--config`, `--total-steps`, `--resume`, `--runs-dir`, `--ui`, `--view3d`), nơi tìm điểm kiểm tra (checkpoint). (AC-5)
3. **Given** hướng dẫn đánh giá, **When** đọc, **Then** nêu `python -m mma_ai.evaluation.cli --checkpoint <ckpt>`, đầu vào `.pt` hoặc `latest.json`, và checkpoint nằm ngoài thư mục run cần `--out`. (AC-5)
4. **Given** hướng dẫn phát lại/demo, **When** đọc, **Then** nêu hai chế độ `--episode <tệp>` và `--checkpoint <ckpt>` (chọn đúng một), cờ `--headless`, và khi không có màn hình dùng được thì lệnh thoát mã 7 kèm gợi ý `--headless`. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Người đọc dùng Windows/macOS: README không hứa chạy được; chỉ nêu Windows/macOS đang làm ở spec 006 và gợi ý WSL2. (INV-003)
- Máy không có màn hình dùng được: hướng dẫn phát lại nêu mã thoát 7 và `--headless` thay vì để người đọc tưởng lệnh hỏng. (AC-5)
- Lệnh đánh giá nhận checkpoint ngoài thư mục run: hướng dẫn nêu cần `--out`, nếu không lệnh báo lỗi. (AC-5)
- Lệnh đo hiệu năng yêu cầu `--repeats` tối thiểu 5: tài liệu dùng đúng `--repeats 5`, không ghi giá trị nhỏ hơn. (AC-2)
- `ruff` và `mypy` không nằm trong nhóm `dev` của `pyproject.toml`: CONTRIBUTING dùng lệnh chạy qua `uv run --with`, không bảo người đọc `uv sync --extra dev` rồi gọi thẳng hai công cụ này. (AC-3)
- Một lệnh trong tài liệu không chạy được trên máy đo (thiếu màn hình, thiếu nhóm `rl`/`eval`): báo cáo đối chiếu ghi "CHƯA KIỂM" kèm lý do, không ghi "đạt". (INV-001)
- Cờ nêu trong tài liệu không có trong `--help`: sửa tài liệu cho khớp mã; tuyệt đối không sửa mã để khớp tài liệu. (INV-001, INV-002)
- Tên tác giả "Dương Quan Bao" có dấu tiếng Việt: `LICENSE` và mọi tệp Markdown lưu UTF-8, không lỗi mã hoá. (AC-1)
- README và các tệp khác nói cùng một sự thật (lệnh, nhóm cài đặt, trạng thái nền tảng) một chỗ gốc: nơi khác trỏ tới thay vì chép lệch (hiến chương IX). (INV-004)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: `LICENSE` MUST là giấy phép MIT chuẩn ở gốc repo với dòng bản quyền đúng `Copyright (c) 2026 Dương Quan Bao`. (AC-1)
- **FR-002**: `README.md` ở gốc repo MUST bằng tiếng Việt, thuật ngữ song ngữ ở lần xuất hiện đầu, chuẩn format và thân thiện, có tiêu đề + mô tả 2–3 dòng, huy hiệu (Python 3.11–3.12, giấy phép MIT) và đủ các mục: Tính năng; Yêu cầu hệ thống; Cài đặt bằng uv; Bắt đầu nhanh; Cấu trúc thư mục; cách chạy kiểm thử; Tình trạng nền tảng; Tài liệu; Đóng góp; Giấy phép. (AC-2)
- **FR-003**: Mục Cài đặt của README MUST nêu `uv sync` và các nhóm tuỳ chọn `rl`, `eval`, `dev` đúng như `pyproject.toml`. (AC-2)
- **FR-004**: Mục Bắt đầu nhanh của README MUST có đúng 4 lệnh thật: huấn luyện `python scripts/train.py --stage elbow --seed 42`; đánh giá `python -m mma_ai.evaluation.cli --checkpoint <ckpt>`; phát lại/demo 3D `python -m mma_ai.visualization.cli --episode <tệp>` hoặc `--checkpoint <ckpt>`; đo hiệu năng `python -m mma_ai.learning.benchmark --seed 42 --repeats 5`. (AC-2)
- **FR-005**: Mục Cấu trúc thư mục MUST liệt kê `src/mma_ai/{physics,environment,learning,monitoring,evaluation,visualization}`, `specs/`, `docs/`, `tests/` và mục cách chạy kiểm thử MUST nêu lệnh chạy bộ test của dự án. (AC-2)
- **FR-006**: Mục Tình trạng nền tảng MUST nói thẳng hiện nhắm Linux/WSL2, Windows/macOS đang làm ở spec 006, không hứa quá. (AC-2)
- **FR-007**: Mục Tài liệu MUST trỏ tới `docs/MAP.md`, `specs/` và 3 hướng dẫn trong `docs/guides/`; mục Đóng góp trỏ tới `CONTRIBUTING.md`; mục Giấy phép trỏ tới `LICENSE`. (AC-2, AC-5)
- **FR-008**: `CONTRIBUTING.md` MUST ngắn gọn và nêu: cách chạy test, lint, mypy; quy ước tiếng Việt; luồng ai-sdlc. (AC-3)
- **FR-009**: `CHANGELOG.md` MUST theo Keep a Changelog, có mục `[Unreleased]` và bản `[0.1.0]` tóm tắt M0–M1, khớp `version` trong `pyproject.toml`. (AC-4)
- **FR-010**: `docs/guides/` MUST gồm đúng 3 hướng dẫn ngắn: huấn luyện, đánh giá, phát lại/demo; mỗi hướng dẫn nêu lệnh, cờ chính, đầu vào/đầu ra và lỗi/mã thoát thường gặp, khớp `--help` và mã. (AC-5)
- **FR-011**: Mọi lệnh và cờ xuất hiện trong tài liệu MUST chạy được hoặc có trợ giúp (`--help`) đúng; MUST có một lượt đối chiếu độc lập (vai reviewer) so từng lệnh với trợ giúp thật và ghi báo cáo. Không bịa tính năng: mỗi lệnh kiểm được bằng cờ trợ giúp hoặc mã. (AC-2, AC-5)
- **FR-012**: Mọi tệp Markdown mới MUST lưu UTF-8 và có liên kết tương đối hợp lệ (không liên kết gãy). (AC-2, AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-DOC-001**: Độ chính xác của lệnh trong tài liệu.
  Ngưỡng: 100% lệnh trong README, CONTRIBUTING và `docs/guides/*` có `--help` hoặc mã khớp; 0 cờ không tồn tại; lệnh chưa chạy được ghi "CHƯA KIỂM".
  Đo bằng: báo cáo đối chiếu của vai reviewer, chạy `--help` của từng lệnh (`uv run --isolated python <lệnh> --help` thoát 0). (AC-2, AC-5)
- **NFR-DOC-002**: Thời gian từ đọc README tới chạy lệnh đầu tiên.
  Ngưỡng: ≤ 10 phút (không kể thời gian tải phụ thuộc) cho người làm theo mục Cài đặt và Bắt đầu nhanh.
  Đo bằng: kiểm tay một lượt của reviewer trên môi trường sạch; ghi thời gian vào báo cáo đối chiếu. (AC-2)
- **NFR-DOC-003**: Độ ngắn gọn của tài liệu nhập môn.
  Ngưỡng: mỗi hướng dẫn trong `docs/guides/` ≤ 120 dòng; `CONTRIBUTING.md` ≤ 100 dòng.
  Đo bằng: `wc -l` trên các tệp. (AC-3, AC-5)
- **NFR-DOC-004**: Liên kết và mã hoá.
  Ngưỡng: 0 liên kết tương đối gãy; 100% tệp mới là UTF-8 hợp lệ.
  Đo bằng: quét liên kết tương đối trong các tệp mới và `file --mime-encoding` / giải mã UTF-8. (AC-2, AC-5)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Mọi lệnh/cờ trong tài liệu MUST khớp `--help` hoặc mã thật; khi lệch thì sửa tài liệu, không bịa tính năng. (AC-2, AC-5)
- **INV-002**: Feature MUST NOT đổi mã nguồn (`src/`, `scripts/`, `tests/`, `pyproject.toml`), CI hay tài liệu khách hàng `deliverables/`; vùng ghi chỉ gồm `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/**` (và tệp spec/bằng chứng của chính feature). (AC-1, AC-2, AC-3, AC-4, AC-5)
- **INV-003**: Tài liệu MUST NOT hứa hỗ trợ Windows native hay macOS khi spec 006 chưa hoàn thành; tình trạng nền tảng phản ánh đúng hiện trạng mã. (AC-2)
- **INV-004**: Mỗi sự thật (lệnh, nhóm cài đặt, trạng thái nền tảng) có một chỗ gốc; nơi khác trỏ tới thay vì chép lệch. (AC-2, AC-3, AC-5)

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: `LICENSE` tồn tại ở gốc repo, là MIT chuẩn với dòng `Copyright (c) 2026 Dương Quan Bao`. (AC-1)
- **SC-002**: `README.md` có đủ 10 mục bắt buộc của FR-002, đúng 4 lệnh Bắt đầu nhanh và đúng ba nhóm `rl`, `eval`, `dev`. (AC-2)
- **SC-003**: Người lần đầu tới repo cài và chạy lệnh đầu tiên trong ≤ 10 phút (NFR-DOC-002) chỉ nhờ README. (AC-2)
- **SC-004**: `CONTRIBUTING.md` có đủ ba nội dung (test/lint/mypy, quy ước tiếng Việt, luồng ai-sdlc) và ≤ 100 dòng. (AC-3)
- **SC-005**: `CHANGELOG.md` theo Keep a Changelog, bản 0.1.0 tóm tắt M0–M1, mỗi ý truy được về spec hoặc mã. (AC-4)
- **SC-006**: `docs/guides/` có đúng 3 hướng dẫn, mỗi hướng dẫn ≤ 120 dòng. (AC-5)
- **SC-007**: 100% lệnh trong tài liệu được đối chiếu với trợ giúp thật; 0 lệnh sai; số lệnh "CHƯA KIỂM" được liệt kê rõ. (AC-2, AC-5)
- **SC-008**: `git diff --name-only` của feature chỉ chứa `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/guides/**` và tệp của chính feature (spec, bằng chứng); 0 thay đổi ở mã nguồn, CI, `deliverables/`. (AC-1, AC-2, AC-3, AC-4, AC-5)

<a id="out-of-scope"></a>
## Out of Scope

- Đổi mã nguồn (`src/`, `scripts/`, `tests/`, `pyproject.toml`).
- Đổi hay thêm CI (hệ thống tích hợp liên tục).
- Tài liệu khách hàng `deliverables/`.
- Hỗ trợ Windows/macOS (thuộc `specs/006-cross-platform-support`); tài liệu chỉ ghi đúng hiện trạng.
- Dùng vai QA hoặc challenger cho feature này; vai thi công là vai `docs`.

<a id="assumptions"></a>
## Assumptions

- Mã M0–M1 (spec 001–005) đã có trên nhánh hiện hành; bốn điểm vào CLI khai báo đúng như `docs/00-survey/mma-ai-project-docs.md` (khảo sát đã ghi `--help` của bốn lệnh thoát 0 trong worktree sạch tại HEAD `629550d`).
- Vai thi công là vai `docs`, outputs `README.md LICENSE CONTRIBUTING.md CHANGELOG.md docs/guides/**`; tối đa 3 task: (1) README + LICENSE + CONTRIBUTING; (2) CHANGELOG + guides; (3) reviewer đối chiếu lệnh trong tài liệu với trợ giúp thật của từng lệnh. Không dùng QA/challenger. Bố cục task thuộc bước tasks, không thuộc spec này.
- Huy hiệu là huy hiệu tĩnh (Python 3.11–3.12, giấy phép MIT); không có huy hiệu CI vì dự án không đổi/thêm CI trong feature này.
- Phép đối chiếu chạy `--help` chỉ cần phụ thuộc nền; lệnh cần nhóm `rl`/`eval` hoặc màn hình không chạy được trên máy đo thì ghi "CHƯA KIỂM", không ghi "đạt".
- Ngày phát hành của `[0.1.0]` là ngày ghi tài liệu; không gắn thẻ git vì tạo thẻ/phát hành ngoài phạm vi.
