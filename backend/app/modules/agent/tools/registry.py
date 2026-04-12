import logging
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

if TYPE_CHECKING:
    from backend.app.core.config import AppSettings

logger = logging.getLogger(__name__)

_tools: list[BaseTool] | None = None


def init_core_tools(settings: "AppSettings") -> list[BaseTool]:
    """Build and register all core LangChain tools (single init per process)."""
    global _tools
    from backend.app.modules.agent.tools.bootstrap import build_core_tools

    _tools = build_core_tools(settings)
    logger.info("core tools initialized: %s", [t.name for t in _tools])
    return _tools


def get_core_tools() -> list[BaseTool]:
    if _tools is None:
        raise RuntimeError("Core tools not initialized; call init_core_tools() at startup.")
    return _tools
