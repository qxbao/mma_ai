"""Kiểm thử cấu hình đóng gói và phụ thuộc môi trường (packaging & dependencies).

Chứng minh các yêu cầu:
- FR-015: Quyết định phiên bản gymnasium và bỏ myosuite (tham chiếu research.md Q1).
- FR-016: Không tự giả định tương thích, ghim đúng dải phiên bản, khoá trong lockfile.
- NFR-INST-001: Môi trường cài đặt được sạch sẽ, phụ thuộc nhất quán.
- AC-5: Cài đặt và cấu hình gói hợp lệ, kiểm tra pin range và package data.
"""

import tomllib
from pathlib import Path


def _load_pyproject() -> dict[str, object]:
    """Nạp tệp pyproject.toml từ thư mục gốc dự án."""
    root_dir = Path(__file__).resolve().parents[2]
    pyproject_path = root_dir / "pyproject.toml"
    assert pyproject_path.is_file(), f"Không tìm thấy tệp pyproject.toml tại {pyproject_path}"
    with pyproject_path.open("rb") as f:
        return tomllib.load(f)


def test_gymnasium_pin_range() -> None:
    """FR-015, AC-5: Khẳng định gymnasium được ghim dải >=1.4,<1.5 và có chú thích Q1."""
    data = _load_pyproject()
    project = data.get("project", {})
    assert isinstance(project, dict), "[project] phải là một bảng toml"

    dependencies = project.get("dependencies", [])
    assert isinstance(dependencies, list), "dependencies phải là danh sách chuỗi"

    gym_deps = [
        dep for dep in dependencies if isinstance(dep, str) and dep.startswith("gymnasium")
    ]
    assert len(gym_deps) == 1, (
        f"Cần đúng 1 khai báo gymnasium trong dependencies, tìm thấy: {gym_deps}"
    )
    gym_spec = gym_deps[0]
    assert gym_spec == "gymnasium>=1.4,<1.5", (
        f"Khai báo gymnasium phải đúng ghim 'gymnasium>=1.4,<1.5', thực tế: {gym_spec}"
    )

    # Khẳng định có dòng chú thích trỏ tới specs/002-elbow-muscle-env/research.md (Q1)
    root_dir = Path(__file__).resolve().parents[2]
    content = (root_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert "specs/002-elbow-muscle-env/research.md" in content and "Q1" in content, (
        "Thiếu dòng chú thích trỏ tới research.md (Q1) trong pyproject.toml"
    )


def test_myosuite_absent() -> None:
    """FR-015, FR-016: Khẳng định myosuite và các phụ thuộc cấm không có trong dự án."""
    data = _load_pyproject()
    project = data.get("project", {})
    assert isinstance(project, dict), "[project] phải là một bảng toml"

    dependencies = project.get("dependencies", [])
    assert isinstance(dependencies, list), "dependencies phải là danh sách"

    # myosuite không được nằm trong dependencies chính hoặc optional
    dep_names = [
        dep.split(";")[0].split("=")[0].split(">")[0].split("<")[0].strip()
        for dep in dependencies
    ]
    assert "myosuite" not in dep_names, "myosuite không được xuất hiện trong dependencies"
    assert "stable-baselines3" not in dep_names, "stable-baselines3 không được có trong deps"
    assert "torch" not in dep_names, "torch chỉ được đặt trong optional-dependencies rl"

    optional_deps = project.get("optional-dependencies", {})
    if isinstance(optional_deps, dict):
        for group, reqs in optional_deps.items():
            if isinstance(reqs, list):
                for req in reqs:
                    assert "myosuite" not in req, (
                        f"myosuite không được xuất hiện trong extra '{group}'"
                    )


def test_myo_sim_pinned_exact() -> None:
    """FR-015, AC-5: Khẳng định myo-sim được ghim phiên bản chính xác ==0.2.3."""
    data = _load_pyproject()
    project = data.get("project", {})
    assert isinstance(project, dict), "[project] phải là một bảng toml"

    dependencies = project.get("dependencies", [])
    assert isinstance(dependencies, list), "dependencies phải là danh sách"

    myo_sim_deps = [
        dep for dep in dependencies if isinstance(dep, str) and dep.startswith("myo-sim")
    ]
    assert len(myo_sim_deps) == 1, (
        f"Cần đúng 1 khai báo myo-sim trong dependencies, tìm thấy: {myo_sim_deps}"
    )
    assert myo_sim_deps[0] == "myo-sim==0.2.3", (
        f"myo-sim phải được ghim chính xác 'myo-sim==0.2.3', thực tế: {myo_sim_deps[0]}"
    )


def test_package_data_covers_environment_yaml() -> None:
    """NFR-INST-001, AC-5: Khẳng định cấu hình package data bao phủ environment yaml."""
    data = _load_pyproject()
    tool = data.get("tool", {})
    assert isinstance(tool, dict), "[tool] phải là một bảng toml"

    hatch = tool.get("hatch", {})
    assert isinstance(hatch, dict), "[tool.hatch] phải là một bảng toml"

    build = hatch.get("build", {})
    assert isinstance(build, dict), "[tool.hatch.build] phải là một bảng toml"

    targets = build.get("targets", {})
    assert isinstance(targets, dict), "[tool.hatch.build.targets] phải là một bảng toml"

    wheel = targets.get("wheel", {})
    assert isinstance(wheel, dict), "[tool.hatch.build.targets.wheel] phải là một bảng toml"

    artifacts = wheel.get("artifacts", [])
    assert isinstance(artifacts, list), "wheel.artifacts phải là danh sách mẫu đóng gói"

    expected_pattern = "src/mma_ai/environment/*.yaml"
    assert expected_pattern in artifacts, (
        f"Package data phải chứa mẫu '{expected_pattern}', danh sách hiện tại: {artifacts}"
    )
