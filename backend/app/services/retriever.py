"""Local FAISS retriever for WheelTrip Jeju RAG search.

Needs the heavy deps in requirements-rag.txt (numpy/sentence-transformers/faiss-cpu);
these are excluded from backend/requirements.txt since /api/rag/ask is not
currently called by the frontend.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, get_settings


PROJECT_ROOT = BASE_DIR.parent


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _load_metadata(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


class RagRetriever:
    def __init__(self, vector_store_dir: Path, embedding_model: str) -> None:
        import faiss
        from sentence_transformers import SentenceTransformer

        self.vector_store_dir = vector_store_dir
        self.embedding_model = embedding_model
        self.index = faiss.read_index(str(vector_store_dir / "faiss_index" / "index.faiss"))
        self.metadata = _load_metadata(vector_store_dir / "metadata.jsonl")
        self.model = SentenceTransformer(embedding_model)
        if self.index.ntotal != len(self.metadata):
            raise RuntimeError(
                "FAISS index and metadata size mismatch: "
                f"{self.index.ntotal} != {len(self.metadata)}"
            )

    def _candidate_match(
        self,
        doc: dict[str, Any],
        place_name: str | None,
        category: str | None,
    ) -> bool:
        if place_name:
            wanted_place = _norm(place_name)
            doc_place = _norm(doc.get("place_name"))
            if wanted_place not in doc_place and doc_place not in wanted_place:
                return False
        if category and _norm(doc.get("category")) != _norm(category):
            return False
        return True

    def _format_result(self, score: float, doc: dict[str, Any]) -> dict[str, Any]:
        place_id = doc.get("place_id")
        return {
            "score": float(score),
            "doc_id": doc.get("doc_id"),
            "place_id": str(place_id) if place_id is not None else None,
            "place_name": doc.get("place_name"),
            "lat": doc.get("lat"),
            "lng": doc.get("lng"),
            "category": doc.get("category"),
            "risk_level": doc.get("risk_level"),
            "text": doc.get("text") or "",
            "source_type": doc.get("source_type"),
            "source_file": doc.get("source_file"),
            "image_file": doc.get("image_file"),
            "source": doc.get("source"),
        }

    def retrieve_documents(
        self,
        query: str,
        place_name: str | None = None,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        limit = max(top_k, 1)
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        # The current index is small, so searching all vectors gives reliable
        # filtered retrieval without maintaining per-filter FAISS sub-indexes.
        search_k = max(self.index.ntotal, limit)
        scores, indices = self.index.search(query_embedding, search_k)

        filtered: list[dict[str, Any]] = []
        fallback: list[dict[str, Any]] = []
        seen_doc_ids: set[str] = set()

        for score, index_id in zip(scores[0], indices[0]):
            if index_id < 0 or index_id >= len(self.metadata):
                continue
            doc = self.metadata[int(index_id)]
            doc_id = str(doc.get("doc_id"))
            if doc_id in seen_doc_ids:
                continue
            result = self._format_result(float(score), doc)
            if self._candidate_match(doc, place_name, category):
                filtered.append(result)
                seen_doc_ids.add(doc_id)
            else:
                fallback.append(result)

            if len(filtered) >= limit:
                break

        if len(filtered) < limit and (place_name or category):
            for result in fallback:
                doc_id = str(result.get("doc_id"))
                if doc_id in seen_doc_ids:
                    continue
                filtered.append(result)
                seen_doc_ids.add(doc_id)
                if len(filtered) >= limit:
                    break

        return filtered[:limit]


@lru_cache
def get_retriever() -> RagRetriever:
    settings = get_settings()
    vector_store_dir = _resolve_path(settings.rag_vector_store_dir)
    return RagRetriever(vector_store_dir, settings.rag_embedding_model)


def retrieve_documents(
    query: str,
    place_name: str | None = None,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    return get_retriever().retrieve_documents(
        query=query,
        place_name=place_name,
        category=category,
        top_k=top_k,
    )
