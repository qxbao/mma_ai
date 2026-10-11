"""Thử thách bất biến (challenge) INV-001/003/004/005/006 của đánh giá policy (T425).

Mỗi test nhắm một bất biến của sản phẩm qua đầu vào mà người dùng/hệ thống gặp được: tệp cấu hình
`--config`, cờ CLI, hồ sơ `manifest.json` của con 2, hành động của policy, ngắt/lỗi ghi đĩa.
Ca đỏ (finding) mang `xfail` KHÔNG strict với mã F-NNN trong `reason` khi còn chưa sửa; ca xanh là
vector đã thử mà không lách được (ghi vào `disproved_hypotheses`). Vòng 2: mọi finding vòng 1 đã
được sửa nên dấu `xfail` đã gỡ, các ca nay là hồi quy (regression) xanh.

- INV-001 (AC-4): tập đánh giá không giao tập train — mục tiêu, seed, chuỗi run cha, hồ sơ thiếu.
- INV-003 (AC-1): hành động tới `env.step` luôn hữu hạn, thuộc `[0,1]^6`, đúng chiều.
- INV-004 (AC-5): lỗi/ngắt ở mọi bước 1…8 không để lại bản ghi trông hợp lệ hay `.tmp-*`.
- INV-005 (AC-1): đánh giá chỉ đọc với run của con 2, không ghi đè kết quả cũ.
- INV-006 (AC-2): tiêu chí kết luận không đổi theo cờ/ghi đè, báo cáo ghi nguyên văn tiêu chí.

Harness dùng đối tượng giả (mock) cho checkpoint/policy học được để chạy được khi không có torch;
phần nặng (sinh mục tiêu, rollout) được lưu đệm một lần cho cả module.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import warnings
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import yaml
from eval_fixtures import ScriptedZeroPolicy, make_run_dir

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.environment.targets import Target, TargetGenerator, TargetSet, TargetSetPair
from mma_ai.evaluation import cli, report, runner
from mma_ai.evaluation.errors import (
    EvalConfigError,
    EvalError,
    EvalWriteError,
    LeakageError,
    TrainSetUnknown,
)
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.rollout import EpisodeRecord, run_policy_on_targets
from mma_ai.evaluation.split_guard import DisjointnessReport, check_disjoint
from mma_ai.physics.body_model import load_muscle_model

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_YAML = _REPO_ROOT / "src" / "mma_ai" / "environment" / "elbow_env.yaml"
_N_EVAL = 50


# --------------------------------------------------------------------------------------
# Harness dùng chung
# --------------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Cache:
    """Đối tượng nặng dựng một lần cho cả module (chỉ đọc)."""

    pair: TargetSetPair
    env_cfg: ElbowEnvConfig
    model_sha256: str
    records: list[EpisodeRecord]
    disjoint: DisjointnessReport


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def cache(tmp_path_factory: pytest.TempPathFactory) -> Iterator[_Cache]:
    """Sinh cặp mục tiêu mặc định và một bộ episode thật (chạy một lần)."""
    warnings.simplefilter("ignore")
    body = load_muscle_model("myoelbow")
    env_cfg = ElbowEnvConfig.load(_ENV_YAML)
    pair = TargetGenerator(
        model=body.model, cfg=env_cfg, model_sha256=body.info.sha256
    ).generate(seed=env_cfg.targets.default_seed)
    env = ElbowReachEnv(cfg=env_cfg, targets=pair, split="test")
    records = run_policy_on_targets(
        env=env,
        policy=ScriptedZeroPolicy(),
        n_targets=len(pair.test),
        repeats=1,
        seed_base=12345,
        policy_name="learned",
    )
    run_dir = make_run_dir(tmp_path_factory.mktemp("t425_cache") / "run_cache", seed=42)
    disjoint = check_disjoint(run_dir, EvalConfig.load(), pair)
    yield _Cache(pair, env_cfg, body.info.sha256, records, disjoint)


@dataclasses.dataclass
class _World:
    """Một run mẫu + các lời gọi đã ghi lại khi chạy `evaluate_checkpoint`."""

    run_dir: Path
    ckpt: Path
    calls: dict[str, int]

    @property
    def eval_dir(self) -> Path:
        return self.run_dir / "eval"

    def residue(self) -> list[str]:
        """Tên mọi mục trong `eval/` (kết quả hoặc `.tmp-*`)."""
        if not self.eval_dir.exists():
            return []
        return sorted(p.name for p in self.eval_dir.iterdir())


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    cache: _Cache,
    calls: dict[str, int],
    ckpt_seed: int = 42,
    fast_split: bool = True,
) -> None:
    """Thay checkpoint/policy học được và (tuỳ chọn) các bước nặng bằng bản lưu đệm."""
    monkeypatch.chdir(_REPO_ROOT)
    warnings.simplefilter("ignore")

    def fake_load(path: Any, for_training: bool = False) -> Any:
        calls["load_checkpoint"] = calls.get("load_checkpoint", 0) + 1
        return SimpleNamespace(
            model_sha256=cache.model_sha256,
            update_idx=1,
            env_steps=10,
            library_versions={},
            seed=ckpt_seed,
        )

    monkeypatch.setattr("mma_ai.learning.checkpoint.load_checkpoint", fake_load)
    monkeypatch.setattr(runner, "LearnedPolicy", lambda p: ScriptedZeroPolicy())
    # Bước 7 không phụ thuộc pandas/matplotlib: đọc nhật ký giả, vẽ biểu đồ giả "không có đồ họa".
    monkeypatch.setattr(runner, "read_training_log", lambda run_dir, cfg: object())

    def fake_render(log: Any, muscle_names: Any, out_dir: Path, cfg: Any) -> Any:
        raise RuntimeError("không có đồ họa trong harness")

    monkeypatch.setattr(runner, "render_charts", fake_render)

    def fake_rollout(**kw: Any) -> list[EpisodeRecord]:
        calls["rollout"] = calls.get("rollout", 0) + 1
        return [dataclasses.replace(r, policy=kw["policy_name"]) for r in cache.records]

    monkeypatch.setattr(runner, "run_policy_on_targets", fake_rollout)

    if fast_split:
        def fake_check(run: Any, cfg: Any, pair: Any = None) -> DisjointnessReport:
            calls["check_disjoint"] = calls.get("check_disjoint", 0) + 1
            return cache.disjoint

        class _CachedGen:
            def __init__(self, **kw: Any) -> None:
                pass

            def generate(self, seed: int) -> TargetSetPair:
                return cache.pair

        monkeypatch.setattr(runner, "check_disjoint", fake_check)
        monkeypatch.setattr(runner, "TargetGenerator", _CachedGen)


@pytest.fixture  # type: ignore[untyped-decorator]
def world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cache: _Cache
) -> _World:
    """Run mẫu seed 42 với checkpoint/policy giả, các bước nặng lấy từ đệm."""
    calls: dict[str, int] = {}
    _install_fakes(monkeypatch, cache, calls)
    run_dir = make_run_dir(tmp_path / "run_w", seed=42)
    return _World(run_dir, run_dir / "checkpoints" / "latest.json", calls)


def _snapshot(run_dir: Path) -> dict[str, str]:
    """Băm mọi tệp của run NGOÀI `eval/` (phần của con 2 phải bất biến)."""
    snap: dict[str, str] = {}
    for p in sorted(run_dir.rglob("*")):
        rel = p.relative_to(run_dir)
        if rel.parts and rel.parts[0] == "eval":
            continue
        snap[rel.as_posix()] = (
            hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "<dir>"
        )
    return snap


def _tree_hash(root: Path) -> dict[str, str]:
    """Băm mọi tệp dưới `root` (dùng để chứng minh kết quả cũ không đổi)."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _rewrite_manifest(run_dir: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = run_dir / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _run_main(world: _World, *extra: str) -> int:
    return cli.main(["--checkpoint", str(world.ckpt), *extra])


