"""Thử thách bất biến (challenge) INV-001..INV-004 của môi trường khuỷu tay (T219).

Mỗi test nhắm một bất biến của sản phẩm qua đầu vào mà người dùng/hệ thống gặp được.
Các ca đỏ (finding) mang `xfail` KHÔNG strict với mã F-NNN trong `reason`; ca xanh là
vector đã thử mà không lách được (ghi vào `disproved_hypotheses`).

- INV-001: train/test giao rỗng, cách nhau >= min_separation_m; chế độ test không chọn train.
- INV-002: cùng seed + cấu hình => cùng danh sách và cùng mục tiêu chọn ở reset(seed).
- INV-003: điều khiển duy nhất qua kích thích cơ; mọi actuator là cơ.
- INV-004: observation luôn đúng chiều, hữu hạn, trong cận — hoặc có lỗi rõ ràng.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path
from typing import Any

import mujoco
import myo_sim
import numpy as np
import pytest

from mma_ai.environment.env_config import TargetConfig
from mma_ai.environment.errors import (
    ActivationError,
    EnvironmentBaseError,
    EnvStateError,
    ModelError,
    ObservationError,
    PhysicsInstabilityError,
    TargetConfigError,
)
from mma_ai.environment.observation import validate_observation
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.environment.targets import TargetGenerator, TargetSet, TargetSetPair

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(_REPO_ROOT / "src")
_BASE_CFG: dict[str, Any] = {
    "n_train": 200,
    "n_test": 50,
    "min_separation_m": 0.02,
    "split_block_m": 0.05,
    "angle_margin_rad": 0.05,
    "default_seed": 42,
}
_U_HALF = np.full(6, 0.5)


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def env() -> Any:
    """Môi trường mặc định dùng chung để lấy mô hình MuJoCo (chỉ đọc)."""
    return ElbowReachEnv()


def _generator(model: Any, **overrides: Any) -> TargetGenerator:
    cfg = {**_BASE_CFG, **overrides}
    return TargetGenerator(model, TargetConfig(**cfg))


def _independent_positions(model: Any, angles: list[float]) -> np.ndarray:
    """Tính lại vị trí đầu mút từ góc bằng MjData riêng, không tin position_m của bộ sinh."""
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "wrist")
    data = mujoco.MjData(model)
    out = []
    for angle in angles:
        data.qpos[0] = angle
        mujoco.mj_kinematics(model, data)
        out.append(data.site_xpos[site_id].copy())
    return np.asarray(out, dtype=np.float64)


def _assert_inv001(model: Any, pair: TargetSetPair, min_sep: float) -> None:
    train = _independent_positions(model, [t.angle_rad for t in pair.train])
    test = _independent_positions(model, [t.angle_rad for t in pair.test])
    dist = np.linalg.norm(train[:, None, :] - test[None, :, :], axis=2)
    assert float(dist.min()) >= min_sep, f"INV-001: cặp gần nhất {dist.min():.9f} < {min_sep}"
    assert set(pair.arc.train_blocks).isdisjoint(pair.arc.test_blocks), "INV-001: khối giao nhau"


# --------------------------------------------------------------------------------------
# INV-001
# --------------------------------------------------------------------------------------


def test_inv001_sweep_300_seeds_and_extreme_seeds(env: Any) -> None:
    """INV-001: ≥ 300 seed + seed 0 + seed cực lớn; đo lại khoảng cách độc lập, không dung sai."""
    gen = _generator(env.model)
    seeds = list(range(300)) + [2**31 - 1, 2**32, 2**63 - 1, 2**64 + 5, 2**200]
    for seed in seeds:
        _assert_inv001(env.model, gen.generate(seed), 0.02)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("n_train", "n_test"),
    [(1, 1), (1, 50), (50, 1), (3, 500), (500, 3), (200, 50)],
)
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("min_sep", "split_scale"),
    [(0.02, 1.1 * (1 + 1e-9)), (0.02, 1.1 + 1e-6), (0.05, 1.12), (0.2, 1.25), (0.001, 1.1000001)],
)
def test_inv001_boundary_configs_hold_or_raise(
    env: Any, n_train: int, n_test: int, min_sep: float, split_scale: float
) -> None:
    """INV-001: sát ngưỡng split_block_m ≈ 1,1·min_sep và kích thước tập biên."""
    gen = _generator(
        env.model,
        n_train=n_train,
        n_test=n_test,
        min_separation_m=min_sep,
        split_block_m=min_sep * split_scale,
    )
    for seed in (0, 1, 7, 2**40):
        try:
            pair = gen.generate(seed)
        except TargetConfigError:
            continue
        _assert_inv001(env.model, pair, min_sep)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "overrides",
    [
        {"n_train": 0},
        {"n_test": 0},
        {"n_train": -3},
        {"min_separation_m": 0.0},
        {"min_separation_m": -0.02},
        {"split_block_m": 0.02 * 1.1},
        {"split_block_m": 0.0},
        {"split_block_m": float("inf")},
        {"min_separation_m": 5.0, "split_block_m": 6.0},
        {"angle_margin_rad": 5.0},
        {"split_block_m": 0.3},
    ],
)
def test_inv001_infeasible_config_raises_target_config_error(
    env: Any, overrides: dict[str, Any]
) -> None:
    """INV-001: cấu hình bất khả thi ném TargetConfigError, không giảm khoảng cách âm thầm."""
    with pytest.raises(TargetConfigError):
        _generator(env.model, **overrides).generate(1)


def test_inv001_test_mode_never_returns_train_target_under_option_swaps() -> None:
    """INV-001: chế độ test (từ cấu hình) không chọn train dù options tráo qua lại giữa reset."""
    env_test = ElbowReachEnv(split="test")
    train_pos = {tuple(t.position_m) for t in env_test.targets.train}
    test_pos = {tuple(t.position_m) for t in env_test.targets.test}
    min_sep = env_test.cfg.targets.min_separation_m
    train_arr = np.array(sorted(train_pos))
    for seed in range(300):
        _, info = env_test.reset(seed=seed)  # không options: phải giữ nguyên chế độ test
        pos = tuple(info["target_position_m"])
        assert info["target_split"] == "test"
        assert pos in test_pos and pos not in train_pos
        assert float(np.linalg.norm(train_arr - np.array(pos), axis=1).min()) >= min_sep
        if seed % 3 == 0:  # chen một reset sang train rồi quay lại
            _, other = env_test.reset(seed=seed, options={"split": "train"})
            assert tuple(other["target_position_m"]) in train_pos


@pytest.mark.parametrize("bad", ["Test", " test", "test ", "", "all", None, b"test", 1, ["test"]])  # type: ignore[untyped-decorator]
def test_inv001_split_option_spoof_is_rejected(bad: Any) -> None:
    """INV-001: giá trị split lạ/khoảng trắng/kiểu khác bị từ chối, không rơi về train."""
    env_test = ElbowReachEnv(split="test")
    with pytest.raises(EnvironmentBaseError):
        env_test.reset(seed=1, options={"split": bad})
    _, info = env_test.reset(seed=1)
    assert info["target_split"] == "test"


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-001: cấu hình NaN ném ValueError thay vì TargetConfigError"
)
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "overrides",
    [
        {"min_separation_m": float("nan")},
        {"split_block_m": float("nan")},
        {"angle_margin_rad": float("nan")},
    ],
)
def test_inv001_nan_config_raises_target_config_error(
    env: Any, overrides: dict[str, Any]
) -> None:
    """INV-001: cấu hình bất khả thi (NaN) phải ném TargetConfigError nêu giới hạn vi phạm."""
    with pytest.raises(TargetConfigError):
        _generator(env.model, **overrides).generate(1)


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-002: angle_margin_rad âm sinh mục tiêu ngoài hành trình khớp"
)
def test_inv001_negative_margin_never_yields_unreachable_targets(env: Any) -> None:
    """FR-010/INV-001: mục tiêu phải ứng với góc khớp trong giới hạn, kể cả cấu hình dict."""
    cfg = {**_BASE_CFG, "angle_margin_rad": -0.5}
    pair = TargetGenerator(env.model, cfg).generate(1)
    lo, hi = (float(x) for x in env.model.jnt_range[0])
    angles = [t.angle_rad for t in pair.train] + [t.angle_rad for t in pair.test]
    assert min(angles) >= lo and max(angles) <= hi


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-003: ElbowReachEnv(targets=...) không kiểm giao rỗng/khoảng cách"
)
def test_inv001_env_rejects_injected_overlapping_target_pair(env: Any) -> None:
    """INV-001: cặp mục tiêu tiêm vào có train == test phải bị từ chối khi dựng môi trường."""
    base = env.targets
    overlapping = TargetSetPair(
        master_seed=base.master_seed,
        model_sha256=base.model_sha256,
        config=base.config,
        arc=base.arc,
        train=base.train,
        test=TargetSet(role="test", targets=base.train.targets),
        min_cross_distance_m=0.03,
        fingerprint_sha256=base.fingerprint_sha256,
    )
    with pytest.raises(EnvironmentBaseError):
        ElbowReachEnv(split="test", targets=overlapping)


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-004: tập quá lớn làm cạn bộ nhớ (MemoryError) thay vì TargetConfigError"
)
def test_inv001_oversized_sets_fail_with_target_config_error() -> None:
    """INV-001/trần: n_train, n_test cực lớn phải ném TargetConfigError, không MemoryError."""
    code = textwrap.dedent(
        """
        import resource, sys
        resource.setrlimit(resource.RLIMIT_AS, (6 * 2**30, 6 * 2**30))
        from mma_ai.environment.single_agent import ElbowReachEnv
        from mma_ai.environment.targets import TargetGenerator
        from mma_ai.environment.env_config import TargetConfig
        from mma_ai.environment.errors import TargetConfigError
        env = ElbowReachEnv()
        cfg = TargetConfig(30000, 30000, 0.02, 0.05, 0.05, 1)
        try:
            TargetGenerator(env.model, cfg).generate(1)
        except TargetConfigError:
            print("TARGET_CONFIG_ERROR")
        except BaseException as exc:
            print("OTHER", type(exc).__name__)
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONPATH": _SRC},
    )
    assert "TARGET_CONFIG_ERROR" in proc.stdout, proc.stdout + proc.stderr[-300:]


