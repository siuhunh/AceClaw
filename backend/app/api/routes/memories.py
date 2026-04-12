from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.storage import PathContentBody
from backend.app.modules.memory.store import MemoryStore
from backend.app.modules.storage.files import read_memory_file, write_memory_file


router = APIRouter(prefix="/api/memories", tags=["memories"])
memory_store = MemoryStore()


@router.get("")
async def memories(
    path: str | None = Query(None, description="若提供则返回该文件全文，如 memory/main_session.md"),
):
    if path:
        try:
            content = read_memory_file(path)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid path") from None
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="not found") from None
        return {"path": path, "content": content}

    return {"memories": memory_store.list_memory_files()}


@router.post("")
async def save_memory(body: PathContentBody) -> dict[str, str]:
    try:
        write_memory_file(body.path, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {"path": body.path, "status": "saved"}
