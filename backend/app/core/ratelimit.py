"""通用内存滑动窗口限流（唯一实现）。

设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.3/§6.4。

边界（与 api/v1/client_logs.py 的限流同源，已在该 ADR 记录）：
- 单进程语义：多进程/多副本部署需换外部存储（Redis 或表级计数）
- 进程重启即清零；不试图伪装成分布式限流

为什么窗口按调用传入：调用方（验证码服务）的策略值来自 settings，
测试与运行期都可能调整，因此不在构造期固化。
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class LimitDecision:
    """一次命中判定：allowed=False 时给出建议等待秒数（用于 429 话术）。"""

    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowLimiter:
    """key → 窗口内命中时间戳列表；命中数 >= limit 即拒绝。"""

    def __init__(self, max_keys: int = 4096) -> None:
        self._max_keys = max_keys
        self._hits: dict[str, list[float]] = {}

    def peek(self, key: str, *, limit: int, window_seconds: int) -> LimitDecision:
        """只读判定（不记账）。

        用途：先拦掉已超限的请求，避免为它们白做昂贵校验（如 bcrypt）；
        与 hit 判据一致，区别只在"是否写入"。
        """
        now = time.monotonic()
        stamps = [stamp for stamp in self._hits.get(key, []) if now - stamp < window_seconds]
        if len(stamps) >= limit:
            oldest = min(stamps)
            wait = int(window_seconds - (now - oldest)) + 1
            return LimitDecision(allowed=False, retry_after_seconds=max(1, wait))
        return LimitDecision(allowed=True)

    def hit(self, key: str, *, limit: int, window_seconds: int) -> LimitDecision:
        """记录一次命中并返回判定；超限时不写入（保持计数不膨胀）。"""
        decision = self.peek(key, limit=limit, window_seconds=window_seconds)
        if not decision.allowed:
            return decision
        now = time.monotonic()
        stamps = [stamp for stamp in self._hits.get(key, []) if now - stamp < window_seconds]
        stamps.append(now)
        self._hits[key] = stamps
        if len(self._hits) > self._max_keys:
            self._prune(now)
        return LimitDecision(allowed=True)

    def reset(self) -> None:
        """测试用：清空全部计数。"""
        self._hits.clear()

    def _prune(self, now: float) -> None:
        """键数超上限：丢弃已无活跃命中的 key（O(n)，仅在越界时触发）。"""
        longest = 86400
        self._hits = {
            key: [stamp for stamp in stamps if now - stamp < longest]
            for key, stamps in self._hits.items()
            if any(now - stamp < longest for stamp in stamps)
        }
