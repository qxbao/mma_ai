# Specification Quality Checklist: M1 (3/4) — Đánh giá policy so với random policy và biểu đồ

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — chỉ nhắc tên do yêu cầu gốc ràng buộc (`scripts/evaluate.py`, `metrics.py`, TensorBoard/CSV, NumPy/Pandas); phương pháp tính khoảng tin cậy và thư viện vẽ để plan quyết định
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders — mức phù hợp với người dùng là nhà nghiên cứu RL
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined — AC-1…AC-5 của yêu cầu mỗi mã có ≥ 1 scenario ghi đúng mã
- [x] Edge cases are identified — mỗi dòng kết thúc bằng mã `(AC-n)` hoặc `(INV-n)`
- [x] Scope is clearly bounded — mục Out of Scope chép từ mục "Ngoài" của yêu cầu
- [x] Dependencies and assumptions identified — phụ thuộc con 1/con 2 ghi ở Assumptions, đánh dấu CHƯA KIỂM

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows — 6 story, mỗi story có dòng `**Tần suất**`
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Hai câu hỏi mở §8 của yêu cầu (tiêu chí "tốt hơn random"; tần suất ghi activation) đã được tự chốt ở `## Clarifications`; không có quyết định mở rộng phạm vi nên không có `[NEEDS CLARIFICATION]`.
- Q-0001 (người, C-0010) thuộc `003-ppo-train-repro`; con 3 không dựng giao diện thời gian thực (ghi ở Clarifications).
- Các con số 50 mục tiêu, 0,02 m, 95%, seed 12345 là mặc định khởi đầu cấu hình được, chưa đo; không có khẳng định về chất lượng policy.
