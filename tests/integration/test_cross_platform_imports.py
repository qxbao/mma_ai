from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import mma_ai


def test_fr_001_fr_003_fr_015_inv_002_ac_1_every_mma_ai_module_imports() -> None:
    module_names = sorted(
        module.name
        for module in pkgutil.walk_packages(mma_ai.__path__, prefix="mma_ai.")
    )

    failures: list[str] = []
    for module_name in module_names:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    optional_torch_failures = {
        "mma_ai.learning.networks: ModuleNotFoundError: No module named 'torch'",
        "mma_ai.learning.ppo: ModuleNotFoundError: No module named 'torch'",
        "mma_ai.learning.trainer: ModuleNotFoundError: No module named 'torch'",
    }
    unexpected_failures = [
        failure for failure in failures if failure not in optional_torch_failures
    ]
    assert not unexpected_failures, "Không nhập được mô-đun mma_ai:\n" + "\n".join(
        unexpected_failures
    )


def test_fr_001_fr_003_inv_001_ac_1_no_module_level_os_specific_imports() -> None:
    package_dir = Path(mma_ai.__file__).parent
    forbidden = {"resource", "fcntl", "msvcrt", "winreg"}
    violations: list[str] = []

    for source_path in sorted(package_dir.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in tree.body:
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            for name in names:
                if name in forbidden:
                    violations.append(
                        f"{source_path.relative_to(package_dir)}:{node.lineno}: {name}"
                    )

    assert not violations, "Import phụ thuộc riêng OS ở mức mô-đun:\n" + "\n".join(violations)