# --------------------------------------------------------------------------------------
# INV-001 — tập đánh giá không giao tập train
# --------------------------------------------------------------------------------------


def _mini_manifest(seed: Any, resumed: Any = None) -> dict[str, Any]:
    return {
        "run_id": "r",
        "seed": seed,
        "resumed_from": resumed,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        "model": {},
    }


def _write_chain(root: Path, seeds: list[int]) -> Path:
    """Dựng chuỗi run: seeds[0] là run đánh giá, seeds[i+1] là cha của seeds[i]."""
    for i, seed in enumerate(seeds):
        parent = {"run_id": f"run{i + 1}"} if i + 1 < len(seeds) else None
        d = root / f"run{i}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.json").write_text(
            json.dumps(_mini_manifest(seed, parent)), encoding="utf-8"
        )
    return root / "run0"


def _cfg(**seeds: int) -> EvalConfig:
    cfg = EvalConfig.load()
    return dataclasses.replace(cfg, seeds=dataclasses.replace(cfg.seeds, **seeds))


@pytest.mark.parametrize("repeats", [1, 2, 3])  # type: ignore[untyped-decorator]
def test_inv001_seed_range_boundary_sweep(
    tmp_path: Path, cache: _Cache, repeats: int
) -> None:
    """AC-4/INV-001: quét `episode_base` quanh seed train — từ chối ĐÚNG khi dải giao seed."""
    train_seed = 400
    run_dir = _write_chain(tmp_path, [train_seed])
    n = _N_EVAL * repeats
    base_cfg = EvalConfig.load()
    cfg_r = dataclasses.replace(
        base_cfg, episodes=dataclasses.replace(base_cfg.episodes, repeats=repeats)
    )
    for base in range(train_seed - n - 3, train_seed + 4):
        cfg = dataclasses.replace(
            cfg_r, seeds=dataclasses.replace(cfg_r.seeds, episode_base=base, random_policy=9999)
        )
        overlap = base <= train_seed < base + n
        if overlap:
            with pytest.raises(LeakageError):
                check_disjoint(run_dir, cfg, cache.pair)
        else:
            rep = check_disjoint(run_dir, cfg, cache.pair)
            assert rep.eval_seed_range == (base, base + n)


def test_inv001_random_policy_seed_equal_train_rejected(tmp_path: Path, cache: _Cache) -> None:
    """AC-4/INV-001: seed random policy trùng seed train bị từ chối dù dải episode không giao."""
    run_dir = _write_chain(tmp_path, [400])
    with pytest.raises(LeakageError):
        check_disjoint(run_dir, _cfg(episode_base=100_000, random_policy=400), cache.pair)


def test_inv001_resume_chain_every_ancestor_seed_checked(tmp_path: Path, cache: _Cache) -> None:
    """AC-4/INV-001: seed của MỌI tổ tiên trong chuỗi `resumed_from` (độ sâu 5) đều bị kiểm."""
    seeds = [10, 20_000, 30_000, 40_000, 50_000]
    run_dir = _write_chain(tmp_path, seeds)
    for s in seeds:
        with pytest.raises(LeakageError):
            check_disjoint(run_dir, _cfg(episode_base=s - 7, random_policy=999_999), cache.pair)
        with pytest.raises(LeakageError):
            check_disjoint(run_dir, _cfg(episode_base=777_777, random_policy=s), cache.pair)
    rep = check_disjoint(run_dir, _cfg(episode_base=777_777, random_policy=888_888), cache.pair)
    assert set(rep.train_seeds) == set(seeds)


def test_inv001_resume_cycle_terminates_and_still_checks(tmp_path: Path, cache: _Cache) -> None:
    """INV-001: chuỗi cha vòng tròn (A→B→A) không treo và vẫn kiểm seed của cả hai."""
    for name, seed, parent in (("a", 5, "b"), ("b", 600, "a")):
        d = tmp_path / name
        d.mkdir()
        (d / "manifest.json").write_text(
            json.dumps(_mini_manifest(seed, {"run_id": parent})), encoding="utf-8"
        )
    with pytest.raises(LeakageError):
        check_disjoint(tmp_path / "a", _cfg(episode_base=600, random_policy=99_999), cache.pair)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "bad_seed", [None, True, False, -1, 4.5, "42", [], {}, float("nan")]
)
def test_inv001_bad_manifest_seed_refused(tmp_path: Path, cache: _Cache, bad_seed: Any) -> None:
    """FR-009/INV-001: seed hồ sơ sai kiểu/âm ⇒ TrainSetUnknown, không kiểm 'ngầm'."""
    run_dir = _write_chain(tmp_path, [1])
    (run_dir / "manifest.json").write_text(
        json.dumps(_mini_manifest(bad_seed), allow_nan=True), encoding="utf-8"
    )
    with pytest.raises(TrainSetUnknown):
        check_disjoint(run_dir, EvalConfig.load(), cache.pair)


