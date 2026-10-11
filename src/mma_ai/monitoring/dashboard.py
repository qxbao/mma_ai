"""Bảng quan sát (dashboard) tiến trình huấn luyện MMA-AI qua giao diện web chỉ-đọc.

Mô-đun này cung cấp máy chủ HTTP vòng lặp ngược (loopback) phục vụ các điểm cuối
API-TRN-0001 (/api/progress) và API-TRN-0002 (/) tuân thủ bất biến chỉ-đọc INV-005,
FR-020, FR-021 và NFR-PERF-002.
"""

from __future__ import annotations

import http.server
import json
import socket
import threading
import urllib.parse
from pathlib import Path
from typing import Any, cast

ALLOWED_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})


def _build_html_template(poll_interval_ms: int) -> str:
    """Sinh mã HTML tĩnh tự chứa kèm mã JavaScript nội tuyến cho giao diện quan sát."""
    template_parts = [
        "<!DOCTYPE html>",
        '<html lang="vi">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>MMA-AI Bảng quan sát huấn luyện</title>",
        "  <style>",
        "    :root {",
        "      --bg: #0f172a;",
        "      --card-bg: #1e293b;",
        "      --border: #334155;",
        "      --text: #f8fafc;",
        "      --text-muted: #94a3b8;",
        "      --accent: #38bdf8;",
        "      --success: #4ade80;",
        "      --warning: #facc15;",
        "      --danger: #f87171;",
        "    }",
        "    * { box-sizing: border-box; margin: 0; padding: 0; }",
        "    body {",
        '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;',
        "      background-color: var(--bg);",
        "      color: var(--text);",
        "      line-height: 1.5;",
        "      padding: 1.5rem;",
        "    }",
        "    header {",
        "      display: flex;",
        "      justify-content: space-between;",
        "      align-items: center;",
        "      margin-bottom: 1.5rem;",
        "      border-bottom: 1px solid var(--border);",
        "      padding-bottom: 1rem;",
        "    }",
        "    h1 { font-size: 1.5rem; font-weight: 600; }",
        "    .badge {",
        "      display: inline-block;",
        "      padding: 0.25rem 0.75rem;",
        "      border-radius: 9999px;",
        "      font-size: 0.875rem;",
        "      font-weight: 500;",
        "      background: var(--border);",
        "      color: var(--text);",
        "    }",
        "    .badge.running { background: #0369a1; color: #e0f2fe; }",
        "    .badge.done { background: #15803d; color: #dcfce7; }",
        "    .badge.error { background: #b91c1c; color: #fee2e2; }",
        "    .badge.interrupted { background: #b45309; color: #fef3c7; }",
        "    .grid {",
        "      display: grid;",
        "      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));",
        "      gap: 1.25rem;",
        "    }",
        "    .card {",
        "      background: var(--card-bg);",
        "      border: 1px solid var(--border);",
        "      border-radius: 0.5rem;",
        "      padding: 1.25rem;",
        "    }",
        "    .card-title {",
        "      font-size: 1rem;",
        "      font-weight: 600;",
        "      color: var(--text-muted);",
        "      margin-bottom: 0.75rem;",
        "      text-transform: uppercase;",
        "      letter-spacing: 0.05em;",
        "    }",
        "    .metric-value {",
        "      font-size: 1.5rem;",
        "      font-weight: 700;",
        "      color: var(--text);",
        "      margin-bottom: 0.25rem;",
        "    }",
        "    .metric-sub { font-size: 0.875rem; color: var(--text-muted); }",
        "    .bar-container {",
        "      margin: 0.5rem 0;",
        "      background: #090d16;",
        "      border-radius: 4px;",
        "      overflow: hidden;",
        "      height: 16px;",
        "    }",
        "    .bar {",
        "      background: var(--accent);",
        "      height: 100%;",
        "      width: 0%;",
        "      transition: width 0.3s ease;",
        "    }",
        "    .muscle-row {",
        "      display: flex;",
        "      justify-content: space-between;",
        "      font-size: 0.875rem;",
        "      margin-bottom: 0.25rem;",
        "    }",
        "    .no-data { color: var(--warning); font-style: italic; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <header>",
        "    <div>",
        "      <h1>Bảng quan sát huấn luyện MMA-AI (Dashboard)</h1>",
        '      <p id="meta-info" class="metric-sub">',
        '        Run ID: <span id="run-id">-</span> | ',
        '        Giai đoạn: <span id="stage">elbow</span> | ',
        '        Mầm: <span id="seed">-</span>',
        "      </p>",
        "    </div>",
        "    <div>",
        '      <span id="status-badge" class="badge">Đang khởi động</span>',
        "    </div>",
        "  </header>",
        '  <main class="grid">',
        '    <section class="card" id="panel-steps">',
        '      <h2 class="card-title">Tiến độ bước môi trường (Steps)</h2>',
        '      <div class="metric-value">',
        '        <span id="env-steps">-</span> / <span id="total-steps">-</span>',
        "      </div>",
        '      <div class="bar-container">',
        '        <div id="steps-bar" class="bar"></div>',
        "      </div>",
        '      <p class="metric-sub">Cập nhật: <span id="update-idx">-</span></p>',
        "    </section>",
        '    <section class="card" id="panel-throughput">',
        '      <h2 class="card-title">Tốc độ bước môi trường (env steps/s)</h2>',
        '      <div class="metric-value" id="throughput-val">-</div>',
        '      <p class="metric-sub">Dấu thời gian UTC: <span id="timestamp-utc">-</span></p>',
        "    </section>",
        '    <section class="card" id="panel-reward">',
        '      <h2 class="card-title">Phần thưởng (Reward)</h2>',
        '      <div class="metric-value" id="reward-val">-</div>',
        '      <p class="metric-sub">Trung bình mỗi tập (mean_return)</p>',
        '      <div id="reward-history" class="metric-sub" style="margin-top: 0.5rem;"></div>',
        "    </section>",
        '    <section class="card" id="panel-loss">',
        '      <h2 class="card-title">Tổn thất (Loss)</h2>',
        '      <div class="muscle-row">',
        "        <span>Chính sách (Policy):</span>",
        '        <span id="loss-policy">-</span>',
        "      </div>",
        '      <div class="muscle-row">',
        "        <span>Giá trị (Value):</span>",
        '        <span id="loss-value">-</span>',
        "      </div>",
        '      <div class="muscle-row">',
        "        <span>Entropy:</span>",
        '        <span id="loss-entropy">-</span>',
        "      </div>",
        "    </section>",
        '    <section class="card" id="panel-activation">',
        '      <h2 class="card-title">Kích hoạt 6 cơ (Activation)</h2>',
        '      <div id="muscles-list">',
        '        <div class="no-data">chưa có dữ liệu</div>',
        "      </div>",
        "    </section>",
        '    <section class="card" id="panel-checkpoint">',
        '      <h2 class="card-title">Trạng thái Checkpoint</h2>',
        '      <div class="muscle-row">',
        "        <span>Số lượng lưu:</span>",
        '        <span id="ckpt-count">-</span>',
        "      </div>",
        '      <div class="muscle-row">',
        "        <span>Tần số (lượt):</span>",
        '        <span id="ckpt-every">-</span>',
        "      </div>",
        '      <div class="muscle-row">',
        "        <span>Lượt lưu gần nhất:</span>",
        '        <span id="ckpt-last-idx">-</span>',
        "      </div>",
        '      <div class="metric-sub" style="margin-top: 0.25rem; word-break: break-all;">',
        '        Đường dẫn: <span id="ckpt-last-path">-</span>',
        "      </div>",
        "    </section>",
        "  </main>",
        "  <script>",
        f"    const pollIntervalMs = {poll_interval_ms};",
        "    let timerId = null;",
        "    function renderNoData() {",
        "      const ph = '<span class=\"no-data\">chưa có dữ liệu</span>';",
        "      document.getElementById('status-badge').textContent = 'Chưa có dữ liệu';",
        "      document.getElementById('status-badge').className = 'badge';",
        "      document.getElementById('env-steps').innerHTML = ph;",
        "      document.getElementById('total-steps').innerHTML = ph;",
        "      document.getElementById('update-idx').innerHTML = ph;",
        "      document.getElementById('throughput-val').innerHTML = ph;",
        "      document.getElementById('timestamp-utc').innerHTML = ph;",
        "      document.getElementById('reward-val').innerHTML = ph;",
        "      document.getElementById('reward-history').innerHTML = '';",
        "      document.getElementById('loss-policy').innerHTML = ph;",
        "      document.getElementById('loss-value').innerHTML = ph;",
        "      document.getElementById('loss-entropy').innerHTML = ph;",
        "      document.getElementById('muscles-list').innerHTML =",
        "        '<div class=\"no-data\">chưa có dữ liệu</div>';",
        "      document.getElementById('ckpt-count').innerHTML = ph;",
        "      document.getElementById('ckpt-every').innerHTML = ph;",
        "      document.getElementById('ckpt-last-idx').innerHTML = ph;",
        "      document.getElementById('ckpt-last-path').innerHTML = ph;",
        "    }",
        "    function renderSnapshot(data) {",
        "      const ph = '<span class=\"no-data\">chưa có dữ liệu</span>';",
        "      document.getElementById('run-id').textContent = data.run_id || '-';",
        "      document.getElementById('stage').textContent = data.stage || 'elbow';",
        "      document.getElementById('seed').textContent =",
        "        data.seed !== undefined ? data.seed : '-';",
        "      const badge = document.getElementById('status-badge');",
        "      const st = data.status || 'running';",
        "      badge.className = 'badge ' + st;",
        "      if (st === 'running') badge.textContent = 'Đang huấn luyện (running)';",
        "      else if (st === 'starting') badge.textContent = 'Đang khởi động (starting)';",
        "      else if (st === 'done') badge.textContent = 'Đã hoàn thành (done)';",
        "      else if (st === 'error') badge.textContent = 'Lỗi huấn luyện (error)';",
        "      else if (st === 'interrupted') badge.textContent = 'Bị ngắt (interrupted)';",
        "      else badge.textContent = st;",
        "      const stepsVal = data.env_steps !== null ? data.env_steps.toLocaleString() : '0';",
        "      document.getElementById('env-steps').textContent = stepsVal;",
        "      document.getElementById('total-steps').textContent =",
        "        data.total_steps !== null ? data.total_steps.toLocaleString() : '-';",
        "      document.getElementById('update-idx').textContent =",
        "        data.update_idx !== null ? data.update_idx : '-';",
        "      if (data.total_steps && data.env_steps !== null) {",
        "        const frac = data.env_steps / data.total_steps;",
        "        const pct = Math.min(100, Math.max(0, frac * 100));",
        "        document.getElementById('steps-bar').style.width = pct.toFixed(1) + '%';",
        "      }",
        "      const sps = data.env_steps_per_second;",
        "      if (sps !== null && sps !== undefined) {",
        "        document.getElementById('throughput-val').textContent =",
        "          Number(sps).toFixed(1) + ' bước/giây';",
        "      } else {",
        "        document.getElementById('throughput-val').innerHTML = ph;",
        "      }",
        "      document.getElementById('timestamp-utc').textContent =",
        "        data.timestamp_utc || '-';",
        "      if (data.mean_return !== null && data.mean_return !== undefined) {",
        "        document.getElementById('reward-val').textContent =",
        "          Number(data.mean_return).toFixed(3);",
        "      } else {",
        "        document.getElementById('reward-val').innerHTML = ph;",
        "      }",
        "      if (data.history && Array.isArray(data.history.mean_return)) {",
        "        const validRet = data.history.mean_return.filter(x => x !== null);",
        "        if (validRet.length > 0) {",
        "          document.getElementById('reward-history').textContent =",
        "            'Lịch sử: ' + validRet.slice(-5).map(x => Number(x).toFixed(1)).join(' → ');",
        "        }",
        "      }",
        "      if (data.loss) {",
        "        document.getElementById('loss-policy').textContent =",
        "          data.loss.policy !== null ? Number(data.loss.policy).toFixed(4) : '-';",
        "        document.getElementById('loss-value').textContent =",
        "          data.loss.value !== null ? Number(data.loss.value).toFixed(4) : '-';",
        "        document.getElementById('loss-entropy').textContent =",
        "          data.loss.entropy !== null ? Number(data.loss.entropy).toFixed(4) : '-';",
        "      } else {",
        "        document.getElementById('loss-policy').innerHTML = ph;",
        "        document.getElementById('loss-value').innerHTML = ph;",
        "        document.getElementById('loss-entropy').innerHTML = ph;",
        "      }",
        "      if (data.activation && Array.isArray(data.activation.muscle_names) &&",
        "          Array.isArray(data.activation.mean)) {",
        "        let listHtml = '';",
        "        for (let i = 0; i < data.activation.muscle_names.length; i++) {",
        "          const mName = data.activation.muscle_names[i];",
        "          const val = data.activation.mean[i];",
        "          const mPct = (val * 100).toFixed(1);",
        "          listHtml += '<div class=\"muscle-row\"><span>' + mName + '</span><span>' +",
        "            val.toFixed(3) + '</span></div><div class=\"bar-container\">' +",
        "            '<div class=\"bar\" style=\"width: ' + mPct + '%\"></div></div>';",
        "        }",
        "        document.getElementById('muscles-list').innerHTML = listHtml;",
        "      } else {",
        "        document.getElementById('muscles-list').innerHTML =",
        "          '<div class=\"no-data\">chưa có dữ liệu</div>';",
        "      }",
        "      if (data.checkpoint) {",
        "        document.getElementById('ckpt-count').textContent = data.checkpoint.count;",
        "        document.getElementById('ckpt-every').textContent =",
        "          data.checkpoint.every_updates;",
        "        const lastIdx = data.checkpoint.last_update_idx;",
        "        document.getElementById('ckpt-last-idx').textContent =",
        "          lastIdx !== null ? lastIdx : '-';",
        "        document.getElementById('ckpt-last-path').textContent =",
        "          data.checkpoint.last_path || 'chưa có';",
        "      } else {",
        "        document.getElementById('ckpt-count').innerHTML = ph;",
        "        document.getElementById('ckpt-every').innerHTML = ph;",
        "        document.getElementById('ckpt-last-idx').innerHTML = ph;",
        "        document.getElementById('ckpt-last-path').innerHTML = ph;",
        "      }",
        "      if (['done', 'error', 'interrupted'].includes(st) && timerId) {",
        "        clearInterval(timerId);",
        "        timerId = null;",
        "      }",
        "    }",
        "    async function fetchProgress() {",
        "      try {",
        "        const response = await fetch('/api/progress');",
        "        if (response.status === 200) {",
        "          const data = await response.json();",
        "          renderSnapshot(data);",
        "        } else if (response.status === 503) {",
        "          renderNoData();",
        "        }",
        "      } catch (err) {",
        "        renderNoData();",
        "      }",
        "    }",
        "    fetchProgress();",
        "    timerId = setInterval(fetchProgress, pollIntervalMs);",
        "  </script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(template_parts)


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    """Bộ xử lý yêu cầu HTTP chỉ-đọc cho bảng quan sát huấn luyện."""

    @property
    def run_dir(self) -> Path:
        """Đường dẫn thư mục chạy huấn luyện gắn với máy chủ hiện hành."""
        server_obj = getattr(self, "server", None)
        if server_obj is not None and hasattr(server_obj, "run_dir"):
            return cast(Path, server_obj.run_dir)
        return Path(".")

    @property
    def html_content(self) -> bytes:
        """Nội dung HTML tĩnh gắn với máy chủ hiện hành."""
        server_obj = getattr(self, "server", None)
        if server_obj is not None and hasattr(server_obj, "html_content"):
            return cast(bytes, server_obj.html_content)
        return b""

    def log_message(self, format: str, *args: Any) -> None:
        """Tắt ghi nhật ký mặc định ra thiết bị xuất chuẩn để bảo đảm yên lặng."""

    def _send_method_not_allowed(self) -> None:
        """Từ chối mọi phương thức sửa đổi dữ liệu theo bất biến INV-005."""
        payload = json.dumps(
            {"error": "Phương thức không được hỗ trợ", "allowed": ["GET"]},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(405)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        self._send_method_not_allowed()

    def do_PUT(self) -> None:
        self._send_method_not_allowed()

    def do_DELETE(self) -> None:
        self._send_method_not_allowed()

    def do_PATCH(self) -> None:
        self._send_method_not_allowed()

    def do_HEAD(self) -> None:
        self._send_method_not_allowed()

    def do_OPTIONS(self) -> None:
        self._send_method_not_allowed()

    def do_GET(self) -> None:
        """Phục vụ các điểm cuối GET hợp lệ hoặc trả 404 cho đường dẫn lạ."""
        parsed_path = urllib.parse.urlparse(self.path).path

        if parsed_path in ("/", "/index.html"):
            # API-TRN-0002: phục vụ trang HTML tĩnh một tệp nội tuyến
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.html_content)))
            self.end_headers()
            self.wfile.write(self.html_content)
            return

        if parsed_path == "/api/progress":
            # API-TRN-0001: phục vụ ảnh chụp tiến trình huấn luyện
            progress_file = self.run_dir / "progress.json"
            if not progress_file.is_file():
                payload = json.dumps({"error": "chưa có dữ liệu"}, ensure_ascii=False).encode(
                    "utf-8"
                )
                self.send_response(503)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            try:
                data = progress_file.read_bytes()
            except OSError:
                payload = json.dumps({"error": "chưa có dữ liệu"}, ensure_ascii=False).encode(
                    "utf-8"
                )
                self.send_response(503)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Đường dẫn lạ hoặc cố tình duyệt thư mục bị từ chối 404
        payload = json.dumps({"error": "Đường dẫn không tồn tại"}, ensure_ascii=False).encode(
            "utf-8"
        )
        self.send_response(404)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class _DashboardHTTPServer(http.server.ThreadingHTTPServer):
    """Máy chủ HTTP đa luồng xử lý đồng thời yêu cầu thăm dò."""

    daemon_threads = True
    allow_reuse_address = True
    run_dir: Path
    html_content: bytes

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[http.server.BaseHTTPRequestHandler],
        run_dir: Path,
        html_content: bytes,
    ) -> None:
        self.run_dir = run_dir
        self.html_content = html_content
        super().__init__(server_address, RequestHandlerClass)


