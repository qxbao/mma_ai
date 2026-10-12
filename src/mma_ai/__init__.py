"""Gói mã nguồn chính của MMA AI (mma_ai)."""

import os

if os.environ.get("MMA_AI_FORCE_NO_DISPLAY", "") not in ("", "0"):
    os.environ.setdefault("MUJOCO_GL", "egl")
else:
    from mma_ai.compat.display import probe_display
    os.environ.setdefault("MUJOCO_GL", "egl") if not probe_display().available else None

__version__: str = "0.1.0"
__all__: list[str] = ["__version__"]
