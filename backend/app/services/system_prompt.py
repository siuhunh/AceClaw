"""
§3.9 System Prompt：每次 Agent 调用时从 backend/workspace/*.md 重新读取并组装，
顺序与 dev.md 一致；技能列表可通过 {{AUTO_SKILLS}} 注入；长期记忆为当前 session 的 memory md。
"""

from pathlib import Path

from backend.app.core.config import MEMORY_DIR, SYSTEM_PROMPT_WORKSPACE


def _read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _auto_skills_block() -> str:
    from backend.app.api.routes.skills import skill_manager

    lines = ["<available_skills>"]
    for s in skill_manager.list():
        lines.append(f"- **{s.name}** (`{s.path}`): {s.description}")
    if len(lines) == 1:
        lines.append("- （当前无已扫描技能，可在 storage/skill/ 添加 *.md）")
    lines.append("</available_skills>")
    return "\n".join(lines)


def build_system_prompt(session_id: str) -> str:
    ws = SYSTEM_PROMPT_WORKSPACE
    blocks: list[str] = []

    # 1) Skills Snapshot
    snap_path = ws / "SKILLS_SNAPSHOT.md"
    snap = _read_text(snap_path)
    if not snap:
        snap = "<!-- Skills Snapshot -->\n\n{{AUTO_SKILLS}}"
    if "{{AUTO_SKILLS}}" in snap:
        snap = snap.replace("{{AUTO_SKILLS}}", _auto_skills_block())
    else:
        snap = snap + "\n\n" + _auto_skills_block()
    blocks.append(snap)

    # 2) Soul
    soul = _read_text(ws / "SOUL.md")
    blocks.append(soul if soul else "<!-- Soul -->\n\n（未找到 SOUL.md，请在 backend/workspace/ 补充核心设定。）")

    # 3) Identity
    ident = _read_text(ws / "IDENTITY.md")
    blocks.append(
        ident if ident else "<!-- Identity -->\n\n（未找到 IDENTITY.md，请补充自我认知。）"
    )

    # 4) User Profile
    user = _read_text(ws / "USER.md")
    blocks.append(
        user if user else "<!-- User Profile -->\n\n（未找到 USER.md，请补充用户画像。）"
    )

    # 5) Agents Guide
    agents = _read_text(ws / "AGENTS.md")
    blocks.append(
        agents
        if agents
        else "<!-- Agents Guide -->\n\n（未找到 AGENTS.md，请补充行为准则与记忆操作说明。）"
    )

    # 6) Long-term Memory (session)
    mem_path = MEMORY_DIR / f"{session_id}.md"
    mem_body = _read_text(mem_path)
    if not mem_body:
        mem_body = (
            "（本会话尚无 memory 文件；多轮对话后会写入 "
            f"`storage/memory/{session_id}.md`。RAG 检索请用 search_knowledge_base 工具，勿与对话记忆混淆。）"
        )
    blocks.append(f"<!-- Long-term Memory -->\n\n{mem_body}")

    return "\n\n".join(blocks)
