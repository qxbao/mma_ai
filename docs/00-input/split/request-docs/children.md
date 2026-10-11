---
status: no-split
parent: .ai/chat/request-docs.md
reason: "một năng lực duy nhất — bộ tài liệu dự án (README, LICENSE, CONTRIBUTING, CHANGELOG, guides) do một vai docs viết, không có ranh giới sở hữu dữ liệu hay bounded context; yêu cầu tự giới hạn tối đa 3 task, 0 module khách nêu"
children: []
---

# Không tách (no-split)

Yêu cầu chỉ có MỘT năng lực: bộ tài liệu nhập môn cho `mma_ai`. Ba nhóm đầu ra trong dàn ý reader (nhập môn · lịch sử/hướng dẫn · đối chiếu lệnh) là ba task của cùng một spec, không phải ba năng lực tự đứng được.

## Lý do (rationale)

| Tiêu chí | Kết quả |
|---|---|
| Ranh giới sở hữu dữ liệu / bounded context | Không có — chỉ là tệp Markdown, không đổi mã nguồn (§4 Ngoài) |
| Số con tách được ≥ 3 và tự đứng được | Không: CHANGELOG và guides tham chiếu lệnh README; task 3 chỉ là đối chiếu (reviewer) các tệp của task 1–2, không có giá trị riêng |
| Ước lượng quy mô | ≤ 3 task, do yêu cầu tự ràng buộc (§5) — thấp hơn ngưỡng cỡ L (> 20 task) |
| Module khách nêu (§4 `- M01 …`) | Không có ⇒ no-split hợp lệ |
| Vai thi công | Một vai `docs`, outputs `README.md LICENSE CONTRIBUTING.md CHANGELOG.md docs/guides/**` |

## Hướng đi tiếp

Chạy `specify` cho cả yêu cầu gốc `.ai/chat/request-docs.md`, giữ nguyên bố cục 3 task: (1) README + LICENSE + CONTRIBUTING · (2) CHANGELOG + guides · (3) reviewer đối chiếu lệnh trong tài liệu với trợ giúp thật của từng lệnh.

- Tự chốt: no-split — tách ra dưới 3 con thì trái luật `request-split`, tách ra 3 con theo tệp là cắt theo đầu ra chứ không theo năng lực, và làm tăng chi phí fan-out (3 spec, 3 nhánh) cho việc ≤ 3 task.
