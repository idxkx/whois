"""
行分割域名查询编排模块。

提供将多行文本转换为基础域名片段、读取后缀配置、组合并调用 whois API 的能力，
供上层 agent 或 CLI 功能复用。
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Union
from urllib import parse, request, error


@dataclass
class DomainQueryResult:
    """whois 查询返回的关键信息。"""

    domain: str
    domain_suffix: str
    is_registered: bool
    query_time: str | None = None


class DomainQueryError(RuntimeError):
    """统一的业务异常，便于调用方捕获。"""


def parse_text_lines(inputs: Union[str, Sequence[str]]) -> List[str]:
    """
    将输入文本按行拆分并返回非空片段，保留原始顺序。

    :param inputs: 单个字符串或字符串序列
    :return: 去除空行、首尾空白后的片段列表
    """
    if isinstance(inputs, str):
        chunks: Iterable[str] = [inputs]
    else:
        chunks = inputs

    results: List[str] = []
    for chunk in chunks:
        if chunk is None:
            continue
        for line in str(chunk).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            trimmed = line.strip()
            if trimmed:
                results.append(trimmed)
    return results


def load_suffixes(config_path: Union[str, Path]) -> List[str]:
    """
    从配置文件中提取启用的域名后缀。

    支持两种结构：
    1. ["com", "io"]
    2. [{"suffix": "com", "enabled": true}]
    """
    path = Path(config_path)
    if not path.exists():
        raise DomainQueryError(f"未找到后缀配置文件：{path}")

    with path.open("r", encoding="utf-8-sig") as fh:
        data = json.load(fh)

    suffixes: List[str] = []
    raw_list = data.get("suffixes") if isinstance(data, dict) else data
    if not isinstance(raw_list, list):
        raise DomainQueryError("配置格式错误，需提供数组 suffixes。")

    for entry in raw_list:
        if isinstance(entry, str):
            suffix = entry.strip().lstrip(".")
            enabled = True
        elif isinstance(entry, dict):
            suffix = str(entry.get("suffix", "")).strip().lstrip(".")
            enabled = bool(entry.get("enabled", True))
        else:
            continue
        if not suffix or not enabled:
            continue
        suffixes.append(suffix.lower())

    if not suffixes:
        raise DomainQueryError("无启用的域名后缀，请检查配置。")
    return suffixes


def combine_domain(base: str, suffix: str) -> str:
    """拼接基础片段与后缀，避免重复的点。"""
    base = base.strip().strip(".")
    suffix = suffix.strip().lstrip(".")
    if not base or not suffix:
        raise DomainQueryError("基础片段或后缀为空，无法组合域名。")
    return f"{base}.{suffix}"


class WhoisApiClient:
    """负责调用 whoiscx 接口。"""

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 1,
        retry_delay: float = 2.0,
        respect_rate_limit: bool = True,
    ):
        self.timeout = timeout
        self.endpoint_template = "https://api.whoiscx.com/whois/?domain={domain}"
        self.max_retries = max(0, max_retries)
        self.retry_delay = max(0.0, retry_delay)
        self.respect_rate_limit = respect_rate_limit

    def lookup(self, domain: str) -> DomainQueryResult:
        last_error: DomainQueryError | None = None
        for attempt in range(self.max_retries + 1):
            payload = self._perform_request(domain)
            if payload.get("status") == 1:
                data = payload.get("data") or {}
                is_available = data.get("is_available")
                domain_suffix = data.get("domain_suffix") or domain.split(".")[-1]
                return DomainQueryResult(
                    domain=data.get("domain") or domain,
                    domain_suffix=domain_suffix,
                    is_registered=is_available == 0,
                    query_time=data.get("query_time"),
                )

            error_msg = payload.get("error") or str(payload)
            if self.respect_rate_limit and self._is_rate_limited(error_msg) and attempt < self.max_retries:
                if self.retry_delay > 0:
                    time.sleep(self.retry_delay)
                continue
            last_error = DomainQueryError(f"whois 接口返回错误：{error_msg}")
            break

        if last_error:
            raise last_error
        raise DomainQueryError("whois 接口返回错误：未知原因")

    def _perform_request(self, domain: str) -> dict:
        url = self.endpoint_template.format(domain=parse.quote(domain))
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            raise DomainQueryError(f"whois 查询失败：{exc}") from exc
        except json.JSONDecodeError as exc:
            raise DomainQueryError("whois 接口返回非 JSON 数据。") from exc

    @staticmethod
    def _is_rate_limited(message: str) -> bool:
        normalized = (message or "").lower()
        return any(token in normalized for token in ("频次", "rate", "limit", "超限"))


DEFAULT_SUFFIX_FILE = Path(__file__).resolve().parents[1] / "config" / "domain_suffixes.json"


def batch_query_from_text(
    text_inputs: Union[str, Sequence[str]],
    config_path: Union[str, Path] = DEFAULT_SUFFIX_FILE,
    client: WhoisApiClient | None = None,
    *,
    respect_rate_limit: bool | None = None,
    retry_delay: float | None = None,
    max_retries: int | None = None,
) -> List[DomainQueryResult]:
    """
    输入文本 + 后缀配置 => whois 查询结果列表。
    """
    base_names = parse_text_lines(text_inputs)
    if not base_names:
        return []

    suffixes = load_suffixes(config_path)
    if client is None:
        client = WhoisApiClient(
            respect_rate_limit=True if respect_rate_limit is None else respect_rate_limit,
            retry_delay=2.0 if retry_delay is None else retry_delay,
            max_retries=1 if max_retries is None else max_retries,
        )
    else:
        if respect_rate_limit is not None:
            client.respect_rate_limit = respect_rate_limit
        if retry_delay is not None:
            client.retry_delay = max(0.0, retry_delay)
        if max_retries is not None:
            client.max_retries = max(0, max_retries)

    results: List[DomainQueryResult] = []
    for base in base_names:
        for suffix in suffixes:
            domain = combine_domain(base, suffix)
            results.append(client.lookup(domain))
    return results


__all__ = [
    "DomainQueryError",
    "DomainQueryResult",
    "WhoisApiClient",
    "batch_query_from_text",
    "parse_text_lines",
    "load_suffixes",
    "combine_domain",
]
