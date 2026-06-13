# ============================================================
# vector_store.py — Couche base vectorielle (ChromaDB)
# ============================================================
#
# Rôle :
#   - Indexer dataset/knowledge_base.json (FAQ, définitions métier,
#     politiques) dans une base vectorielle persistante (Chroma).
#   - Servir de FALLBACK SÉMANTIQUE quand une requête utilisateur ne
#     correspond à aucun tool calling structuré (visitor_agent.py).
#
# Embeddings : sentence-transformers/all-MiniLM-L6-v2 (léger, CPU-friendly,
# multilingue suffisant pour FR ; fonctionne aussi raisonnablement en AR).
#
# Persistance : ./vector_db (monté en volume Docker, voir docker-compose.yml)
#
# Usage :
#   python app/vector_store.py --reindex     # (re)construit l'index
#   python app/vector_store.py "définition du panier moyen"
# ============================================================

from __future__ import annotations

import json
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parent.parent
KB_PATH = ROOT / "dataset" / "knowledge_base.json"
DB_PATH = ROOT / "vector_db"
COLLECTION_NAME = "shopanalytics_kb"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_client() -> chromadb.PersistentClient:
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_PATH))


def get_collection(client: chromadb.PersistentClient | None = None):
    client = client or get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )


def reindex(kb_path: Path = KB_PATH) -> int:
    """Reconstruit l'index vectoriel à partir de knowledge_base.json."""
    with open(kb_path, encoding="utf-8") as f:
        docs = json.load(f)

    client = get_client()
    # Repart d'une collection vide pour éviter les doublons à chaque reindex
    try:
        client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass
    collection = get_collection(client)

    collection.add(
        ids=[d["id"] for d in docs],
        documents=[f"{d['title']} : {d['content']}" for d in docs],
        metadatas=[{"title": d["title"]} for d in docs],
    )
    return len(docs)


def semantic_search(query: str, n_results: int = 2) -> list[dict]:
    """Retourne les documents KB les plus pertinents pour une requête."""
    collection = get_collection()
    if collection.count() == 0:
        reindex()
        collection = get_collection()

    results = collection.query(query_texts=[query], n_results=n_results)
    out = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        out.append({"title": meta.get("title"), "content": doc, "distance": dist})
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reindex":
        n = reindex()
        print(f"Index reconstruit : {n} documents.")
    else:
        q = " ".join(sys.argv[1:]) or "définition du panier moyen"
        for r in semantic_search(q):
            print(f"[{r['distance']:.3f}] {r['title']}: {r['content']}")
