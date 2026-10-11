"""Kiểm thử tích hợp các ràng buộc nhập (import constraints) cho phân hệ hiển thị (US4/FR-015).

Hiện thực và bảo vệ các yêu cầu:
- US4: Episode lưu đủ thông tin để phát lại đúng mô hình.
- FR-015: Replay chạy ở tiến trình riêng, chỉ đọc dữ liệu của run,
  và TUYỆT ĐỐI KHÔNG nhập các mô-đun huấn luyện (learning.trainer, learning.ppo).
- INV-003: Bất biến tính tự đủ và ranh giới mô-đun độc lập.
- INV-005: Mô-đun hiển thị chỉ-đọc (read-only), tách biệt khỏi vòng lặp huấn luyện.
- AC-1: Phát lại episode hợp lệ trên tiến trình độc lập.
- AC-4: Ranh giới độc lập khi kiểm tra tính tương thích của mô hình.
- NFR-REL-001: Ràng buộc nhập cô lập đảm bảo độ ổn định và khả năng tái lập.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def _get_project_root() -> Path:
    """Trả về thư mục gốc của dự án (project root)."""
    return Path(__file__).resolve().parents[2]


def test_visualization_has_no_training_imports() -> None:
    """US4, FR-015, INV-003, INV-005, AC-1: Quét AST tĩnh đảm bảo không import trainer hay ppo."""
    root = _get_project_root()
    vis_dir = root / "src" / "mma_ai" / "visualization"
    assert vis_dir.is_dir(), f"Thư mục hiển thị không tồn tại: {vis_dir}"

    py_files = sorted(vis_dir.glob("*.py"))
    assert len(py_files) > 0, "Không tìm thấy tệp mã Python nào trong src/mma_ai/visualization"

    forbidden_modules = ("learning.trainer", "learning.ppo", "trainer", "ppo")

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert forbidden not in alias.name, (
                            f"FR-015 vi phạm: {py_file.name} chứa lệnh import '{alias.name}' "
                            f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for forbidden in forbidden_modules:
                    assert forbidden not in module, (
                        f"FR-015 vi phạm: {py_file.name} chứa lệnh from {module} import ... "
                        f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                    )
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    for forbidden in forbidden_modules:
                        assert forbidden not in full_name, (
                            f"FR-015 vi phạm: {py_file.name} nhập '{alias.name}' từ '{module}' "
                            f"(bị cấm vì chứa '{forbidden}') tại dòng {node.lineno}"
                        )

    # Kiểm tra động trong tiến trình con cô lập (isolated subprocess)
    check_code = (
        "import sys\n"
        "import mma_ai.visualization.cli\n"
        "import mma_ai.visualization.replay\n"
        "import mma_ai.visualization.recorder\n"
        "forbidden = ('mma_ai.learning.trainer', 'mma_ai.learning.ppo')\n"
        "for mod in forbidden:\n"
        "    assert mod not in sys.modules, f'{mod} đã bị nạp vào sys.modules'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Kiểm tra động nạp mô-đun huấn luyện thất bại: {result.stderr}"


def test_episode_path_does_not_import_torch() -> None:
    """US4, FR-015, AC-1, NFR-REL-001: Đường dẫn phát lại episode không nạp thư viện PyTorch."""
    root = _get_project_root()
    episode_file = root / "src" / "mma_ai" / "visualization" / "episode.py"
    assert episode_file.is_file(), f"Tệp episode.py không tồn tại: {episode_file}"

    # 1. Kiểm tra AST tĩnh của tệp episode.py
    tree = ast.parse(episode_file.read_text(encoding="utf-8"), filename=str(episode_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "torch" not in alias.name, (
                    f"FR-015 vi phạm: episode.py import '{alias.name}' tại dòng {node.lineno}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert "torch" not in module, (
                f"FR-015 vi phạm: episode.py from '{module}' import tại dòng {node.lineno}"
            )

    # 2. Kiểm tra động khi đọc episode và chạy replay không màn hình
    sample_episode = (
        root
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
        / "examples"
        / "episode.minimal-null-source.json"
    )
    assert sample_episode.is_file(), f"Tệp episode mẫu không tồn tại: {sample_episode}"

    check_code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from mma_ai.visualization.episode import read_episode\n"
        "from mma_ai.visualization.replay import run_replay\n"
        f"ep_path = Path(r'{sample_episode}')\n"
        "ep = read_episode(ep_path)\n"
        "assert ep is not None\n"
        "assert 'torch' not in sys.modules, 'torch bị nạp khi gọi read_episode'\n"
        "cmd = ['--episode', str(ep_path), '--headless', '--allow-model-mismatch']\n"
        "code = run_replay(cmd)\n"
        "assert code == 0, f'run_replay trả về mã lỗi: {code}'\n"
        "assert 'torch' not in sys.modules, 'torch bị nạp khi chạy replay headless'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Đường dẫn episode nạp thư viện torch: {result.stderr}"


def test_headless_never_imports_viewer() -> None:
    """US4, FR-015, AC-1, NFR-REL-001: Chế độ không màn hình tuyệt đối không nhập MuJoCo Viewer."""
    root = _get_project_root()
    vis_dir = root / "src" / "mma_ai" / "visualization"

    # 1. Quét AST tĩnh: chỉ duy nhất viewer.py được phép import mujoco.viewer (nhập lười)
    for py_file in vis_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        if py_file.name != "viewer.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "mujoco.viewer" not in alias.name, (
                            f"FR-015: {py_file.name} import '{alias.name}' dòng {node.lineno}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    assert "mujoco.viewer" not in module, (
                        f"FR-015: {py_file.name} from '{module}' dòng {node.lineno}"
                    )
                    for alias in node.names:
                        assert "viewer" not in alias.name or "mujoco" not in module, (
                            f"FR-015: {py_file.name} import viewer từ '{module}' dòng {node.lineno}"
                        )
        else:
            # Trong viewer.py: mujoco.viewer không được import ở cấp độ mô-đun (top-level)
            for top_node in tree.body:
                if isinstance(top_node, ast.Import):
                    for alias in top_node.names:
                        assert "mujoco.viewer" not in alias.name, (
                            f"FR-015: viewer.py import '{alias.name}' top-level {top_node.lineno}"
                        )
                elif isinstance(top_node, ast.ImportFrom):
                    module = top_node.module or ""
                    assert "mujoco.viewer" not in module, (
                        f"FR-015: viewer.py from '{module}' top-level dòng {top_node.lineno}"
                    )

    # 2. Kiểm tra động khi chạy CLI với cờ --headless
    sample_episode = (
        root
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
        / "examples"
        / "episode.minimal-null-source.json"
    )
    check_code = (
        "import sys\n"
        "from mma_ai.visualization.replay import run_replay\n"
        f"ep_str = r'{sample_episode}'\n"
        "cmd = ['--episode', ep_str, '--headless', '--allow-model-mismatch']\n"
        "code = run_replay(cmd)\n"
        "assert code == 0, f'run_replay trả về mã lỗi: {code}'\n"
        "assert 'mujoco.viewer' not in sys.modules, 'mujoco.viewer bị nạp khi headless'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Chế độ headless nạp mujoco.viewer: {result.stderr}"


def test_visualization_package_init_clean() -> None:
    """US4, FR-015, AC-1: Nhập gói visualization không nạp viewer, glfw, hay torch."""
    root = _get_project_root()
    check_code = (
        "import sys\n"
        "import mma_ai.visualization\n"
        "forbidden = (\n"
        "    'mujoco.viewer',\n"
        "    'glfw',\n"
        "    'torch',\n"
        "    'mma_ai.learning.trainer',\n"
        "    'mma_ai.learning.ppo',\n"
        ")\n"
        "for mod in forbidden:\n"
        "    assert mod not in sys.modules, f'{mod} bị nạp khi chỉ import mma_ai.visualization'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Gói visualization nạp phụ thuộc nặng khi khởi tạo: {result.stderr}"
    )