# --------------------------------------------------------------------------------------
# INV-002
# --------------------------------------------------------------------------------------

_CROSS_PROCESS_SCRIPT = textwrap.dedent(
    """
    import json
    from mma_ai.environment.single_agent import ElbowReachEnv
    env = ElbowReachEnv(split="test")
    picks = []
    for seed in (0, 5, 99, 2**40):
        _, info = env.reset(seed=seed)
        picks.append([info["target_index"], info["target_position_m"]])
    print(json.dumps({"fp": env.targets.fingerprint_sha256, "picks": picks}))
    """
)


def _run_with_hash_seed(hash_seed: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-c", _CROSS_PROCESS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PYTHONPATH": _SRC, "PYTHONHASHSEED": hash_seed},
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    result: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
    return result


def test_inv002_same_lists_and_picks_across_processes_with_different_hash_seeds() -> None:
    """INV-002: PYTHONHASHSEED khác nhau => cùng fingerprint và cùng mục tiêu chọn."""
    results = [_run_with_hash_seed(h) for h in ("0", "1", "424242", "random")]
    assert all(r == results[0] for r in results[1:])


def test_inv002_seed_none_then_reuse_recorded_seed_across_instances() -> None:
    """INV-002: seed=None ghi seed thực dùng; tái dùng seed đó (cả ở env mới) cho cùng mục tiêu."""
    env_a = ElbowReachEnv()
    env_b = ElbowReachEnv()
    for _ in range(25):
        obs_a, info_a = env_a.reset(seed=None)
        obs_b, info_b = env_b.reset(seed=info_a["seed"])
        assert info_b["target_index"] == info_a["target_index"]
        assert info_b["target_position_m"] == info_a["target_position_m"]
        assert np.array_equal(obs_a, obs_b)


