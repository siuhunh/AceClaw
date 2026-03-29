from pydantic import BaseModel, Field


class PathContentBody(BaseModel):
    """保存技能或记忆文件；path 为 API 逻辑路径，如 `skill/foo.md`、`memory/bar.json`。"""

    path: str = Field(..., min_length=3)
    content: str = Field(..., description="Full file text")
