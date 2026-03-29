from langchain_core.tools import StructuredTool
from langchain_experimental.tools import PythonREPLTool


def build_python_repl_tool() -> StructuredTool:
    """§3.9.2 — stateful Python REPL (langchain-experimental)."""
    inner = PythonREPLTool()

    def run_python(code: str) -> str:
        try:
            return str(inner.invoke({"query": code}))
        except Exception:
            return str(inner.invoke(code))

    return StructuredTool.from_function(
        run_python,
        name="python_repl",
        description=(
            "Run Python in a REPL for calculations, data transforms, or short scripts. "
            "Do not use for shell, files, or HTTP; use dedicated tools."
        ),
    )
