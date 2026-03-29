import logging
from typing import Any, Callable

from langchain_core.tools import BaseTool

from backend.app.core.config import INDEX_DIR, KNOWLEDGE_DIR

logger = logging.getLogger(__name__)


def _collect_text_docs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if not KNOWLEDGE_DIR.exists():
        return pairs
    for ext in ("*.md", "*.txt", "*.MD", "*.TXT"):
        for path in KNOWLEDGE_DIR.rglob(ext):
            if path.is_file():
                try:
                    pairs.append((str(path.relative_to(KNOWLEDGE_DIR)), path.read_text(encoding="utf-8", errors="ignore")))
                except OSError:
                    continue
    return pairs


def _bm25_search_factory() -> Callable[[str], str]:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:

        def _no_bm25(query: str) -> str:
            return "rank-bm25 not installed; cannot run keyword search."

        return _no_bm25

    pairs = _collect_text_docs()
    if not pairs:
        return lambda q: "Knowledge base is empty. Add .md/.txt under storage/knowledge/."

    tokenized_corpus = [doc.lower().split() for _, doc in pairs]
    bm25 = BM25Okapi(tokenized_corpus)

    def search(query: str) -> str:
        q = query.lower().split()
        if not q:
            return "Empty query."
        scores = bm25.get_scores(q)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:6]
        chunks: list[str] = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            rel, body = pairs[i]
            chunks.append(f"### {rel} (score={scores[i]:.3f})\n{body[:1200]}")
        return "\n\n".join(chunks) if chunks else "No BM25 hits."

    return search


def _try_build_llama_hybrid(settings: Any) -> Callable[[str], str] | None:
    if not (settings.llm.api_key or "").strip():
        logger.info("No LLM API key; skip LlamaIndex vector index (BM25 fallback still available).")
        return None

    try:
        from llama_index.core import (
            SimpleDirectoryReader,
            VectorStoreIndex,
            StorageContext,
            Settings as LISettings,
            load_index_from_storage,
        )
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.retrievers import QueryFusionRetriever
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.retrievers.bm25 import BM25Retriever
    except ImportError as e:
        logger.warning("LlamaIndex not available: %s", e)
        return None

    if not KNOWLEDGE_DIR.exists() or not any(KNOWLEDGE_DIR.iterdir()):
        return lambda q: "Knowledge base is empty. Add PDF/MD/TXT under storage/knowledge/."

    persist = str(INDEX_DIR.resolve())
    embed_model_name = (settings.embedding.model or "text-embedding-3-small").strip()
    api_base = (settings.embedding.base_url or settings.llm.base_url or "").strip() or None

    try:
        LISettings.embed_model = OpenAIEmbedding(
            model=embed_model_name,
            api_key=settings.llm.api_key.strip(),
            api_base=api_base,
        )
    except Exception as e:
        logger.warning("LlamaIndex embedding init failed: %s", e)
        return None

    try:
        reader = SimpleDirectoryReader(input_dir=str(KNOWLEDGE_DIR), recursive=True)
        documents = reader.load_data()
        if not documents:
            return lambda q: "No loadable documents in storage/knowledge/."

        index: VectorStoreIndex
        try:
            if INDEX_DIR.exists() and any(INDEX_DIR.iterdir()):
                storage_context = StorageContext.from_defaults(persist_dir=persist)
                index = load_index_from_storage(storage_context)
            else:
                raise FileNotFoundError("no index")
        except Exception:
            sc = StorageContext.from_defaults()
            index = VectorStoreIndex.from_documents(documents, storage_context=sc)
            index.storage_context.persist(persist_dir=persist)

        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
        nodes = splitter.get_nodes_from_documents(documents)
        vector_retriever = index.as_retriever(similarity_top_k=4)
        bm25_retriever = None
        try:
            bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=4)
        except Exception as e:
            logger.warning("BM25Retriever init failed: %s", e)

        qe = index.as_query_engine(similarity_top_k=6)

        def search_qe(query: str) -> str:
            return str(qe.query(query))

        if bm25_retriever is None:
            return search_qe

        try:
            fusion = QueryFusionRetriever(
                [vector_retriever, bm25_retriever],
                num_queries=1,
                mode="reciprocal_rerank",
            )

            def search_fusion(query: str) -> str:
                nodes_out = fusion.retrieve(query)
                parts = []
                for n in nodes_out[:8]:
                    parts.append(n.get_content()[:1800])
                return "\n\n---\n\n".join(parts) if parts else "No retrieval results."

            return search_fusion
        except Exception as e:
            logger.warning("QueryFusionRetriever unavailable (%s); using vector query engine.", e)
            return search_qe
    except Exception as e:
        logger.warning("LlamaIndex pipeline failed: %s", e)
        return None


def build_knowledge_search_tool(settings: Any) -> BaseTool:
    """§3.9.5 — hybrid when LlamaIndex + embeddings work; else BM25 on text files."""
    hybrid = _try_build_llama_hybrid(settings)
    bm25_only = _bm25_search_factory()
    runner = hybrid or bm25_only

    class SearchKnowledgeBaseTool(BaseTool):
        name: str = "search_knowledge_base"
        description: str = (
            "Search the local knowledge base under storage/knowledge (not chat history). "
            "Uses vector+BM25 fusion when the LlamaIndex index is available; otherwise keyword search."
        )

        def _run(self, query: str, **kwargs: Any) -> str:
            return runner(query.strip() or "")

        async def _arun(self, query: str, **kwargs: Any) -> str:
            return self._run(query, **kwargs)

    return SearchKnowledgeBaseTool()