@pytest.mark.parametrize("missing", ["seed", "config", "env_config", "manifest"])  # type: ignore[untyped-decorator]
def test_inv001_missing_manifest_field_never_runs_episode(
    world: _World, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    """AC-4/FR-009: hồ sơ thiếu từng trường ⇒ thoát khác 0, không episode, không bản ghi."""

    def mutate(d: dict[str, Any]) -> None:
        if missing == "env_config":
            del d["config"]["env_config"]
        else:
            d.pop(missing, None)

    if missing == "manifest":
        (world.run_dir / "manifest.json").unlink()
    else:
        _rewrite_manifest(world.run_dir, mutate)
    # Dùng split guard THẬT để chứng minh bước 4 chặn trước episode đầu.
    monkeypatch.setattr(runner, "check_disjoint", check_disjoint)
    code = _run_main(world)
    assert code != 0
    assert world.calls.get("rollout", 0) == 0
    assert world.residue() == []


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "which", ["ckpt_hash", "manifest_hash"]
)
def test_inv001_xml_hash_mismatch_never_runs_episode(
    world: _World, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    """INV-002/004: hash XML lệch giữa checkpoint/hồ sơ và mô hình ⇒ mã 4, không episode."""
    if which == "manifest_hash":
        _rewrite_manifest(world.run_dir, lambda d: d["model"].update(sha256="0" * 64))
    else:
        monkeypatch.setattr(
            "mma_ai.learning.checkpoint.load_checkpoint",
            lambda p, for_training=False: SimpleNamespace(
                model_sha256="f" * 64, update_idx=1, env_steps=1, library_versions={}, seed=42
            ),
        )
    assert _run_main(world) == 4
    assert world.calls.get("rollout", 0) == 0
    assert world.residue() == []


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "delta", [-1e-6, -1e-4, -0.005]
)
def test_inv001_target_below_min_distance_rejected(
    cache: _Cache, tmp_path: Path, delta: float
) -> None:
    """AC-4/INV-001: mục tiêu đánh giá cách train < min_separation (quét ε) bị từ chối."""
    run_dir = _write_chain(tmp_path, [1])
    min_sep = float(cache.pair.config["min_separation_m"])
    anchor = cache.pair.train[0].position_m
    probe = Target(
        index=0,
        angle_rad=0.0,
        position_m=(anchor[0] + min_sep + delta, anchor[1], anchor[2]),
    )
    # khoảng cách thực = min_sep + delta (delta âm ⇒ sát biên bên trong)
    far = tuple(cache.pair.test.targets[1:])
    pair = dataclasses.replace(
        cache.pair, test=TargetSet(role="test", targets=(probe, *far))
    )
    d = min(math.dist(probe.position_m, t.position_m) for t in pair.train)
    if d >= min_sep:
        pytest.skip("mục tiêu dò rơi vào khoảng cách hợp lệ so với train khác (fixture)")
    with pytest.raises(LeakageError):
        check_disjoint(run_dir, EvalConfig.load(), pair)


def test_inv001_target_exactly_at_min_distance_accepted(cache: _Cache, tmp_path: Path) -> None:
    """INV-001 (biên): mục tiêu đúng bằng min_separation so với MỌI train thì được chấp nhận."""
    run_dir = _write_chain(tmp_path, [1])
    min_sep = float(cache.pair.config["min_separation_m"])
    # Dời mục tiêu ra xa train một đoạn rất lớn rồi kiểm không bị từ chối oan.
    far_target = Target(index=0, angle_rad=0.0, position_m=(9.0, 9.0, 9.0))
    pair = dataclasses.replace(
        cache.pair, test=TargetSet(role="test", targets=(far_target,))
    )
    rep = check_disjoint(run_dir, EvalConfig.load(), pair)
    assert rep.min_cross_distance_m >= min_sep


def _env_variant(tmp_path: Path, **targets: Any) -> Path:
    data = yaml.safe_load(_ENV_YAML.read_text(encoding="utf-8"))
    data["targets"].update(targets)
    out = tmp_path / f"env_{abs(hash(str(sorted(targets.items()))))}.yaml"
    out.write_text(yaml.safe_dump(data), encoding="utf-8")
    return out


def test_inv001_env_override_cannot_move_eval_set_off_the_runs_train_set(
    tmp_path: Path, cache: _Cache
) -> None:
    """AC-4/INV-001 (+INV-002): tập đánh giá dựng từ `env_config_override` khác run phải bị chặn,
    hoặc ít nhất tập đánh giá thực dùng KHÔNG được chồng lên tập train THẬT của run."""
    run_dir = make_run_dir(tmp_path / "run_o", seed=42)
    override = _env_variant(tmp_path, default_seed=7)
    base = EvalConfig.load()
    cfg = dataclasses.replace(
        base, paths=dataclasses.replace(base.paths, env_config_override=str(override))
    )
    body = load_muscle_model("myoelbow")
    env_cfg = ElbowEnvConfig.load(override)
    used = TargetGenerator(
        model=body.model, cfg=env_cfg, model_sha256=body.info.sha256
    ).generate(seed=env_cfg.targets.default_seed)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            check_disjoint(run_dir, cfg)
    except EvalError:
        return  # bị chặn đúng hợp đồng
    min_sep = float(cache.pair.config["min_separation_m"])
    dmin = min(
        math.dist(a.position_m, b.position_m) for a in cache.pair.train for b in used.test
    )
    assert dmin >= min_sep, (
        f"tập đánh giá từ override cách train THẬT chỉ {dmin:.6f} m < {min_sep} m "
        "nhưng check_disjoint vẫn passed"
    )


