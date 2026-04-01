from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage

from backend.app.core.config import get_settings
from backend.app.services.model_factory import build_chat_model


class AgentRuntime:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._chat_model = build_chat_model(self._settings)

    async def run(self, user_message: str) -> str:
        result = await self._chat_model.ainvoke([HumanMessage(content=user_message)])
        return str(result.content)

    async def stream(self, user_message: str) -> AsyncGenerator[str, None]:
        async for chunk in self._chat_model.astream([HumanMessage(content=user_message)]):
            content = getattr(chunk, "content", "")
            if isinstance(content, str):
                if content:
                    yield content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            yield text