def test_inv002_pick_is_independent_of_reset_history() -> None:
    """INV-002: mục tiêu ở reset(seed) không phụ thuộc lịch sử reset/step trước đó."""
    fresh = ElbowReachEnv()
    used = ElbowReachEnv()
    used.reset(seed=3)
    for _ in range(5):
        used.step(_U_HALF)
    used.reset(seed=None)
    used.reset(seed=8, options={"split": "test"})
    for seed in (0, 1, 17, 2**31, 2**62):
        _, expected = fresh.reset(seed=seed)
        _, got = used.reset(seed=seed)
        assert (got["target_index"], got["target_position_m"]) == (
            expected["target_index"],
            expected["target_position_m"],
        )


@pytest.mark.parametrize("seed_type", [np.int64, np.int32, np.uint64, np.uint8, int])  # type: ignore[untyped-decorator]
def test_inv002_numpy_integer_seeds_same_sets_and_picks(env: Any, seed_type: Any) -> None:
    """INV-002: seed kiểu numpy cho cùng danh sách và cùng mục tiêu như seed int thường."""
    seed = 7
    gen = _generator(env.model)
    assert gen.generate(seed_type(seed)).fingerprint_sha256 == gen.generate(seed).fingerprint_sha256
    fresh_a, fresh_b = ElbowReachEnv(), ElbowReachEnv()
    _, info_a = fresh_a.reset(seed=seed_type(seed))
    _, info_b = fresh_b.reset(seed=seed)
    assert info_a["target_index"] == info_b["target_index"]
    assert info_a["seed"] == seed and type(info_a["seed"]) is int


