from fastapi import APIRouter

from backend.app.services.memory_store import MemoryStore


router = APIRouter(prefix="/api/memory", tags=["memory"])
memory_store = MemoryStore()


@router.get("/{session_id}")
async def get_memory(session_id: str) -> dict[str, str]:
    content = await memory_store.read(session_id)
    return {"session_id": session_id, "content": content}
