"""
轻量 HTTP 服务，提供批量域名查询 API、Swagger 风格交互页以及简单 Web 表单。
"""
from __future__ import annotations

import json
import sys
import argparse
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from domain_query.line_query import (  # noqa: E402
    DomainQueryError,
    WhoisApiClient,
    batch_query_from_text,
    DEFAULT_SUFFIX_FILE,
)

STATIC_DIR = ROOT_DIR / "static"
ENV_FILE = ROOT_DIR / ".env"


def load_env_file(path: Path = ENV_FILE) -> Dict[str, str]:
    """
    读取 .env 文件，将配置注入到 os.environ（仅在原变量不存在时设置）。
    """
    if not path.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value

    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


load_env_file()


class DomainQueryHTTPRequestHandler(BaseHTTPRequestHandler):
    """处理批量查询 API 与静态页面。"""

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "文件不存在")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", ""):
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/ui/domain-query")
            self.end_headers()
            return

        if self.path == "/ui/domain-query":
            self._serve_file(STATIC_DIR / "domain_query_ui.html", "text/html; charset=utf-8")
            return

        if self.path == "/swagger":
            self._serve_file(STATIC_DIR / "swagger.html", "text/html; charset=utf-8")
            return

        if self.path == "/swagger.json":
            self._serve_file(STATIC_DIR / "swagger.json", "application/json; charset=utf-8")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/domain-query/batch":
            self._handle_batch_query()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "未找到资源")

    def _handle_batch_query(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        raw = self.rfile.read(length) if length else b""
        if not raw:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "请求体为空"})
            return

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "请求体不是有效 JSON"})
            return

        text_field = payload.get("text", "")
        lines_field = payload.get("lines", [])

        text_inputs: Any
        if text_field and isinstance(lines_field, list) and lines_field:
            text_inputs = list(lines_field) + [text_field]
        elif isinstance(lines_field, list) and lines_field:
            text_inputs = lines_field
        else:
            text_inputs = text_field

        try:
            results = batch_query_from_text(
                text_inputs,
                config_path=self.server.config_path,  # type: ignore[attr-defined]
                client=self.server.client,  # type: ignore[attr-defined]
            )
        except DomainQueryError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if not results:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "无有效域名片段"})
            return

        response_items = [
            {
                "domain": item.domain,
                "domain_suffix": item.domain_suffix,
                "is_registered": item.is_registered,
                "query_time": item.query_time,
            }
            for item in results
        ]
        self._send_json(HTTPStatus.OK, {"items": response_items})


class DomainQueryHTTPServer(ThreadingHTTPServer):
    """自定义服务器，用于向 handler 注入依赖。"""

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass,  # noqa: N803
        config_path: Path,
        client: WhoisApiClient | None = None,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.config_path = config_path
        self.client = client or WhoisApiClient()


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    config_path: Path | None = None,
    client: WhoisApiClient | None = None,
) -> DomainQueryHTTPServer:
    """构建服务器实例，供脚本或测试使用。"""
    handler = DomainQueryHTTPRequestHandler
    server = DomainQueryHTTPServer(
        (host, port),
        handler,
        config_path=Path(config_path or os.environ.get("DOMAIN_QUERY_CONFIG", DEFAULT_SUFFIX_FILE)),
        client=client,
    )
    return server


def run(host: str | None = None, port: int | None = None) -> None:
    """启动服务，阻塞运行。"""
    host = host or os.environ.get("DOMAIN_QUERY_HOST", "127.0.0.1")
    env_port = os.environ.get("DOMAIN_QUERY_PORT")
    if port is None:
        port = int(env_port) if env_port else 8000

    server = create_server(host=host, port=port)
    print(f"Domain query server running on http://{host}:{port}")
    with server:
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动域名批量查询 HTTP 服务")
    parser.add_argument("--host", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, help="监听端口，默认 8000")
    args = parser.parse_args()
    try:
        run(host=args.host, port=args.port)
    except OSError as exc:
        print(f"启动失败：{exc}. 请尝试使用更高的端口（如 --port 8080）。")
