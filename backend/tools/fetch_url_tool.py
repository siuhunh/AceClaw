import os
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_community.tools import RequestsGetTool
from langchain_core.tools import BaseTool
import html2text

from backend.tools.tavily_stats import (
    extract_tokens_from_tavily_response,
    is_tavily_configured,
    record_tavily_call,
)


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    text = h.handle(str(soup))
    if len(text) > 16000:
        return text[:16000] + "\n\n...[truncated]"
    return text


def _tavily_search(query: str) -> str:
    if not is_tavily_configured():
        return ""
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", "").strip())
        resp = client.search(query, max_results=5)
        tokens, usage_raw, n_results = extract_tokens_from_tavily_response(resp)
        record_tavily_call(
            query=query,
            success=True,
            tokens_delta=tokens,
            usage_raw=usage_raw,
            result_count=n_results,
        )
        if isinstance(resp, dict):
            lines = []
            for r in resp.get("results", []) or []:
                lines.append(f"- {r.get('title', '')}: {r.get('content', '')}")
            return "\n".join(lines) if lines else str(resp)
        return str(resp)
    except Exception as e:
        err = str(e)
        record_tavily_call(query=query, success=False, error=err)
        return f"Tavily error: {e}"


class FetchUrlTool(BaseTool):
    """§3.9.3 — HTTP GET with HTML cleanup; optional Tavily when API key is set."""

    name: str = "fetch_url"
    description: str = (
        "Fetch web content. If the input looks like a URL (http/https), performs HTTP GET "
        "and returns Markdown/plain text. If TAVILY_API_KEY is configured and the input is not a URL, "
        "runs a Tavily search instead. Prefer short factual queries."
    )

    def _run(self, url_or_query: str, **kwargs: Any) -> str:
        text = (url_or_query or "").strip()
        if not text:
            return "Empty input."
        lower = text.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            try:
                inner = RequestsGetTool()
                raw = inner.invoke({"url": text})
                if isinstance(raw, str) and ("<html" in raw.lower() or "<!doctype" in raw.lower()):
                    return _clean_html(raw)
                if isinstance(raw, str) and len(raw) > 16000:
                    return raw[:16000] + "\n\n...[truncated]"
                return str(raw)
            except Exception as e:
                return f"fetch error: {e}"
        tav = _tavily_search(text)
        if tav:
            return tav
        return (
            "No TAVILY_API_KEY set for non-URL queries. "
            "Pass a full http(s) URL or configure TAVILY_API_KEY in the environment."
        )

    async def _arun(self, url_or_query: str, **kwargs: Any) -> str:
        return self._run(url_or_query, **kwargs)


def build_fetch_url_tool() -> BaseTool:
    return FetchUrlTool()
