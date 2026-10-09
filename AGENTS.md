<!-- ai-sdlc:ban-do:bat-dau — MÁY ghi đoạn này; chữ ngoài hai dấu là của bạn, máy không đụng -->

## Dự án do ai-sdlc điều phối

- Bản đồ phân hệ ↔ spec ↔ tài liệu ↔ vùng mã: `docs/MAP.md` (máy sinh). Mở ĐÚNG dòng của phân hệ đang làm.
- Tài liệu năm lớp: `docs/01-intent` (SRS; năng lực ở `capability/`; spec light theo module ở `modules/`) · `02-strategic` · `03-tactical` (theo bounded context) · `04-implementation` (`ui/` theo phân hệ) · `05-tracing` (`trace/` theo phân hệ). Tệp chỉ mục do máy sinh — sửa tệp phân hệ trong thư mục con.
- Vùng ghi của mỗi task là cột outputs trong `specs/*/tasks.md`; kit chấm diff đã commit theo đúng các glob đó.

<!-- ai-sdlc:ban-do:ket-thuc -->
