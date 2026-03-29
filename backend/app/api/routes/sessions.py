from fastapi import APIRouter

from backend.app.services.memory_store import MemoryStore


router = APIRouter(prefix="/api/sessions", tags=["sessions"])
memory_store = MemoryStore()


@router.get("")
async def list_sessions() -> dict[str, list[dict[str, str]]]:
    """按 `updated_at` 降序返回会话（来自 `storage/memory` 下文件）。"""
    rows = memory_store.list_memory_files()
    return {"sessions": rows}