class _DashboardIPv6Server(_DashboardHTTPServer):
    """Máy chủ HTTP đa luồng hỗ trợ địa chỉ vòng lặp ngược IPv6."""

    address_family = socket.AF_INET6


class Server:
    """Đối tượng máy chủ quan sát huấn luyện hỗ trợ đóng sạch và quản lý ngữ cảnh."""

    def __init__(
        self,
        httpd: http.server.ThreadingHTTPServer,
        thread: threading.Thread,
        run_dir: Path,
        host: str,
        port: int,
    ) -> None:
        self._httpd = httpd
        self._thread = thread
        self._run_dir = run_dir
        self._host = host
        self._port = port

    @property
    def host(self) -> str:
        """Địa chỉ máy chủ đang lắng nghe."""
        return self._host

    @property
    def port(self) -> int:
        """Cổng mạng thực tế mà hệ điều hành cấp phát."""
        return self._port

    @property
    def url(self) -> str:
        """Địa chỉ URL hoàn chỉnh để truy cập giao diện."""
        return f"http://{self._host}:{self._port}"

    @property
    def server_address(self) -> tuple[str, int]:
        """Cặp (địa chỉ, cổng) của máy chủ."""
        return (self._host, self._port)

    def close(self) -> None:
        """Đóng máy chủ và giải phóng cổng mạng ngay lập tức."""
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def shutdown(self) -> None:
        """Bí danh của close để tương thích giao diện."""
        self.close()

    def __enter__(self) -> Server:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def serve(
    run_dir: str | Path,
    host: str = "127.0.0.1",
    port: int = 0,
    poll_interval_ms: int = 2000,
) -> Server:
    """Khởi chạy máy chủ HTTP chỉ-đọc phục vụ bảng quan sát trên giao diện loopback.

    Tham số:
        run_dir: Thư mục chứa tiến trình huấn luyện để đọc progress.json.
        host: Địa chỉ mạng loopback hợp lệ (127.0.0.1, ::1 hoặc localhost).
        port: Cổng mạng cần bind; 0 nghĩa là hệ điều hành tự động cấp cổng rảnh.
        poll_interval_ms: Chu kỳ thăm dò API tính bằng mili-giây cho mã JavaScript.

    Ngoại lệ:
        ValueError: Nếu địa chỉ host không nằm trong danh sách loopback được phép.
    """
    if host not in ALLOWED_LOOPBACK_HOSTS:
        raise ValueError(
            f"Địa chỉ '{host}' không hợp lệ; máy chủ chỉ chấp nhận địa chỉ vòng lặp ngược "
            f"(loopback): {sorted(ALLOWED_LOOPBACK_HOSTS)}"
        )

    resolved_run_dir = Path(run_dir).resolve()
    html_bytes = _build_html_template(poll_interval_ms).encode("utf-8")

    server_factory = _DashboardIPv6Server if host == "::1" else _DashboardHTTPServer
    httpd = server_factory(
        (host, port),
        _DashboardHandler,
        run_dir=resolved_run_dir,
        html_content=html_bytes,
    )

    # Lấy cổng thực tế sau khi bind
    actual_port = int(httpd.server_address[1])

    worker = threading.Thread(
        target=httpd.serve_forever,
        name=f"DashboardServer-{actual_port}",
        daemon=True,
    )
    worker.start()

    return Server(
        httpd=httpd,
        thread=worker,
        run_dir=resolved_run_dir,
        host=host,
        port=actual_port,
    )


__all__ = ["ALLOWED_LOOPBACK_HOSTS", "Server", "serve"]
