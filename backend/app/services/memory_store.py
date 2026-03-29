import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import MEMORY_DIR
class MemoryStore:
    def md_path(self, session_id: str) -> Path:
        return MEMORY_DIR / f"{session_id}.md"

    def json_path(self, session_id: str) -> Path:
        return MEMORY_DIR / f"{session_id}.json"

    def memory_path(self, session_id: str) -> str:
        return str(self.md_path(session_id))

    async def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        md_file = self.md_path(session_id)
        block = (
            f"## {ts}\n"
            f"**user**: {user_message}\n\n"
            f"**assistant**: {assistant_message}\n\n"
            "---\n"
        )
        with md_file.open("a", encoding="utf-8") as f:
            f.write(block)

        jf = self.json_path(session_id)
        data: dict = {"session_id": session_id, "updated_at": ts, "messages": []}
        if jf.exists():
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        if "messages" not in data or not isinstance(data["messages"], list):
            data["messages"] = []
        data["session_id"] = session_id
        data["updated_at"] = ts
        data["messages"].append({"role": "user", "content": user_message, "ts": ts})
        data["messages"].append({"role": "assistant", "content": assistant_message, "ts": ts})
        jf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def read(self, session_id: str) -> str:
        path = self.md_path(session_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def list_memory_files(self) -> list[dict[str, str]]:
        """Entries with API-style paths `memory/{session_id}.md|json`."""
        if not MEMORY_DIR.exists():
            return []
        stems: set[str] = set()
        for p in MEMORY_DIR.glob("*.md"):
            stems.add(p.stem)
        for p in MEMORY_DIR.glob("*.json"):
            stems.add(p.stem)
        out: list[dict[str, str]] = []
        for sid in sorted(stems):
            md_p = self.md_path(sid)
            js_p = self.json_path(sid)
            mtime = 0.0
            for p in (md_p, js_p):
                if p.exists():
                    mtime = max(mtime, p.stat().st_mtime)
            out.append(
                {
                    "session_id": sid,
                    "path_md": f"memory/{sid}.md",
                    "path_json": f"memory/{sid}.json",
                    "updated_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat() if mtime else "",
                }
            )
        out.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return out
