# Nhật ký thay đổi

Tài liệu này theo quy ước nhật ký thay đổi (Keep a Changelog) và phiên bản ngữ nghĩa (Semantic Versioning).

## [Unreleased]

## [0.1.0] - 2026-10-12

### Added

- M0: mô phỏng vật lý và kiểm tra sức khỏe số học trong [`src/mma_ai/physics/`](src/mma_ai/physics/), theo [đặc tả 001](specs/001-m0-physics-benchmark/).
- M1: môi trường khuỷu tay cơ bắp với tập mục tiêu huấn luyện và kiểm thử trong [`src/mma_ai/environment/`](src/mma_ai/environment/), theo [đặc tả 002](specs/002-elbow-muscle-env/).
- M1: huấn luyện bằng tối ưu chính sách gần đúng (Proximal Policy Optimization, PPO), lưu điểm kiểm tra (checkpoint), ghi hồ sơ tái lập, theo dõi qua `--ui`/`--view3d` và đo hiệu năng trong [`src/mma_ai/learning/`](src/mma_ai/learning/) và [`src/mma_ai/monitoring/`](src/mma_ai/monitoring/), theo [đặc tả 003](specs/003-ppo-train-repro/).
- M1: đánh giá chính sách so với chính sách ngẫu nhiên (random policy) và tạo biểu đồ trong [`src/mma_ai/evaluation/`](src/mma_ai/evaluation/), theo [đặc tả 004](specs/004-eval-vs-random-plots/).
- M1: phát lại và trình diễn chuyển động 3D trong [`src/mma_ai/visualization/`](src/mma_ai/visualization/), theo [đặc tả 005](specs/005-replay-3d-muscle-demo/).
