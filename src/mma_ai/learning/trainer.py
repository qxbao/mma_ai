"""Mô-đun điều phối vòng lặp huấn luyện PPO (mma_ai.learning.trainer).

Hiện thực lớp Trainer điều phối vòng lặp thu mẫu (rollout) -> GAE -> cập nhật chính sách,
đảm bảo các bất biến mô hình INV-002, INV-003, INV-004 và quản lý điểm kiểm tra an toàn.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.learning.checkpoint import (
    CheckpointMeta,
    LoadedCheckpoint,
    load_checkpoint,
    save_checkpoint,
)
from mma_ai.learning.errors import (
    CheckpointError,
    CheckpointIOError,
    NonFiniteError,
    TrainError,
)
from mma_ai.learning.manifest import (
    DEFAULT_MUSCLE_NAMES,
    build_manifest,
    write_manifest,
)
from mma_ai.learning.metrics_log import MetricsLogger
from mma_ai.learning.networks import ActorCritic
from mma_ai.learning.normalizer import RunningNorm
from mma_ai.learning.ppo import PPOAgent, compute_gae
from mma_ai.learning.progress import ProgressWriter
from mma_ai.learning.repro import seed_everything
from mma_ai.learning.train_config import TrainConfig


@dataclass(frozen=True)
class RunResult:
    """Kết quả hoàn thành của một tiến trình huấn luyện (run result)."""

    run_id: str
    status: str
    env_steps: int
    n_updates: int
    wall_clock_seconds: float
    env_steps_per_second: float
    checkpoints: list[CheckpointMeta]
    manifest_path: Path
    error: Exception | None = None


class Trainer:
    """Bộ điều phối huấn luyện PPO trên môi trường cơ bắp khuỷu tay."""

    def __init__(
        self,
        cfg: TrainConfig,
        env: Any,
        run_dir: str | Path | Any,
        *,
        resume_checkpoint: LoadedCheckpoint | str | Path | None = None,
    ) -> None:
        """Khởi tạo Trainer với cấu hình, môi trường và thư mục chạy."""
        # Bảo vệ bất biến INV-003: Chỉ làm việc với môi trường huấn luyện
        env_split = getattr(env, "split", None)
        if env_split is not None and env_split != "train":
            raise TrainError(
                f"Trainer chỉ chấp nhận môi trường với split='train' "
                f"(hiện tại: '{env_split}') (INV-003)."
            )

        self.cfg = cfg
        self.env = env
        self.run_dir = Path(getattr(run_dir, "path", run_dir))
        self.run_id = str(getattr(run_dir, "run_id", self.run_dir.name))

        # Thiết lập hạt giống ngẫu nhiên gốc cho toàn bộ hệ thống
        seed_everything(cfg.seed, cfg)

        # Suy ra kích thước quan sát (observation dimension) và hành động (action dimension)
        obs_dim = 14
        if hasattr(env, "observation_space") and hasattr(env.observation_space, "shape"):
            obs_dim = int(env.observation_space.shape[0])

        act_dim = 6
        if hasattr(env, "action_space") and hasattr(env.action_space, "shape"):
            act_dim = int(env.action_space.shape[0])

        # Trích xuất danh sách tên 6 cơ bắp chuẩn cho ghi log số liệu
        self.muscle_names: list[str] = list(DEFAULT_MUSCLE_NAMES)
        if hasattr(env, "model_record") and callable(env.model_record):
            record = env.model_record()
            names = record.get("muscle_names")
            if isinstance(names, Sequence) and len(names) == 6:
                self.muscle_names = [str(n) for n in names]
        elif hasattr(env, "muscle_names") and len(env.muscle_names) == 6:
            self.muscle_names = [str(n) for n in env.muscle_names]

        # Khởi tạo mô hình mạng nơ-ron, bộ chuẩn hoá và thuật toán PPO
        self.model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=cfg)
        self.normalizer = RunningNorm(clip_obs=cfg.normalization.clip_obs)
        self.agent = PPOAgent(model=self.model, cfg=cfg)

        self.start_update_idx = 0
        self.start_env_steps = 0
        self.resumed_from: dict[str, Any] | None = None

        # Khôi phục trạng thái từ điểm kiểm tra (checkpoint) nếu có
        if resume_checkpoint is not None:
            self._restore_from_checkpoint(resume_checkpoint)

    def _restore_from_checkpoint(
        self,
        resume_checkpoint: LoadedCheckpoint | str | Path,
    ) -> None:
        """Khôi phục trạng thái bộ chuẩn hoá, mạng nơ-ron, optimizer và RNG từ checkpoint."""
        model_sha = getattr(self.env, "model_sha256", None)
        if model_sha is None and hasattr(self.env, "model_record"):
            model_sha = self.env.model_record().get("sha256")

        if isinstance(resume_checkpoint, (str, Path)):
            ckpt_path = Path(resume_checkpoint)
            loaded = load_checkpoint(
                ckpt_path,
                for_training=True,
                expected_cfg=self.cfg,
                expected_model_sha256=model_sha,
            )
            ckpt_rel_path = f"checkpoints/{ckpt_path.name}"
            ckpt_sha256 = loaded.raw_data.get("sha256", "0" * 64)
            resumed_run_id = loaded.raw_data.get("run_id", "parent_run")
        else:
            loaded = resume_checkpoint
            if model_sha and loaded.model_sha256 != model_sha:
                raise CheckpointError(
                    f"Từ chối huấn luyện tiếp do sai khác mã băm XML: "
                    f"checkpoint có '{loaded.model_sha256}', "
                    f"mô hình hiện tại có '{model_sha}'."
                )
            raw_path = loaded.raw_data.get("path", "checkpoints/checkpoint.pt")
            ckpt_rel_path = str(raw_path).lstrip("/")
            ckpt_sha256 = str(loaded.raw_data.get("sha256", "0" * 64))
            resumed_run_id = str(loaded.raw_data.get("run_id", "parent_run"))

        state_dict_payload: dict[str, Any] = {
            "actor": loaded.actor_state_dict,
            "critic": loaded.critic_state_dict,
            "log_std": (
                loaded.log_std if loaded.log_std is not None else self.agent.model.log_std
            ),
            "optimizer": loaded.optimizer_state_dict,
        }
        self.agent.load_state_dict(state_dict_payload)
        self.normalizer.load_state_dict(loaded.obs_normalizer_state_dict)

        # Khôi phục các trạng thái sinh số ngẫu nhiên
        torch.set_rng_state(loaded.rng_state["torch_cpu"])
        if torch.cuda.is_available() and "torch_cuda" in loaded.rng_state:
            torch.cuda.set_rng_state(loaded.rng_state["torch_cuda"])

        if "numpy" in loaded.rng_state and loaded.rng_state["numpy"]:
            try:
                self.agent._rng.bit_generator.state = loaded.rng_state["numpy"]
            except Exception:
                pass

        self.start_update_idx = int(loaded.update_idx)
        self.start_env_steps = int(loaded.env_steps)
        self.resumed_from = {
            "run_id": resumed_run_id,
            "checkpoint": ckpt_rel_path,
            "checkpoint_sha256": ckpt_sha256,
        }

    def _assert_train_split(self, info: Mapping[str, Any]) -> None:
        """Bảo vệ bất biến INV-003: Xác nhận mọi lượt reset chỉ dùng tập huấn luyện."""
        target_split = info.get("target_split")
        if target_split != "train":
            raise TrainError(
                f"Phát hiện mục tiêu không thuộc tập huấn luyện: '{target_split}' (INV-003)."
            )

    def _pad_muscle_activations(self, activations: np.ndarray) -> list[float]:
        """Chuẩn hoá vector kích thích cơ bắp về độ dài 6 cho các tệp ghi nhật ký."""
        act_list = [float(x) for x in activations[:6]]
        if len(act_list) < 6:
            act_list.extend([0.0] * (6 - len(act_list)))
        return act_list

    def run(self) -> RunResult:
        """Thực thi toàn bộ quy trình huấn luyện và lưu trữ các tạo tác (artifacts)."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        start_wall_clock = time.perf_counter()

        # Dựng và ghi hồ sơ thí nghiệm (run manifest) trạng thái running ban đầu
        initial_manifest = build_manifest(
            run_id=self.run_id,
            config=self.cfg,
            seed=self.cfg.seed,
            stage=self.cfg.stage,
            status="running",
            resumed_from=self.resumed_from,
            env=self.env,
        )
        write_manifest(self.run_dir, initial_manifest)

        # Khởi tạo các bộ ghi nhật ký và ảnh chụp tiến trình
        metrics_logger = MetricsLogger(self.run_dir, self.muscle_names)
        progress_writer = ProgressWriter(
            self.run_dir,
            snapshot_interval_s=self.cfg.ui.snapshot_interval_s,
            history_points=self.cfg.ui.history_points,
        )

        update_idx = self.start_update_idx
        env_steps = self.start_env_steps
        total_timesteps = self.cfg.schedule.total_timesteps
        n_steps = self.cfg.schedule.n_steps
        normalize_obs = self.cfg.normalization.normalize_obs

        saved_checkpoints: list[CheckpointMeta] = []
        head_mean_returns: list[float] = []
        episode_returns: list[float] = []
        current_episode_return = 0.0
        n_episodes = 0
        terminated_episodes = 0

        history_env_steps: list[int] = []
        history_mean_return: list[float | None] = []
        history_value_loss: list[float | None] = []
        last_loss_dict: dict[str, float] | None = None
        last_activations: list[float] = [0.0] * 6

        def _build_snapshot_payload(current_status: str) -> dict[str, Any]:
            elapsed_time = time.perf_counter() - start_wall_clock
            speed = env_steps / elapsed_time if elapsed_time > 0 else None
            m_return = float(np.mean(episode_returns[-10:])) if episode_returns else None
            last_path = saved_checkpoints[-1].path if saved_checkpoints else None
            last_idx = saved_checkpoints[-1].update_idx if saved_checkpoints else None

            return {
                "schema_version": "1.0.0",
                "run_id": self.run_id,
                "stage": self.cfg.stage,
                "seed": self.cfg.seed,
                "status": current_status,
                "update_idx": update_idx,
                "env_steps": env_steps,
                "total_steps": total_timesteps,
                "env_steps_per_second": speed,
                "mean_return": m_return,
                "loss": last_loss_dict,
                "activation": {
                    "muscle_names": self.muscle_names,
                    "mean": last_activations,
                },
                "checkpoint": {
                    "count": len(saved_checkpoints),
                    "every_updates": self.cfg.checkpoint.every_updates,
                    "last_path": last_path,
                    "last_update_idx": last_idx,
                },
                "history": {
                    "env_steps": history_env_steps,
                    "mean_return": history_mean_return,
                    "value_loss": history_value_loss,
                },
            }

        try:
            # Thiết lập lại môi trường lần đầu kèm seed gốc
            obs, info = self.env.reset(seed=self.cfg.seed)
            self._assert_train_split(info)
            if normalize_obs:
                self.normalizer.update(obs)

            # Ghi ảnh chụp tiến trình đầu tiên
            progress_writer.write(_build_snapshot_payload("running"), final=False)

            while env_steps < total_timesteps:
                rollout_obs: list[torch.Tensor] = []
                rollout_actions: list[torch.Tensor] = []
                rollout_log_probs: list[torch.Tensor] = []
                rollout_rewards: list[float] = []
                rollout_dones: list[bool] = []
                rollout_values: list[torch.Tensor] = []
                rollout_activations: list[np.ndarray] = []

                # Vòng lặp thu mẫu (rollout collection loop)
                for _ in range(n_steps):
                    obs_input = self.normalizer(obs) if normalize_obs else obs
                    obs_tensor = torch.as_tensor(obs_input, dtype=torch.float32).unsqueeze(0)

                    with torch.no_grad():
                        # Hành động trả về luôn là kích thích cơ sigmoid(a) trong (0, 1)^6 (INV-002)
                        action_tensor, log_prob_tensor, value_tensor = self.agent.model.act(
                            obs_tensor, deterministic=False
                        )

                    action_np = action_tensor.squeeze(0).cpu().numpy()
                    next_obs, reward, terminated, truncated, step_info = self.env.step(action_np)

                    env_steps += 1
                    current_episode_return += float(reward)
                    done = bool(terminated or truncated)

                    rollout_obs.append(obs_tensor.squeeze(0))
                    rollout_actions.append(action_tensor.squeeze(0))
                    rollout_log_probs.append(log_prob_tensor.squeeze(0))
                    rollout_rewards.append(float(reward))
                    rollout_dones.append(done)
                    rollout_values.append(value_tensor.squeeze(0))
                    rollout_activations.append(action_np)

                    if normalize_obs:
                        self.normalizer.update(next_obs)

                    # Ghi ảnh chụp tiến trình nguyên tử trong lúc thu mẫu (>= 1s/lần)
                    progress_writer.write(_build_snapshot_payload("running"), final=False)

                    if done:
                        n_episodes += 1
                        if terminated:
                            terminated_episodes += 1
                        episode_returns.append(current_episode_return)
                        current_episode_return = 0.0

                        # Các lần reset tiếp theo không truyền seed lại
                        next_obs, reset_info = self.env.reset()
                        self._assert_train_split(reset_info)
                        if normalize_obs:
                            self.normalizer.update(next_obs)

                    obs = next_obs
                    if env_steps >= total_timesteps:
                        break

                # Tính toán giá trị trạng thái cuối (last_value) cho GAE
                if rollout_dones[-1]:
                    last_val = 0.0
                else:
                    last_obs_input = self.normalizer(obs) if normalize_obs else obs
                    last_obs_tensor = torch.as_tensor(
                        last_obs_input, dtype=torch.float32
                    ).unsqueeze(0)
                    with torch.no_grad():
                        last_val = float(
                            self.agent.model.critic(last_obs_tensor).squeeze().item()
                        )

                # Chuyển đổi dữ liệu sang Tensor để tính toán lợi thế (advantages)
                rewards_tensor = torch.tensor(rollout_rewards, dtype=torch.float32)
                values_tensor = torch.stack(rollout_values)
                dones_tensor = torch.tensor(rollout_dones, dtype=torch.bool)

                advantages = compute_gae(
                    rewards_tensor,
                    values_tensor,
                    dones_tensor,
                    last_value=last_val,
                    gamma=self.cfg.ppo.gamma,
                    gae_lambda=self.cfg.ppo.gae_lambda,
                )
                returns = advantages + values_tensor

                buffer = {
                    "observations": torch.stack(rollout_obs),
                    "actions": torch.stack(rollout_actions),
                    "old_log_probs": torch.stack(rollout_log_probs),
                    "returns": returns,
                    "advantages": advantages,
                }

                # Cập nhật chính sách PPO (quét tính hữu hạn NaN/Inf)
                update_idx += 1
                try:
                    update_stats = self.agent.update(buffer)
                except NonFiniteError as non_finite_err:
                    setattr(non_finite_err, "update_idx", update_idx)
                    raise non_finite_err

                # Tính toán các chỉ số cập nhật
                elapsed_seconds = time.perf_counter() - start_wall_clock
                steps_per_sec = env_steps / elapsed_seconds if elapsed_seconds > 0 else 0.0
                current_mean_return = (
                    float(np.mean(episode_returns[-10:])) if episode_returns else 0.0
                )

                if len(head_mean_returns) < self.cfg.reproducibility.head_updates:
                    head_mean_returns.append(current_mean_return)

                mean_act_raw = np.mean(rollout_activations, axis=0)
                last_activations = self._pad_muscle_activations(mean_act_raw)
                last_loss_dict = {
                    "policy": update_stats.policy_loss,
                    "value": update_stats.value_loss,
                    "entropy": update_stats.entropy,
                }

                # Ghi nhật ký số liệu TensorBoard và metrics.jsonl
                metrics_logger.log_update(
                    update=update_idx,
                    env_steps=env_steps,
                    policy_loss=update_stats.policy_loss,
                    value_loss=update_stats.value_loss,
                    entropy=update_stats.entropy,
                    mean_return=current_mean_return,
                    activations=last_activations,
                    env_steps_per_second=steps_per_sec,
                )

                history_env_steps.append(env_steps)
                history_mean_return.append(current_mean_return)
                history_value_loss.append(update_stats.value_loss)

                # Lưu điểm kiểm tra định kỳ (periodic checkpoint)
                if update_idx % self.cfg.checkpoint.every_updates == 0:
                    agent_rng_state = (
                        copy.deepcopy(self.agent._rng.bit_generator.state)
                        if hasattr(self.agent, "_rng") and hasattr(self.agent._rng, "bit_generator")
                        else None
                    )
                    ckpt_ctx = {
                        "update_idx": update_idx,
                        "env_steps": env_steps,
                        "model_sha256": getattr(self.env, "model_sha256", ""),
                        "seed": self.cfg.seed,
                        "config": self.cfg,
                        "obs_normalizer": self.normalizer,
                        "rng_state": {
                            "numpy": agent_rng_state,
                        },
                    }
                    periodic_meta = save_checkpoint(
                        self.agent, self.run_dir, kind="periodic", ctx=ckpt_ctx
                    )
                    saved_checkpoints.append(periodic_meta)

                progress_writer.write(_build_snapshot_payload("running"), final=False)

            # LUÔN lưu điểm kiểm tra cuối cùng (final checkpoint) khi kết thúc
            final_agent_rng = (
                copy.deepcopy(self.agent._rng.bit_generator.state)
                if hasattr(self.agent, "_rng") and hasattr(self.agent._rng, "bit_generator")
                else None
            )
            final_ctx = {
                "update_idx": update_idx,
                "env_steps": env_steps,
                "model_sha256": getattr(self.env, "model_sha256", ""),
                "seed": self.cfg.seed,
                "config": self.cfg,
                "obs_normalizer": self.normalizer,
                "rng_state": {
                    "numpy": final_agent_rng,
                },
            }
            final_meta = save_checkpoint(self.agent, self.run_dir, kind="final", ctx=final_ctx)
            saved_checkpoints.append(final_meta)

            # Ghi ảnh chụp tiến trình cuối cùng
            progress_writer.write(_build_snapshot_payload("done"), final=True)
            metrics_logger.close()

            total_elapsed = time.perf_counter() - start_wall_clock
            final_throughput = env_steps / total_elapsed if total_elapsed > 0 else 0.0

            reward_metrics_payload = {
                "n_updates": update_idx,
                "n_episodes": n_episodes,
                "head_updates": len(head_mean_returns),
                "head_mean_return": head_mean_returns,
                "first_mean_return": head_mean_returns[0] if head_mean_returns else None,
                "last_mean_return": head_mean_returns[-1] if head_mean_returns else None,
                "success_rate": (
                    (terminated_episodes / n_episodes) if n_episodes > 0 else 0.0
                ),
            }

            throughput_payload = {
                "env_steps": env_steps,
                "env_steps_per_second": final_throughput,
                "wall_clock_seconds": total_elapsed,
            }

            final_manifest = build_manifest(
                base_manifest=initial_manifest,
                status="done",
                checkpoints=saved_checkpoints,
                reward_metrics=reward_metrics_payload,
                throughput=throughput_payload,
            )
            manifest_file = write_manifest(self.run_dir, final_manifest)

            return RunResult(
                run_id=self.run_id,
                status="done",
                env_steps=env_steps,
                n_updates=update_idx,
                wall_clock_seconds=total_elapsed,
                env_steps_per_second=final_throughput,
                checkpoints=saved_checkpoints,
                manifest_path=manifest_file,
            )

        except (NonFiniteError, PhysicsInstabilityError, CheckpointIOError, CheckpointError) as err:
            metrics_logger.close()
            total_elapsed = time.perf_counter() - start_wall_clock
            final_throughput = env_steps / total_elapsed if total_elapsed > 0 else 0.0

            progress_writer.write(_build_snapshot_payload("error"), final=True)

            error_manifest = build_manifest(
                base_manifest=initial_manifest,
                status="error",
                checkpoints=saved_checkpoints,
                error=err,
                throughput={
                    "env_steps": env_steps,
                    "env_steps_per_second": final_throughput,
                    "wall_clock_seconds": total_elapsed,
                },
            )
            write_manifest(self.run_dir, error_manifest)
            raise err

        except KeyboardInterrupt as interrupt_err:
            metrics_logger.close()
            total_elapsed = time.perf_counter() - start_wall_clock
            final_throughput = env_steps / total_elapsed if total_elapsed > 0 else 0.0

            progress_writer.write(_build_snapshot_payload("interrupted"), final=True)

            interrupted_manifest = build_manifest(
                base_manifest=initial_manifest,
                status="interrupted",
                checkpoints=saved_checkpoints,
                throughput={
                    "env_steps": env_steps,
                    "env_steps_per_second": final_throughput,
                    "wall_clock_seconds": total_elapsed,
                },
            )
            write_manifest(self.run_dir, interrupted_manifest)
            raise interrupt_err
