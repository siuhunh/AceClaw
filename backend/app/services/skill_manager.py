from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import SKILLS_DIR


@dataclass
class SkillInfo:
    name: str
    location: str
    description: str


class SkillManager:
    def __init__(self) -> None:
        self._skills: list[SkillInfo] = []

    def reload(self) -> list[SkillInfo]:
        skills: list[SkillInfo] = []
        if not SKILLS_DIR.exists():
            self._skills = []
            return self._skills

        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            description = self._extract_description(skill_file)
            skills.append(
                SkillInfo(
                    name=skill_dir.name,
                    location=str(skill_file),
                    description=description,
                )
            )
        self._skills = skills
        return self._skills

    def list(self) -> list[SkillInfo]:
        return self._skills

    def _extract_description(self, skill_file: Path) -> str:
        content = skill_file.read_text(encoding="utf-8").strip()
        if not content:
            return ""
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return ""
