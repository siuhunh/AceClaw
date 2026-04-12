"""LangChain tools wired to the Agent (terminal, REPL, fetch_url, read_file, RAG)."""

from backend.app.modules.agent.tools.registry import get_core_tools, init_core_tools

__all__ = ["get_core_tools", "init_core_tools"]
