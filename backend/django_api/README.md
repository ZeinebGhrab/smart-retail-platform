# `django_api/` — API REST Django (production)

Ce dossier contient le **serveur API HTTP de ShopAnalytics**, exposé aux clients (frontend Ionic, intégrations tierces). Basé sur **Django 5 + Django REST Framework**, il fournit l'authentification des comptes commerce, les endpoints analytiques visiteurs, ainsi qu'un endpoint de chat RAG alimenté par Ollama.

Ce conteneur est **léger** : il délègue les embeddings directement à Ollama via HTTP (pas de `torch`, pas de `chromadb`, pas de `sentence-transformers`).

---

## Structure

```
django_api/
├── accounts/                # Application Django — authentification
│   ├── models.py            # User (auth par e-mail) + PasswordResetToken (OTP)
│   ├── managers.py          # UserManager (création par e-mail, sans username)
│   ├── serializers.py       # Register / Login / PasswordReset (validation FR)
│   ├── views.py             # register, login, me, logout, password-reset/*
│   ├── urls.py              # Routage /api/auth/...
│   ├── admin.py             # Interface admin du modèle User
│   └── apps.py
├── config/                  # Configuration Django globale
│   ├── settings.py          # Paramètres (DB, apps, CORS, EMAIL_* — lus depuis l'environnement)
│   ├── urls.py              # Routage racine + Swagger
│   ├── wsgi.py / asgi.py    # Points d'entrée WSGI/ASGI
│   └── __init__.py
├── history/                 # Application Django — analytics + RAG + notifications
│   ├── views.py             # Endpoints REST analytics visiteurs + notifications N8N + SSE
│   ├── chat_view.py         # Endpoint POST /api/chat/
│   ├── rag_pipeline.py      # Pipeline RAG (Ollama HTTP)
│   ├── visitor_data.py      # Couche données CSV (identique à app/)
│   ├── urls.py              # Routage de l'app history
│   └── apps.py
├── manage.py                # CLI Django
├── requirements.txt         # Dépendances (sans torch/chromadb)
├── Dockerfile               # Image légère python:3.11-slim
└── db.sqlite3               # Base SQLite (comptes utilisateurs, sessions admin)
```

---

## Endpoints exposés

Base URL : `http://localhost:8000/api/`

### Authentification (`accounts/`)

| Méthode | URL | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Inscription — prénom, nom, nom du commerce, e-mail, mot de passe |
| `POST` | `/api/auth/login/` | Connexion par e-mail + mot de passe → tokens JWT |
| `POST` | `/api/auth/refresh/` | Renouvellement de l'access token |
| `GET` | `/api/auth/me/` | Profil de l'utilisateur connecté (JWT requis) |
| `POST` | `/api/auth/logout/` | Déconnexion — blackliste le refresh token |
| `POST` | `/api/auth/password-reset/request/` | Étape 1 — envoie un OTP 6 chiffres par e-mail (Gmail SMTP) |
| `POST` | `/api/auth/password-reset/verify/` | Étape 2 — vérifie le code OTP |
| `POST` | `/api/auth/password-reset/confirm/` | Étape 3 — change le mot de passe |

