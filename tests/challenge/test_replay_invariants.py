"""Thử thách bất biến (challenge) INV-001..INV-005 của replay 3D và demo khuỷu tay (T522).

Mỗi test nhắm MỘT bất biến của sản phẩm qua đầu vào mà người dùng gặp được (tệp episode,
policy/checkpoint, đường dẫn `--save-episode`, cờ dòng lệnh). Ca đỏ (finding) mang `xfail`
KHÔNG strict với mã F-NNN trong `reason`; ca xanh là vector đã thử mà không lách được.

- INV-001 (AC-4): episode lệch hash/cấu trúc mô hình không bao giờ được phát ngầm.
- INV-002 (AC-2): hành động tới `env.step` luôn hữu hạn, nằm trong [0,1]^6, đúng 6 chiều.
- INV-003 (AC-1, AC-4): episode đọc vào luôn đủ trường, đúng khuôn, không NaN/Infinity.
- INV-004 (AC-3, AC-5): ngắt/ghi lỗi ở mọi bước không để lại tệp episode dở dang, không treo.
- INV-005 (AC-1): replay/demo chỉ đọc nguồn, không ghi đè bất kỳ tệp đã tồn tại.

Mã finding:
- F-001: chuỗi số ("NaN", "inf", "1e999") lọt kiểm tra episode, `float()` thành NaN/Inf (INV-003).
- F-002: kiểm tra episode yếu hơn `episode.schema.json` (split/index/created_utc/...) (INV-003).
- F-003: `os.replace` sau kiểm `exists()` ⇒ ghi đè tệp xuất hiện giữa hai bước (INV-005).
- F-004: đích `--save-episode` là symlink treo (dangling) bị thay thế êm (INV-005).
- F-005: checkpoint không khai hash XML vượt kiểm tra lệch mô hình (INV-001).
- F-006: thiếu quyền duyệt thư mục tổ tiên ⇒ mã 1 thay vì mã 8 (INV-004/AC-5).
"""

from __future__ import annotations

import copy
import errno
import functools
import json
import math
import os
import random
import stat
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization import episode as episode_mod
from mma_ai.visualization.episode import (
    Episode,
    read_episode,
    write_episode,
)
from mma_ai.visualization.errors import EpisodeWriteError
from mma_ai.visualization.model_check import check_model, enforce
from mma_ai.visualization.recorder import record_episode, validate_action
from mma_ai.visualization.replay import reset_viewer_opened, run_replay

_CONTRACTS = (
    Path(__file__).resolve().parents[2] / "specs" / "005-replay-3d-muscle-demo" / "contracts"
)

_NON_FINITE_STRINGS = ["NaN", "nan", "inf", "-inf", "Infinity", "-Infinity", "1e999"]

# Các đường dẫn số học mà validate_episode_dict chỉ kiểm độ dài/khoá, không kiểm kiểu phần tử.
_UNCHECKED_NUMERIC_PATHS: list[tuple[str | int, ...]] = [
    ("frames", 1, "qpos", 0),
    ("frames", 1, "qvel", 0),
    ("frames", 2, "fingertip_position_m", 1),
    ("frames", 1, "reward"),
    ("target", "tolerance_m"),
    ("outcome", "final_distance_m"),
]


# Nút mà validate_episode_dict không kiểm kiểu/miền (F-002).
_F002_UNVALIDATED = {"created_utc", "target.split", "target.index"}


class Result(NamedTuple):
    """Kết quả một lần chạy `run_replay` trong tiến trình."""

    code: int
    out: str
    err: str


# ----------------------------------------------------------------------------------------------
# Dựng đầu vào
# ----------------------------------------------------------------------------------------------


@functools.cache
def _info() -> Any:
    """Thông tin mô hình cơ bắp hiện tại (hash XML, tên 6 cơ)."""
    return load_muscle_model("myoelbow").info


def make_episode(
    *,
    nq: int = 1,
    nv: int = 1,
    sha: str | None = None,
    names: list[str] | None = None,
    n_frames: int = 3,
) -> dict[str, Any]:
    """Dựng dict episode hợp lệ theo luật R1–R7, cho phép chỉnh hash/cấu trúc mô hình."""
    info = _info()
    frames: list[dict[str, Any]] = []
    for k in range(n_frames):
        frames.append(
            {
                "t_s": round(0.04 * k, 10),
                "qpos": [0.1 * k] * nq,
                "qvel": [0.0] * nv,
                "activation": [0.1] * 6,
                "excitation": None if k == 0 else [0.2] * 6,
                "fingertip_position_m": [0.1, 0.2, 0.3],
                "distance_m": 0.1,
                "reward": 0.0,
            }
        )
    return {
        "schema_version": "1.0.0",
        "created_utc": "2026-10-10T12:00:00Z",
        "seed": 1,
        "model": {
            "sha256": sha if sha is not None else info.sha256,
            "source": "myo_sim/elbow/myoelbow_1dof6muscles.xml",
            "muscle_names": list(names) if names is not None else list(info.muscle_names),
            "nq": nq,
            "nv": nv,
        },
        "target": {"position_m": [0.1, 0.2, 0.3], "split": "test", "index": 0, "tolerance_m": 0.05},
        "source": None,
        "library_versions": {"mujoco": "3.0.0", "numpy": "1.26.0"},
        "timing": {"action_dt_s": 0.04, "physics_timestep_s": 0.002},
        "outcome": {
            "terminated": False,
            "truncated": True,
            "end_reason": "max_actions",
            "reached": False,
            "n_actions": n_frames - 1,
            "final_distance_m": 0.1,
        },
        "frames": frames,
    }


def put(data: dict[str, Any], path: tuple[str | int, ...], value: Any) -> dict[str, Any]:
    """Trả bản sao của `data` với phần tử ở `path` đặt thành `value`."""
    out = copy.deepcopy(data)
    cur: Any = out
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value
    return out


def drop(data: dict[str, Any], path: tuple[str | int, ...]) -> dict[str, Any]:
    """Trả bản sao của `data` với khoá ở `path` bị xoá."""
    out = copy.deepcopy(data)
    cur: Any = out
    for key in path[:-1]:
        cur = cur[key]
    del cur[path[-1]]
    return out


def walk(data: Any, prefix: tuple[str | int, ...] = ()) -> Iterator[tuple[str | int, ...]]:
    """Liệt kê mọi nút (kể cả nút trong) của cây JSON, trừ gốc."""
    if isinstance(data, dict):
        for k, v in data.items():
            yield (*prefix, k)
            yield from walk(v, (*prefix, k))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            yield (*prefix, i)
            yield from walk(v, (*prefix, i))


