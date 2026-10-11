"""Ngoại lệ miền cho pipeline huấn luyện."""


class TrainError(Exception):
    """Lỗi cơ sở của pipeline huấn luyện, có mã thoát CLI ổn định."""

    exit_code = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TrainConfigError(TrainError):
    """Cấu hình huấn luyện không hợp lệ."""

    exit_code = 2


class StageNotImplemented(TrainError):
    """Stage được yêu cầu chưa được triển khai."""

    exit_code = 3


class CheckpointError(TrainError):
    """Checkpoint không hợp lệ hoặc thiếu thành phần."""

    exit_code = 4


class NonFiniteError(TrainError):
    """Phát hiện giá trị NaN hoặc vô cực trong quá trình huấn luyện."""

    exit_code = 1


class CheckpointIOError(TrainError):
    """Không thể đọc hoặc ghi checkpoint."""

    exit_code = 1


class RunDirError(TrainError):
    """Không thể tạo hoặc bảo vệ thư mục run."""

    exit_code = 1
