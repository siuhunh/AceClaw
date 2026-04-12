"""Process-wide skill index instance (API routes + system prompt share this)."""

from backend.app.modules.skills.manager import SkillManager

skill_manager = SkillManager()