@pytest.mark.parametrize("bad", ["run1", 7, ["run1"]])  # type: ignore[untyped-decorator]
def test_inv001_malformed_resumed_from_refused(tmp_path: Path, cache: _Cache, bad: Any) -> None:
    """FR-009/INV-001: `resumed_from` sai cấu trúc ⇒ không thiết lập được chuỗi train ⇒ từ chối."""
    d = tmp_path / "run0"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(_mini_manifest(5, bad)), encoding="utf-8")
    with pytest.raises(TrainSetUnknown):
        check_disjoint(d, _cfg(episode_base=777_777, random_policy=888_888), cache.pair)


def test_inv001_checkpoint_seed_must_match_manifest_seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cache: _Cache
) -> None:
    """AC-4/INV-001: checkpoint huấn luyện bằng seed trùng seed đánh giá không được lọt chỉ vì
    nằm cạnh hồ sơ của run khác (seed hồ sơ 42, seed trong checkpoint 12345 = seed đánh giá)."""
    calls: dict[str, int] = {}
    _install_fakes(monkeypatch, cache, calls, ckpt_seed=12345, fast_split=False)
    import mma_ai.evaluation.split_guard as sg

    monkeypatch.setattr(
        runner,
        "check_disjoint",
        lambda run, cfg, pair=None: sg.check_disjoint(run, cfg, cache.pair),
    )
    monkeypatch.setattr(
        runner,
        "TargetGenerator",
        type(
            "G",
            (),
            {"__init__": lambda self, **k: None, "generate": lambda self, seed: cache.pair},
        ),
    )
    run_dir = make_run_dir(tmp_path / "run_s", seed=42)
    code = cli.main(["--checkpoint", str(run_dir / "checkpoints" / "latest.json")])
    assert code in (4, 5), f"đánh giá checkpoint seed 12345, eval seed 12345 ra mã {code}"
    assert calls.get("rollout", 0) == 0


# --------------------------------------------------------------------------------------
# INV-003 — hành động tới env.step luôn hợp lệ
# --------------------------------------------------------------------------------------


class _SpyEnv:
    """Môi trường giả ghi lại mọi hành động nhận được ở `step`."""

    def __init__(self, horizon: int = 3) -> None:
        self.horizon = horizon
        self.seen: list[np.ndarray] = []
        self._t = 0

    def reset(self, seed: int | None = None, options: Any = None) -> tuple[Any, dict[str, Any]]:
        self._t = 0
        return np.zeros(14), {}

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        self.seen.append(np.array(action, dtype=object, copy=True))
        self._t += 1
        info = {"distance_m": 0.1, "reached": False, "end_reason": None}
        return np.zeros(14), 0.0, False, self._t >= self.horizon, info


class _ScriptPolicy:
    """Policy giả trả về chuỗi hành động cho sẵn (lặp lại phần tử cuối)."""

    def __init__(self, actions: list[Any]) -> None:
        self.actions = actions
        self.i = 0

    def act(self, obs: Any) -> Any:
        a = self.actions[min(self.i, len(self.actions) - 1)]
        self.i += 1
        return a


_BAD_ACTIONS: list[tuple[str, Any]] = [
    ("nan_all", np.full(6, np.nan)),
    ("nan_one", np.array([0.5, 0.5, np.nan, 0.5, 0.5, 0.5])),
    ("inf_pos", np.array([np.inf, 0.1, 0.1, 0.1, 0.1, 0.1])),
    ("inf_neg", np.array([0.1, -np.inf, 0.1, 0.1, 0.1, 0.1])),
    ("neg_tiny", np.array([-1e-12, 0.1, 0.1, 0.1, 0.1, 0.1])),
    ("gt1_tiny", np.array([0.1, 1.0 + 1e-12, 0.1, 0.1, 0.1, 0.1])),
    ("gt1_f32", np.array([1.0000001] * 6, dtype=np.float32)),
    ("huge", np.array([1e308] * 6)),
    ("neg", np.array([-1.0] * 6)),
    ("len5", np.full(5, 0.5)),
    ("len7", np.full(7, 0.5)),
    ("len0", np.zeros(0)),
    ("scalar", np.float64(0.5)),
    ("none", None),
    ("str", "abc"),
    ("ragged", [[0.1, 0.2], [0.3]]),
    ("dict", {"a": 0.5}),
    ("nested_nan", [[0.5, 0.5, 0.5], [0.5, math.nan, 0.5]]),
]


def _assert_only_valid_actions_reached_step(env: _SpyEnv) -> None:
    for a in env.seen:
        arr = np.asarray(a, dtype=np.float64)
        assert arr.shape == (6,), f"env.step nhận hành động sai chiều {arr.shape}"
        assert bool(np.all(np.isfinite(arr))), f"env.step nhận hành động không hữu hạn {arr}"
        in_box = bool(np.all((arr >= 0.0) & (arr <= 1.0)))
        assert in_box, f"env.step nhận hành động ngoài [0,1]: {arr}"


@pytest.mark.parametrize("name,action", _BAD_ACTIONS, ids=[n for n, _ in _BAD_ACTIONS])  # type: ignore[untyped-decorator]
def test_inv003_bad_action_never_reaches_step(name: str, action: Any) -> None:
    """AC-1/INV-003: hành động hỏng bị chặn tại biên; episode đếm bất thường, lượt không sụp."""
    env = _SpyEnv()
    recs = run_policy_on_targets(
        env=env, policy=_ScriptPolicy([action]), n_targets=2, repeats=2, seed_base=1,
        policy_name="learned",
    )
    assert len(recs) == 4
    assert env.seen == [], f"{name}: hành động hỏng vẫn tới env.step"
    assert all(r.abnormal and r.end_reason == "abnormal_action" and not r.reached for r in recs)
    assert all(r.final_distance_m is None for r in recs)


def test_inv003_nan_inf_counters_increment() -> None:
    """INV-003: số NaN/Inf tăng đúng theo số phần tử hỏng (spec edge case dòng 200)."""
    act = np.array([np.nan, np.inf, -np.inf, 0.5, 0.5, 0.5])
    recs = run_policy_on_targets(
        env=_SpyEnv(), policy=_ScriptPolicy([act]), n_targets=1, repeats=1, seed_base=1,
        policy_name="learned",
    )
    assert recs[0].nan_count == 1 and recs[0].inf_count == 2


