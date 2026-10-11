"""Mô-đun sinh và quản lý tập mục tiêu (mma_ai.environment.targets).

Hiện thực các giao diện và thực thể mục tiêu cho môi trường khuỷu tay:
- FR-010: Mục tiêu với tới được theo động học thuận, tất định theo seed.
- FR-011: Sinh hai tập train và test với giao rỗng và khoảng cách Euclid 3D tối thiểu.
- INV-001: Tập train và test không giao nhau và cách nhau ít nhất min_separation_m.
- INV-002: Tất định theo seed và cấu hình (cùng seed cho cùng tập mục tiêu).
- NFR-REPRO-001: Độ tái lập hoàn toàn giữa các lần chạy có cùng seed (fingerprint_sha256).
- API-002: Cung cấp TargetGenerator.generate, TargetSetPair.to_dict/from_dict.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

import mujoco
import numpy as np

from mma_ai.environment.env_config import ElbowEnvConfig, TargetConfig
from mma_ai.environment.errors import TargetConfigError

# Mã băm SHA-256 tham chiếu của tệp XML myoelbow_1dof6muscles.xml (research.md Q2)
DEFAULT_MYOELBOW_SHA256: str = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"


@dataclass(frozen=True)
class Target:
    """Mục tiêu đơn lẻ của đầu mút tay trên cung chuyển động khuỷu tay (FR-010)."""

    index: int
    angle_rad: float
    position_m: tuple[float, float, float]

    def to_dict(self) -> dict[str, Any]:
        """Chuyển đổi thành từ điển theo hợp đồng target-set.schema.json."""
        return {
            "index": self.index,
            "angle_rad": round(float(self.angle_rad), 6),
            "position_m": [round(float(coord), 6) for coord in self.position_m],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Target:
        """Khôi phục đối tượng Target từ từ điển hợp đồng."""
        pos = data["position_m"]
        return cls(
            index=int(data["index"]),
            angle_rad=float(data["angle_rad"]),
            position_m=(float(pos[0]), float(pos[1]), float(pos[2])),
        )


@dataclass(frozen=True)
class ArcInfo:
    """Thông tin hình học cung khả dụng và phân bổ khối (FR-011)."""

    usable_length_m: float
    n_blocks: int
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        """Chuyển đổi thông tin cung thành từ điển."""
        return {
            "usable_length_m": round(float(self.usable_length_m), 6),
            "n_blocks": int(self.n_blocks),
            "train_blocks": list(self.train_blocks),
            "test_blocks": list(self.test_blocks),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArcInfo:
        """Khôi phục ArcInfo từ từ điển."""
        return cls(
            usable_length_m=float(data["usable_length_m"]),
            n_blocks=int(data["n_blocks"]),
            train_blocks=tuple(int(x) for x in data["train_blocks"]),
            test_blocks=tuple(int(x) for x in data["test_blocks"]),
        )


@dataclass(frozen=True)
class TargetSet(Sequence[Target]):
    """Tập hợp mục tiêu cho một vai trò huấn luyện (train) hoặc kiểm thử (test)."""

    role: str
    targets: tuple[Target, ...]

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, index: int | slice) -> Any:
        return self.targets[index]

    def __iter__(self) -> Iterator[Target]:
        return iter(self.targets)

    def to_dict(self) -> list[dict[str, Any]]:
        """Xuất danh sách mục tiêu thành mảng từ điển theo schema."""
        return [t.to_dict() for t in self.targets]

    @classmethod
    def from_dict(cls, role: str, data: list[dict[str, Any]]) -> TargetSet:
        """Khôi phục TargetSet từ danh sách từ điển."""
        targets = tuple(Target.from_dict(item) for item in data)
        return cls(role=role, targets=targets)


def compute_fingerprint(
    train: Sequence[Target] | list[dict[str, Any]],
    test: Sequence[Target] | list[dict[str, Any]],
) -> str:
    """Tính mã băm fingerprint SHA-256 từ train và test chuẩn hoá (INV-002, NFR-REPRO-001)."""
    train_dicts = [t.to_dict() if isinstance(t, Target) else t for t in train]
    test_dicts = [t.to_dict() if isinstance(t, Target) else t for t in test]
    # Sắp xếp khoá json chuẩn hoá để so sánh tất định giữa hai lần sinh cùng seed
    canonical_payload = {"test": test_dicts, "train": train_dicts}
    serialized = json.dumps(canonical_payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TargetSetPair:
    """Cặp tập mục tiêu train và test sinh từ cùng một seed chủ (master seed) (FR-011, INV-001)."""

    master_seed: int
    model_sha256: str
    config: dict[str, Any]
    arc: ArcInfo
    train: TargetSet
    test: TargetSet
    min_cross_distance_m: float
    fingerprint_sha256: str
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Xuất toàn bộ cặp tập mục tiêu thành từ điển chuẩn theo target-set.schema.json."""
        return {
            "schema_version": self.schema_version,
            "master_seed": self.master_seed,
            "model_sha256": self.model_sha256,
            "config": dict(self.config),
            "arc": self.arc.to_dict(),
            "train": self.train.to_dict(),
            "test": self.test.to_dict(),
            "min_cross_distance_m": round(float(self.min_cross_distance_m), 6),
            "fingerprint_sha256": self.fingerprint_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetSetPair:
        """Khôi phục TargetSetPair từ từ điển hợp đồng."""
        return cls(
            schema_version=str(data.get("schema_version", "1.0.0")),
            master_seed=int(data["master_seed"]),
            model_sha256=str(data["model_sha256"]),
            config=dict(data["config"]),
            arc=ArcInfo.from_dict(data["arc"]),
            train=TargetSet.from_dict("train", data["train"]),
            test=TargetSet.from_dict("test", data["test"]),
            min_cross_distance_m=float(data["min_cross_distance_m"]),
            fingerprint_sha256=str(data["fingerprint_sha256"]),
        )


class TargetGenerator:
    """Bộ sinh mục tiêu (Target Generator) phân tầng trên cung chuyển động khuỷu tay."""

    def __init__(
        self,
        model: Any,
        cfg: Any = None,
        fingertip_site: str = "wrist",
        model_sha256: str | None = None,
    ) -> None:
        """Khởi tạo bộ sinh mục tiêu với mô hình MuJoCo và cấu hình (FR-010)."""
        self.model: Any = model
        self.fingertip_site: str = fingertip_site
        self.model_sha256: str = self._resolve_model_sha256(model, model_sha256)
        self.target_config: TargetConfig = self._resolve_target_config(cfg)

    def _resolve_model_sha256(self, model: Any, override_sha: str | None) -> str:
        """Xác định mã băm SHA-256 chuẩn của mô hình MuJoCo (FR-013)."""
        if override_sha is not None:
            return override_sha
        if hasattr(model, "sha256") and isinstance(model.sha256, str):
            return model.sha256
        if hasattr(model, "model_sha256") and isinstance(model.model_sha256, str):
            return model.model_sha256

        try:
            import myo_sim

            xml_path = myo_sim.get_xml_path("myoelbow")
            p = Path(xml_path)
            if p.is_file():
                return hashlib.sha256(p.read_bytes()).hexdigest()
        except Exception:
            pass

        return DEFAULT_MYOELBOW_SHA256

    def _resolve_target_config(self, cfg: Any) -> TargetConfig:
        """Trích xuất đối tượng TargetConfig từ các nguồn cấu hình khác nhau."""
        if cfg is None:
            loaded_env_cfg = ElbowEnvConfig.load()
            self.fingertip_site = loaded_env_cfg.fingertip_site
            return loaded_env_cfg.targets

        if isinstance(cfg, ElbowEnvConfig):
            self.fingertip_site = cfg.fingertip_site
            return cfg.targets

        if isinstance(cfg, TargetConfig):
            return cfg

        if isinstance(cfg, dict):
            if "fingertip_site" in cfg:
                self.fingertip_site = str(cfg["fingertip_site"])
            return TargetConfig(
                n_train=int(cfg["n_train"]),
                n_test=int(cfg["n_test"]),
                min_separation_m=float(cfg["min_separation_m"]),
                split_block_m=float(cfg["split_block_m"]),
                angle_margin_rad=float(cfg.get("angle_margin_rad", 0.05)),
                default_seed=int(cfg.get("default_seed", 42)),
            )

        raise TargetConfigError(
            f"Kiểu cấu hình không hợp lệ cho TargetGenerator: {type(cfg).__name__}"
        )

    def generate(self, seed: int | None = None) -> TargetSetPair:
        """Sinh cặp tập mục tiêu train và test tất định (FR-010, FR-011, INV-001, INV-002)."""
        active_seed = self.target_config.default_seed if seed is None else seed

        n_train = self.target_config.n_train
        n_test = self.target_config.n_test
        min_sep = self.target_config.min_separation_m
        split_block_m = self.target_config.split_block_m
        margin_rad = self.target_config.angle_margin_rad

        # 1. Kiểm tra tính khả thi của cấu hình (infeasible configuration check)
        if n_train <= 0 or n_test <= 0:
            raise TargetConfigError(
                f"Kích thước tập mục tiêu phải lớn hơn 0: n_train={n_train}, n_test={n_test}"
            )

        if min_sep <= 0:
            raise TargetConfigError(
                f"Khoảng cách tối thiểu phải lớn hơn 0: min_separation_m={min_sep}"
            )

        safety_factor = 1.1
        min_required_block_w = safety_factor * min_sep
        if split_block_m <= min_required_block_w:
            raise TargetConfigError(
                f"Bề rộng khối phân tách ({split_block_m} m) phải lớn hơn 1,1 lần "
                f"khoảng cách tối thiểu ({min_required_block_w:.4f} m)"
            )

        # 2. Xác định giới hạn góc khớp và site đầu mút tay
        jnt_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "r_elbow_flex")
        if jnt_id < 0:
            # Mô hình khớp đơn tổng quát
            jnt_id = 0
        jnt_range = self.model.jnt_range[jnt_id]
        site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, self.fingertip_site)
        if site_id < 0:
            raise TargetConfigError(
                f"Không tìm thấy site '{self.fingertip_site}' trong mô hình MuJoCo"
            )

        theta_lo = float(jnt_range[0] + margin_rad)
        theta_hi = float(jnt_range[1] - margin_rad)
        if theta_lo >= theta_hi:
            raise TargetConfigError(
                f"Lề an toàn góc ({margin_rad} rad) vượt quá nửa hành trình khớp "
                f"[{jnt_range[0]}, {jnt_range[1]}]"
            )

        # 3. Đo độ dài cung khả dụng bằng MjData riêng (không chạm dữ liệu episode, INV-003)
        calc_data = mujoco.MjData(self.model)
        n_samples = 1000
        thetas_eval = np.linspace(theta_lo, theta_hi, n_samples)
        positions = []
        for th in thetas_eval:
            calc_data.qpos[0] = th
            mujoco.mj_kinematics(self.model, calc_data)
            positions.append(calc_data.site_xpos[site_id].copy())
        positions_arr = np.array(positions)
        usable_length_m = float(np.sum(np.linalg.norm(np.diff(positions_arr, axis=0), axis=1)))

        n_blocks = int(usable_length_m // split_block_m)
        if n_blocks < 2:
            raise TargetConfigError(
                f"Số khối phân tách trên cung ({n_blocks}) nhỏ hơn 2, "
                f"không đủ để phân chia tập train và test với split_block_m={split_block_m} m "
                f"trên cung dài {usable_length_m:.4f} m"
            )

        # 4. Xáo trộn và phân bổ khối theo tỉ lệ kích thước tập
        rng = np.random.default_rng(active_seed)
        perm = rng.permutation(n_blocks)

        n_test_blocks = int(np.ceil(n_blocks * n_test / (n_train + n_test)))
        n_test_blocks = min(max(1, n_test_blocks), n_blocks - 1)

        test_blocks = tuple(sorted(int(x) for x in perm[:n_test_blocks]))
        train_blocks = tuple(sorted(int(x) for x in perm[n_test_blocks:]))

        # Thu hẹp mỗi khối ở hai biên bằng lề an toàn
        margin_m = safety_factor * min_sep / 2.0
        eff_block_w = split_block_m - 2.0 * margin_m

        # 5. Lấy mẫu phân tầng đều theo cung có nhiễu (stratified sampling)
        eval_data = mujoco.MjData(self.model)

        def _sample_targets(
            role: str, blocks: tuple[int, ...], n_points: int
        ) -> list[Target]:
            total_w = len(blocks) * eff_block_w
            stratum_w = total_w / n_points
            res: list[Target] = []
            for idx in range(n_points):
                u = float(rng.uniform())
                s_val = (idx + u) * stratum_w
                b_idx = min(int(s_val // eff_block_w), len(blocks) - 1)
                offset_in_block = s_val - b_idx * eff_block_w
                s_target = blocks[b_idx] * split_block_m + margin_m + offset_in_block

                # Ánh xạ cung s sang góc theta
                angle_rad = theta_lo + (s_target / usable_length_m) * (theta_hi - theta_lo)

                # Tính động học thuận trên MjData riêng
                eval_data.qpos[0] = angle_rad
                mujoco.mj_kinematics(self.model, eval_data)
                pos = tuple(float(x) for x in eval_data.site_xpos[site_id])

                res.append(
                    Target(
                        index=idx,
                        angle_rad=float(angle_rad),
                        position_m=(pos[0], pos[1], pos[2]),
                    )
                )
            return res

        train_targets = _sample_targets("train", train_blocks, n_train)
        test_targets = _sample_targets("test", test_blocks, n_test)

        # 6. Tự kiểm tra sau sinh: giao rỗng và khoảng cách Euclid 3D nhỏ nhất (INV-001)
        train_pos_arr = np.array([t.position_m for t in train_targets])
        test_pos_arr = np.array([t.position_m for t in test_targets])
        diff_matrix = train_pos_arr[:, np.newaxis, :] - test_pos_arr[np.newaxis, :, :]
        distance_matrix = np.linalg.norm(diff_matrix, axis=2)
        min_cross_distance_m = float(np.min(distance_matrix))

        if min_cross_distance_m < min_sep - 1e-9:
            raise TargetConfigError(
                f"Khoảng cách Euclid 3D nhỏ nhất giữa train và test ({min_cross_distance_m:.6f} m) "
                f"nhỏ hơn khoảng cách tối thiểu yêu cầu ({min_sep:.6f} m)"
            )

        # 7. Tính fingerprint SHA-256 từ train và test chuẩn hoá (INV-002, NFR-REPRO-001)
        fp_sha256 = compute_fingerprint(train_targets, test_targets)

        config_dict = {
            "n_train": n_train,
            "n_test": n_test,
            "min_separation_m": min_sep,
            "split_block_m": split_block_m,
            "angle_margin_rad": margin_rad,
            "fingertip_site": self.fingertip_site,
        }

        arc_info = ArcInfo(
            usable_length_m=round(usable_length_m, 6),
            n_blocks=n_blocks,
            train_blocks=train_blocks,
            test_blocks=test_blocks,
        )

        return TargetSetPair(
            master_seed=active_seed,
            model_sha256=self.model_sha256,
            config=config_dict,
            arc=arc_info,
            train=TargetSet(role="train", targets=tuple(train_targets)),
            test=TargetSet(role="test", targets=tuple(test_targets)),
            min_cross_distance_m=round(min_cross_distance_m, 6),
            fingerprint_sha256=fp_sha256,
        )


__all__: list[str] = [
    "ArcInfo",
    "DEFAULT_MYOELBOW_SHA256",
    "Target",
    "TargetGenerator",
    "TargetSet",
    "TargetSetPair",
    "compute_fingerprint",
]
