import os
import subprocess
import sys


def test_forced_headless_body_model_does_not_load_glfw() -> None:
    env = {**os.environ, "MMA_AI_FORCE_NO_DISPLAY": "1"}
    env.pop("MUJOCO_GL", None)
    subprocess.run(
        [sys.executable, "-c", "import sys; import mma_ai.physics.body_model; assert "
         "'glfw' not in sys.modules and 'mujoco.glfw' not in sys.modules"], check=True, env=env
    )
