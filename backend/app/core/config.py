import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
SKILLS_DIR = BASE_DIR / "skills"
CONFIG_FILE = BASE_DIR / "config.toml"
DEFAULT_ENV_FILE_NAME = ".env"
DEFAULT_LOG_FILE = BASE_DIR / "ace_claw.log"


@dataclass
class LLMSettings:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.2


@dataclass
class EmbeddingSettings:
    provider: str = "deepseek"
    model: str = ""
    base_url: str = ""
    use_ollama_for_rag: bool = False


@dataclass
class AppSettings:
    llm: LLMSettings
    embedding: EmbeddingSettings


def ensure_runtime_dirs() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def load_env_file(env_dir: str | None = None, env_file_name: str = DEFAULT_ENV_FILE_NAME) -> Path | None:
    target_dir = Path(env_dir).resolve() if env_dir else BASE_DIR
    env_path = target_dir / env_file_name

    if env_dir and not env_path.exists():
        raise RuntimeError(f"Missing env file: {env_path}")
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"' ")
        if key:
            os.environ[key] = value
    return env_path


def resolve_log_path(cli_log_path: str | None = None) -> Path:
    if cli_log_path:
        return Path(cli_log_path).resolve()
    env_log_path = os.getenv("ACE_CLAW_LOG_PATH", "").strip()
    if env_log_path:
        return Path(env_log_path).resolve()
    return DEFAULT_LOG_FILE


def setup_file_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ace_claw")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def _deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _from_file() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    with CONFIG_FILE.open("rb") as f:
        return tomllib.load(f)


def _from_env() -> dict[str, Any]:
    env: dict[str, Any] = {
        "llm": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "model": os.getenv("LLM_MODEL", ""),
            "base_url": os.getenv("LLM_BASE_URL", ""),
        },
        "embedding": {
            "provider": os.getenv("EMBEDDING_PROVIDER", ""),
            "model": os.getenv("EMBEDDING_MODEL", ""),
            "base_url": os.getenv("EMBEDDING_BASE_URL", ""),
            "use_ollama_for_rag": os.getenv("USE_OLLAMA_FOR_RAG", "").lower() == "true",
        },
    }
    return env


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    defaults: dict[str, Any] = {
        "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "",
            "base_url": "https://api.deepseek.com/v1",
            "temperature": 0.2,
        },
        "embedding": {
            "provider": "deepseek",
            "model": "",
            "base_url": "",
            "use_ollama_for_rag": False,
        },
    }

    merged = _deep_merge(defaults, _from_file())
    merged = _deep_merge(merged, _from_env())

    llm_map = merged["llm"]
    emb_map = merged["embedding"]

    llm = LLMSettings(
        provider=llm_map.get("provider") or "deepseek",
        model=llm_map.get("model") or "deepseek-chat",
        api_key=llm_map.get("api_key") or "",
        base_url=llm_map.get("base_url") or "https://api.deepseek.com/v1",
        temperature=float(llm_map.get("temperature", 0.2)),
    )
    embedding = EmbeddingSettings(
        provider=emb_map.get("provider") or "deepseek",
        model=emb_map.get("model") or "",
        base_url=emb_map.get("base_url") or "",
        use_ollama_for_rag=bool(emb_map.get("use_ollama_for_rag", False)),
    )
    return AppSettings(llm=llm, embedding=embedding)
