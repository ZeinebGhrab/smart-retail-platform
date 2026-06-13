# `vector_db/` — Base vectorielle persistante (ChromaDB)

Ce dossier est le **répertoire de persistance de ChromaDB**, utilisé exclusivement par l'agent standalone (`app/vector_store.py`). Il est monté en volume Docker pour survivre aux redémarrages du conteneur.

---

## Contenu

| Fichier | Description |
|---|---|
| `chroma.sqlite3` | Base SQLite interne de ChromaDB — stocke les vecteurs, métadonnées et la collection `shopanalytics_kb` |
| `.gitkeep` | Fichier vide pour que Git suive le dossier même si `chroma.sqlite3` est dans `.gitignore` |

---

## Collection indexée

**Nom :** `shopanalytics_kb`  
**Source :** `dataset/knowledge_base.json` (8 documents)  
**Modèle d'embedding :** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)  
**Similarité :** cosinus (défaut ChromaDB)

---

## Cycle de vie

```
Premier appel à semantic_search()
    ↓ collection vide ?
    → reindex() appelé automatiquement
    → 8 documents ajoutés à chroma.sqlite3

Appels suivants
    → collection chargée depuis le disque (lecture rapide)

Mise à jour de knowledge_base.json
    → python app/vector_store.py --reindex
    → ancienne collection supprimée et reconstruite
```

---

## Notes importantes

- **Ne pas versionner `chroma.sqlite3`** dans Git (fichier binaire lourd, regénérable en une commande). Ajouter à `.gitignore` et ne conserver que `.gitkeep`.
- **Conteneur `django_api`** : ce dossier n'est **pas** monté dans `django_api`. Ce conteneur n'utilise pas ChromaDB — il calcule la similarité cosinus directement en Python avec les embeddings d'Ollama.
- **Rebuild** : si ChromaDB est mis à jour (version majeure), le format de `chroma.sqlite3` peut changer ; supprimer le fichier et relancer `--reindex`.

---

## Volume Docker

Dans `docker-compose.yml` :
```yaml
volumes:
  - ./backend/vector_db:/workspace/vector_db
```

Ce montage garantit que l'index vectoriel survit au redémarrage du conteneur `backend` et évite de reconstruire les embeddings à chaque démarrage (~5-10 secondes sur CPU).