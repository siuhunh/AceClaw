import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from backend.app.core.config import AppSettings, LLMSettings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

_chat_model: "BaseChatModel | None" = None


def _normalize_model_type(raw: str) -> str:
    key = (raw or "deepseek").strip().lower().replace("-", "_")
    aliases = {
        "ds": "deepseek",
        "gpt": "openai",
        "open_ai": "openai",
        "openai_compatible": "openai",
    }
    return aliases.get(key, key)


def _build_chat_deepseek(settings: LLMSettings) -> ChatDeepSeek:
    api_key = settings.api_key.strip() or None
    return ChatDeepSeek(
        model=settings.model,
        temperature=settings.temperature,
        api_key=api_key,
        base_url=settings.base_url,
    )


def _build_chat_openai(settings: LLMSettings) -> ChatOpenAI:
    api_key = settings.api_key.strip() or None
    base_url = settings.base_url.strip() or None
    return ChatOpenAI(
        model=settings.model,
        temperature=settings.temperature,
        api_key=api_key,
        base_url=base_url,
    )


def _build_chat_ollama(settings: LLMSettings) -> ChatOllama:
    base = settings.base_url.strip() or "http://127.0.0.1:11434"
    return ChatOllama(
        model=settings.model,
        temperature=settings.temperature,
        base_url=base,
    )


_MODEL_TYPE_BUILDERS: dict[str, Callable[[LLMSettings], "BaseChatModel"]] = {
    "deepseek": _build_chat_deepseek,
    "openai": _build_chat_openai,
    "ollama": _build_chat_ollama,
}


def map_model_type_to_builder(model_type: str) -> Callable[[LLMSettings], "BaseChatModel"] | None:
    key = _normalize_model_type(model_type)
    return _MODEL_TYPE_BUILDERS.get(key)


def build_chat_model(settings: AppSettings) -> "BaseChatModel":
    llm = settings.llm
    preferred = _normalize_model_type(llm.model_type or llm.provider)
    builder = map_model_type_to_builder(preferred)

    if builder is None:
        logger.warning("unknown llm model_type %r, using ChatDeepSeek", preferred)
        return _build_chat_deepseek(llm)

    if preferred == "deepseek":
        return _build_chat_deepseek(llm)

    try:
        return builder(llm)
    except Exception:
        logger.warning(
            "failed to build chat model for type %r, falling back to ChatDeepSeek",
            preferred,
            exc_info=True,
        )
        return _build_chat_deepseek(llm)


def build_embedding_model(settings: AppSettings):
    use_ollama = (
        settings.embedding.use_ollama_for_rag
        and settings.embedding.provider.lower() == "ollama"
        and bool(settings.embedding.model)
    )
    if use_ollama:
        return OllamaEmbeddings(
            model=settings.embedding.model,
            base_url=settings.embedding.base_url or "http://127.0.0.1:11434",
        )

    embedding_model = settings.embedding.model or settings.llm.model
    return OpenAIEmbeddings(
        model=embedding_model,
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
    )


def init_agent_llm(settings: AppSettings) -> None:
    global _chat_model
    _chat_model = build_chat_model(settings)


def get_chat_model() -> "BaseChatModel":
    if _chat_model is None:
        raise RuntimeError("Agent LLM not initialized; ensure main startup calls init_agent_llm().")
    return _chat_model


def reset_agent_llm_for_tests() -> None:
    global _chat_model
    _chat_model = None