@pytest.mark.parametrize("bad_at", [0, 1, 2])  # type: ignore[untyped-decorator]
def test_inv003_bad_action_midepisode_stops_before_step(bad_at: int) -> None:
    """INV-003: hành động hỏng ở bước k dừng episode TRƯỚC `env.step`; các bước trước hợp lệ."""
    good = np.full(6, 0.25)
    seq: list[Any] = [good] * bad_at + [np.full(6, np.nan)]
    env = _SpyEnv(horizon=10)
    recs = run_policy_on_targets(
        env=env, policy=_ScriptPolicy(seq), n_targets=1, repeats=1, seed_base=1,
        policy_name="learned",
    )
    assert len(env.seen) == bad_at
    _assert_only_valid_actions_reached_step(env)
    assert recs[0].abnormal and recs[0].n_steps == bad_at and not recs[0].reached


def test_inv003_boundary_valid_actions_not_falsely_rejected() -> None:
    """INV-003 (biên): 0, 1, -0.0, bool, int, float32 đúng biên được chạy bình thường."""
    cases: list[Any] = [
        np.zeros(6), np.ones(6), np.full(6, -0.0), np.array([True] * 6),
        np.array([0, 1, 0, 1, 0, 1]), np.array([1.0] * 6, dtype=np.float32),
        [[0.5] * 6], np.full((6, 1), 0.5), np.full((1, 6), 0.5),
    ]
    for act in cases:
        env = _SpyEnv(horizon=2)
        recs = run_policy_on_targets(
            env=env, policy=_ScriptPolicy([act]), n_targets=1, repeats=1, seed_base=1,
            policy_name="learned",
        )
        assert not recs[0].abnormal and len(env.seen) == 2
        _assert_only_valid_actions_reached_step(env)


def test_inv003_shape_fuzz_only_valid_reaches_step() -> None:
    """INV-003 (fuzz, seed cố định): hỗn hợp chiều/giá trị — bất biến ở `env.step` luôn đúng."""
    rng = np.random.default_rng(20261011)
    shapes: list[tuple[int, ...]] = [
        (6,), (5,), (7,), (2, 3), (3, 2), (6, 1), (1, 6), (), (0,), (2, 6),
    ]
    specials = [np.nan, np.inf, -np.inf, -1e-9, 1.0 + 1e-9, 5.0, -5.0, 0.0, 1.0, 0.5]
    for _ in range(300):
        shape = shapes[int(rng.integers(len(shapes)))]
        arr = rng.uniform(-0.2, 1.2, size=shape)
        if arr.size and rng.random() < 0.5:
            flat = arr.reshape(-1)
            flat[int(rng.integers(flat.size))] = specials[int(rng.integers(len(specials)))]
        env = _SpyEnv(horizon=2)
        run_policy_on_targets(
            env=env, policy=_ScriptPolicy([arr]), n_targets=1, repeats=1, seed_base=1,
            policy_name="learned",
        )
        _assert_only_valid_actions_reached_step(env)


def test_inv003_complex_action_imaginary_nan_not_silently_dropped() -> None:
    """INV-003: hành động phức có phần ảo NaN không được lặng lẽ cắt phần ảo rồi chạy."""
    act = np.array([complex(0.5, math.nan)] * 6)
    env = _SpyEnv()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run_policy_on_targets(
            env=env, policy=_ScriptPolicy([act]), n_targets=1, repeats=1, seed_base=1,
            policy_name="learned",
        )
    assert env.seen == []


@pytest.mark.xfail(  # type: ignore[untyped-decorator]
    reason="F-008: nhánh object-dtype của rollout chỉ nhận diện `complex` thuần Python; "
    "np.complex64 trong mảng object bị float() cắt phần ảo ⇒ NaN ảo tới env.step",
    strict=False,
)
def test_inv003_object_array_of_numpy_complex64_nan_imag_not_dropped() -> None:
    """INV-003: mảng object chứa np.complex64 phần ảo NaN không được cắt ảo rồi chạy."""
    act = np.empty(6, dtype=object)
    for i in range(6):
        act[i] = np.complex64(complex(0.5, math.nan))
    env = _SpyEnv()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run_policy_on_targets(
            env=env, policy=_ScriptPolicy([act]), n_targets=1, repeats=1, seed_base=1,
            policy_name="learned",
        )
    assert env.seen == []


# --------------------------------------------------------------------------------------
# INV-004 — lỗi/ngắt không để lại bản ghi trông hợp lệ
# --------------------------------------------------------------------------------------


def _boom(exc: BaseException) -> Callable[..., Any]:
    def raiser(*a: Any, **k: Any) -> Any:
        raise exc

    return raiser


_STAGE_FAULTS: list[tuple[str, str, BaseException]] = [
    ("2_load_checkpoint", "mma_ai.learning.checkpoint.load_checkpoint", RuntimeError("hỏng")),
    ("4_check_disjoint", "runner.check_disjoint", LeakageError("rò rỉ")),
    ("5_rollout", "runner.run_policy_on_targets", RuntimeError("lỗi môi trường")),
    ("5_rollout_ctrlc", "runner.run_policy_on_targets", KeyboardInterrupt()),
    ("6_summarize", "runner.summarize", RuntimeError("thống kê")),
    ("6_decide", "runner.decide", RuntimeError("kết luận")),
    ("6_decide_ctrlc", "runner.decide", KeyboardInterrupt()),
    ("7_render_ctrlc", "runner.render_charts", KeyboardInterrupt()),
    ("7_read_log_ctrlc", "runner.read_training_log", KeyboardInterrupt()),
    ("8_build_report", "runner.build_report", ValueError("NaN trong báo cáo")),
    ("8_build_report_ctrlc", "runner.build_report", KeyboardInterrupt()),
    ("8_save", "runner.save_evaluation_result", EvalWriteError("đĩa đầy")),
    ("8_save_ctrlc", "runner.save_evaluation_result", KeyboardInterrupt()),
    ("8_publish", "runner.publish_report", EvalWriteError("không đổi tên")),
    ("8_publish_ctrlc", "runner.publish_report", KeyboardInterrupt()),
]


