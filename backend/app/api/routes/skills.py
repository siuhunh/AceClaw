from fastapi import APIRouter

from backend.app.services.skill_manager import SkillManager


router = APIRouter(prefix="/api/skills", tags=["skills"])
skill_manager = SkillManager()


@router.get("")
async def list_skills() -> dict[str, list[dict[str, str]]]:
    skills = skill_manager.list()
    return {
        "skills": [
            {"name": s.name, "location": s.location, "description": s.description}
            for s in skills
        ]
    }


@router.post("/reload")
async def reload_skills() -> dict[str, int]:
    skills = skill_manager.reload()
    return {"count": len(skills)}