def test_inv002_generate_none_equals_default_seed_and_no_hidden_state(env: Any) -> None:
    """INV-002: generate(None) == generate(default_seed); gọi xen kẽ không rò trạng thái."""
    gen = _generator(env.model)
    first = gen.generate(5).fingerprint_sha256
    gen.generate(9)
    gen.generate(None)
    assert gen.generate(5).fingerprint_sha256 == first
    assert gen.generate(None).fingerprint_sha256 == gen.generate(42).fingerprint_sha256


def test_inv002_same_seed_different_sizes_stay_disjoint(env: Any) -> None:
    """INV-001/INV-002: cùng seed, khác kích thước tập vẫn giao rỗng giữa train và test."""
    for n_train, n_test in [(10, 5), (200, 50), (7, 300)]:
        pair = _generator(env.model, n_train=n_train, n_test=n_test).generate(11)
        _assert_inv001(env.model, pair, 0.02)


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-005: seed numpy.int64 làm TargetSetPair.to_dict() không serialize được"
)
def test_inv002_numpy_seed_record_is_json_serialisable(env: Any) -> None:
    """INV-002: bản ghi tập mục tiêu của seed numpy.int64 phải ghi JSON được, master_seed là int."""
    pair = _generator(env.model).generate(np.int64(7))  # type: ignore[arg-type]
    assert type(pair.master_seed) is int
    assert json.loads(json.dumps(pair.to_dict()))["master_seed"] == 7


# --------------------------------------------------------------------------------------
# INV-003
# --------------------------------------------------------------------------------------

_ALLOWED_PUBLIC_CALLABLES = {
    "reset",
    "step",
    "close",
    "render",
    "model_record",
    "get_wrapper_attr",
    "has_wrapper_attr",
    "set_wrapper_attr",
}


def test_inv003_public_surface_has_no_state_writing_entry_point() -> None:
    """INV-003: bề mặt công khai của env/gói environment không có hàm ghi qpos/qvel/ctrl/xpos."""
    e = ElbowReachEnv()
    callables = {
        name
        for name in dir(e)
        if not name.startswith("_") and callable(getattr(e, name)) and name != "unwrapped"
    }
    unexpected = callables - _ALLOWED_PUBLIC_CALLABLES
    assert not unexpected, f"INV-003: hàm công khai ngoài danh mục: {sorted(unexpected)}"
    import mma_ai.environment as pkg

    banned = ("set_", "write", "teleport", "force", "apply", "qpos", "qvel", "xpos", "ctrl")
    for name in dir(pkg):
        if name.startswith("_") or name.isupper():
            continue
        assert not any(b in name.lower() for b in banned), f"INV-003: {name}"
    sig_params = set(e.reset.__code__.co_varnames[: e.reset.__code__.co_argcount])
    assert sig_params == {"self", "seed", "options"}


def test_inv003_reset_options_cannot_write_state() -> None:
    """INV-003: khoá lạ trong options (qpos/qvel/ctrl/act/site_xpos) bị bỏ qua, không ghi."""
    e = ElbowReachEnv()
    options = {
        "qpos": [1.5],
        "qvel": [9.0],
        "ctrl": [1.0] * 6,
        "act": [1.0] * 6,
        "site_xpos": [0.0, 0.0, 0.0],
        "split": "train",
    }
    e.reset(seed=1, options=options)
    assert float(e.data.qpos[0]) == 0.0 and float(e.data.qvel[0]) == 0.0
    assert not np.any(e.data.act) and not np.any(e.data.ctrl)


