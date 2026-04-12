from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.storage import PathContentBody
from backend.app.modules.skills.state import skill_manager
from backend.app.modules.storage.files import read_skill_file, write_skill_file


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(path: str | None = Query(None, description="若提供则返回该技能全文，如 skill/foo.md")):
    if path:
        try:
            content = read_skill_file(path)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid path") from None
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="not found") from None
        return {"path": path, "content": content}

    skills = skill_manager.list()
    return {
        "skills": [
            {
                "name": s.name,
                "path": s.path,
                "location": s.location,
                "description": s.description,
            }
            for s in skills
        ]
    }


@router.post("")
async def save_skill(body: PathContentBody) -> dict[str, str]:
    try:
        write_skill_file(body.path, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    skill_manager.reload()
    return {"path": body.path, "status": "saved"}


@router.post("/reload")
async def reload_skills() -> dict[str, int]:
    skills = skill_manager.reload()
    return {"count": len(skills)}
