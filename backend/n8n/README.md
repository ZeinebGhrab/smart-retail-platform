# `n8n/` — Orchestrateur de workflows (rapport quotidien automatisé)

Ce dossier contient la configuration du service **N8N** (`docker-compose.yml`, service `n8n`, port `5678`), utilisé pour automatiser la génération et la diffusion d'un rapport de prévision de fréquentation chaque matin.

---

## Contenu

| Élément | Description |
|---|---|
| `workflows/ShopAnalyticsVersionFinal-2.json` | Le workflow N8N à importer dans l'interface (voir `workflows/README.md`) |

---

## Rôle dans l'architecture

```
N8N (cron 6h00)
  │
  ├─ génère une prédiction de fréquentation
  ├─ demande au LLM (Ollama, via le node LangChain) de rédiger un message professionnel
  ├─ POST http://shopanalytics-django-api:8000/api/daily-report/
  │       └─► Django persiste + diffuse en SSE → Dashboard.tsx (temps réel)
  └─ POST http://django_api:8000/api/chat/ (rapport injecté dans l'historique du chat)
```

N8N communique avec `django_api` et `ollama` via le **réseau Docker interne** (noms de service, pas `localhost`) — voir `docker-compose.yml`, les `container_name` correspondants sont `shopanalytics-django-api` et `shopanalytics-ollama`.

---

## Accès à l'interface

```bash
docker compose up n8n
```

Interface web : http://localhost:5678

Configuration définie dans `docker-compose.yml` :

| Variable | Valeur |
|---|---|
| `N8N_HOST` / `N8N_PORT` | `localhost` / `5678` |
| `WEBHOOK_URL` | `http://localhost:5678/` |
| `GENERIC_TIMEZONE` | `Europe/Paris` |
| `N8N_SECURE_COOKIE` | `false` (dev local, pas de HTTPS) |

Les données N8N (credentials, exécutions) sont persistées dans le volume Docker nommé `shopanalytics_n8n_data` — elles ne sont **pas** dans ce dossier.

---

## Importer le workflow

1. Ouvrir http://localhost:5678
2. **Workflows → Import from File**
3. Sélectionner `workflows/ShopAnalyticsVersionFinal-2.json`
4. Configurer les credentials du node Ollama (`Ollama Model`) pour pointer vers `http://ollama:11434`
5. Activer le workflow (`Active`)

> Aucun secret n'est stocké dans le fichier `.json` du workflow lui-même — les credentials N8N (si besoin) se configurent depuis l'interface et sont chiffrées dans le volume `n8n_data`.
