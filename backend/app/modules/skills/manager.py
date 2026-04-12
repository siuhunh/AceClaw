from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import SKILL_DIR
from backend.app.core.storage_paths import to_api_path


@dataclass
class SkillInfo:
    name: str
    path: str
    location: str
    description: str


class SkillManager:
    def __init__(self) -> None:
        self._skills: list[SkillInfo] = []

    def reload(self) -> list[SkillInfo]:
        skills: list[SkillInfo] = []
        if not SKILL_DIR.exists():
            self._skills = []
            return self._skills

        for path in sorted(SKILL_DIR.glob("*.md")):
            if not path.is_file():
                continue
            name = path.stem
            description = self._extract_description(path)
            skills.append(
                SkillInfo(
                    name=name,
                    path=to_api_path(path),
                    location=str(path.resolve()),
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
