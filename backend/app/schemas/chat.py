from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(default="main_session", min_length=1)
    stream: bool = Field(default=True, description="true: SSE；false: JSON 同步响应")


class ChatResponse(BaseModel):
    session_id: str
    output: str
