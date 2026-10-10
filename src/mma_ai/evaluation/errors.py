"""Các lớp ngoại lệ cho phân hệ đánh giá policy (mma_ai.evaluation).

Định nghĩa các lớp lỗi phản ánh quy tắc miền nghiệp vụ của phân hệ đánh giá:
- FR-015: Lỗi checkpoint không hợp lệ hoặc không tương thích mô hình.
- FR-018: Lỗi cấu hình đánh giá sai tham số hoặc vi phạm ranh giới.
- INV-004: Mã thoát CLI ổn định theo contracts/cli.md, không để lại kết quả dở dang.
- API-EVL-0002: Các lớp lỗi hỗ trợ điều phối đánh giá chính sách và bắt lỗi chi tiết.
"""


class EvalError(Exception):
    """Lớp ngoại lệ cơ sở cho phân hệ đánh giá policy, mang mã thoát CLI ổn định."""

    exit_code: int = 1

    def __init__(self, message: str = "") -> None:
        """Khởi tạo ngoại lệ với thông điệp lỗi tiếng Việt kèm ngữ cảnh."""
        super().__init__(message)
        self.message: str = message


class EvalConfigError(EvalError):
    """Tham số hoặc cấu hình đánh giá không hợp lệ (mã thoát 2)."""

    exit_code: int = 2


class CheckpointUnusable(EvalError):
    """Checkpoint không tồn tại, hỏng hoặc khác cấu trúc/hash XML (mã thoát 4)."""

    exit_code: int = 4


class LeakageError(EvalError):
    """Rò rỉ dữ liệu giữa tập đánh giá và tập huấn luyện hoặc trùng lặp seed (mã thoát 5)."""

    exit_code: int = 5


class TrainSetUnknown(EvalError):
    """Không thiết lập được tập huấn luyện hoặc seed của run để đối chiếu (mã thoát 5)."""

    exit_code: int = 5


class LogMissing(EvalError):
    """Nhật ký huấn luyện bị thiếu chỉ số cần thiết cho biểu đồ (mã thoát 6, không chặn lưu số)."""

    exit_code: int = 6


class EvalWriteError(EvalError):
    """Không thể ghi kết quả đánh giá do đĩa đầy hoặc thiếu quyền hạn (mã thoát 7)."""

    exit_code: int = 7


__all__: list[str] = [
    "CheckpointUnusable",
    "EvalConfigError",
    "EvalError",
    "EvalWriteError",
    "LeakageError",
    "LogMissing",
    "TrainSetUnknown",
]
