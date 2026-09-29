"""网络层工具：客户端 IP 解析的**唯一实现**（信任边界所在）。

规则：仅当直连对端（scope.client）位于可信代理白名单时，才采信 X-Forwarded-For；
否则一律使用直连地址。限流 key、审计日志 IP 都从这里取值，避免"各写各的"。
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.types import Scope


def parse_trusted_proxies(raw: str) -> frozenset[str]:
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def resolve_client_ip(scope: Scope, trusted_proxies: frozenset[str] = frozenset()) -> str:
    client = scope.get("client")
    peer = client[0] if client else "-"
    if peer and peer in trusted_proxies:
        forwarded = Headers(scope=scope).get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return peer or "-"
