"""Tavily 调用计数、最近记录与日志（供 /api/usage/tavily 与运维查看）。"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ace_claw")

_lock = threading.Lock()
_MAX_RECENT = 50

_state: dict[str, Any] = {
    "total_queries": 0,
    "total_tokens": 0,
    "total_errors": 0,
    "recent": [],
}


def is_tavily_configured() -> bool:
    return bool(os.getenv("TAVILY_API_KEY", "").strip())


def record_tavily_call(
    *,
    query: str,
    success: bool,
    tokens_delta: int = 0,
    error: str | None = None,
    usage_raw: dict[str, Any] | None = None,
    result_count: int | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    preview = query if len(query) <= 200 else query[:200] + "…"

    with _lock:
        if success:
            _state["total_queries"] += 1
            _state["total_tokens"] += max(0, tokens_delta)
        else:
            _state["total_errors"] += 1
        entry = {
            "at": ts,
            "query_preview": preview,
            "success": success,
            "tokens_delta": tokens_delta if success else 0,
            "error": error,
            "result_count": result_count,
        }
        recent: list = _state["recent"]
        recent.insert(0, entry)
        del recent[_MAX_RECENT:]

        total_q = _state["total_queries"]
        total_t = _state["total_tokens"]
        total_e = _state["total_errors"]

    if success:
        logger.info(
            "tavily_search ok query_preview=%r tokens_delta=%s result_count=%s "
            "total_queries=%s total_tokens=%s usage_raw=%s",
            preview,
            tokens_delta,
            result_count,
            total_q,
            total_t,
            usage_raw,
        )
    else:
        logger.warning(
            "tavily_search fail query_preview=%r error=%r total_errors=%s",
            preview,
            error,
            total_e,
        )


def get_tavily_usage_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "configured": is_tavily_configured(),
            "total_queries": int(_state["total_queries"]),
            "total_tokens": int(_state["total_tokens"]),
            "total_errors": int(_state["total_errors"]),
            "recent_calls": list(_state["recent"]),
        }


def extract_tokens_from_tavily_response(resp: Any) -> tuple[int, dict[str, Any] | None, int]:
    """Returns (tokens_delta, usage_dict_or_none, result_count)."""
    usage_raw: dict[str, Any] | None = None
    tokens = 0
    n_results = 0

    if isinstance(resp, dict):
        u = resp.get("usage")
        if isinstance(u, dict):
            usage_raw = dict(u)
            tokens = int(u.get("total_tokens") or u.get("tokens") or 0)
        results = resp.get("results") or []
        if isinstance(results, list):
            n_results = len(results)
        return tokens, usage_raw, n_results

    u = getattr(resp, "usage", None)
    if u is not None:
        if isinstance(u, dict):
            usage_raw = dict(u)
            tokens = int(u.get("total_tokens") or u.get("tokens") or 0)
        else:
            t = getattr(u, "total_tokens", None)
            if t is not None:
                tokens = int(t)
                usage_raw = {"total_tokens": tokens}
    results = getattr(resp, "results", None)
    if isinstance(results, list):
        n_results = len(results)
    return tokens, usage_raw, n_results