def test_inv003_step_equals_independent_ctrl_only_simulation() -> None:
    """INV-003: quỹ đạo env trùng khít mô phỏng độc lập chỉ ghi ctrl => step không ghi gì khác."""
    e = ElbowReachEnv()
    e.reset(seed=4)
    ref = mujoco.MjData(e.model)
    mujoco.mj_resetData(e.model, ref)
    rng = np.random.default_rng(0)
    for _ in range(12):
        u = rng.uniform(0.0, 1.0, size=6)
        e.step(u)
        ref.ctrl[:] = u
        for _ in range(e.cfg.substeps_per_action):
            mujoco.mj_step(e.model, ref)
        assert np.array_equal(e.data.qpos, ref.qpos)
        assert np.array_equal(e.data.qvel, ref.qvel)
        assert np.array_equal(e.data.act, ref.act)


def _model_with_extra_actuator(kind: str) -> Any:
    spec = mujoco.MjSpec.from_file(str(myo_sim.get_xml_path("myoelbow")))
    act = spec.add_actuator()
    act.name = "challenge_extra"
    act.target = "r_elbow_flex"
    act.trntype = mujoco.mjtTrn.mjTRN_JOINT
    if kind == "position":
        act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        act.gainprm[0] = 10.0
        act.biasprm[1] = -10.0
    elif kind == "velocity":
        act.gaintype = mujoco.mjtGain.mjGAIN_FIXED
        act.biastype = mujoco.mjtBias.mjBIAS_AFFINE
        act.gainprm[0] = 5.0
        act.biasprm[2] = -5.0
    return spec.compile()


@pytest.mark.parametrize("kind", ["motor", "position", "velocity"])  # type: ignore[untyped-decorator]
def test_inv003_model_with_extra_non_muscle_actuator_is_refused(kind: str) -> None:
    """INV-003: mô hình có thêm motor/position/velocity actuator => từ chối khởi tạo."""
    with pytest.raises(ModelError):
        ElbowReachEnv(model=_model_with_extra_actuator(kind))


def test_inv003_model_missing_a_muscle_is_refused() -> None:
    """INV-003/FR-001: thiếu một cơ (5 cơ) => từ chối khởi tạo."""
    spec = mujoco.MjSpec.from_file(str(myo_sim.get_xml_path("myoelbow")))
    spec.delete(spec.actuators[0])
    with pytest.raises(ModelError):
        ElbowReachEnv(model=spec.compile())


# --------------------------------------------------------------------------------------
# INV-004
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "bad",
    [
        np.full(6, 1e30),
        np.full(6, -1e30),
        np.full(6, np.nan),
        np.full(6, np.inf),
        np.full(6, -np.inf),
        np.array([0.5, 0.5, 0.5, 0.5, 0.5, np.nan]),
        np.array([0.5, 0.5, 0.5, 0.5, 0.5, 1e30]),
        np.full(6, np.finfo(np.float64).max),
        np.full(6, np.nextafter(np.float32(1.0), np.float32(2.0)), dtype=np.float32),
        np.full(6, -1e-30),
        np.ma.masked_array(
            np.array([np.nan] + [0.5] * 5),
            mask=np.array([True, False, False, False, False, False]),
        ),
        np.ma.masked_array(np.zeros(6), mask=np.ones(6, dtype=bool)),
        [1e30] * 6,
        [float("nan")] * 6,
        np.full(7, 0.5),
        np.full(5, 0.5),
        np.array([]),
        np.array([0.5] * 6, dtype=object),
        np.ones(6, dtype=bool),
        "abcdef",
        {i: 0.5 for i in range(6)},
        None,
    ],
)
def test_inv004_hostile_actions_rejected_without_advancing_state(bad: Any) -> None:
    """INV-004: hành động ±1e30/NaN/Inf/sai kiểu bị ActivationError; trạng thái không bị chạm."""
    e, twin = ElbowReachEnv(), ElbowReachEnv()
    e.reset(seed=2)
    twin.reset(seed=2)
    with pytest.raises(ActivationError):
        e.step(bad)
    assert e._n_actions == 0
    obs, reward, *_ = e.step(_U_HALF)
    twin_obs, twin_reward, *_ = twin.step(_U_HALF)
    assert np.array_equal(obs, twin_obs) and reward == twin_reward


