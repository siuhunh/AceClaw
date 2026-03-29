import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.agent_runtime import AgentRuntime
from backend.app.services.memory_store import MemoryStore


router = APIRouter(prefix="/api/chat", tags=["chat"])
memory_store = MemoryStore()
_agent_runtime: AgentRuntime | None = None


def _get_agent_runtime() -> AgentRuntime:
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    return _agent_runtime


@router.post("")
async def chat(payload: ChatRequest) -> ChatResponse | StreamingResponse:
    agent_runtime = _get_agent_runtime()

    if payload.stream:

        async def event_generator() -> AsyncGenerator[str, None]:
            yield _sse("start", {"session_id": payload.session_id})
            chunks: list[str] = []
            async for token in agent_runtime.stream(
                payload.message, session_id=payload.session_id
            ):
                chunks.append(token)
                yield _sse("token", {"content": token})

            full_text = "".join(chunks).strip()
            await memory_store.append_turn(payload.session_id, payload.message, full_text)
            yield _sse("memory_saved", {"session_id": payload.session_id})
            yield _sse("end", {"output": full_text})

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    output = await agent_runtime.run(payload.message, session_id=payload.session_id)
    await memory_store.append_turn(payload.session_id, payload.message, output)
    return ChatResponse(session_id=payload.session_id, output=output)


def _sse(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
