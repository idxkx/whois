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
from typing import Any, Dict, Tuple, List

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

    protocol_version = "HTTP/1.1"

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

    def _parse_request_payload(self) -> Tuple[Any, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        raw = self.rfile.read(length) if length else b""
        if not raw:
            raise DomainQueryError("请求体为空")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise DomainQueryError("请求体不是有效 JSON") from exc

        text_field = payload.get("text", "")
        lines_field = payload.get("lines", [])
        return text_field, lines_field

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
        if self.path == "/domain-query/batch-stream":
            self._handle_batch_stream()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "未找到资源")

    def _merge_text_inputs(self, text_field: Any, lines_field: Any) -> Any:
        if text_field and isinstance(lines_field, list) and lines_field:
            return list(lines_field) + [text_field]
        if isinstance(lines_field, list) and lines_field:
            return lines_field
        return text_field

    def _handle_batch_query(self) -> None:
        try:
            text_field, lines_field = self._parse_request_payload()
        except DomainQueryError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        text_inputs = self._merge_text_inputs(text_field, lines_field)

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

    def _handle_batch_stream(self) -> None:
        try:
            text_field, lines_field = self._parse_request_payload()
        except DomainQueryError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        text_inputs = self._merge_text_inputs(text_field, lines_field)
        try:
            combos = self._build_domain_combinations(text_inputs)
        except DomainQueryError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if not combos:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "无有效域名片段"})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def write_chunk(obj: Dict[str, Any]) -> bool:
            data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            try:
                self.wfile.write(data)
                self.wfile.flush()
                return True
            except BrokenPipeError:
                return False

        total = len(combos)
        if not write_chunk({"type": "start", "total": total}):
            return

        completed = 0
        unregistered: List[str] = []
        for domain in combos:
            try:
                result = self.server.client.lookup(domain)  # type: ignore[attr-defined]
            except DomainQueryError as exc:
                write_chunk({"type": "error", "error": str(exc), "completed": completed, "total": total})
                return

            completed += 1
            if not write_chunk(
                {
                    "type": "result",
                    "domain": result.domain,
                    "domain_suffix": result.domain_suffix,
                    "is_registered": result.is_registered,
                    "query_time": result.query_time,
                    "completed": completed,
                    "total": total,
                }
            ):
                return

            if not result.is_registered:
                unregistered.append(result.domain)

        write_chunk(
            {"type": "complete", "total": total, "completed": completed, "unregistered": unregistered}
        )
        self.close_connection = True

    def _build_domain_combinations(self, text_inputs: Any) -> List[str]:
        from domain_query.line_query import parse_text_lines, load_suffixes, combine_domain

        base_names = parse_text_lines(text_inputs)
        suffixes = load_suffixes(self.server.config_path)  # type: ignore[attr-defined]
        combos: List[str] = []
        for base in base_names:
            for suffix in suffixes:
                combos.append(combine_domain(base, suffix))
        return combos


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

    # 打印启动信息和访问地址
    print("=" * 60)
    print(f"Domain query server started successfully!")
    print("=" * 60)
    print(f"\nAccess URLs:")
    print(f"  Web UI:      http://{host}:{port}/ui/domain-query")
    print(f"  Swagger:     http://{host}:{port}/swagger")
    print(f"  API Batch:   http://{host}:{port}/domain-query/batch")
    print(f"  API Stream:  http://{host}:{port}/domain-query/batch-stream")
    print(f"\nServer running on http://{host}:{port}")
    print("Press Ctrl+C to stop\n")
    print("=" * 60)

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