def _patch_target(monkeypatch: pytest.MonkeyPatch, dotted: str, fn: Callable[..., Any]) -> None:
    if dotted.startswith("runner."):
        monkeypatch.setattr(runner, dotted.split(".", 1)[1], fn)
    else:
        monkeypatch.setattr(dotted, fn)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "label,target,exc", _STAGE_FAULTS, ids=[s[0] for s in _STAGE_FAULTS]
)
def test_inv004_fault_at_every_stage_leaves_no_record(
    world: _World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    label: str,
    target: str,
    exc: BaseException,
) -> None:
    """AC-5/INV-004: lỗi/ngắt ở mỗi bước 1…8 ⇒ mã khác 0, không in kết quả, không bản ghi, không
    `.tmp-*` còn lại, run của con 2 không đổi."""
    before = _snapshot(world.run_dir)
    _patch_target(monkeypatch, target, _boom(exc))
    code = _run_main(world)
    out = capsys.readouterr()
    assert code != 0, f"{label}: thoát 0 dù lỗi"
    if isinstance(exc, KeyboardInterrupt):
        assert code == 130
    assert out.out.strip() == "", f"{label}: in kết quả ra stdout dù lỗi: {out.out[:200]!r}"
    assert world.residue() == [], f"{label}: còn {world.residue()}"
    assert _snapshot(world.run_dir) == before


