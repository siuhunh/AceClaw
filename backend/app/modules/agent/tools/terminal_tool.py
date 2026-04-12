import re
from typing import Any

from langchain_community.tools import ShellTool
from langchain_core.tools import BaseTool

from backend.app.core.config import WORKSPACE_DIR


_DANGEROUS_PATTERNS = (
    r"rm\s+(-[^\s]*\s+)*rf?\s+/",
    r"shutdown",
    r"reboot",
    r"mkfs\.",
    r":\(\)\s*\{",
    r"dd\s+if=",
    r">\s*/dev/",
    r"chmod\s+-R\s+777\s+/",
)


def _is_blocked(command: str) -> bool:
    low = command.strip().lower()
    if not low:
        return False
    for pat in _DANGEROUS_PATTERNS:
        if re.search(pat, low, re.IGNORECASE):
            return True
    return False


def build_terminal_tool() -> BaseTool:
    """Shell in sandbox directory with blacklist."""
    root = str(WORKSPACE_DIR.resolve())
    inner = ShellTool(root_dir=root)

    class SafeTerminalTool(BaseTool):
        name: str = "terminal"
        description: str = (
            "Run shell commands in a sandboxed working directory (storage/workspace). "
            "Use for listing files, small utilities. Dangerous patterns are blocked."
        )

        def _run(self, commands: str, **kwargs: Any) -> str:
            if _is_blocked(commands):
                return "Command rejected: matches security blacklist."
            try:
                return str(inner.invoke({"commands": commands}))
            except Exception:
                try:
                    return str(inner.invoke(commands))
                except Exception as e:
                    return f"Shell error: {e}"

        async def _arun(self, commands: str, **kwargs: Any) -> str:
            return self._run(commands, **kwargs)

    return SafeTerminalTool()
