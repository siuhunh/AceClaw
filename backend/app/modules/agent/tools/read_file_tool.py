from langchain_community.tools.file_management import ReadFileTool
from langchain_core.tools import BaseTool

from backend.app.core.config import BASE_DIR


def build_read_file_tool() -> BaseTool:
    """Read files under backend project root only."""
    tool = ReadFileTool(root_dir=str(BASE_DIR.resolve()))
    tool.name = "read_file"
    tool.description = (
        "Read a text file under the backend project root. "
        "Use relative paths like storage/skill/foo.md or storage/memory/x.md."
    )
    return tool
