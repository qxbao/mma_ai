"""Các lớp ngoại lệ cho phân hệ môi trường mô phỏng (mma_ai.environment).

Định nghĩa các lớp lỗi phản ánh quy tắc miền nghiệp vụ của môi trường học tăng cường:
- FR-002: Quản lý tính hợp lệ của giao diện tương tác Gymnasium và ranh giới mô phỏng.
- FR-003: Báo lỗi khi cấu hình, trạng thái hoặc giá trị điều khiển cơ vi phạm hợp đồng.
- FR-006: Xử lý sự cố mất ổn định vật lý và sai lệch cấu trúc dữ liệu quan sát.
- AC-1 / AC-2: Thông điệp tiếng Việt kèm ngữ cảnh, giá trị vi phạm và số thực thể.
- INV-004: Không sử dụng lại tên OSError/EnvironmentError có sẵn của Python.
"""


class EnvironmentBaseError(Exception):
    """Lớp ngoại lệ cơ sở (base exception) cho toàn bộ phân hệ môi trường mma_ai.environment.

    Tránh kế thừa hoặc trùng tên với OSError/EnvironmentError tích hợp sẵn của Python.
    """

    def __init__(self, message: str = "") -> None:
        """Khởi tạo ngoại lệ với thông điệp lỗi tiếng Việt kèm ngữ cảnh."""
        super().__init__(message)
        self.message: str = message


class EnvConfigError(EnvironmentBaseError):
    """Lỗi cấu hình môi trường không hợp lệ hoặc thiếu tham số bắt buộc."""


class TargetConfigError(EnvironmentBaseError):
    """Lỗi cấu hình tập mục tiêu train/test bất khả thi hoặc vi phạm khoảng cách tối thiểu."""


class ObservationError(EnvironmentBaseError):
    """Lỗi không gian quan sát (observation) sai chiều, ngoài cận khai báo hoặc chứa NaN/Inf."""


class PhysicsInstabilityError(EnvironmentBaseError):
    """Lỗi mô phỏng MuJoCo mất ổn định số học (NaN/Inf hoặc cảnh báo vật lý)."""


class EnvStateError(EnvironmentBaseError):
    """Lỗi trạng thái vòng đời môi trường (gọi step trước khi reset hoặc sau khi kết thúc)."""


__all__: list[str] = [
    "EnvConfigError",
    "EnvStateError",
    "EnvironmentBaseError",
    "ObservationError",
    "PhysicsInstabilityError",
    "TargetConfigError",
]
