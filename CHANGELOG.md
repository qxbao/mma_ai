# Nhật ký thay đổi

Tài liệu này theo quy ước nhật ký thay đổi (Keep a Changelog) và phiên bản ngữ nghĩa (Semantic Versioning).

## [Unreleased]

### Added

- 006: thêm gói tương thích nền tảng `mma_ai.compat`, báo cáo môi trường `python -m mma_ai.compat.env_report`, cổng năng lực với sáu dấu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` và ma trận CI ba hệ điều hành × Python 3.11/3.12 ([đặc tả 006](specs/006-cross-platform-support/)).
- 009: thêm năng lực `requires_git_history` để loại có báo cáo kiểm thử cần lịch sử Git trên bản archive không có `.git` ([đặc tả 009](specs/009-git-history-capability/)).
- 008: thêm bộ tài liệu dự án gồm README, CONTRIBUTING, CHANGELOG và các hướng dẫn trong `docs/guides/` ([đặc tả 008](specs/008-project-docs/)).
- 010: thêm hướng dẫn kiểm tra môi trường và năng lực nền tảng tại `docs/guides/platforms.md` ([đặc tả 010](specs/010-docs-platform-sync/)).

### Changed

- 007: làm ổn định hai kiểm thử viewer và tiến trình View3D bằng cách chọn nhánh kiểm tra theo khả dụng hiển thị, chờ tiến trình khởi chạy có giới hạn và chẩn đoán lỗi viewer ([đặc tả 007](specs/007-stabilize-viewer-tests/)).
- 006: các CLI ghi đầu ra UTF-8 và dùng cơ chế ghi tệp nguyên tử đa nền tảng ([đặc tả 006](specs/006-cross-platform-support/)).
- 010: README mô tả tình trạng nền tảng theo bằng chứng đã kiểm ([đặc tả 010](specs/010-docs-platform-sync/)).

Kết quả đã kiểm chỉ trên Linux; Windows, macOS và CI chạy thật chưa được kiểm.

## [0.1.0] - 2026-10-12

### Added

- M0: mô phỏng vật lý và kiểm tra sức khỏe số học trong [`src/mma_ai/physics/`](src/mma_ai/physics/), theo [đặc tả 001](specs/001-m0-physics-benchmark/).
- M1: môi trường khuỷu tay cơ bắp với tập mục tiêu huấn luyện và kiểm thử trong [`src/mma_ai/environment/`](src/mma_ai/environment/), theo [đặc tả 002](specs/002-elbow-muscle-env/).
- M1: huấn luyện bằng tối ưu chính sách gần đúng (Proximal Policy Optimization, PPO), lưu điểm kiểm tra (checkpoint), ghi hồ sơ tái lập, theo dõi qua `--ui`/`--view3d` và đo hiệu năng trong [`src/mma_ai/learning/`](src/mma_ai/learning/) và [`src/mma_ai/monitoring/`](src/mma_ai/monitoring/), theo [đặc tả 003](specs/003-ppo-train-repro/).
- M1: đánh giá chính sách so với chính sách ngẫu nhiên (random policy) và tạo biểu đồ trong [`src/mma_ai/evaluation/`](src/mma_ai/evaluation/), theo [đặc tả 004](specs/004-eval-vs-random-plots/).
- M1: phát lại và trình diễn chuyển động 3D trong [`src/mma_ai/visualization/`](src/mma_ai/visualization/), theo [đặc tả 005](specs/005-replay-3d-muscle-demo/).