def test_inv004_state_perturbation_sweep_error_or_valid_observation() -> None:
    """INV-004: nhiễu qpos/qvel/act/NaN giữa episode => lỗi rõ ràng HOẶC obs hợp lệ."""
    rng = np.random.default_rng(2026)
    magnitudes = [0.0, 1e-3, 1.0, 3.0, 10.0, 1e2, 1e3, 1e5, 1e8, 1e10, 1e15, 1e30]
    fields = ["qpos", "qvel", "act"]
    outcomes = {"error": 0, "valid": 0}
    e = ElbowReachEnv()
    for trial in range(180):
        e.reset(seed=int(rng.integers(0, 1000)))
        field = fields[trial % 3]
        sign = rng.choice([-1.0, 1.0])
        value = float(sign * magnitudes[(trial // 3) % len(magnitudes)])
        if trial % 11 == 0:
            value = float(rng.choice([np.nan, np.inf, -np.inf]))
        getattr(e.data, field)[0] = value
        for _ in range(3):
            action = rng.uniform(0.0, 1.0, size=6)
            try:
                obs, reward, terminated, truncated, _ = e.step(action)
            except (PhysicsInstabilityError, ObservationError):
                outcomes["error"] += 1
                continue
            except EnvStateError:  # episode đã kết thúc ở bước trước: lỗi rõ ràng, dừng vòng
                break
            outcomes["valid"] += 1
            assert obs.shape == (14,) and obs.dtype == np.float32
            assert np.isfinite(obs).all(), f"INV-004: {field}={value} trả obs không hữu hạn"
            assert e.observation_space.contains(obs), f"INV-004: {field}={value} obs ngoài cận"
            assert np.isfinite(reward)
            if terminated or truncated:
                break
    assert outcomes["error"] > 0 and outcomes["valid"] > 0


def test_inv004_reset_after_instability_recovers_clean_state() -> None:
    """INV-004: sau lỗi mất ổn định, reset() phục hồi trạng thái sạch và obs hợp lệ."""
    e = ElbowReachEnv()
    e.reset(seed=1)
    e.data.qvel[0] = np.nan
    with pytest.raises(PhysicsInstabilityError):
        e.step(_U_HALF)
    obs, _ = e.reset(seed=1)
    assert np.isfinite(obs).all() and e.observation_space.contains(obs)
    obs2, *_ = e.step(_U_HALF)
    assert np.isfinite(obs2).all() and e.observation_space.contains(obs2)


def test_inv004_long_random_rollouts_stay_in_bounds() -> None:
    """INV-004: rollout ngẫu nhiên dài, các góc cực (0/1 biên) không vượt cận khai báo."""
    e = ElbowReachEnv()
    rng = np.random.default_rng(7)
    for ep in range(6):
        e.reset(seed=ep)
        done = False
        steps = 0
        while not done and steps < 100:
            if ep % 2:
                action = rng.choice([0.0, 1.0], size=6)
            else:
                action = rng.uniform(0.0, 1.0, size=6)
            obs, reward, terminated, truncated, _ = e.step(action)
            assert e.observation_space.contains(obs) and np.isfinite(reward)
            done = terminated or truncated
            steps += 1


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-006: validate_observation cho lọt giá trị vượt cận tới 1e-5 (tolerance)"
)
def test_inv004_validate_observation_rejects_value_outside_declared_bounds(env: Any) -> None:
    """INV-004: giá trị 1,500005 vượt cận 1,5 phải bị chặn hoặc obs trả ra thuộc không gian."""
    obs = np.zeros(14, dtype=np.float32)
    obs[0] = np.float32(1.500005)
    try:
        returned = validate_observation(obs, env.layout)
    except ObservationError:
        return
    assert env.observation_space.contains(returned)


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    strict=False, reason="F-007: hành động complex bị bỏ phần ảo âm thầm, không ActivationError"
)
def test_inv004_complex_action_is_rejected() -> None:
    """INV-004: hành động số phức 0,5+9j không được cắt phần ảo rồi chạy tiếp."""
    e = ElbowReachEnv()
    e.reset(seed=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ActivationError):
            e.step(np.array([0.5 + 9j] * 6))