### Analytics & RAG (`history/`)

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/history/visitors/` | Historique journalier avec ventilation genre/âge |
| `GET` | `/api/history/visitors/count/` | Comptage pour une date donnée |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire + heure de pointe |
| `GET` | `/api/history/visitors/forecast/` | Prévision J+1 (régression linéaire) |
| `GET` | `/api/history/summary/` | KPIs globaux (période, total, répartition) |
| `GET` | `/api/history/cameras/` | Liste des caméras disponibles |
| `POST` | `/api/chat/` | Chat RAG en langage naturel (Ollama) |

### Notifications & rapport quotidien N8N (`history/`)

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/notifications/latest/` | Dernière notification reçue de N8N |
| `GET` | `/api/notifications/history/` | Historique des notifications (jusqu'à 100) |
| `GET` | `/api/prediction/stream/` | Connexion SSE longue durée — écoutée par `Dashboard.tsx` |
| `POST` | `/api/daily-report/` | Reçoit le rapport prédictif depuis N8N et le diffuse en SSE |

### Notifications push FCM (`history/`)

| Méthode | URL | Description |
|---|---|---|
| `POST` | `/api/fcm-token/` | Enregistre le token push FCM d'un appareil (appelé par le frontend) |
| `POST` | `/api/send-fcm/` | Envoie une notification push à tous les appareils enregistrés via l'API FCM v1 |

### Documentation

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/api/docs/` | Swagger UI (drf-spectacular) |
| `GET` | `/api/redoc/` | ReDoc |

**Paramètres communs (query string) — endpoints `history/visitors/*` :**
- `date` — format `YYYY-MM-DD` (défaut : dernière date disponible)
- `start_date` / `end_date` — plage de dates
- `camera` — `Porte_nord` ou `Porte_sud` (défaut : toutes)

---

## Application `accounts/`

### `models.py`
Modèle `User` personnalisé (`AbstractUser` avec `username` désactivé) : l'identifiant unique est l'**e-mail**, complété par `store_name` (un compte = un commerce), aligné sur les champs du formulaire `Register.tsx`.

`PasswordResetToken` gère le flux OTP : code à 6 chiffres généré aléatoirement, valable **15 minutes**, à usage unique (`is_valid()` / `consume()`).

### `managers.py`
`UserManager` personnalisé : Django attend par défaut un champ `username`, qui est ici remplacé par l'e-mail comme identifiant de connexion.

### `serializers.py`
- `RegisterSerializer` — valide l'unicité de l'e-mail et la correspondance `password`/`confirm`, avec messages d'erreur en français.
- `LoginSerializer` — authentifie via `authenticate(email=..., password=...)`.
- `PasswordResetRequestSerializer` / `VerifySerializer` / `ConfirmSerializer` — les 3 étapes du mot de passe oublié.

### `views.py` — Authentification JWT (djangorestframework-simplejwt)

| Vue | Détail |
|---|---|
| `register` | Crée le compte, retourne le profil + paire de tokens JWT (access/refresh) |
| `login` | Authentifie, retourne le profil + tokens. Message d'erreur générique (pas de détail champ par champ, par sécurité) |
| `me` | Retourne le profil de l'utilisateur authentifié (`IsAuthenticated`) |
| `logout` | Blackliste le refresh token fourni |
| `password_reset_request` | Génère un OTP et l'envoie par **e-mail HTML via Gmail SMTP** (`EmailMultiAlternatives`) — réponse identique que le compte existe ou non, pour éviter l'énumération d'e-mails |
| `password_reset_verify` | Vérifie le code sans le consommer |
| `password_reset_confirm` | Vérifie le code et met à jour le mot de passe |

**Configuration SMTP utilisée par `password_reset_request`** (voir `config/settings.py`) :

```python
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
```

> Ces deux dernières variables sont des **secrets** : elles sont définies dans le fichier `.env` à la racine du repo (jamais commité), pas dans le code ni dans `docker-compose.yml`. Voir le `README.md` racine, section 9, pour la procédure de configuration et la génération d'un mot de passe d'application Gmail.

---

## Application `history/`

### `views.py`
Vues DRF décorées avec `@extend_schema` (OpenAPI). Chaque vue analytics délègue le calcul à `visitor_data.py` et retourne un `Response` DRF. Les vues sont documentées automatiquement dans Swagger.

Ce fichier contient également le **canal de notifications N8N** :
- `daily_report` (`POST /api/daily-report/`) — reçoit le payload prédictif envoyé chaque matin par le workflow N8N (`backend/n8n/workflows/`), le persiste dans un fichier JSON (100 derniers, via `_append_notification`) et le diffuse immédiatement à tous les clients SSE connectés.
- `sse_stream` (`GET /api/prediction/stream/`, alias `prediction_stream`) — ouvre une connexion SSE longue durée (`StreamingHttpResponse`) avec heartbeat de connexion et keepalive toutes les 30 s ; le `Dashboard.tsx` du frontend s'y abonne via le hook `useSSEPrediction.ts` pour recevoir l'événement `llm_report` en temps réel.
- `latest_notification` / `notifications_history` — exposent respectivement la dernière notification et l'historique complet, lus depuis le même fichier JSON.

Ainsi que le **canal de notifications push FCM** :
- `save_fcm_token` (`POST /api/fcm-token/`) — enregistre un token d'appareil dans le modèle `FCMToken` (`get_or_create`, pas de doublon).
- `send_fcm` (`POST /api/send-fcm/`) — génère un token OAuth2 via `_get_fcm_access_token()` (JWT signé avec `FCM_PRIVATE_KEY`), envoie une notification à chaque token enregistré via l'API FCM v1 et retourne directement le résultat (`sent`, `errors`). Aucune persistance en base pour les logs d'envoi FCM. Lève une `FCMConfigError` si `FCM_PROJECT_ID` / `FCM_CLIENT_EMAIL` / `FCM_PRIVATE_KEY` sont absents ou invalides.

Procédure complète de configuration FCM (Service Account, clés frontend, `google-services.json`) : [`frontend/README_APK_Android.md` section 4](../../frontend/README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

### `visitor_data.py`
Copie fonctionnelle de `app/visitor_data.py`, adaptée au contexte Docker (chemin CSV via variable d'environnement `VISITOR_DATA_CSV`). Inclut un **cache en mémoire** avec invalidation par `mtime` : le CSV est rechargé uniquement si le fichier a changé sur disque.

### `rag_pipeline.py`
Pipeline RAG sans dépendances lourdes :

1. `_build_csv_context()` — extrait les métriques clés du CSV (KPIs du jour, flux horaire, top caméra) pour les injecter dans le prompt
2. `_retrieve_kb()` — calcule la similarité cosinus entre la question et les 8 documents de `dataset/knowledge_base.json` via `Ollama /api/embeddings` (pas de ChromaDB)
3. `_build_prompt()` — assemble le contexte CSV + les documents KB pertinents + la question utilisateur
4. `_call_ollama()` — envoie le prompt à `Ollama /api/generate` et retourne la réponse en streaming ou bloc

**Architecture réseau dans Docker :**
```
[frontend] → [django_api:8000] → [ollama:11434]
                  ↑
          lit /app/data/*.csv  (volume partagé)
```

### `chat_view.py`
Vue `POST /api/chat/` qui orchestre `rag_pipeline.py`. Accepte `{ "question": "..." }` et retourne `{ "answer": "...", "model": "...", "sources": {...} }`.

---

## Recherche approfondie — Pipeline RAG : frameworks, outils et paramètres

### Qu'est-ce que le RAG ?

**RAG (Retrieval-Augmented Generation)** est une architecture qui enrichit la génération de texte par un LLM avec des données externes récupérées dynamiquement. Au lieu de se reposer uniquement sur les connaissances mémorisées lors de l'entraînement, le modèle reçoit des extraits de contexte pertinents avant de formuler sa réponse.

```
Question utilisateur
        │
        ▼
  [ Retriever ]  ────────────────────────────────────────────────────►┐
  Recherche sémantique dans la base vectorielle                        │
  (embedding de la question + cosine similarity)                       │
                                                                       │
  [ Augmentation ]  ◄────────────────────────────────────────────────┘
  Construction du prompt : contexte récupéré + question               │
                                                                       │
  [ Generation ]                                                       │
  LLM local (Llama 3.2 / Qwen 2.5 / Mistral via Ollama)              │
        │                                                              │
        ▼
  Réponse enrichie et factuellement ancrée
```

---

### Principaux frameworks RAG disponibles

#### 1. LangChain

Le framework le plus populaire pour construire des applications LLM complètes.

**Fonctionnalités clés :**
- Chargement de documents (PDF, Word, Excel, Web, bases de données, etc.)
- Découpage de texte configurable (chunking) — `RecursiveCharacterTextSplitter`, `TokenTextSplitter`
- Génération d'embeddings via OpenAI, HuggingFace, Ollama
- Connexion native aux bases vectorielles : Qdrant, Chroma, FAISS, Weaviate, Pinecone
- Chaînes RAG complètes (`RetrievalQA`, `ConversationalRetrievalChain`)
- Agents IA avec tool calling
- LangSmith pour l'observabilité et le débogage

**Avantages :**
- Écosystème très riche, grande communauté
- Nombreuses intégrations prêtes à l'emploi
- Compatible avec les modèles locaux (Ollama, llama.cpp)

**Inconvénients :**
- Abstraction parfois trop complexe pour les projets simples
- Versioning instable, breaking changes fréquents

**Exemple minimal (Python) :**
```python
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Qdrant
from langchain.chains import RetrievalQA

llm = Ollama(model="llama3.2:3b-instruct-q4_K_M")
vectorstore = Qdrant.from_documents(docs, embeddings, url="http://localhost:6333")
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())
response = qa_chain.run("Combien de visiteurs hier ?")
```

---

#### 2. LlamaIndex

Spécialisé dans l'indexation et la recherche de données structurées/non structurées pour les LLM.

**Fonctionnalités clés :**
- Ingestion de documents multiformats
- Création d'index avancés : `VectorStoreIndex`, `SummaryIndex`, `KnowledgeGraphIndex`
- Recherche sémantique fine
- RAG optimisé pour des bases de connaissances larges
- Sous-question decomposition, HyDE (Hypothetical Document Embeddings)

**Avantages :**
- Très performant pour le RAG documentaire
- Facile à mettre en œuvre, API claire
- Support natif d'Ollama

**Cas d'usage :**
- Chatbots documentaires d'entreprise
- Assistants métier sur bases de connaissances
- Recherche sémantique sur grands corpus

---

#### 3. Haystack (deepset)

Framework open source orienté recherche documentaire et question answering industriel.

**Fonctionnalités clés :**
- Pipelines RAG modulaires et composables
- Recherche hybride (BM25 lexical + Vector Search sémantique)
- Support natif de Elasticsearch, OpenSearch, Qdrant, Weaviate, Chroma
- Évaluation automatisée des pipelines RAG

**Points forts :**
- Excellente architecture pour les projets d'entreprise
- Très adapté à la recherche documentaire à grande échelle
- Bonne gestion de la recherche hybride dense+sparse

---

#### 4. DSPy (Stanford)

Framework de recherche développé par des chercheurs de Stanford — paradigme différent des chaînes classiques.

**Concept clé :**
- Optimisation **automatique** des prompts via des algorithmes d'optimisation (BootstrapFewShot, MIPROv2)
- Le développeur définit le **schéma** de raisonnement, DSPy optimise les prompts pour l'atteindre
- Pipeline RAG traité comme un problème d'optimisation

**Avantages :**
- Résultats souvent supérieurs aux prompts écrits manuellement
- Intéressant pour la recherche avancée et les cas nécessitant une précision maximale

---

#### 5. Semantic Kernel (Microsoft)

Framework d'orchestration LLM de Microsoft, très adapté à l'écosystème Azure.

**Fonctionnalités clés :**
- Orchestration de plugins LLM
- Agents IA avec mémoire persistante
- RAG natif avec connecteurs Azure Cognitive Search
- Support C#, Python, Java

**Adapté à :**
- Intégrations Microsoft 365 / Azure OpenAI
- Projets d'entreprise dans l'écosystème Microsoft

---

### Comparaison synthétique

| Framework | Points forts | Idéal pour | Complexité |
|---|---|---|---|
| **LangChain** | Richesse fonctionnelle, intégrations | Prototypage rapide, chatbots | Moyenne |
| **LlamaIndex** | Performance RAG, indexation avancée | Chatbots documentaires, KB | Faible |
| **Haystack** | Recherche hybride, pipelines modulaires | Entreprise, grands corpus | Élevée |
| **DSPy** | Optimisation automatique des prompts | Recherche, précision maximale | Élevée |
| **Semantic Kernel** | Écosystème Microsoft, agents | Azure, Microsoft 365 | Moyenne |

---

### Bases vectorielles associées au RAG

Le retriever s'appuie sur une **base vectorielle** pour stocker et rechercher les embeddings :

| Base vectorielle | Type | Points forts |
|---|---|---|
| **Qdrant** | Open source, self-hosted | Filtrage avancé, payload indexing, très rapide |
| **Chroma** | Open source, embarqué | Facilité d'intégration, idéal pour le développement |
| **Weaviate** | Open source, cloud-native | GraphQL, multimodalité, hybrid search |
| **Milvus** | Open source, distribué | Scalabilité massive (milliards de vecteurs) |
| **Pinecone** | SaaS managé | Zéro infrastructure, production clé en main |
| **FAISS** | Bibliothèque locale | Ultra-rapide en mémoire, pas de persistance native |
| **pgvector** | Extension PostgreSQL | Intégration SQL native, simple à opérer |

> **Choix dans Anavid Store 360 :** la knowledge base ne contient que 8 documents, ce qui rend ChromaDB et Qdrant inutiles. Les embeddings sont calculés à la volée via `Ollama /api/embeddings` et la recherche cosinus est implémentée en Python pur — aucune dépendance externe lourde.

---

### Architecture RAG moderne (pipeline complet)

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE D'INGESTION (offline)                                 │
│                                                              │
│  Documents (PDF, CSV, JSON, Web…)                           │
│        │                                                     │
│        ▼                                                     │
│  Chunking (découpage en segments)                            │
│  ├── Taille fixe : 512 tokens, overlap 50                   │
│  ├── Sémantique : coupure aux frontières de paragraphes     │
│  └── Hiérarchique : parent-child chunks (LlamaIndex)        │
│        │                                                     │
│        ▼                                                     │
│  Embedding Model                                             │
│  ├── all-MiniLM-L6-v2 (384 dim, rapide)                    │
│  ├── text-embedding-3-small (OpenAI, 1536 dim)             │
│  └── nomic-embed-text (Ollama, 768 dim)                     │
│        │                                                     │
│        ▼                                                     │
│  Base Vectorielle (Qdrant / Chroma / FAISS…)                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PHASE DE GÉNÉRATION (online / temps réel)                   │
│                                                              │
│  Question utilisateur                                        │
│        │                                                     │
│        ▼                                                     │
│  Embedding de la question (même modèle que l'ingestion)     │
│        │                                                     │
│        ▼                                                     │
│  Retriever                                                   │
│  ├── Top-k : k=2 à 5 documents les plus similaires          │
│  ├── Seuil de similarité : cosine ≥ 0.7 (configurable)     │
│  ├── Recherche Dense (vecteurs)                              │
│  └── Recherche Hybride : Dense + BM25 (sparse)              │
│        │                                                     │
│        ▼                                                     │
│  Reranker (optionnel)                                        │
│  └── Cross-encoder pour reclasser les résultats             │
│        │                                                     │
│        ▼                                                     │
│  Prompt Builder                                              │
│  ├── System prompt (rôle, contraintes, format)              │
│  ├── Contexte récupéré (documents triés)                    │
│  └── Question utilisateur                                    │
│        │                                                     │
│        ▼                                                     │
│  LLM (Qwen 2.5 / Llama 3.2 / Mistral via Ollama)          │
│        │                                                     │
│        ▼                                                     │
│  Réponse générée (JSON ou texte)                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Paramètres d'inférence LLM utilisés dans Anavid Store 360

Le pipeline `rag_pipeline.py` utilise les paramètres suivants lors de l'appel à `Ollama /api/generate` :

| Paramètre | Valeur | Rôle |
|---|---|---|
| `temperature` | `0.1` | Contrôle la créativité. Proche de 0 = réponses déterministes, factuelles. Idéal pour le RAG métier |
| `top_p` | `0.9` | Nucleus sampling : sélectionne parmi les tokens couvrant 90 % de la probabilité cumulée. Filtre les tokens très improbables |
| `num_ctx` | `4096` | Taille de la fenêtre de contexte (tokens). Détermine combien de texte le modèle peut "lire" en une fois (prompt + contexte + réponse) |
| `num_predict` | `1024` | Nombre maximum de tokens à générer en sortie. 1024 couvre les réponses JSON complexes sans tronquer |

#### Explication détaillée des paramètres d'échantillonnage

**Temperature (`temperature`)**
- Contrôle l'entropie de la distribution de probabilité des tokens
- `0.0` → le modèle choisit toujours le token le plus probable (greedy decoding)
- `1.0` → distribution originale du modèle
- `> 1.0` → réponses plus aléatoires et créatives
- **Recommandation RAG :** `0.0` à `0.3` pour des réponses factuelles ancrées dans le contexte

**Top-p / Nucleus Sampling (`top_p`)**
- À chaque étape de génération, seuls les tokens dont la probabilité cumulée dépasse `top_p` sont conservés
- `top_p=0.9` : les tokens représentant 90 % de la masse de probabilité
- Complémentaire à `temperature` — les deux s'appliquent ensemble
- **Recommandation RAG :** `0.85` à `0.95`

**Top-k (non utilisé ici)**
- Limite la sélection aux `k` tokens les plus probables à chaque étape
- Exemple : `top_k=40` → parmi les 40 tokens les plus probables
- Moins flexible que `top_p` ; souvent utilisé combiné

**Repeat Penalty (non configuré explicitement)**
- Pénalise la répétition de tokens déjà générés
- Valeurs typiques : `1.1` à `1.3`
- Utile pour éviter les boucles dans les longues générations

**num_ctx (Context Window)**
- Définit la fenêtre de tokens que le modèle traite simultanément
- Budget total = prompt system + contexte RAG + historique + réponse
- `llama3.2:3b` supporte jusqu'à 128k tokens natifs, mais 4096 suffit pour le cas d'usage retail
- Augmenter `num_ctx` consomme plus de VRAM

#### Tableau récapitulatif des paramètres d'échantillonnage

| Paramètre | Plage typique | Usage RAG | Usage créatif |
|---|---|---|---|
| `temperature` | 0.0 – 2.0 | 0.0 – 0.3 | 0.7 – 1.2 |
| `top_p` | 0.0 – 1.0 | 0.85 – 0.95 | 0.9 – 1.0 |
| `top_k` | 1 – 100 | 20 – 40 | 40 – 100 |
| `repeat_penalty` | 1.0 – 1.5 | 1.1 – 1.2 | 1.0 – 1.1 |
| `num_predict` | 64 – 4096 | 256 – 1024 | 512 – 2048 |

---

### Implémentation RAG dans Anavid Store 360 vs frameworks complets

| Aspect | Anavid Store 360 (custom) | LangChain/LlamaIndex |
|---|---|---|
| **Dépendances** | `requests`, `pandas`, `numpy` uniquement | `langchain`, `sentence-transformers`, `chromadb`, `torch` (500+ Mo) |
| **Image Docker** | ~200 Mo (python:3.11-slim) | ~800 Mo – 2 Go avec torch |
| **Base vectorielle** | Cosine similarity Python pur (8 docs) | Qdrant / Chroma / FAISS |
| **Embedding** | Ollama `/api/embeddings` (modèle déjà chargé) | Modèle sentence-transformers dédié |
| **Retrieval** | Top-k=2 cosine similarity | Top-k configurable + reranking optionnel |
| **Chunking** | Documents entiers (KB petite) | Chunking configurable (512 tokens, overlap 50) |
| **Fallback** | Détection par mots-clés si Ollama indispo | Gestion d'erreurs LangChain |
| **Observabilité** | Logs Django standard | LangSmith, traces intégrées |
| **Adapté à** | KB petite, contraintes VRAM, production locale | Corpus larges, besoins évolués |

> **Justification du choix custom :** avec seulement 8 documents dans la knowledge base et une contrainte de 5,5 Go de VRAM sur la machine cible, l'implémentation sans framework externe est la plus légère, la plus rapide à démarrer et la plus simple à maintenir. Un framework comme LangChain serait pertinent si la KB dépassait quelques centaines de documents ou nécessitait des stratégies de chunking avancées.

---

## Configuration (`config/`)

### `settings.py`
| Paramètre | Valeur / Source |
|---|---|
| `AUTH_USER_MODEL` | `accounts.User` — authentification par e-mail (pas de `username`) |
| `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` (env) ou `*` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` (toutes origines — sans risque, l'auth se fait par JWT/header, pas par cookies/session) |
| `DATABASES` | SQLite (`db.sqlite3`) — comptes utilisateurs + sessions admin |
| `SIMPLE_JWT` | Access token 60 min, refresh token 14 jours, rotation + blacklist activées |
| `EMAIL_*` | Backend SMTP Gmail — `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` lus depuis `.env` (racine) |
| `INSTALLED_APPS` | `accounts`, `history`, `rest_framework`, `rest_framework_simplejwt.token_blacklist`, `corsheaders`, `drf_spectacular` |

### `urls.py`
Routage racine : monte `accounts.urls` et `history.urls` sous `/api/`, et les vues Swagger/ReDoc sous `/api/docs/` et `/api/redoc/`.

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du service Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle LLM utilisé |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin vers le CSV visiteurs |
| `DJANGO_ALLOWED_HOSTS` | `*` | Hosts autorisés |
| `DJANGO_DEBUG` | `true` | Mode debug Django |
| `EMAIL_HOST` | `smtp.gmail.com` | Serveur SMTP |
| `EMAIL_PORT` | `587` | Port SMTP (TLS) |
| `EMAIL_HOST_USER` | *(secret, depuis `.env` racine)* | Compte Gmail expéditeur des OTP de reset mot de passe |
| `EMAIL_HOST_PASSWORD` | *(secret, depuis `.env` racine)* | Mot de passe d'application Gmail |
| `DEFAULT_FROM_EMAIL` | `Anavid Store 360 <${EMAIL_HOST_USER}>` | Expéditeur affiché |
| `FCM_PROJECT_ID` | *(secret, depuis `.env` racine)* | ID du projet Firebase (Service Account, notifications push) |
| `FCM_CLIENT_EMAIL` | *(secret, depuis `.env` racine)* | E-mail du Service Account Firebase |
| `FCM_PRIVATE_KEY` | *(secret, depuis `.env` racine)* | Clé privée du Service Account (format `\n` littéral) |

> 🔒 `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `FCM_PROJECT_ID`, `FCM_CLIENT_EMAIL` et `FCM_PRIVATE_KEY` ne sont **jamais** écrits en dur dans `docker-compose.yml` ni dans ce dossier — ils sont injectés depuis le fichier `.env` à la racine du repo (non versionné, voir `.gitignore`). Copier `.env.example` en `.env` avant le premier lancement. Détail complet de récupération des clés FCM : [`frontend/README_APK_Android.md` section 4](../../frontend/README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

---

## Dépendances notables

```
Django>=5.0          # framework web
djangorestframework  # API REST
django-cors-headers  # CORS (frontend cross-origin)
drf-spectacular      # génération OpenAPI / Swagger
pandas, numpy        # traitement données CSV
requests             # appels HTTP vers Ollama
# ⚠️ PAS de torch / chromadb / sentence-transformers
# → image Docker allégée de ~800 Mo à ~200 Mo
# → embeddings délégués à Ollama (modèle déjà en VRAM)
```

> L'absence de `torch` réduit l'image Docker de ~800 Mo à ~200 Mo et élimine les dépendances CUDA, tout en maintenant des capacités RAG complètes grâce à la délégation des embeddings à Ollama.