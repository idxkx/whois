import json
import os
import tempfile
import threading
import time
import unittest
import http.client

from domain_query.line_query import DomainQueryResult
from server.app import create_server


class FakeClient:
    def __init__(self):
        self.domains = []

    def lookup(self, domain: str) -> DomainQueryResult:
        self.domains.append(domain)
        return DomainQueryResult(domain=domain, domain_suffix=domain.split(".")[-1], is_registered=False, query_time="2026-01-12 10:00:30")


class ServerApiTest(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"suffixes": ["com"]}, fh)
        self.config_path = path
        self.client = FakeClient()
        self.server = create_server(host="127.0.0.1", port=0, config_path=path, client=self.client)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        # 等待服务器绑定端口
        timeout = time.time() + 2
        while self.server.server_address[1] == 0 and time.time() < timeout:
            time.sleep(0.01)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    def _request(self, method: str, path: str, body: dict | None = None):
        port = self.server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            payload = json.dumps(body).encode("utf-8") if body is not None else None
            headers = {"Content-Type": "application/json"} if payload else {}
            conn.request(method, path, body=payload, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, data
        finally:
            conn.close()

    def _request_stream(self, body: dict | None = None):
        return self._request("POST", "/domain-query/batch-stream", body)

    def test_batch_query_success(self):
        status, body = self._request("POST", "/domain-query/batch", {"text": "alpha"})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["domain"], "alpha.com")
        self.assertEqual(self.client.domains, ["alpha.com"])

    def test_batch_query_invalid(self):
        status, body = self._request("POST", "/domain-query/batch", {"text": ""})
        self.assertEqual(status, 400)
        payload = json.loads(body)
        self.assertIn("无有效域名片段", payload["error"])

    def test_batch_stream_returns_progress(self):
        status, body = self._request_stream({"text": "alpha"})
        self.assertEqual(status, 200)
        lines = [json.loads(line) for line in body.decode("utf-8").strip().splitlines()]
        self.assertEqual(lines[0]["type"], "start")
        result_events = [line for line in lines if line.get("type") == "result"]
        self.assertTrue(result_events)
        self.assertEqual(result_events[0]["domain"], "alpha.com")
        complete_events = [line for line in lines if line.get("type") == "complete"]
        self.assertTrue(complete_events)


if __name__ == "__main__":
    unittest.main()