def test_inv004_interrupt_during_second_policy_leaves_no_record(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-004: ngắt khi policy thứ hai (random) đang chạy — nửa kết quả không được lộ ra."""
    real = run_policy_on_targets
    state = {"n": 0}

    def flaky(**kw: Any) -> Any:
        state["n"] += 1
        if state["n"] == 2:
            raise KeyboardInterrupt()
        return real(**kw)

    monkeypatch.setattr(runner, "run_policy_on_targets", flaky)
    assert _run_main(world) == 130
    assert world.residue() == []


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "exc", [SystemExit(3), GeneratorExit()], ids=["SystemExit", "GeneratorExit"]
)
@pytest.mark.parametrize("target", ["runner.run_policy_on_targets", "runner.render_charts"])  # type: ignore[untyped-decorator]
def test_inv004_baseexception_leaves_no_tmp(
    world: _World, monkeypatch: pytest.MonkeyPatch, target: str, exc: BaseException
) -> None:
    """INV-004: thoát khẩn (SystemExit/GeneratorExit) ở bước 5/7 không được để lại `.tmp-*`."""
    _patch_target(monkeypatch, target, _boom(exc))
    with pytest.raises(BaseException):
        _run_main(world)
    assert world.residue() == []


@pytest.mark.parametrize("how", ["eval_is_file", "readonly_run", "out_parent_is_file"])  # type: ignore[untyped-decorator]
def test_inv004_unwritable_destination_exits7_without_summary(
    world: _World, capsys: pytest.CaptureFixture[str], tmp_path: Path, how: str
) -> None:
    """AC-5/INV-004: đích không ghi được ⇒ mã 7, không in kết quả như thể đã lưu."""
    extra: tuple[str, ...] = ()
    if how == "eval_is_file":
        world.eval_dir.write_text("không phải thư mục", encoding="utf-8")
    elif how == "out_parent_is_file":
        blocker = tmp_path / "blocker"
        blocker.write_text("x", encoding="utf-8")
        extra = ("--out", str(blocker / "sub"))
    else:
        if os.geteuid() == 0:
            pytest.skip("root bỏ qua quyền ghi")
        world.run_dir.chmod(0o555)
    try:
        code = _run_main(world, *extra)
    finally:
        world.run_dir.chmod(0o755)
    out = capsys.readouterr()
    assert code == 7, f"{how}: mã {code}"
    assert out.out.strip() == ""
    if how != "eval_is_file":
        assert world.residue() == []


def test_inv004_disk_full_on_second_file_leaves_nothing(
    world: _World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """INV-004: đĩa đầy SAU khi `report.json` đã ghi (ghi `episodes.csv` lỗi) ⇒ mã 7, không dư."""
    def full(*a: Any, **k: Any) -> Any:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(report, "write_episodes_csv", full)
    code = _run_main(world)
    assert code == 7
    assert capsys.readouterr().out.strip() == ""
    assert world.residue() == []


def test_inv004_stale_tmp_dir_not_mixed_into_published_result(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-004/005: `.tmp-<id>` còn sót từ lượt bị giết không được trộn vào kết quả công bố."""
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return datetime(2026, 10, 11, 1, 2, 3, tzinfo=timezone.utc)

    monkeypatch.setattr(report, "datetime", _Frozen)
    stale = world.eval_dir / ".tmp-20261011T010203Z_e12345"
    stale.mkdir(parents=True)
    (stale / "STALE_FROM_KILLED_RUN.txt").write_text("cũ", encoding="utf-8")
    assert _run_main(world) in (0, 6)
    published = [p for p in world.eval_dir.iterdir() if not p.name.startswith(".tmp-")]
    assert len(published) == 1
    assert not (published[0] / "STALE_FROM_KILLED_RUN.txt").exists()


def test_inv004_chart_failure_after_partial_png_is_flagged_incomplete(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-004/FR-011: biểu đồ lỗi giữa chừng ⇒ báo cáo `incomplete` + mã 6, không giả hoàn tất."""
    def partial(log: Any, muscle_names: Any, out_dir: Path, cfg: Any) -> Any:
        (out_dir / "loss.png").write_bytes(b"\x89PNG partial")
        raise RuntimeError("vẽ dở")

    monkeypatch.setattr(runner, "render_charts", partial)
    assert _run_main(world) == 6
    (published,) = [p for p in world.eval_dir.iterdir()]
    rep = json.loads((published / "report.json").read_text(encoding="utf-8"))
    assert rep["charts"]["status"] == "incomplete"
    assert rep["status"] == "done_charts_incomplete"


# --------------------------------------------------------------------------------------
# INV-005 — chỉ đọc với run của con 2, không ghi đè kết quả cũ
# --------------------------------------------------------------------------------------


def test_inv005_success_leaves_run_files_untouched(world: _World) -> None:
    """AC-1/INV-005: đánh giá thành công không sửa tệp nào của run (hồ sơ, checkpoint, nhật ký)."""
    before = _snapshot(world.run_dir)
    assert _run_main(world) in (0, 6)
    assert _snapshot(world.run_dir) == before
    assert len(world.residue()) == 1


def test_inv005_two_runs_same_second_do_not_overwrite(
    world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-005: hai lượt trùng giây (thời gian đóng băng) ⇒ hai thư mục khác nhau, lượt đầu giữ
    nguyên từng byte."""
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return datetime(2026, 10, 11, 1, 2, 3, tzinfo=timezone.utc)

    monkeypatch.setattr(report, "datetime", _Frozen)
    assert _run_main(world) in (0, 6)
    (first,) = world.residue()
    first_hash = _tree_hash(world.eval_dir / first)
    for k in range(3):
        assert _run_main(world, "--repeats", "1") in (0, 6)
        names = world.residue()
        assert len(names) == 2 + k and len(set(names)) == len(names)
        assert _tree_hash(world.eval_dir / first) == first_hash


def test_inv005_existing_nonempty_destination_is_not_overwritten(
    world: _World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """INV-005 (đua): id trùng đích đã có nội dung (hai tiến trình cùng giây) ⇒ mã 7, đích cũ
    không đổi và không để `.tmp-*`."""
    dest = world.eval_dir / "20261011T000000Z_e12345"
    dest.mkdir(parents=True)
    (dest / "report.json").write_text('{"old": true}', encoding="utf-8")
    (dest / "episodes.csv").write_text("old\n", encoding="utf-8")
    before = _tree_hash(dest)
    monkeypatch.setattr(runner, "generate_eval_id", lambda **kw: dest.name)
    code = _run_main(world)
    assert code == 7
    assert capsys.readouterr().out.strip() == ""
    assert _tree_hash(dest) == before
    assert world.residue() == [dest.name]


@pytest.mark.parametrize("sub", ["checkpoints", ""])  # type: ignore[untyped-decorator]
def test_inv005_out_inside_run_does_not_modify_existing_files(world: _World, sub: str) -> None:
    """INV-005: `--out` trỏ vào chính run (checkpoints/ hoặc gốc run) không sửa tệp CÓ SẴN."""
    target = world.run_dir / sub if sub else world.run_dir
    before = _snapshot(world.run_dir)
    assert _run_main(world, "--out", str(target)) in (0, 6)
    after = _snapshot(world.run_dir)
    for rel, digest in before.items():
        assert after.get(rel) == digest, f"{rel} bị đổi"


def test_inv005_foreign_checkpoint_without_out_refused_and_writes_nothing(
    world: _World, tmp_path: Path
) -> None:
    """FR-014/INV-005: checkpoint ngoài thư mục run, không `--out` ⇒ mã 2, không tạo thư mục."""
    foreign = tmp_path / "elsewhere_zz"
    foreign.mkdir()
    pt = next((world.run_dir / "checkpoints").glob("*.pt"))
    (foreign / pt.name).write_bytes(pt.read_bytes())
    code = cli.main(["--checkpoint", str(foreign / pt.name), "--runs-dir", "no_such_runs_dir"])
    assert code == 2
    assert sorted(p.name for p in foreign.iterdir()) == [pt.name]


def test_inv005_foreign_checkpoint_with_out_writes_nothing_when_run_unknown(
    world: _World, tmp_path: Path
) -> None:
    """INV-005/FR-009: có `--out` nhưng không ghép được run ⇒ mã 5 và `--out` không được tạo."""
    foreign = tmp_path / "elsewhere_yy"
    foreign.mkdir()
    pt = next((world.run_dir / "checkpoints").glob("*.pt"))
    (foreign / pt.name).write_bytes(pt.read_bytes())
    out = tmp_path / "out_dir_zz"
    code = cli.main([
        "--checkpoint", str(foreign / pt.name), "--out", str(out),
        "--runs-dir", "no_such_runs_dir",
    ])
    assert code == 5
    assert not out.exists()


# --------------------------------------------------------------------------------------
# INV-006 — tiêu chí không đổi theo cờ/ghi đè; báo cáo ghi nguyên văn
# --------------------------------------------------------------------------------------

_CRITERION_KEYS = [
    "criterion", "criterion.confidence_level", "criterion.primary_metric",
    "criterion.rule", "criterion.alpha", "criterion.",
]


@pytest.mark.parametrize("key", _CRITERION_KEYS)  # type: ignore[untyped-decorator]
def test_inv006_criterion_override_keys_rejected(key: str) -> None:
    """AC-2/INV-006: mọi dạng khoá `criterion*` trong overrides bị từ chối."""
    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={key: 0.5})
    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={key: {"confidence_level": 0.5}})


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "overrides",
    [
        {"criterion": {"confidence_level": 0.5}},
        {"criterion": {"primary_metric": "return"}},
        {"episodes": {"repeats": 2}, "criterion": {"confidence_level": 0.5}},
        {"seeds": {"episode_base": 3}, "criterion.confidence_level": 0.5},
        {"Criterion": {"confidence_level": 0.5}},
        {" criterion.confidence_level": 0.5},
        {"criterion​.confidence_level": 0.5},
        {"stats.bootstrap_seed": 1},
        {"stats": {"bootstrap_resamples": 100}},
        {"episodes.min_targets": 2},
        {"paths.expect_fingerprint_sha256": "0" * 64},
        {"paths.env_config_override": "x.yaml"},
        {"charts.dpi": 50},
        {"schema_version": "9"},
        {"seeds.random_policy": 1},
        {"confidence_level": 0.5},
        {"primary_metric": "return"},
        {"alpha": 0.1},
    ],
)
def test_inv006_disallowed_overrides_rejected(overrides: dict[str, Any]) -> None:
    """INV-006: danh sách trắng ghi đè — khoá lạ/biến thể chữ hoa, khoảng trắng, ký tự vô hình
    đều bị từ chối, không lọt vào cấu hình."""
    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides=overrides)


