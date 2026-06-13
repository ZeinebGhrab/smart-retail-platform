# `dataset/` — Jeux de données applicatifs

Ce dossier contient les **données structurées fixes** utilisées par le pipeline RAG et le système de benchmarking. Contrairement à `data/` (données opérationnelles volumineuses), ces fichiers sont légers, versionnés dans Git, et embarqués directement dans les images Docker.

---

## Fichiers

### `knowledge_base.json`

Base de connaissances métier du chatbot RAG. Contient **8 documents** couvrant les définitions, politiques et procédures du magasin.

**Structure d'un document :**
```json
{
  "id": "kb-001",
  "title": "Horaires d'ouverture du magasin",
  "content": "Le magasin Anavid Store 360 est ouvert..."
}
```

**Documents inclus :**

| ID | Sujet |
|---|---|
| `kb-001` | Horaires d'ouverture |
| `kb-002` | Définition du taux de conversion |
| `kb-003` | Définition du panier moyen |
| `kb-004` | Caméras de comptage installées (Porte_nord / Porte_sud) |
| `kb-005` | Procédure d'alerte stock critique |
| `kb-006` | Politique de confidentialité des données retail |
| `kb-007` | Interprétation du flux horaire de visiteurs |
| `kb-008` | Limites du modèle de prévision de visiteurs |

**Utilisation :**
- Dans `app/vector_store.py` : indexé dans **ChromaDB** via `sentence-transformers/all-MiniLM-L6-v2`. L'index est reconstruit avec `python app/vector_store.py --reindex`.
- Dans `django_api/history/rag_pipeline.py` : lu directement en mémoire, les embeddings sont calculés à la volée via `Ollama /api/embeddings` (pas de ChromaDB dans ce conteneur).

> **Pour enrichir la KB :** ajouter un objet JSON au tableau en respectant le schéma `{ id, title, content }`, puis relancer `--reindex` si l'agent standalone est utilisé.

---

### `tool_calling_queries.json`

Jeu de test pour le système de **benchmarking LLM** (`scripts/benchmark.py`). Contient une collection de requêtes utilisateurs annotées avec l'outil attendu et les paramètres corrects.

**Structure d'une requête :**
```json
{
  "id": 3,
  "query": "Combien de visiteurs aujourd'hui ?",
  "expected_tool": "get_visitor_count",
  "expected_params": { "date": null, "camera": null }
}
```

**Couverture des tests :**
- Requêtes en français, anglais et arabe
- Les 5 outils : `get_visitor_count`, `get_hourly_visitor_flow`, `forecast_visitors`, `get_visitor_history`, `search_knowledge_base`
- Cas limites : paramètres null, dates relatives ("hier", "demain"), filtres par caméra

Ce fichier est la référence pour évaluer la précision du **tool calling** de chaque modèle candidat (taux de JSON valide, bon outil sélectionné, bons paramètres extraits).