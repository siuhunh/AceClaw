import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.core.config import AppSettings
from backend.app.core.model_factory import build_embedding_model

logger = logging.getLogger("ace_claw")

_store: "MilvusVectorMemoryStore | None" = None


class MilvusVectorMemoryStore:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._cfg = settings.vectordb
        self._embedding = build_embedding_model(settings)
        self._connected = False
        self._collection = None
        self._pymilvus = None

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled and self._cfg.provider.lower() == "milvus"

    def initialize(self) -> None:
        if not self.enabled:
            logger.info("vector memory disabled by config")
            return
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )
        except Exception as e:
            logger.warning("pymilvus not available, vector memory disabled: %s", e)
            return

        try:
            self._pymilvus = {
                "Collection": Collection,
                "CollectionSchema": CollectionSchema,
                "DataType": DataType,
                "FieldSchema": FieldSchema,
                "connections": connections,
                "utility": utility,
            }
            uri = (self._cfg.uri or "").strip()
            kwargs: dict[str, Any] = {"alias": "aceclaw_milvus"}
            if uri:
                kwargs["uri"] = uri
            else:
                kwargs["host"] = self._cfg.host
                kwargs["port"] = self._cfg.port
            if self._cfg.token:
                kwargs["token"] = self._cfg.token
            if self._cfg.db_name:
                kwargs["db_name"] = self._cfg.db_name
            connections.connect(**kwargs)

            collection_name = self._cfg.collection_name
            utility_mod = self._pymilvus["utility"]
            if utility_mod.has_collection(collection_name, using="aceclaw_milvus"):
                collection = Collection(collection_name, using="aceclaw_milvus")
            else:
                collection = self._create_collection(collection_name)
            self._collection = collection
            self._collection.load()
            self._connected = True
            logger.info("milvus vector memory initialized collection=%s", collection_name)
        except Exception as e:
            logger.warning("milvus init failed, vector memory disabled: %s", e)
            self._connected = False
            self._collection = None

    def _create_collection(self, collection_name: str):
        FieldSchema = self._pymilvus["FieldSchema"]
        DataType = self._pymilvus["DataType"]
        CollectionSchema = self._pymilvus["CollectionSchema"]
        Collection = self._pymilvus["Collection"]

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="ts", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self._cfg.embedding_dim),
        ]
        schema = CollectionSchema(fields=fields, description="AceClaw conversation memories")
        collection = Collection(
            name=collection_name,
            schema=schema,
            using="aceclaw_milvus",
        )
        try:
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "AUTOINDEX",
                    "metric_type": self._cfg.metric_type,
                    "params": {},
                },
            )
        except Exception:
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "HNSW",
                    "metric_type": self._cfg.metric_type,
                    "params": {"M": 16, "efConstruction": 200},
                },
            )
        return collection

    def _embed_query(self, text: str) -> list[float]:
        if hasattr(self._embedding, "embed_query"):
            return list(self._embedding.embed_query(text))
        if hasattr(self._embedding, "embed_documents"):
            return list(self._embedding.embed_documents([text])[0])
        raise RuntimeError("embedding model does not support query embeddings")

    def remember_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        if not self._connected or self._collection is None:
            return
        ts = datetime.now(timezone.utc).isoformat()
        text = f"user: {user_message}\nassistant: {assistant_message}"
        if len(text) > 8000:
            text = text[:8000]
        try:
            vec = self._embed_query(text)
            self._collection.insert(
                [
                    [session_id],
                    [ts],
                    [text],
                    [vec],
                ]
            )
        except Exception as e:
            logger.warning("milvus remember_turn failed: %s", e)

    def search(self, session_id: str, query: str) -> list[str]:
        if not self._connected or self._collection is None:
            return []
        if not query.strip():
            return []
        try:
            vec = self._embed_query(query)
            results = self._collection.search(
                data=[vec],
                anns_field="embedding",
                param={"metric_type": self._cfg.metric_type, "params": {"nprobe": 10}},
                limit=max(1, self._cfg.top_k),
                expr=f'session_id == "{session_id}"',
                output_fields=["text", "ts"],
            )
            out: list[str] = []
            if results:
                for hit in results[0]:
                    ent = hit.entity
                    text = ent.get("text") if ent else ""
                    ts = ent.get("ts") if ent else ""
                    if text:
                        out.append(f"[{ts}] {text}")
            return out
        except Exception as e:
            logger.warning("milvus search failed: %s", e)
            return []


def init_vector_memory(settings: AppSettings) -> None:
    global _store
    _store = MilvusVectorMemoryStore(settings)
    _store.initialize()


def get_vector_memory() -> MilvusVectorMemoryStore | None:
    return _store