def test_inv006_allowed_overrides_do_not_touch_criterion() -> None:
    """INV-006: các ghi đè hợp lệ không làm đổi `criterion` so với bản không ghi đè."""
    base = EvalConfig.load()
    mixed = EvalConfig.load(
        overrides={"repeats": 3, "eval_seed": 99, "runs_dir": "xyz"},
    )
    assert mixed.criterion == base.criterion
    assert mixed.stats == base.stats


def test_inv006_config_is_frozen_after_load() -> None:
    """INV-006: cấu hình đã nạp là bất biến — không đổi `criterion` sau khi có kết quả."""
    cfg = EvalConfig.load()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.criterion.confidence_level = 0.1  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.criterion = dataclasses.replace(cfg.criterion)  # type: ignore[misc]


_FORBIDDEN_FLAGS = [
    ["--criterion", "x"], ["--confidence-level", "0.5"], ["--confidence_level=0.5"],
    ["--primary-metric", "return"], ["--alpha", "0.1"], ["--level", "0.5"],
    ["--set", "criterion.confidence_level=0.5"], ["--override", "criterion=0"],
    ["--criterion.confidence_level", "0.5"], ["--ci", "0.5"], ["--better-if", "always"],
    ["--min-targets", "1"], ["--bootstrap-seed", "3"],
]


@pytest.mark.parametrize("flags", _FORBIDDEN_FLAGS, ids=[" ".join(f) for f in _FORBIDDEN_FLAGS])  # type: ignore[untyped-decorator]
def test_inv006_no_cli_flag_can_change_criterion(
    world: _World, flags: list[str]
) -> None:
    """AC-2/INV-006: không cờ CLI nào đổi tiêu chí — cờ lạ ⇒ mã 2, không chạy episode."""
    assert _run_main(world, *flags) == 2
    assert world.calls.get("rollout", 0) == 0
    assert world.residue() == []


def test_inv006_cli_argv_cannot_smuggle_criterion_via_abbreviation(world: _World) -> None:
    """INV-006: viết tắt cờ (argparse prefix) không khớp nhầm tiêu chí; `--conf` là `--config`."""
    assert _run_main(world, "--conf", "0.5") == 2
    assert world.calls.get("rollout", 0) == 0


def test_inv006_report_records_declared_criterion_verbatim(
    world: _World, tmp_path: Path
) -> None:
    """AC-2/INV-006: tiêu chí khai trong cấu hình (0.9) được dùng và ghi nguyên văn vào báo cáo."""
    data = yaml.safe_load(
        (_REPO_ROOT / "src/mma_ai/evaluation/eval_elbow.yaml").read_text(encoding="utf-8")
    )
    data["criterion"]["confidence_level"] = 0.9
    cfg_path = tmp_path / "eval_90.yaml"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert _run_main(world, "--config", str(cfg_path)) in (0, 6)
    (name,) = world.residue()
    rep = json.loads((world.eval_dir / name / "report.json").read_text(encoding="utf-8"))
    assert rep["criterion"] == {
        "primary_metric": "success_rate",
        "confidence_level": 0.9,
        "rule": "better_iff_ci_lower_bound_of_difference_gt_0",
        "declared_before_run": True,
    }
    assert rep["config"]["criterion"]["confidence_level"] == 0.9


def test_inv006_verdict_follows_declared_rule_not_result(world: _World) -> None:
    """INV-006: `better` trong báo cáo luôn bằng (ci_low > 0) — không luật phụ theo kết quả."""
    assert _run_main(world) in (0, 6)
    (name,) = world.residue()
    rep = json.loads((world.eval_dir / name / "report.json").read_text(encoding="utf-8"))
    cmp_ = rep["comparison"]
    assert cmp_["better"] == (cmp_["ci_low"] > 0.0)
    assert cmp_["confidence_level"] == rep["criterion"]["confidence_level"]


def test_inv006_rerun_with_other_config_keeps_old_result_and_old_criterion(
    world: _World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-005/006: chạy lại tiêu chí khác (cùng giây) tạo bản ghi MỚI, bản cũ giữ tiêu chí cũ."""
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return datetime(2026, 10, 11, 1, 2, 3, tzinfo=timezone.utc)

    monkeypatch.setattr(report, "datetime", _Frozen)
    assert _run_main(world) in (0, 6)
    (first,) = world.residue()
    before = _tree_hash(world.eval_dir / first)
    data = yaml.safe_load(
        (_REPO_ROOT / "src/mma_ai/evaluation/eval_elbow.yaml").read_text(encoding="utf-8")
    )
    data["criterion"]["confidence_level"] = 0.8
    cfg_path = tmp_path / "eval_80.yaml"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert _run_main(world, "--config", str(cfg_path)) in (0, 6)
    assert _tree_hash(world.eval_dir / first) == before
    old = json.loads((world.eval_dir / first / "report.json").read_text(encoding="utf-8"))
    assert old["criterion"]["confidence_level"] == 0.95


# --------------------------------------------------------------------------------------
# INV-001 — check_disjoint với tập rỗng/NaN (qua tham số `pair` công khai)
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["train_empty", "test_empty", "test_nan"])  # type: ignore[untyped-decorator]
def test_inv001_degenerate_pair_never_reported_as_passed(
    tmp_path: Path, cache: _Cache, kind: str
) -> None:
    """INV-001: phép kiểm không có cặp nào để so (hoặc so với NaN) không được báo `passed`."""
    run_dir = _write_chain(tmp_path, [1])
    pair = cache.pair
    if kind == "train_empty":
        pair = dataclasses.replace(pair, train=TargetSet(role="train", targets=()))
    elif kind == "test_empty":
        pair = dataclasses.replace(pair, test=TargetSet(role="test", targets=()))
    else:
        nan_t = Target(index=0, angle_rad=0.0, position_m=(math.nan, math.nan, math.nan))
        pair = dataclasses.replace(
            pair, test=TargetSet(role="test", targets=(nan_t, *pair.test.targets[1:]))
        )
    with pytest.raises(EvalError):
        check_disjoint(run_dir, EvalConfig.load(), pair)
