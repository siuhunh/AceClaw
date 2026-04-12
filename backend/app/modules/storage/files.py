from pathlib import Path

from backend.app.core.storage_paths import resolve_memory_path, resolve_skill_path


def read_skill_file(path: str) -> str:
    p = resolve_skill_path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def write_skill_file(path: str, content: str) -> Path:
    p = resolve_skill_path(path)
    if p.suffix.lower() != ".md":
        raise ValueError("skill path must end with .md")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def read_memory_file(path: str) -> str:
    p = resolve_memory_path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def write_memory_file(path: str, content: str) -> Path:
    p = resolve_memory_path(path)
    if p.suffix.lower() not in (".md", ".json"):
        raise ValueError("memory path must end with .md or .json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
