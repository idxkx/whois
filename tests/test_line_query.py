import json
import os
import tempfile
import unittest
from unittest import mock

from domain_query.line_query import (
    DomainQueryResult,
    DomainQueryError,
    WhoisApiClient,
    batch_query_from_text,
    combine_domain,
    load_suffixes,
    parse_text_lines,
)


class ParseLinesTest(unittest.TestCase):
    def test_parse_text_lines_skips_blank_and_preserves_order(self):
        text = "example\n\n test  \r\nwhois.ai\rother"
        self.assertEqual(
            parse_text_lines(text),
            ["example", "test", "whois.ai", "other"],
        )


class LoadSuffixesTest(unittest.TestCase):
    def _write_config(self, payload) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_load_suffixes_filters_disabled_entries(self):
        path = self._write_config(
            {
                "suffixes": [
                    {"suffix": "com", "enabled": True},
                    {"suffix": "net", "enabled": False},
                    " io ",
                ]
            }
        )

        self.assertEqual(load_suffixes(path), ["com", "io"])

    def test_load_suffixes_error_on_empty(self):
        path = self._write_config({"suffixes": []})
        with self.assertRaises(DomainQueryError):
            load_suffixes(path)


class BatchQueryTest(unittest.TestCase):
    class FakeClient:
        def __init__(self):
            self.domains = []

        def lookup(self, domain: str) -> DomainQueryResult:
            self.domains.append(domain)
            return DomainQueryResult(domain=domain, domain_suffix=domain.split(".")[-1], is_registered=False)

    def test_batch_query_combines_lines_and_suffixes(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"suffixes": ["com", "io"]}, fh)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        client = self.FakeClient()
        results = batch_query_from_text(["alpha", "beta"], config_path=path, client=client)

        self.assertEqual([r.domain for r in results], ["alpha.com", "alpha.io", "beta.com", "beta.io"])
        self.assertEqual(client.domains, ["alpha.com", "alpha.io", "beta.com", "beta.io"])

    def test_combine_domain_validates_inputs(self):
        with self.assertRaises(DomainQueryError):
            combine_domain(" ", "com")


class WhoisApiClientTest(unittest.TestCase):
    def _fake_response(self, payload):
        class _Resp:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(self.data).encode("utf-8")

        return _Resp(payload)

    def test_retry_on_rate_limit(self):
        payloads = [
            {"status": 0, "error": "调用频次超限，请2秒后重试"},
            {"status": 1, "data": {"domain": "alpha.com", "domain_suffix": "com", "is_available": 0}},
        ]

        def fake_urlopen(req, timeout):
            return self._fake_response(payloads.pop(0))

        client = WhoisApiClient(timeout=1, max_retries=1, retry_delay=0)

        with mock.patch("domain_query.line_query.request.urlopen", side_effect=fake_urlopen):
            result = client.lookup("alpha.com")
            self.assertTrue(result.is_registered)

    def test_rate_limit_failure_after_retries(self):
        payloads = [
            {"status": 0, "error": "调用频次超限，请2秒后重试"},
            {"status": 0, "error": "调用频次超限，请2秒后重试"},
        ]

        def fake_urlopen(req, timeout):
            return self._fake_response(payloads.pop(0))

        client = WhoisApiClient(timeout=1, max_retries=1, retry_delay=0)
        with mock.patch("domain_query.line_query.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(DomainQueryError):
                client.lookup("alpha.com")

    def test_respect_rate_limit_flag(self):
        payloads = [
            {"status": 0, "error": "调用频次超限，请2秒后重试"},
        ]

        def fake_urlopen(req, timeout):
            return self._fake_response(payloads.pop(0))

        client = WhoisApiClient(timeout=1, max_retries=2, retry_delay=0, respect_rate_limit=False)
        with mock.patch("domain_query.line_query.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(DomainQueryError):
                client.lookup("alpha.com")


if __name__ == "__main__":
    unittest.main()