def write_json(path: Path, data: Any) -> Path:
    """Ghi JSON thô (cho phép NaN/Infinity) để dựng tệp xấu."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def strict_json(text: str) -> Any:
    """Parse JSON nghiêm ngặt: từ chối NaN/Infinity (đúng như người tiêu thụ stdout)."""

    def _reject(token: str) -> Any:
        raise ValueError(f"JSON chứa hằng không hợp lệ: {token}")

    return json.loads(text, parse_constant=_reject)


def non_finite_leaves(obj: Any) -> list[Any]:
    """Các số không hữu hạn nằm trong cây dict/list."""
    found: list[Any] = []
    if isinstance(obj, float) and not math.isfinite(obj):
        found.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            found.extend(non_finite_leaves(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            found.extend(non_finite_leaves(v))
    return found


def listing(root: Path) -> list[str]:
    """Danh sách tương đối mọi mục dưới `root` (không theo symlink)."""
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


# ----------------------------------------------------------------------------------------------
# Fixture
# ----------------------------------------------------------------------------------------------


@pytest.fixture
def cli(capsys: pytest.CaptureFixture[str]) -> Callable[..., Result]:
    """Chạy `run_replay` trong tiến trình, trả (mã thoát, stdout, stderr)."""

    def _run(*argv: str | Path) -> Result:
        capsys.readouterr()
        code = run_replay([str(a) for a in argv])
        out, err = capsys.readouterr()
        return Result(code, out, err)

    return _run


class _FnPolicy:
    """Policy giả: hành động thứ k do `fn(k)` quyết định (không cần torch)."""

    def __init__(self, fn: Callable[[int], Any]) -> None:
        self._fn = fn
        self.calls = 0

    def act_deterministic(self, obs: Any) -> Any:
        k = self.calls
        self.calls += 1
        return self._fn(k)


@pytest.fixture
def fake_checkpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[..., Path]:
    """Cài `mma_ai.learning.checkpoint` giả (không cần extra rl) và tạo tệp .pt giả."""

    def install(policy_fn: Callable[[int], Any], *, model_sha: str | None = None) -> Path:
        ckpt = tmp_path / "run" / "checkpoints" / "ckpt_u000001_final.pt"
        ckpt.parent.mkdir(parents=True, exist_ok=True)
        ckpt.write_bytes(b"checkpoint-bytes-khong-duoc-doi")
        sha = _info().sha256 if model_sha is None else model_sha
        policy = _FnPolicy(policy_fn)
        mod = types.ModuleType("mma_ai.learning.checkpoint")
        setattr(
            mod,
            "load_checkpoint",
            lambda path, **kw: types.SimpleNamespace(model_sha256=sha, update_idx=1),
        )
        setattr(mod, "load_policy", lambda path, **kw: policy)
        monkeypatch.setitem(sys.modules, "mma_ai.learning.checkpoint", mod)
        return ckpt

    return install


def _good_action(_k: int) -> list[float]:
    return [0.5] * 6


def _fake_namespace(module: Any, **overrides: Any) -> types.SimpleNamespace:
    """Bản sao SimpleNamespace của một module với vài thuộc tính bị thay."""
    attrs = {k: getattr(module, k) for k in dir(module) if not k.startswith("__")}
    attrs.update(overrides)
    return types.SimpleNamespace(**attrs)


# ==============================================================================================
# INV-003 — episode tự đủ, không NaN/Infinity, đúng khuôn (AC-1, AC-4)
# ==============================================================================================


def test_inv003_baseline_episode_is_accepted(cli: Callable[..., Result], tmp_path: Path) -> None:
    """INV-003: episode dựng bởi make_episode là hợp lệ (đối chứng cho mọi đột biến bên dưới)."""
    p = write_json(tmp_path / "ok.json", make_episode())
    res = cli("--episode", p, "--headless")
    assert res.code == 0, res.err
    strict_json(res.out)


@pytest.mark.xfail(
    strict=False,
    reason="F-001: validate_episode_dict không kiểm kiểu phần tử qpos/qvel/fingertip/reward/"
    "tolerance_m/final_distance_m; chuỗi 'NaN'/'inf' qua R7 rồi float() thành NaN/Inf",
)
@pytest.mark.parametrize("value", _NON_FINITE_STRINGS)
@pytest.mark.parametrize("path", _UNCHECKED_NUMERIC_PATHS, ids=lambda p: ".".join(map(str, p)))
def test_inv003_non_finite_numeric_string_rejected_exit5(
    cli: Callable[..., Result], tmp_path: Path, path: tuple[str | int, ...], value: str
) -> None:
    """INV-003 (AC-1, FR-009): chuỗi 'NaN'/'inf' ở trường số phải bị từ chối bằng mã 5."""
    p = write_json(tmp_path / "bad.json", put(make_episode(), path, value))
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:200])


@pytest.mark.xfail(
    strict=False,
    reason="F-001: Episode đọc từ tệp chứa NaN/Inf thật (qua chuỗi số) dù luật R7 cấm",
)
def test_inv003_read_episode_never_yields_non_finite(tmp_path: Path) -> None:
    """INV-003 (NFR-REL-001): đã `read_episode` thành công thì không còn số không hữu hạn."""
    leaks: list[str] = []
    for path in _UNCHECKED_NUMERIC_PATHS:
        for value in _NON_FINITE_STRINGS:
            p = write_json(tmp_path / "e.json", put(make_episode(), path, value))
            try:
                ep = read_episode(p)
            except Exception:
                continue
            if non_finite_leaves(ep.to_dict()):
                leaks.append(f"{'.'.join(map(str, path))}={value}")
    assert not leaks, leaks


@pytest.mark.parametrize(
    "literal", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999", "1E400", "0.0e0001e999"]
)
@pytest.mark.parametrize(
    "path",
    [
        ("seed",),
        ("model", "nq"),
        ("target", "position_m", 0),
        ("timing", "action_dt_s"),
        ("frames", 1, "t_s"),
        ("frames", 1, "qpos", 0),
        ("frames", 1, "activation", 3),
        ("frames", 1, "excitation", 2),
        ("frames", 1, "reward"),
        ("frames", 2, "distance_m"),
        ("outcome", "final_distance_m"),
        ("target", "tolerance_m"),
    ],
    ids=lambda p: ".".join(map(str, p)),
)
def test_inv003_bare_non_finite_literals_rejected(
    cli: Callable[..., Result], tmp_path: Path, path: tuple[str | int, ...], literal: str
) -> None:
    """INV-003: hằng JSON trần NaN/Infinity/1e999 ở MỌI vị trí số ⇒ luôn mã 5 (vector đã bác)."""
    text = json.dumps(put(make_episode(), path, "@@LIT@@")).replace('"@@LIT@@"', literal)
    p = tmp_path / "lit.json"
    p.write_text(text, encoding="utf-8")
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:200])


def test_inv003_huge_integer_rejected_exit5(cli: Callable[..., Result], tmp_path: Path) -> None:
    """INV-003: số nguyên khổng lồ (10**400) không làm tràn/crash — vẫn là mã 5 (vector đã bác)."""
    text = json.dumps(make_episode()).replace('"reward": 0.0', f'"reward": {10**400}', 1)
    p = tmp_path / "huge.json"
    p.write_text(text, encoding="utf-8")
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:200])


def test_inv003_every_required_key_missing_rejected(tmp_path: Path) -> None:
    """INV-003 (FR-009): xoá từng khoá của mọi dict (kể cả khung 0 và 1) ⇒ luôn bị từ chối."""
    base = make_episode()
    survivors: list[str] = []
    for path in walk(base):
        container: Any = base
        for key in path[:-1]:
            container = container[key]
        if not isinstance(container, dict):
            continue
        p = write_json(tmp_path / "m.json", drop(base, path))
        try:
            read_episode(p)
        except Exception:
            continue
        survivors.append(".".join(map(str, path)))
    assert not survivors, f"xoá khoá mà episode vẫn được nhận: {survivors}"


def test_inv003_container_type_swaps_rejected(tmp_path: Path) -> None:
    """INV-003: thay mọi nút bằng {} hoặc [] (sai kiểu cấu trúc) ⇒ luôn bị từ chối."""
    base = make_episode()
    survivors: list[str] = []
    for path in walk(base):
        if ".".join(map(str, path)) in _F002_UNVALIDATED:
            continue  # đã có ca xfail riêng (F-002) bên dưới
        swaps: list[Any] = [{}, [], {"x": 1}]
        for swap in swaps:
            candidate = put(base, path, swap)
            p = write_json(tmp_path / "s.json", candidate)
            try:
                read_episode(p)
            except Exception:
                continue
            survivors.append(f"{'.'.join(map(str, path))}={swap!r}")
    assert not survivors, survivors


@pytest.mark.parametrize(
    "names",
    [
        ["a", "a", "b", "c", "d", "e"],
        ["a", "b", "c", "d", "e", ""],
        ["a", "b", "c", "d", "e", "   "],
        ["a", "b", "c", "d", "e", "\t\n"],
        ["a", "b", "c", "d", "e"],
        ["a", "b", "c", "d", "e", "f", "g"],
        ["a", "b", "c", "d", "e", None],
        ["a", "b", "c", "d", "e", 7],
    ],
)
def test_inv003_bad_muscle_names_rejected_exit5(
    cli: Callable[..., Result], tmp_path: Path, names: list[Any]
) -> None:
    """INV-003 (R5): tên cơ trùng/rỗng/trắng/thiếu/thừa/sai kiểu ⇒ mã 5 (vector đã bác)."""
    p = write_json(tmp_path / "n.json", put(make_episode(), ("model", "muscle_names"), names))
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:200])


def test_inv003_truncated_file_never_accepted(tmp_path: Path) -> None:
    """INV-003/INV-004: mọi tiền tố thực sự của một tệp episode hợp lệ đều bị từ chối."""
    text = json.dumps(make_episode(), indent=2)
    rng = random.Random(522)
    cuts = sorted({rng.randrange(0, len(text) - 1) for _ in range(120)} | {0, 1, len(text) - 2})
    accepted: list[int] = []
    for cut in cuts:
        p = tmp_path / "t.json"
        p.write_text(text[:cut], encoding="utf-8")
        try:
            read_episode(p)
        except Exception:
            continue
        accepted.append(cut)
    assert not accepted, f"tiền tố cắt tại {accepted} vẫn được nhận như episode hợp lệ"


def test_inv003_non_utf8_and_directory_sources_rejected(
    cli: Callable[..., Result], tmp_path: Path
) -> None:
    """INV-003: tệp không phải UTF-8, thư mục, tệp rỗng làm nguồn ⇒ mã 5 (vector đã bác)."""
    bad = tmp_path / "bin.json"
    bad.write_bytes(b"\xff\xfe\x00\x01{")
    empty = tmp_path / "empty.json"
    empty.write_bytes(b"")
    a_dir = tmp_path / "dir.json"
    a_dir.mkdir()
    for p in (bad, empty, a_dir):
        res = cli("--episode", p, "--headless")
        assert res.code == 5, (p.name, res.code, res.err[:160])


_FUZZ_POOL: list[Any] = [
    None, True, False, 0, -1, 2, 1.5, -0.5, 1e308, "", "x", "NaN", "train", "test", [], {}, [1],
]  # fmt: skip


def _fuzz_cases(n: int) -> list[tuple[dict[str, Any], tuple[str | int, ...], Any]]:
    """Sinh n đột biến một-trường tất định (seed cố định) trên episode hợp lệ."""
    rng = random.Random(20261010)
    base = make_episode()
    leaves = list(walk(base))
    cases = []
    for _ in range(n):
        path = rng.choice(leaves)
        cases.append((base, path, copy.deepcopy(rng.choice(_FUZZ_POOL))))
    return cases


@pytest.mark.xfail(
    strict=False,
    reason="F-001: đột biến một-trường tạo Episode chứa số không hữu hạn mà read_episode vẫn nhận",
)
def test_inv003_fuzz_accepted_episode_is_always_finite(tmp_path: Path) -> None:
    """INV-003 (property): đột biến ngẫu nhiên có seed — nếu được nhận thì mọi số hữu hạn."""
    leaks: list[str] = []
    for base, path, value in _fuzz_cases(600):
        p = write_json(tmp_path / "f.json", put(base, path, value))
        try:
            ep = read_episode(p)
        except Exception:
            continue
        if non_finite_leaves(ep.to_dict()):
            leaks.append(f"{'.'.join(map(str, path))}={value!r}")
    assert not leaks, leaks[:10]


@pytest.mark.xfail(
    strict=False,
    reason="F-002: read_episode nhận episode sai khuôn episode.schema.json "
    "(split ngoài enum, index âm/sai kiểu, tolerance<=0, final_distance<0, bool thay số...)",
)
def test_inv003_fuzz_accepted_episode_conforms_to_schema(tmp_path: Path) -> None:
    """INV-003 (property, FR-009): episode được nhận phải hợp lệ theo episode.schema.json."""
    schema = json.loads((_CONTRACTS / "episode.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    nonconforming: list[str] = []
    for base, path, value in _fuzz_cases(600):
        mutated = put(base, path, value)
        p = write_json(tmp_path / "f.json", mutated)
        try:
            read_episode(p)
        except Exception:
            continue
        if not validator.is_valid(mutated):
            nonconforming.append(f"{'.'.join(map(str, path))}={value!r}")
    assert not nonconforming, sorted(set(nonconforming))[:12]


@pytest.mark.xfail(
    strict=False,
    reason="F-002: target.index kiểu sai được nhận ở bước đọc rồi crash muộn bằng mã 1 "
    "thay vì mã 5 (episode không dùng được)",
)
@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("target", "split"), 123),
        (("target", "split"), "validation"),
        (("target", "index"), "x"),
        (("target", "index"), -5),
        (("target", "tolerance_m"), -0.05),
        (("outcome", "final_distance_m"), -1.0),
        (("created_utc",), {}),
        (("created_utc",), 12345),
        (("target", "split"), {}),
        (("target", "index"), []),
    ],
    ids=lambda v: str(v),
)
def test_inv003_schema_enum_and_range_violations_exit5(
    cli: Callable[..., Result], tmp_path: Path, path: tuple[str | int, ...], value: Any
) -> None:
    """INV-003 (AC-1): giá trị ngoài enum/miền của schema ⇒ mã 5, không phải mã 0 hay mã 1."""
    p = write_json(tmp_path / "s.json", put(make_episode(), path, value))
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:160])


@pytest.mark.parametrize(
    "path",
    [
        ("frames", 1, "excitation", 0),
        ("frames", 0, "activation", 2),
        ("frames", 2, "excitation", 5),
    ],
    ids=lambda p: ".".join(map(str, p)),
)
@pytest.mark.parametrize("value", [1.0000001, -1e-9, 2, True, "0.5", None])
def test_inv003_activation_excitation_out_of_unit_interval_rejected(
    cli: Callable[..., Result], tmp_path: Path, path: tuple[str | int, ...], value: Any
) -> None:
    """INV-003/INV-002: activation/excitation ngoài [0,1] hay sai kiểu ⇒ mã 5 (đã bác)."""
    p = write_json(tmp_path / "u.json", put(make_episode(), path, value))
    res = cli("--episode", p, "--headless")
    assert res.code == 5, (res.code, res.err[:160])


def test_inv003_write_episode_never_emits_non_finite(tmp_path: Path) -> None:
    """INV-003: write_episode với NaN/Inf thật ở mọi trường số ⇒ từ chối, không để lại tệp."""
    base = make_episode()
    numeric_paths = [
        ("seed",),
        ("target", "position_m", 1),
        ("timing", "action_dt_s"),
        ("frames", 1, "t_s"),
        ("frames", 1, "qpos", 0),
        ("frames", 1, "qvel", 0),
        ("frames", 1, "activation", 0),
        ("frames", 1, "excitation", 0),
        ("frames", 2, "fingertip_position_m", 2),
        ("frames", 1, "distance_m"),
        ("frames", 1, "reward"),
        ("target", "tolerance_m"),
        ("outcome", "final_distance_m"),
    ]
    for path in numeric_paths:
        for bad in (float("nan"), float("inf"), float("-inf")):
            dest = tmp_path / "out" / "ep.json"
            with pytest.raises(EpisodeWriteError):
                write_episode(put(base, path, bad), dest)
            assert not dest.exists()
            assert listing(tmp_path) in ([], ["out"]), listing(tmp_path)


# ==============================================================================================
# INV-001 — không phát sai ngầm khi lệch mô hình (AC-4)
# ==============================================================================================


def _flip_hex(sha: str, pos: int) -> str:
    flipped = "0" if sha[pos] != "0" else "1"
    return sha[:pos] + flipped + sha[pos + 1 :]


def test_inv001_every_single_hex_digit_flip_blocks_without_flag() -> None:
    """INV-001: đổi MỘT chữ số hex ở bất kỳ vị trí nào trong 64 ⇒ enforce() dừng (không cờ)."""
    info = _info()
    for pos in range(64):
        ep = make_episode(sha=_flip_hex(info.sha256, pos))
        current = {
            "sha256": info.sha256,
            "nq": 1,
            "nv": 1,
            "muscle_names": list(info.muscle_names),
        }
        res = check_model(ep, current)
        assert not res.match
        with pytest.raises(Exception, match="Lệch mã băm|lệch"):
            enforce(res, allow_mismatch=False)


@pytest.mark.parametrize("mode", ["permute", "rename", "swap2"])
@pytest.mark.parametrize("flag", [False, True])
def test_inv001_muscle_name_structure_mismatch_blocks_even_with_flag(
    cli: Callable[..., Result], tmp_path: Path, mode: str, flag: bool
) -> None:
    """INV-001: đổi thứ tự/tên cơ ⇒ mã 6, kể cả khi bật --allow-model-mismatch."""
    names = list(_info().muscle_names)
    if mode == "permute":
        names = names[1:] + names[:1]
    elif mode == "rename":
        names[2] = names[2] + "_x"
    else:
        names[0], names[5] = names[5], names[0]
    p = write_json(tmp_path / "e.json", make_episode(names=names))
    argv = ["--episode", p, "--headless", *(["--allow-model-mismatch"] if flag else [])]
    res = cli(*argv)
    assert res.code == 6, (res.code, res.err[:160])
    assert res.out == ""


@pytest.mark.parametrize("flag", [False, True])
@pytest.mark.parametrize(("nq", "nv"), [(2, 1), (1, 2), (3, 3)])
def test_inv001_nq_nv_mismatch_blocks_even_with_flag(
    cli: Callable[..., Result], tmp_path: Path, nq: int, nv: int, flag: bool
) -> None:
    """INV-001: nq/nv lệch (episode tự nhất quán nội bộ) ⇒ mã 6, kể cả khi có cờ."""
    p = write_json(tmp_path / "e.json", make_episode(nq=nq, nv=nv))
    argv = ["--episode", p, "--headless", *(["--allow-model-mismatch"] if flag else [])]
    res = cli(*argv)
    assert res.code == 6, (res.code, res.err[:160])
    assert res.out == ""


def test_inv001_property_hash_and_structure_mutations_never_play_silently(
    cli: Callable[..., Result], tmp_path: Path
) -> None:
    """INV-001 (property, AC-4): tổ hợp ngẫu nhiên có seed của hash/nq/nv/tên cơ/cờ.

    Quy tắc: cấu trúc lệch ⇒ 6 luôn; chỉ lệch hash + không cờ ⇒ 6; chỉ lệch hash + có cờ ⇒ 0
    kèm `warnings` không rỗng trong tóm tắt; khớp hoàn toàn ⇒ 0 và không cảnh báo.
    """
    rng = random.Random(1001)
    info = _info()
    for i in range(40):
        sha_changed = rng.random() < 0.5
        nq = rng.choice([1, 1, 2, 3])
        nv = rng.choice([1, 1, 2])
        names = list(info.muscle_names)
        name_mode = rng.choice(["same", "same", "perm", "rename"])
        if name_mode == "perm":
            rng.shuffle(names)
            if names == list(info.muscle_names):
                names = names[1:] + names[:1]
        elif name_mode == "rename":
            names[rng.randrange(6)] += "'"
        flag = rng.random() < 0.5
        sha = _flip_hex(info.sha256, rng.randrange(64)) if sha_changed else info.sha256
        p = write_json(tmp_path / f"e{i}.json", make_episode(nq=nq, nv=nv, sha=sha, names=names))
        res = cli("--episode", p, "--headless", *(["--allow-model-mismatch"] if flag else []))
        structure_ok = nq == 1 and nv == 1 and name_mode == "same"
        label = (i, sha_changed, nq, nv, name_mode, flag)
        if not structure_ok:
            assert res.code == 6, (label, res.code)
            assert res.out == "", label
        elif sha_changed and not flag:
            assert res.code == 6, (label, res.code)
            assert res.out == "", label
        elif sha_changed and flag:
            assert res.code == 0, (label, res.err[:160])
            summary = strict_json(res.out)
            assert summary["warnings"], label
        else:
            assert res.code == 0, (label, res.err[:160])
            assert strict_json(res.out)["warnings"] == [], label


def test_inv001_viewer_path_shows_persistent_warning_when_hash_mismatch_allowed(
    monkeypatch: pytest.MonkeyPatch, cli: Callable[..., Result], tmp_path: Path
) -> None:
    """INV-001 (AC-4): đường có viewer + lệch hash + cờ ⇒ cảnh báo 'MÔ HÌNH LỆCH' tới play.

    Viewer/play được thay bằng bản giả ghi lại tham số (không cần màn hình thật).
    """
    from mma_ai.visualization import display as display_mod
    from mma_ai.visualization import playback as playback_mod
    from mma_ai.visualization import viewer as viewer_mod

    warnings_seen: list[Any] = []

    class FakeSink:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def set_target(self, *a: Any, **k: Any) -> None:
            pass

        def close(self) -> None:
            pass

    def fake_play(
        episode: Any, cfg: Any, sink: Any, pacer: Any = None, warning: Any = None, **k: Any
    ) -> Any:
        warnings_seen.append(warning)
        return types.SimpleNamespace(sim_s=0.0, wall_s=0.0, ratio=None, frames_late=0)

    monkeypatch.setattr(
        display_mod,
        "display_available",
        lambda: types.SimpleNamespace(available=True, reason=""),
    )
    monkeypatch.setattr(viewer_mod, "ViewerSink", FakeSink)
    monkeypatch.setattr(playback_mod, "play", fake_play)
    try:
        info = _info()
        mismatched = write_json(tmp_path / "m.json", make_episode(sha=_flip_hex(info.sha256, 7)))
        matched = write_json(tmp_path / "ok.json", make_episode())

        blocked = cli("--episode", mismatched)
        assert blocked.code == 6 and warnings_seen == []

        allowed = cli("--episode", mismatched, "--allow-model-mismatch")
        assert allowed.code == 0, allowed.err[:200]
        assert warnings_seen and warnings_seen[-1], "phát lệch mô hình mà không có cảnh báo"
        assert "LỆCH" in str(warnings_seen[-1])

        clean = cli("--episode", matched)
        assert clean.code == 0 and warnings_seen[-1] is None
    finally:
        reset_viewer_opened()


@pytest.mark.xfail(
    strict=False,
    reason="F-005: checkpoint không khai model_sha256 (chuỗi rỗng) bỏ qua kiểm lệch hash XML "
    "ở bước demo ⇒ demo chạy trên mô hình hiện tại mà không dừng/cảnh báo",
)
def test_inv001_checkpoint_without_model_hash_not_accepted_silently(
    cli: Callable[..., Result], fake_checkpoint: Callable[..., Path]
) -> None:
    """INV-001 (AC-4): checkpoint không chứng minh được hash XML không được demo êm."""
    ckpt = fake_checkpoint(_good_action, model_sha="")
    res = cli("--checkpoint", ckpt, "--headless")
    silently_played = res.code == 0 and not strict_json(res.out)["warnings"]
    assert not silently_played, "demo chạy êm với checkpoint không có hash XML"


def test_inv001_checkpoint_with_wrong_hash_exit4(
    cli: Callable[..., Result], fake_checkpoint: Callable[..., Path]
) -> None:
    """INV-001: checkpoint khai hash XML khác ⇒ mã 4, không chạy demo (vector đã bác)."""
    ckpt = fake_checkpoint(_good_action, model_sha="0" * 64)
    res = cli("--checkpoint", ckpt, "--headless")
    assert res.code == 4 and res.out == ""


# ==============================================================================================
# INV-002 — chỉ kích thích cơ hợp lệ tới env.step (AC-2)
# ==============================================================================================

_BAD_ACTIONS: list[tuple[str, Callable[[], Any]]] = [
    ("nan", lambda: np.full(6, np.nan)),
    ("nan_one", lambda: [0.5, 0.5, 0.5, 0.5, 0.5, float("nan")]),
    ("inf", lambda: np.array([0.5] * 5 + [np.inf])),
    ("neg_inf", lambda: np.array([-np.inf] + [0.5] * 5)),
    ("negative", lambda: [-0.001] + [0.5] * 5),
    ("above_one_eps", lambda: [1.0000001] + [0.5] * 5),
    ("above_one_f32", lambda: np.array([1.0000001] * 6, dtype=np.float32)),
    ("large", lambda: [1e30] * 6),
    ("len5", lambda: [0.5] * 5),
    ("len7", lambda: [0.5] * 7),
    ("empty", lambda: []),
    ("none", lambda: None),
    ("string", lambda: "abcdef"),
    ("bools", lambda: [True] * 6),
    ("numeric_strings", lambda: ["0.5"] * 6),
    ("complex", lambda: [0.5 + 0j] * 6),
    ("nested", lambda: [[0.5]] * 6),
    ("object_none", lambda: np.array([0.5] * 5 + [None], dtype=object)),
    ("scalar", lambda: 0.5),
    ("dict", lambda: {i: 0.5 for i in range(6)}),
    ("shape_2x3", lambda: np.full((2, 3), 0.5)),
    ("shape_6x1", lambda: np.full((6, 1), 0.5)),
    ("int_two", lambda: [2] * 6),
]


def _spy_step(monkeypatch: pytest.MonkeyPatch) -> list[np.ndarray]:
    """Ghi lại mọi hành động thực sự tới ElbowReachEnv.step."""
    seen: list[np.ndarray] = []
    original = ElbowReachEnv.step

    def spy(self: Any, action: Any) -> Any:
        seen.append(np.array(action, dtype=np.float64, copy=True))
        return original(self, action)

    monkeypatch.setattr(ElbowReachEnv, "step", spy)
    return seen


@pytest.mark.parametrize("at_step", [0, 3])
@pytest.mark.parametrize(("name", "make"), _BAD_ACTIONS, ids=[n for n, _ in _BAD_ACTIONS])
def test_inv002_bad_policy_action_never_reaches_env_step(
    monkeypatch: pytest.MonkeyPatch, name: str, make: Callable[[], Any], at_step: int
) -> None:
    """INV-002 (AC-2): hành động xấu ở bước k ⇒ mọi thứ tới env.step hữu hạn, [0,1], đủ 6 chiều."""
    seen = _spy_step(monkeypatch)
    policy = _FnPolicy(lambda k: make() if k >= at_step else _good_action(k))
    env = ElbowReachEnv(split="test")
    ep = record_episode(env, policy, split="test", target_index=0, seed=0)
    for a in seen:
        assert a.shape == (6,), (name, a.shape)
        assert np.all(np.isfinite(a)) and np.all(a >= 0.0) and np.all(a <= 1.0), (name, a)
    assert not non_finite_leaves(ep.to_dict())
    for frame in ep.frames[1:]:
        assert frame.excitation is not None
        assert all(0.0 <= u <= 1.0 for u in frame.excitation)


def test_inv002_property_random_actions_validate_action_agrees_with_definition() -> None:
    """INV-002 (property): validate_action chấp nhận ⇔ đúng 6 số thực hữu hạn trong [0,1]."""
    rng = random.Random(2002)
    specials = [0.0, 1.0, -0.0, 1e-320, 0.9999999999999999, 1.0000000000000002, -1e-320, 5e-324]
    for _ in range(3000):
        vec = [
            rng.choice(specials)
            if rng.random() < 0.3
            else rng.choice([rng.uniform(-0.5, 1.5), float("nan"), float("inf"), rng.random()])
            for _ in range(6)
        ]
        ok, clean = validate_action(vec)
        expected = all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in vec)
        assert ok == expected, vec
        if ok:
            assert clean is not None and len(clean) == 6
            f32 = np.array(clean, dtype=np.float32)
            assert np.all(f32 >= 0.0) and np.all(f32 <= 1.0), clean


@pytest.mark.parametrize("at_step", [0, 2])
def test_inv002_cli_demo_with_nan_policy_is_contained(
    monkeypatch: pytest.MonkeyPatch,
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
    at_step: int,
) -> None:
    """INV-002 (AC-2): demo CLI với policy NaN ⇒ env.step sạch, JSON chặt, tệp đọc lại được."""
    seen = _spy_step(monkeypatch)
    nan_issued: list[int] = []

    def policy_fn(k: int) -> Any:
        if k < at_step:
            return _good_action(k)
        nan_issued.append(k)
        return np.full(6, np.nan)

    ckpt = fake_checkpoint(policy_fn)
    out = tmp_path / "saved" / "demo.episode.json"
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", out)
    assert res.code in (0, 1), res.err[:200]
    for a in seen:
        assert np.all(np.isfinite(a)) and np.all(a >= 0.0) and np.all(a <= 1.0)
    if res.code == 0:
        summary = strict_json(res.out)
        saved = read_episode(out)
        assert not non_finite_leaves(saved.to_dict())
        if nan_issued:  # NaN đã được policy xuất ⇒ episode PHẢI ghi nhận bất thường
            assert summary["n_actions"] == at_step
            assert summary["outcome"]["end_reason"] == "abnormal"
            assert saved.outcome.end_reason == "abnormal"


# ==============================================================================================
# INV-004 — ngắt/ghi lỗi không để lại tệp dở dang, không treo (AC-3, AC-5)
# ==============================================================================================


def _install_fault(monkeypatch: pytest.MonkeyPatch, stage: str, exc: BaseException) -> None:
    """Chèn lỗi `exc` vào bước `stage` của write_episode."""
    real_fsync = os.fsync
    real_replace = os.replace

    def boom(*_a: Any, **_k: Any) -> Any:
        raise exc

    def partial_then_raise(obj: Any, fp: Any, **kw: Any) -> None:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
        fp.write(text[: len(text) // 2])
        fp.flush()
        raise exc

    if stage == "dump":
        monkeypatch.setattr(episode_mod, "json", _fake_namespace(json, dump=partial_then_raise))
    elif stage == "fsync":
        monkeypatch.setattr(
            episode_mod, "os", _fake_namespace(os, fsync=lambda fd: (real_fsync(fd), boom())[1])
        )
    elif stage == "replace":
        monkeypatch.setattr(episode_mod, "os", _fake_namespace(os, replace=boom))
    else:  # replace_after: thay thế xong rồi mới nổ — tệp đích đã đầy đủ

        def replace_then_boom(src: Any, dst: Any) -> None:
            real_replace(src, dst)
            raise exc

        monkeypatch.setattr(episode_mod, "os", _fake_namespace(os, replace=replace_then_boom))


@pytest.mark.parametrize("stage", ["dump", "fsync", "replace"])
@pytest.mark.parametrize(
    "exc",
    [
        KeyboardInterrupt(),
        OSError(errno.ENOSPC, "No space left on device"),
        OSError(errno.EIO, "I/O error"),
        SystemExit(130),
    ],
    ids=["ctrl-c", "enospc", "eio", "sysexit"],
)
def test_inv004_write_episode_fault_leaves_no_partial_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stage: str, exc: BaseException
) -> None:
    """INV-004 (AC-3): lỗi/ngắt ở dump/fsync/replace ⇒ không có tệp đích, không còn tệp tạm."""
    out_dir = tmp_path / "out"
    dest = out_dir / "ep.json"
    _install_fault(monkeypatch, stage, exc)
    with pytest.raises((KeyboardInterrupt, SystemExit, EpisodeWriteError)):
        write_episode(make_episode(), dest)
    assert not dest.exists()
    assert listing(out_dir) == [], listing(out_dir)


@pytest.mark.parametrize("stage", ["dump", "replace"])
def test_inv004_cli_demo_ctrl_c_during_save_exit130_no_leftover(
    monkeypatch: pytest.MonkeyPatch,
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
    stage: str,
) -> None:
    """INV-004 (AC-3): Ctrl-C trong lúc ghi episode ở demo ⇒ mã 130, không tệp đích/tệp tạm."""
    ckpt = fake_checkpoint(_good_action)
    out_dir = tmp_path / "saved"
    before = listing(tmp_path)
    _install_fault(monkeypatch, stage, KeyboardInterrupt())
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", out_dir / "ep.json")
    assert res.code == 130, (res.code, res.err[:200])
    assert res.out == ""
    assert [p for p in listing(tmp_path) if p not in before] in ([], ["saved"]), listing(tmp_path)
    assert listing(out_dir) == [] if out_dir.exists() else True


def test_inv004_cli_disk_full_during_save_exit8_no_leftover(
    monkeypatch: pytest.MonkeyPatch,
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """INV-004 (AC-5): đĩa đầy giữa chừng ⇒ mã 8, không tệp dở dang, stdout trống."""
    ckpt = fake_checkpoint(_good_action)
    out_dir = tmp_path / "saved"
    _install_fault(monkeypatch, "dump", OSError(errno.ENOSPC, "No space left on device"))
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", out_dir / "ep.json")
    assert res.code == 8, (res.code, res.err[:200])
    assert res.out == ""
    assert listing(out_dir) == []


@pytest.mark.parametrize(
    "target",
    [
        "mma_ai.visualization.episode.read_episode",
        "mma_ai.visualization.model_check.check_model",
        "mma_ai.visualization.summary.summarize_episode",
    ],
)
def test_inv004_ctrl_c_at_each_stage_exit130_and_silent_stdout(
    monkeypatch: pytest.MonkeyPatch, cli: Callable[..., Result], tmp_path: Path, target: str
) -> None:
    """INV-004 (AC-3): Ctrl-C ở bước đọc/đối chiếu/tóm tắt ⇒ mã 130 và không in tóm tắt."""

    def interrupt(*_a: Any, **_k: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(target, interrupt)
    p = write_json(tmp_path / "e.json", make_episode())
    res = cli("--episode", p, "--headless")
    assert res.code == 130, (res.code, res.err[:160])
    assert res.out == ""


def test_inv004_no_display_blocks_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """INV-004 (AC-3, AC-5): không màn hình + demo + --save-episode ⇒ mã 7 TRƯỚC khi ghi đĩa."""
    from mma_ai.visualization import display as display_mod

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(
        display_mod,
        "display_available",
        lambda: types.SimpleNamespace(available=False, reason="không có màn hình"),
    )
    ckpt = fake_checkpoint(_good_action)
    out = tmp_path / "x" / "ep.json"
    res = cli("--checkpoint", ckpt, "--save-episode", out)
    assert res.code == 7, (res.code, res.err[:160])
    assert not out.exists() and not out.parent.exists()


# ==============================================================================================
# INV-005 — chỉ đọc nguồn, không ghi đè tệp đã có (AC-1)
# ==============================================================================================


@pytest.mark.parametrize(
    "kind",
    ["file", "dir", "symlink_file", "symlink_dir", "fifo", "hardlink_to_ckpt", "ckpt_itself"],
)
def test_inv005_existing_destination_exit8_untouched(
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
    kind: str,
) -> None:
    """INV-005 (AC-1): đích đã tồn tại (tệp/thư mục/symlink/FIFO/hardlink/checkpoint) ⇒ mã 8."""
    ckpt = fake_checkpoint(_good_action)
    ckpt_bytes = ckpt.read_bytes()
    victim_dir = tmp_path / "victim"
    victim_dir.mkdir()
    sentinel = victim_dir / "nguoi-dung.txt"
    sentinel.write_text("DU-LIEU-QUAN-TRONG")
    dest = victim_dir / "dest.json"
    if kind == "file":
        dest.write_text("CU")
    elif kind == "dir":
        dest.mkdir()
    elif kind == "symlink_file":
        dest.symlink_to(sentinel)
    elif kind == "symlink_dir":
        dest.symlink_to(tmp_path)
    elif kind == "fifo":
        os.mkfifo(dest)
    elif kind == "hardlink_to_ckpt":
        os.link(ckpt, dest)
    else:
        dest = Path(os.path.join(str(ckpt.parent), "..", "checkpoints", ckpt.name))
    before = listing(tmp_path)
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", dest)
    assert res.code == 8, (kind, res.code, res.err[:200])
    assert listing(tmp_path) == before
    assert sentinel.read_text() == "DU-LIEU-QUAN-TRONG"
    assert ckpt.read_bytes() == ckpt_bytes


@pytest.mark.xfail(
    strict=False,
    reason="F-004: đích là symlink treo — Path.exists() False nên bị thay êm bằng tệp thường "
    "(mất liên kết người dùng đặt), không mã 8",
)
def test_inv005_dangling_symlink_destination_not_replaced(
    cli: Callable[..., Result], fake_checkpoint: Callable[..., Path], tmp_path: Path
) -> None:
    """INV-005 (AC-1): symlink treo là một mục đã tồn tại ⇒ mã 8 và liên kết còn nguyên."""
    ckpt = fake_checkpoint(_good_action)
    link = tmp_path / "link.episode.json"
    link.symlink_to(tmp_path / "khong-ton-tai.json")
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", link)
    assert res.code == 8, (res.code, res.err[:160])
    assert link.is_symlink()
    assert os.readlink(link) == str(tmp_path / "khong-ton-tai.json")


@pytest.mark.xfail(
    strict=False,
    reason="F-004: write_episode (API-VIS-0003) thay êm symlink treo vì chỉ kiểm exists()",
)
def test_inv005_write_episode_dangling_symlink_not_replaced(tmp_path: Path) -> None:
    """INV-005: API ghi trực tiếp cũng phải từ chối đích là symlink treo."""
    link = tmp_path / "l.json"
    link.symlink_to(tmp_path / "nowhere.json")
    with pytest.raises(EpisodeWriteError):
        write_episode(make_episode(), link)
    assert link.is_symlink()


@pytest.mark.xfail(
    strict=False,
    reason="F-003: kiểm exists() rồi os.replace ⇒ tệp do người dùng/tiến trình khác tạo "
    "GIỮA hai bước bị ghi đè êm (replace luôn ghi đè)",
)
def test_inv005_file_created_between_check_and_replace_is_not_overwritten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """INV-005 (AC-1): tệp xuất hiện giữa kiểm tra và hoán đổi nguyên tử không được bị ghi đè."""
    dest = tmp_path / "ep.json"
    real_replace = os.replace

    def racing_replace(src: Any, dst: Any) -> None:
        Path(dst).write_text("TIEN-TRINH-KHAC-VUA-GHI")
        real_replace(src, dst)

    monkeypatch.setattr(episode_mod, "os", _fake_namespace(os, replace=racing_replace))
    try:
        write_episode(make_episode(), dest)
    except EpisodeWriteError:
        pass
    assert dest.read_text() == "TIEN-TRINH-KHAC-VUA-GHI"


def test_inv005_second_write_to_same_path_refused_first_content_kept(tmp_path: Path) -> None:
    """INV-005: ghi hai lần cùng đích tuần tự ⇒ lần hai bị từ chối, nội dung lần một nguyên vẹn."""
    dest = tmp_path / "ep.json"
    write_episode(make_episode(), dest)
    first = dest.read_bytes()
    with pytest.raises(EpisodeWriteError):
        write_episode(make_episode(n_frames=5), dest)
    assert dest.read_bytes() == first
    assert listing(tmp_path) == ["ep.json"]


@pytest.mark.parametrize("kind", ["parent_is_file", "readonly_parent", "nul_in_path"])
def test_inv005_unwritable_destination_exit8_no_stray_files(
    cli: Callable[..., Result],
    fake_checkpoint: Callable[..., Path],
    tmp_path: Path,
    kind: str,
) -> None:
    """INV-005/INV-004 (AC-5): đích không ghi được ⇒ mã 8, không tạo gì ngoài ý muốn."""
    if kind == "readonly_parent" and os.geteuid() == 0:
        pytest.skip("root bỏ qua quyền thư mục")
    ckpt = fake_checkpoint(_good_action)
    base = tmp_path / "area"
    base.mkdir()
    if kind == "parent_is_file":
        (base / "f").write_text("x")
        dest: Path | str = base / "f" / "ep.json"
    elif kind == "readonly_parent":
        base.chmod(stat.S_IRUSR | stat.S_IXUSR)
        dest = base / "sub" / "ep.json"
    else:
        dest = str(base / "ep\0.json")
    before = listing(tmp_path)
    try:
        res = cli("--checkpoint", ckpt, "--headless", "--save-episode", dest)
    finally:
        base.chmod(stat.S_IRWXU)
    assert res.code == 8, (kind, res.code, res.err[:200])
    assert res.out == ""
    assert listing(tmp_path) == before


@pytest.mark.xfail(
    strict=False,
    reason="F-006: Path.exists() ném PermissionError khi thư mục tổ tiên không duyệt được; "
    "nằm ngoài khối try của bước ghi ⇒ rơi vào mã 1 thay vì mã 8 theo hợp đồng (thiếu quyền)",
)
def test_inv005_untraversable_ancestor_exit8(
    cli: Callable[..., Result], fake_checkpoint: Callable[..., Path], tmp_path: Path
) -> None:
    """INV-004/AC-5: thiếu quyền duyệt tổ tiên của đích ⇒ mã 8 (không phải mã 1)."""
    if os.geteuid() == 0:
        pytest.skip("root bỏ qua quyền thư mục")
    ckpt = fake_checkpoint(_good_action)
    locked = tmp_path / "locked"
    locked.mkdir()
    dest = locked / "sub" / "ep.json"
    locked.chmod(0)
    try:
        res = cli("--checkpoint", ckpt, "--headless", "--save-episode", dest)
    finally:
        locked.chmod(stat.S_IRWXU)
    assert res.code == 8, (res.code, res.err[:200])
    assert list(locked.iterdir()) == []


@pytest.mark.parametrize("flags", [[], ["--allow-model-mismatch"], ["--speed", "2", "--loop"]])
def test_inv005_replay_never_modifies_source_episode(
    cli: Callable[..., Result], tmp_path: Path, flags: list[str]
) -> None:
    """INV-005 (AC-1): replay --episode không đổi nội dung/mtime/quyền của episode nguồn."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    p = write_json(src_dir / "e.json", make_episode(sha=_flip_hex(_info().sha256, 3)))
    p.chmod(0o444)
    src_dir.chmod(0o555)
    try:
        st0 = p.stat()
        bytes0 = p.read_bytes()
        names0 = listing(tmp_path)
        cli("--episode", p, "--headless", *flags)
        st1 = p.stat()
        assert p.read_bytes() == bytes0
        assert (st1.st_mtime_ns, st1.st_size, st1.st_mode) == (
            st0.st_mtime_ns,
            st0.st_size,
            st0.st_mode,
        )
        assert listing(tmp_path) == names0
    finally:
        src_dir.chmod(stat.S_IRWXU)


def test_inv005_demo_never_modifies_checkpoint_or_run_dir(
    cli: Callable[..., Result], fake_checkpoint: Callable[..., Path], tmp_path: Path
) -> None:
    """INV-005 (AC-1): demo không đổi checkpoint hay thêm tệp vào thư mục run."""
    ckpt = fake_checkpoint(_good_action)
    run_dir = ckpt.parent.parent
    st0 = ckpt.stat()
    bytes0 = ckpt.read_bytes()
    run0 = listing(run_dir)
    out = tmp_path / "out" / "ep.json"
    res = cli("--checkpoint", ckpt, "--headless", "--save-episode", out)
    assert res.code == 0, res.err[:200]
    st1 = ckpt.stat()
    assert ckpt.read_bytes() == bytes0
    assert (st1.st_mtime_ns, st1.st_size) == (st0.st_mtime_ns, st0.st_size)
    assert listing(run_dir) == run0
    assert out.is_file()
    ep: Episode = read_episode(out)
    assert not non_finite_leaves(ep.to_dict())
