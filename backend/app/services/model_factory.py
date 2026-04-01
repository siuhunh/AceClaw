from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from backend.app.core.config import AppSettings


def build_chat_model(settings: AppSettings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm.model,
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        temperature=settings.llm.temperature,
    )


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
