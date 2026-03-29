"""
将 API 中的逻辑路径解析为 `backend/storage/` 下的真实文件。

约定（相对路径均相对于 `STORAGE_ROOT` = `backend/storage/`）：

- `skill/<相对路径>` → `backend/storage/skill/<相对路径>`
- `memory/<相对路径>` → `backend/storage/memory/<相对路径>`
"""

from pathlib import Path

from backend.app.core.config import MEMORY_DIR, SKILL_DIR, STORAGE_ROOT


def to_api_path(absolute: Path) -> str:
    rel = absolute.resolve().relative_to(STORAGE_ROOT.resolve())
    return "/".join(rel.parts)


def resolve_skill_path(path: str) -> Path:
    return _resolve_under(SKILL_DIR, path, "skill")


def resolve_memory_path(path: str) -> Path:
    return _resolve_under(MEMORY_DIR, path, "memory")


def _resolve_under(base_dir: Path, path: str, expected_prefix: str) -> Path:
    normalized = path.replace("\\", "/").strip().lstrip("/")
    if not normalized or ".." in normalized.split("/"):
        raise ValueError("invalid path")
    prefix, _, rest = normalized.partition("/")
    if prefix != expected_prefix or not rest:
        raise ValueError("invalid path")
    target = (base_dir / rest).resolve()
    base_resolved = base_dir.resolve()
    if not target.is_relative_to(base_resolved):
        raise ValueError("invalid path")
    return target
