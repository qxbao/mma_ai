"""Mô-đun điều phối phát lại mô phỏng 3D và phiên demo (mma_ai.visualization.replay).

Hiện thực hợp đồng API-VIS-0011 và lệnh dòng lệnh CMD-VIS-0001:
- FR-001: Phát lại chuỗi khung hình theo đúng thứ tự đã ghi trong MuJoCo Viewer.
- FR-002: Chạy demo một episode từ điểm kiểm tra (checkpoint) bằng chính sách xác định.
- FR-008: Ghi episode nguyên tử (atomic write) qua tệp tạm và từ chối ghi đè (overwrite).
- FR-010: Chế độ không màn hình (--headless) in tóm tắt JSON ra stdout.
- FR-011: Kiểm tra màn hình hiển thị (display), thoát mã 7 trong <= 5 s khi thiếu hiển thị.
- FR-012: Đối chiếu mô hình (model check), báo lỗi mã 6 hoặc cảnh báo khi lệch mô hình.
- FR-013: Báo lỗi mã 2, 4, 5 khi tham số, checkpoint hoặc episode không hợp lệ.
- FR-016: Chọn mục tiêu qua chỉ số (target_index) và phân tách (split).
- FR-018: Định dạng đường dẫn tương đối và thông báo lỗi tiếng Việt kèm ngữ cảnh.
- INV-001: Ngăn chặn phát lại sai ngầm, duy trì cảnh báo trên HUD khi có cờ cho phép.
- INV-004: Xử lý ngoại lệ chuẩn, dọn dẹp tệp tạm khi ngắt Ctrl-C, trả mã 130.
- INV-005: Hoạt động chỉ đọc đối với tệp nguồn (read-only source).
- API-VIS-0011: run_replay(args) -> int.
- CMD-VIS-0001: Hợp đồng dòng lệnh với các mã thoát:
  0 (thành công), 1 (lỗi không lường trước/mất ổn định), 2 (tham số sai),
  4 (checkpoint lỗi), 5 (episode lỗi), 6 (lệch mô hình), 7 (thiếu màn hình),
  8 (lỗi ghi tệp), 130 (ngắt Ctrl-C).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence

from mma_ai.visualization.errors import (
    DemoUnstable,
    EpisodeInvalid,
    EpisodeNotFound,
    EpisodeWriteError,
    ModelMismatch,
    ReplayConfigError,
)
from mma_ai.visualization.replay_config import ReplayConfig

_viewer_was_opened: bool = False
_last_viewer_sink: Any | None = None

__all__: list[str] = [
    "get_active_viewer_sink",
    "reset_viewer_opened",
    "run_replay",
    "was_viewer_opened",
]


def was_viewer_opened() -> bool:
    """Kiểm tra xem MuJoCo Viewer có được mở trong phiên chạy gần nhất hay không."""
    return _viewer_was_opened


def reset_viewer_opened() -> None:
    """Đặt lại trạng thái theo dõi mở MuJoCo Viewer."""
    global _viewer_was_opened, _last_viewer_sink
    _viewer_was_opened = False
    _last_viewer_sink = None


def get_active_viewer_sink() -> Any | None:
    """Lấy thể hiện bộ nhận khung hình ViewerSink đang hoạt động hoặc gần nhất."""
    return _last_viewer_sink


def _mark_viewer_opened(sink: Any) -> None:
    """Đánh dấu MuJoCo Viewer đã được mở trong phiên chạy và lưu tham chiếu sink."""
    global _viewer_was_opened, _last_viewer_sink
    _viewer_was_opened = True
    _last_viewer_sink = sink


class _ReplayArgumentParser(argparse.ArgumentParser):
    """Bộ phân tích cú pháp dòng lệnh tuỳ biến ngăn chặn SystemExit ngoài ý muốn."""

    def error(self, message: str) -> NoReturn:
        """Ném ngoại lệ ReplayConfigError thay vì gọi sys.exit()."""
        raise ReplayConfigError(f"Lỗi tham số dòng lệnh (command-line argument error): {message}")


def _build_parser() -> _ReplayArgumentParser:
    """Xây dựng bộ phân tích cú pháp dòng lệnh theo hợp đồng CMD-VIS-0001."""
    parser = _ReplayArgumentParser(
        prog="replay",
        description=(
            "Phát lại mô phỏng 3D hoặc chạy demo khuỷu tay do cơ điều khiển (CMD-VIS-0001)."
        ),
        add_help=True,
    )
    parser.add_argument(
        "--episode",
        type=str,
        default=None,
        help="Đường dẫn tới tệp episode đã lưu phục vụ phát lại 3D.",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Đường dẫn tới tệp checkpoint (.pt hoặc latest.json) phục vụ phiên demo.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Chế độ không mở giao diện đồ hoạ (headless mode), in tóm tắt JSON ra stdout.",
    )
    parser.add_argument(
        "--save-episode",
        type=str,
        default=None,
        help="Đường dẫn lưu tệp episode mới từ phiên demo (chỉ dùng với --checkpoint).",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Hệ số tốc độ phát lại (> 0, mặc định 1.0 thời gian thực).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=False,
        help="Phát lặp lại liên tục cho tới khi người dùng đóng cửa sổ.",
    )
    parser.add_argument(
        "--allow-model-mismatch",
        action="store_true",
        default=False,
        help="Cho phép tiếp tục phát khi mã băm XML mô hình bị lệch nhưng cấu trúc tương thích.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=None,
        choices=["train", "test"],
        help="Phân tách tập mục tiêu ('train' hoặc 'test', chỉ dùng với --checkpoint).",
    )
    parser.add_argument(
        "--target-index",
        type=int,
        default=None,
        help="Chỉ số mục tiêu trong tập chỉ định (chỉ dùng với --checkpoint).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Hạt giống ngẫu nhiên (seed) khởi tạo mô phỏng (chỉ dùng với --checkpoint).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Đường dẫn tệp cấu hình YAML tuỳ biến (mặc định dùng replay.yaml đóng gói).",
    )
    return parser


def _parse_cli_args(
    args: Sequence[str] | argparse.Namespace | None,
) -> tuple[argparse.Namespace | None, int | None]:
    """Phân tích các đối số dòng lệnh thành Namespace và mã thoát nếu gặp lỗi."""
    if isinstance(args, argparse.Namespace):
        return args, None

    parser = _build_parser()
    argv_list = list(args) if args is not None else sys.argv[1:]

    try:
        parsed_ns = parser.parse_args(argv_list)
        return parsed_ns, None
    except SystemExit as err:
        # Khi người dùng gọi --help, exit code là 0
        return None, 0 if err.code == 0 else 2
    except ReplayConfigError as err:
        sys.stderr.write(f"{err}\n")
        sys.stderr.flush()
        return None, 2
    except Exception as err:
        sys.stderr.write(f"Lỗi tham số dòng lệnh không hợp lệ: {err}\n")
        sys.stderr.flush()
        return None, 2


def run_replay(args: Sequence[str] | argparse.Namespace | None = None) -> int:
    """Điều phối toàn bộ quy trình phát lại 3D hoặc chạy demo (API-VIS-0011).

    Tuân thủ nghiêm ngặt thứ tự 7 bước bắt buộc theo hợp đồng contracts/cli.md:
    (1) Kiểm tra tham số và nạp cấu hình -> mã thoát 2 nếu sai.
    (2) Nạp nguồn (đọc episode hoặc checkpoint) -> mã thoát 5/4 nếu lỗi.
    (3) Đối chiếu mô hình và thực thi bất biến -> mã thoát 6 nếu lệch.
    (4) Kiểm tra tính khả dụng của màn hình hiển thị -> mã thoát 7 nếu thiếu.
    (5) Thực thi mô phỏng demo nếu ở chế độ checkpoint -> mã thoát 1 nếu mất ổn định.
    (6) Ghi episode nếu có cờ --save-episode TRƯỚC khi mở viewer -> mã thoát 8 nếu lỗi.
    (7) Xuất tóm tắt JSON nếu --headless; ngược lại mở MuJoCo Viewer và phát lại.

    Args:
        args: Danh sách chuỗi tham số dòng lệnh hoặc đối tượng argparse.Namespace.

    Returns:
        Mã thoát nguyên (exit code) tương ứng theo bảng mã chuẩn.
    """
    reset_viewer_opened()
    save_path_obj: Path | None = None

    try:
        # ==============================================================================
        # BƯỚC 1: KIỂM TRA THAM SỐ VÀ NẠP CẤU HÌNH (MÃ THOÁT 2)
        # ==============================================================================
        parsed_args, parse_exit = _parse_cli_args(args)
        if parse_exit is not None:
            return parse_exit
        assert parsed_args is not None

        # 1.1 Kiểm tra tính loại trừ lẫn nhau của chế độ nguồn
        has_ep = bool(parsed_args.episode)
        has_ckpt = bool(parsed_args.checkpoint)

        if not has_ep and not has_ckpt:
            sys.stderr.write(
                "Lỗi tham số dòng lệnh: Phải chỉ định đúng một trong hai chế độ: "
                "--episode <đường-dẫn> hoặc --checkpoint <đường-dẫn>.\n"
            )
            sys.stderr.flush()
            return 2

        if has_ep and has_ckpt:
            sys.stderr.write(
                "Lỗi tham số dòng lệnh: Không thể sử dụng đồng thời cả hai chế độ "
                "--episode và --checkpoint. Vui lòng chỉ chọn một chế độ.\n"
            )
            sys.stderr.flush()
            return 2

        # 1.2 Kiểm tra các cờ dành riêng cho checkpoint khi chạy chế độ --episode
        if has_ep:
            if parsed_args.split is not None:
                sys.stderr.write(
                    "Lỗi tham số dòng lệnh: Cờ phân tách mục tiêu (--split) chỉ áp dụng cho "
                    "chế độ demo (--checkpoint), không hợp lệ khi chạy --episode.\n"
                )
                sys.stderr.flush()
                return 2

            if parsed_args.target_index is not None:
                sys.stderr.write(
                    "Lỗi tham số dòng lệnh: Cờ chỉ số mục tiêu (--target-index) chỉ áp dụng cho "
                    "chế độ demo (--checkpoint), không hợp lệ khi chạy --episode.\n"
                )
                sys.stderr.flush()
                return 2

            if parsed_args.seed is not None:
                sys.stderr.write(
                    "Lỗi tham số dòng lệnh: Cờ hạt giống ngẫu nhiên (--seed) chỉ áp dụng cho "
                    "chế độ demo (--checkpoint), không hợp lệ khi chạy --episode.\n"
                )
                sys.stderr.flush()
                return 2

            if parsed_args.save_episode is not None:
                sys.stderr.write(
                    "Lỗi tham số dòng lệnh: Cờ lưu episode (--save-episode) chỉ áp dụng cho "
                    "chế độ demo (--checkpoint), không hợp lệ khi chạy --episode.\n"
                )
                sys.stderr.flush()
                return 2

        # 1.3 Kiểm tra hệ số tốc độ phát lại (playback speed)
        if parsed_args.speed is not None and parsed_args.speed <= 0:
            sys.stderr.write(
                f"Lỗi tham số dòng lệnh: Hệ số tốc độ phát lại (--speed) phải lớn hơn 0, "
                f"nhận giá trị không hợp lệ: {parsed_args.speed}.\n"
            )
            sys.stderr.flush()
            return 2

        # 1.4 Kiểm tra chỉ số mục tiêu cơ bản
        if parsed_args.target_index is not None and parsed_args.target_index < 0:
            sys.stderr.write(
                f"Lỗi tham số dòng lệnh: Chỉ số mục tiêu (--target-index) không được âm: "
                f"{parsed_args.target_index}.\n"
            )
            sys.stderr.flush()
            return 2

        # 1.5 Xây dựng từ điển ghi đè (overrides) và nạp cấu hình ReplayConfig
        overrides: dict[str, Any] = {}
        if parsed_args.speed is not None:
            overrides["speed"] = float(parsed_args.speed)
        if parsed_args.loop:
            overrides["loop"] = True
        if parsed_args.split is not None:
            overrides["split"] = str(parsed_args.split)
        if parsed_args.target_index is not None:
            overrides["target_index"] = int(parsed_args.target_index)
        if parsed_args.seed is not None:
            overrides["seed"] = int(parsed_args.seed)

        try:
            cfg = ReplayConfig.load(path=parsed_args.config, overrides=overrides)
        except ReplayConfigError as err:
            sys.stderr.write(f"Lỗi cấu hình phát lại (replay config error): {err}\n")
            sys.stderr.flush()
            return 2
        except Exception as err:
            sys.stderr.write(f"Lỗi nạp cấu hình phát lại: {err}\n")
            sys.stderr.flush()
            return 2

        # ==============================================================================
        # BƯỚC 2: NẠP NGUỒN DỮ LIỆU (MÃ THOÁT 5 HOẶC 4)
        # ==============================================================================
        episode: Any = None
        loaded_ckpt: Any = None
        policy: Any = None
        current_model_sha256 = ""
        loaded_model: Any = None

        # Nạp trước thông tin mô hình vật lý hiện tại của hệ thống để đối chiếu
        try:
            from mma_ai.physics.body_model import load_muscle_model

            loaded_model = load_muscle_model("myoelbow")
            current_model_sha256 = loaded_model.info.sha256
        except Exception as err:
            sys.stderr.write(
                f"Lỗi khởi tạo mô hình vật lý cơ bắp hiện tại (muscle model error): {err}\n"
            )
            sys.stderr.flush()
            return 1

        if has_ep:
            # Chế độ 2.1: Đọc tệp episode đã ghi
            from mma_ai.visualization.episode import read_episode

            ep_path = Path(str(parsed_args.episode))
            try:
                episode = read_episode(ep_path)
            except EpisodeNotFound as err:
                sys.stderr.write(f"Lỗi không tìm thấy tệp episode: {err}\n")
                sys.stderr.flush()
                return 5
            except EpisodeInvalid as err:
                sys.stderr.write(f"Lỗi tệp episode không hợp lệ: {err}\n")
                sys.stderr.flush()
                return 5
            except Exception as err:
                sys.stderr.write(f"Lỗi đọc tệp episode tại '{ep_path}': {err}\n")
                sys.stderr.flush()
                return 5
        else:
            # Chế độ 2.2: Nạp checkpoint cho phiên demo
            ckpt_path = Path(str(parsed_args.checkpoint))
            if not ckpt_path.exists():
                sys.stderr.write(
                    f"Lỗi điểm kiểm tra không tồn tại: Tệp checkpoint tại '{ckpt_path}' "
                    "không tồn tại trên hệ thống ổ đĩa.\n"
                )
                sys.stderr.flush()
                return 4

            try:
                # Nhập lười mô-đun checkpoint học máy (FR-015)
                from mma_ai.learning.checkpoint import load_checkpoint, load_policy
                from mma_ai.learning.errors import CheckpointError

                loaded_ckpt = load_checkpoint(ckpt_path, for_training=False)
                policy = load_policy(ckpt_path)
            except ImportError as err:
                sys.stderr.write(
                    f"Lỗi thiếu thư viện học máy: Cần cài đặt gói bổ sung extra 'rl' "
                    f"để nạp checkpoint demo ({err}).\n"
                )
                sys.stderr.flush()
                return 4
            except CheckpointError as err:
                sys.stderr.write(f"Lỗi checkpoint không sử dụng được: {err}\n")
                sys.stderr.flush()
                return 4
            except Exception as err:
                sys.stderr.write(f"Lỗi không thể nạp checkpoint tại '{ckpt_path}': {err}\n")
                sys.stderr.flush()
                return 4

            # Kiểm tra mã băm XML mô hình lưu trong checkpoint
            ckpt_model_sha = getattr(loaded_ckpt, "model_sha256", "")
            if ckpt_model_sha and ckpt_model_sha != current_model_sha256:
                sys.stderr.write(
                    f"Lỗi checkpoint không tương thích: Mã băm XML mô hình của checkpoint "
                    f"'{ckpt_model_sha}' khác với mô hình hiện tại '{current_model_sha256}'.\n"
                )
                sys.stderr.flush()
                return 4

        # ==============================================================================
        # BƯỚC 3: KIỂM TRA LỆCH MÔ HÌNH VÀ BẤT BIẾN (MÃ THOÁT 6)
        # ==============================================================================
        from mma_ai.visualization.model_check import ModelCheck, check_model, enforce

        current_model_info = {
            "sha256": current_model_sha256,
            "nq": loaded_model.model.nq,
            "nv": loaded_model.model.nv,
            "muscle_names": loaded_model.info.muscle_names,
        }

        if has_ep:
            model_check_res = check_model(episode, current_model_info)
            try:
                enforce(model_check_res, allow_mismatch=parsed_args.allow_model_mismatch)
            except ModelMismatch as err:
                sys.stderr.write(f"Lỗi lệch mô hình mô phỏng (model mismatch): {err}\n")
                sys.stderr.flush()
                return 6
        else:
            # Ở chế độ demo, episode sẽ được sinh trực tiếp từ mô hình hiện tại
            model_check_res = ModelCheck(
                match=True,
                compatible=True,
                episode_sha256=current_model_sha256,
                current_sha256=current_model_sha256,
                reasons=[],
            )

        # ==============================================================================
        # BƯỚC 4: KIỂM TRA MÀN HÌNH HIỂN THỊ (MÃ THOÁT 7)
        # ==============================================================================
        if not parsed_args.headless:
            from mma_ai.visualization.display import display_available

            disp_status = display_available()
            if not disp_status.available:
                sys.stderr.write(f"Lỗi hiển thị giao diện đồ hoạ: {disp_status.reason}\n")
                sys.stderr.flush()
                return 7

        # ==============================================================================
        # BƯỚC 5: CHẠY DEMO THU BẢN GHI EPISODE (MÃ THOÁT 1 NẾU MẤT ỔN ĐỊNH)
        # ==============================================================================
        if has_ckpt:
            from mma_ai.environment.single_agent import ElbowReachEnv
            from mma_ai.visualization.recorder import record_episode

            # Khởi tạo môi trường mô phỏng cánh tay khuỷu
            env = ElbowReachEnv(split=cfg.demo.split)

            # Kiểm tra chỉ số mục tiêu trong phạm vi tập mục tiêu
            target_set = env.targets.train if cfg.demo.split == "train" else env.targets.test
            n_targets = len(target_set.targets)
            if cfg.demo.target_index < 0 or cfg.demo.target_index >= n_targets:
                sys.stderr.write(
                    f"Lỗi tham số dòng lệnh: Chỉ số mục tiêu target_index={cfg.demo.target_index} "
                    f"vượt quá phạm vi của tập '{cfg.demo.split}' "
                    f"(kỳ vọng 0 <= target_index < {n_targets}).\n"
                )
                sys.stderr.flush()
                return 2

            try:
                episode = record_episode(
                    env,
                    policy,
                    split=cfg.demo.split,
                    target_index=cfg.demo.target_index,
                    seed=cfg.demo.seed,
                    source=parsed_args.checkpoint,
                )
            except DemoUnstable as err:
                sys.stderr.write(
                    f"Lỗi mô phỏng demo mất ổn định số học hoặc vật lý (demo unstable): {err}\n"
                )
                sys.stderr.flush()
                return 1
            except Exception as err:
                sys.stderr.write(f"Lỗi trong quá trình thực thi demo: {err}\n")
                sys.stderr.flush()
                return 1

        # ==============================================================================
        # BƯỚC 6: LƯU TỆP EPISODE NGUYÊN TỬ NẾU CÓ CỜ --SAVE-EPISODE (MÃ THOÁT 8)
        # ==============================================================================
        if parsed_args.save_episode is not None:
            save_path_obj = Path(str(parsed_args.save_episode))
            if save_path_obj.exists():
                sys.stderr.write(
                    f"Lỗi ghi tệp episode: Tệp đích '{save_path_obj}' đã tồn tại trên đĩa. "
                    "Theo bất biến INV-005, hệ thống từ chối ghi đè lên tệp có sẵn.\n"
                )
                sys.stderr.flush()
                return 8

            from mma_ai.visualization.episode import write_episode

            try:
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                write_episode(episode, save_path_obj)
            except EpisodeWriteError as err:
                sys.stderr.write(f"Lỗi không thể ghi tệp episode ra ổ đĩa: {err}\n")
                sys.stderr.flush()
                return 8
            except Exception as err:
                sys.stderr.write(f"Lỗi ghi tệp episode ra '{save_path_obj}': {err}\n")
                sys.stderr.flush()
                return 8

        # ==============================================================================
        # BƯỚC 7: XUẤT TÓM TẮT HOẶC MỞ CỬA SỔ MUJOCO VIEWER (MÃ THOÁT 0)
        # ==============================================================================
        if parsed_args.headless:
            # 7.1 Chế độ không màn hình (--headless)
            if parsed_args.speed is not None or parsed_args.loop:
                sys.stderr.write(
                    "Cảnh báo: Các cờ tuỳ chọn phát lại (--speed, --loop) bị bỏ qua "
                    "trong chế độ không màn hình (--headless).\n"
                )
                sys.stderr.flush()

            from mma_ai.visualization.summary import summarize_episode

            source_param = (
                {"checkpoint_path": str(parsed_args.checkpoint), "mode": "demo"}
                if has_ckpt
                else {"episode_path": str(parsed_args.episode), "mode": "episode"}
            )
            warnings_list: list[str] = []
            if not model_check_res.match:
                warnings_list.append(
                    "Cảnh báo: Mô hình lệch mã băm XML (model mismatch allowed)."
                )

            summary_dict = summarize_episode(
                episode,
                model_check_res,
                source=source_param,
                saved_episode=str(parsed_args.save_episode) if parsed_args.save_episode else None,
                playback=None,
                warnings=warnings_list,
            )

            # In bản tóm tắt JSON chuẩn hoá ra stdout
            sys.stdout.write(json.dumps(summary_dict, indent=2) + "\n")
            sys.stdout.flush()
            return 0
        else:
            # 7.2 Chế độ có màn hình hiển thị: mở MuJoCo Viewer
            import mujoco

            from mma_ai.visualization.pacing import Pacer
            from mma_ai.visualization.playback import play
            from mma_ai.visualization.viewer import ViewerSink

            duration_sim_s = 0.0
            if len(episode.frames) > 1:
                duration_sim_s = float(episode.frames[-1].t_s - episode.frames[0].t_s)

            if duration_sim_s < 1.0:
                sys.stderr.write(
                    f"Thông báo: Thời lượng mô phỏng của episode ngắn "
                    f"({duration_sim_s:.3f} s < 1.0 s). Gợi ý: Dùng cờ '--speed 0.1' để làm chậm "
                    "hoặc '--loop' để lặp lại cho quan sát trực quan.\n"
                )
                sys.stderr.flush()

            viewer_model = loaded_model.model
            viewer_data = mujoco.MjData(viewer_model)

            sink = ViewerSink(viewer_model, viewer_data, cfg)
            _mark_viewer_opened(sink)
            sink.set_target(episode.target.position_m)

            pacer = Pacer()
            warning_hud = "MÔ HÌNH LỆCH" if not model_check_res.match else None

            try:
                stats = play(episode, cfg, sink, pacer=pacer, warning=warning_hud)
            finally:
                sink.close()

            # In dòng tóm tắt tiếng Việt cuối phiên phát lại
            ratio_str = f"{stats.ratio:.2f}x" if stats.ratio is not None else "N/A"
            sys.stdout.write(
                f"Tóm tắt phiên phát lại: Thời lượng mô phỏng={stats.sim_s:.3f} s, "
                f"Thời gian thực={stats.wall_s:.3f} s, Tỷ lệ tốc độ={ratio_str}, "
                f"Số khung trễ={stats.frames_late}\n"
            )
            sys.stdout.flush()
            return 0

    except KeyboardInterrupt:
        # Dọn dẹp tệp tạm dở dang nếu có sự cố ngắt bởi người dùng
        if save_path_obj is not None:
            tmp_candidate = Path(str(save_path_obj) + ".tmp")
            if tmp_candidate.exists():
                try:
                    tmp_candidate.unlink()
                except OSError:
                    pass

        sys.stderr.write("\nTiến trình bị ngắt bởi tín hiệu người dùng (Ctrl-C).\n")
        sys.stderr.flush()
        return 130
    except Exception as err:
        sys.stderr.write(f"Lỗi không lường trước phát sinh trong phiên phát lại: {err}\n")
        sys.stderr.flush()
        return 1
