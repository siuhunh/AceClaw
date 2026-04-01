from datetime import datetime, timezone

from backend.app.core.config import MEMORY_DIR


class MemoryStore:
    def memory_path(self, session_id: str) -> str:
        return str(MEMORY_DIR / f"{session_id}.md")

    async def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        path = MEMORY_DIR / f"{session_id}.md"
        block = (
            f"## {ts}\n"
            f"**user**: {user_message}\n\n"
            f"**assistant**: {assistant_message}\n\n"
            "---\n"
        )
        with path.open("a", encoding="utf-8") as f:
            f.write(block)

    async def read(self, session_id: str) -> str:
        path = MEMORY_DIR / f"{session_id}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
