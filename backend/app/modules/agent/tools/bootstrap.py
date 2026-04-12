import logging

from langchain_core.tools import BaseTool

from backend.app.core.config import AppSettings
from backend.app.modules.agent.tools.fetch_url_tool import build_fetch_url_tool
from backend.app.modules.agent.tools.knowledge_tool import build_knowledge_search_tool
from backend.app.modules.agent.tools.python_repl_tool import build_python_repl_tool
from backend.app.modules.agent.tools.read_file_tool import build_read_file_tool
from backend.app.modules.agent.tools.terminal_tool import build_terminal_tool

logger = logging.getLogger(__name__)


def build_core_tools(settings: AppSettings) -> list[BaseTool]:
    tools: list[BaseTool] = [
        build_terminal_tool(),
        build_python_repl_tool(),
        build_fetch_url_tool(),
        build_read_file_tool(),
        build_knowledge_search_tool(settings),
    ]
    return tools
