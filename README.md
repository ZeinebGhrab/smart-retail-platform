# Anavid Store 360 — Smart Retail Platform

Plateforme d'analyse retail intelligente avec assistant IA RAG, API historique visiteurs et benchmark LLM local.

---

## Sommaire

1. [Architecture](#1-architecture)
2. [Prérequis](#2-prérequis)
3. [Lancement rapide](#3-lancement-rapide)
4. [Services & ports](#4-services--ports)
5. [Chat IA — RAG](#5-chat-ia--rag)
6. [API REST — endpoints](#6-api-rest--endpoints)
7. [Benchmark LLM](#7-benchmark-llm)
8. [Structure du projet](#8-structure-du-projet)
9. [Variables d'environnement](#9-variables-denvironnement)
10. [Commandes Makefile](#10-commandes-makefile)
11. [Application mobile (APK Android)](#11-application-mobile-apk-android)
12. [FAQ](#12-faq)

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  docker-compose                                                  │
│                                                                  │
│  ┌──────────────┐     HTTP :5173     ┌───────────────────────┐  │
│  │   frontend   │ ◄────────────────► │   Utilisateur         │  │
│  │ Ionic/React  │                    └───────────────────────┘  │
│  │  ChatIA.tsx  │                                                │
│  └──────┬───────┘                                                │
│         │ POST /api/chat/  (HTTP :8000)                          │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │  django_api  │  API REST historique visiteurs                 │
│  │   Django 5   │  Pipeline RAG :                                │
│  │              │   1. Retrieval CSV  (volume ./backend/data)    │
│  │  rag_        │   2. Retrieval KB   (volume ./backend/dataset) │
│  │  pipeline.py │   3. Prompt Builder                           │
│  └──────┬───────┘                                                │
│         │ HTTP :11434  (réseau Docker interne)                   │
│         ▼                                                        │
│  ┌──────────────┐                                                │
│  │    ollama    │  LLM local                                     │
│  │              │  Modèle retenu : llama3.2:3b-instruct-q4_K_M  │
│  │  /api/generate    (génération)                                │
│  │  /api/embeddings  (recherche sémantique KB)                   │
│  └──────────────┘                                                │
│                                                                  │
│  ┌──────────────┐  (one-shot)                                    │
│  │  benchmark   │  Sélection automatique du modèle               │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline RAG (sans torch ni ChromaDB)

```
Question utilisateur (langage naturel)
        │
        ├──► Retrieval CSV ──────────────────────────────────────────►┐
        │    shoppingclub_2025_2026.csv                                │
        │    Extrait : date, caméra, genre, âge, flux horaire          │
        │                                                              │
        ├──► Retrieval KB (8 docs) ─────────────────────────────────►┤
        │    knowledge_base.json                                       │
        │    Embeddings via Ollama /api/embeddings + cosine similarity │
        │                                                              ▼
        └──► Prompt Builder ──────────────────────────────────────────►
                                                                       │
                                        ┌──────────────────────────── ▼
                                        │  Ollama /api/generate
                                        │  llama3.2:3b-instruct-q4_K_M
                                        │  temperature=0.1, num_ctx=4096
                                        └──────────────────────────── ▼
                                                              Réponse JSON
                                                         { answer, model, sources }
```

### Résultats du benchmark (06/2026)

| Critère | Valeur | Seuil |
|---|---|---|
| TTFT moyen | **0.246 s** | ≤ 1.5 s ✅ |
| Débit | **68.3 tokens/s** | ≥ 20 t/s ✅ |
| JSON valide (tool calling) | **90 %** | ≥ 95 % ⚠️ |
| Modèle retenu | `llama3.2:3b-instruct-q4_K_M` | — |

---

## 2. Prérequis

| Outil | Version minimale | Obligatoire |
|---|---|---|
| Docker Desktop | 24+ | ✅ |
| docker compose | v2 (`docker compose`) | ✅ |
| GPU NVIDIA + drivers | — | ⚠️ recommandé |
| nvidia-container-toolkit | — | si GPU |
| make | — | optionnel (Linux/Mac) |

> **Sans GPU** : Ollama tourne en CPU. Le modèle 3B q4_K_M reste utilisable (~5-10 tokens/s). Retirez le bloc `deploy.resources` dans `docker-compose.yml`.

> **VRAM requise** : Llama 3.2 3B q4_K_M ≈ 4.1 Go. Ajustez `VRAM_AVAILABLE_GB` dans `backend/scripts/config.py` si vous relancez le benchmark.

---

## 3. Lancement rapide

### Premier lancement

```bash
git clone <url-du-repo>
cd anavid-smart-retail-platform

# 1. Configurer les secrets (jamais commités, voir section 9)
cp .env.example .env
# → éditer .env et renseigner EMAIL_HOST_USER / EMAIL_HOST_PASSWORD

# 2. Lancer la stack
docker compose up --build
```

Accès :
- **Frontend** → http://localhost:5173
- **API** → http://localhost:8000/api/
- **Swagger** → http://localhost:8000/api/docs/
- **Ollama** → http://localhost:11434

### Lancement par service

```bash
# Ollama seul
docker compose up ollama

# API Django + Ollama
docker compose up --build django_api ollama

# Stack complète (sans benchmark)
docker compose up --build ollama django_api frontend

# Avec Make (Linux/Mac)
make up
```

### Rebuild après modification du code

```bash
docker compose up --build django_api
```

> Le frontend utilise un volume monté avec hot-reload : **pas besoin de rebuild** après modification d'un fichier `.tsx` ou `.css`.

---

## 4. Services & ports

| Service | Port | URL | Description |
|---|---|---|---|
| `frontend` | 5173 | http://localhost:5173 | App Ionic/React (hot-reload) |
| `django_api` | 8000 | http://localhost:8000 | API REST + Auth + Chat IA RAG |
| `ollama` | 11434 | http://localhost:11434 | LLM local Llama 3.2 |
| `n8n` | 5678 | http://localhost:5678 | Orchestrateur — rapport quotidien (6h00) |
| `benchmark` | — | one-shot | Sélection automatique du modèle |

### Communication interne Docker

```
frontend   ──► django_api  via http://localhost:8000  (depuis le navigateur)
django_api ──► ollama       via http://ollama:11434    (réseau Docker interne)
```

---

## 5. Chat IA — RAG

### Depuis le frontend

Ouvrir http://localhost:5173 → onglet **Chat IA**.

Exemples de questions :

```
Nombre de visiteurs le 2026-05-30 ?
Flux horaire hier Porte_nord
Historique des 7 derniers jours
Prévision pour demain
Résumé global de la période
Qu'est-ce que le taux de conversion ?
Quelles caméras sont installées ?
```

### Directement via l'API

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Nombre de visiteurs le 2026-05-30 ?"}'
```

Réponse :

```json
{
  "answer": "📊 Visiteurs du 2026-05-30 :\n  • Total : 7\n  • Cam porte1 : 5\n  • Cam_porte2 : 2",
  "model": "llama3.2:3b-instruct-q4_K_M",
  "sources": {
    "csv": "/app/data/shoppingclub_2025_2026.csv",
    "kb": "/app/dataset/knowledge_base.json",
    "embeddings": "http://ollama:11434/api/embeddings"
  }
}
```

---

## 6. API REST — endpoints

Documentation Swagger interactive : http://localhost:8000/api/docs/

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Inscription (e-mail + mot de passe) |
| `POST` | `/api/auth/login/` | Connexion — retourne les tokens JWT |
| `POST` | `/api/auth/refresh/` | Renouvellement de l'access token |
| `GET` | `/api/auth/me/` | Profil de l'utilisateur connecté |
| `POST` | `/api/auth/logout/` | Déconnexion (blacklist du refresh token) |
| `POST` | `/api/auth/password-reset/request/` | Envoie un code OTP par e-mail (Gmail SMTP) |
| `POST` | `/api/auth/password-reset/verify/` | Vérifie le code OTP |
| `POST` | `/api/auth/password-reset/confirm/` | Change le mot de passe avec le code OTP |
| `POST` | `/api/chat/` | **Chat IA RAG** — question en langage naturel |
| `GET` | `/api/history/visitors/` | Historique journalier (genre, âge) |
| `GET` | `/api/history/visitors/count/` | Nombre de visiteurs par date |
| `GET` | `/api/history/visitors/hourly/` | Flux horaire par date |
| `GET` | `/api/history/visitors/forecast/` | Prévision (régression linéaire) |
| `GET` | `/api/history/summary/` | KPIs globaux |
| `GET` | `/api/history/cameras/` | Liste des caméras |
| `GET` | `/api/notifications/latest/` | Dernière notification reçue de N8N |
| `GET` | `/api/notifications/history/` | Historique des notifications N8N |
| `GET` | `/api/prediction/stream/` | Flux SSE temps réel (écouté par le Dashboard) |
| `POST` | `/api/daily-report/` | Réception du rapport quotidien (appelé par N8N) |
| `POST` | `/api/fcm-token/` | Enregistre le token push FCM d'un appareil (appelé par l'app mobile) |
| `POST` | `/api/send-fcm/` | Envoie une notification push à tous les appareils enregistrés |

### Paramètres communs

| Paramètre | Format | Exemple |
|---|---|---|
| `date` | `YYYY-MM-DD` | `?date=2026-05-30` |
| `start_date` | `YYYY-MM-DD` | `?start_date=2026-05-01` |
| `end_date` | `YYYY-MM-DD` | `?end_date=2026-05-30` |
| `camera` | `Porte_nord` ou `Porte_sud` | `?camera=Porte_nord` |

---

## 7. Benchmark LLM

Le benchmark sélectionne automatiquement le meilleur modèle Ollama selon la VRAM disponible.

### Lancer le benchmark

```bash
make bench
# ou
docker compose run --rm benchmark
```

### Configurer avant le benchmark

Éditer `backend/scripts/config.py` :

```python
VRAM_AVAILABLE_GB = 5.5   # ← Adapter à votre machine

CANDIDATE_MODELS = [
    {"id": "llama3.2:3b-instruct-q4_K_M", "params_b": 3, ...},
    {"id": "qwen2.5:7b-instruct-q4_K_M",  "params_b": 7, ...},
    {"id": "mistral:7b-instruct-v0.3-q4_K_M", "params_b": 7, ...},
]
```

### Résultats

Générés dans `backend/results/` :
- `benchmark_report.json` — rapport complet
- `eligible_models.json` — modèle retenu (lu par `django_api` au démarrage)

---

## 8. Structure du projet

```
anavid-smart-retail-platform/
│
├── docker-compose.yml               # Orchestration des 5 services
├── Makefile                         # Commandes raccourcies (Linux/Mac)
├── run.bat                          # Commandes raccourcies (Windows)
├── .env                             # Secrets locaux (Gmail SMTP, FCM) — jamais commité
├── .env.example                     # Modèle versionné, sans secrets
├── .gitignore
├── README.md                        # Ce fichier
│
├── frontend/                        # App Ionic React (Vite)
│   ├── Dockerfile
│   ├── README.md
│   ├── README_APK_Android.md        # Guide complet : build APK + configuration FCM
│   ├── .env                         # VITE_API_URL + clés Firebase — jamais commité
│   ├── .env.example                 # Modèle versionné, sans secrets
│   ├── android/                     # Projet Android natif (généré par Capacitor)
│   │   └── app/google-services.json # Identifiants Firebase Android — jamais commité
│   └── src/
│       ├── App.tsx                  # Routage (public: /login, /register · protégé: /dashboard, /chat, /predictions)
│       ├── components/              # TabBar, Notifications, PrivateRoute
│       ├── hooks/                   # useSSEPrediction.ts (flux SSE temps réel)
│       ├── pages/                   # Login, Register, Dashboard, ChatIA, Historique
│       ├── services/                # api.ts, auth.ts, chatBridge.ts (clients HTTP)
│       ├── theme/                   # variables.css (thème Ionic)
│       └── types/                   # Types partagés (dashboard.types.ts)
│
└── backend/
    ├── README.md
    ├── django_api/                  # API REST Django (port 8000)
    │   ├── Dockerfile               # Image légère ~200 Mo (sans torch)
    │   ├── requirements.txt         # Django, DRF, pandas, requests
    │   ├── README.md
    │   ├── accounts/                # App auth — inscription/connexion/JWT/reset mdp par e-mail
    │   │   ├── models.py            # User (auth par e-mail) + PasswordResetToken (OTP)
    │   │   ├── views.py             # register, login, me, logout, password-reset/*
    │   │   └── urls.py
    │   ├── config/
    │   │   ├── settings.py          # Lit EMAIL_*, OLLAMA_*, DB_* depuis l'environnement
    │   │   └── urls.py
    │   └── history/
    │       ├── views.py             # Endpoints analytics + notifications N8N + SSE
    │       ├── visitor_data.py      # Lecture CSV + calculs analytiques
    │       ├── rag_pipeline.py      # Pipeline RAG (Retrieval + Ollama)
    │       ├── chat_view.py         # Endpoint POST /api/chat/
    │       └── urls.py
    │
    ├── n8n/                         # Orchestrateur de workflows (rapport quotidien 6h00)
    │   └── workflows/
    │       └── ShopAnalyticsVersionFinal-2.json
    │
    ├── scripts/                     # Benchmark LLM (one-shot)
    │   ├── config.py                # VRAM, modèles candidats, seuils
    │   ├── pull_models.py           # Filtrage VRAM + pull Ollama
    │   ├── benchmark.py             # TTFT, throughput, JSON, hallucinations
    │   ├── rag_eval/                # Évaluation qualité du pipeline RAG
    │   └── results/                 # Rapports rag_eval générés
    │
    ├── data/
    │   └── shoppingclub_2025_2026.csv   # Historique visiteurs (349 jours)
    │
    ├── dataset/
    │   ├── knowledge_base.json      # FAQ métier (8 docs, embeddings via Ollama)
    │   └── tool_calling_queries.json # 50 requêtes benchmark
    │
    └── results/
        ├── benchmark_report.json    # Rapport benchmark
        └── eligible_models.json     # Modèle retenu → lu par django_api
```

---

## 9. Variables d'environnement

### Fichier `.env` (racine du projet) — secrets, **jamais commité**

`docker compose` lit automatiquement le fichier `.env` situé à la racine pour substituer les `${VARIABLES}` déclarées dans `docker-compose.yml`. Ce fichier contient les vrais identifiants Gmail et la clé de service Firebase, et **ne doit jamais être poussé sur Git** — il est listé dans `.gitignore`.

```bash
cp .env.example .env
# puis éditer .env avec vos propres valeurs
```

| Variable | Description |
|---|---|
| `EMAIL_HOST_USER` | Adresse Gmail utilisée pour l'envoi des e-mails OTP (réinitialisation de mot de passe) |
| `EMAIL_HOST_PASSWORD` | **Mot de passe d'application** Gmail (16 caractères) — pas le mot de passe du compte |
| `FCM_PROJECT_ID` | ID du projet Firebase (Service Account) — pour l'envoi de notifications push |
| `FCM_CLIENT_EMAIL` | E-mail du Service Account Firebase |
| `FCM_PRIVATE_KEY` | Clé privée du Service Account (format PEM avec `\n` littéraux, voir ci-dessous) |

> ⚠️ **Sécurité** — Ne jamais utiliser le mot de passe principal du compte Gmail. Générer un mot de passe d'application dédié sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (nécessite la validation en 2 étapes activée sur le compte Google). Si ces identifiants ont déjà été commités par le passé, ils restent visibles dans l'historique Git même après suppression : il faut alors révoquer ce mot de passe d'application depuis le compte Google et en générer un nouveau.

> ⚠️ **FCM_PRIVATE_KEY** — la clé privée du Service Account Firebase (Console Firebase → Paramètres du projet → Comptes de service → Générer une nouvelle clé privée) doit être collée sur **une seule ligne**, retours à la ligne encodés en `\n` littéral, entourée de guillemets doubles :
> ```env
> FCM_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEv...\n-----END PRIVATE KEY-----\n"
> ```
> Procédure complète, y compris la configuration côté frontend (`VITE_FIREBASE_*`, `google-services.json`) : voir [`frontend/README_APK_Android.md`](frontend/README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

`.env.example` est le modèle versionné (sans secrets) servant de documentation pour quiconque clone le projet.

### `django_api` (définies dans `docker-compose.yml`)

| Variable | Valeur par défaut | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://ollama:11434` | URL du conteneur Ollama |
| `OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Modèle LLM utilisé |
| `VISITOR_DATA_CSV` | `/app/data/shoppingclub_2025_2026.csv` | Chemin du CSV visiteurs |
| `DJANGO_DEBUG` | `true` | Mode debug Django |
| `EMAIL_HOST` | `smtp.gmail.com` | Serveur SMTP |
| `EMAIL_PORT` | `587` | Port SMTP (TLS) |
| `EMAIL_USE_TLS` | `true` | Chiffrement TLS |
| `EMAIL_HOST_USER` | *(depuis `.env`)* | Voir ci-dessus |
| `EMAIL_HOST_PASSWORD` | *(depuis `.env`)* | Voir ci-dessus |
| `DEFAULT_FROM_EMAIL` | `Anavid Store 360 <${EMAIL_HOST_USER}>` | Expéditeur affiché dans les e-mails envoyés |
| `FCM_PROJECT_ID` | *(depuis `.env`)* | ID du projet Firebase (notifications push) |
| `FCM_CLIENT_EMAIL` | *(depuis `.env`)* | E-mail du Service Account Firebase |
| `FCM_PRIVATE_KEY` | *(depuis `.env`)* | Clé privée du Service Account Firebase |

### `frontend` (fichier `frontend/.env`)

| Variable | Valeur | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | URL de base de l'API Django |
| `VITE_FIREBASE_API_KEY` | *(depuis Firebase Console)* | Clé API du projet Firebase |
| `VITE_FIREBASE_AUTH_DOMAIN` | *(depuis Firebase Console)* | Domaine d'authentification Firebase |
| `VITE_FIREBASE_PROJECT_ID` | *(depuis Firebase Console)* | ID du projet Firebase |
| `VITE_FIREBASE_STORAGE_BUCKET` | *(depuis Firebase Console)* | Bucket de stockage Firebase |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | *(depuis Firebase Console)* | Sender ID FCM |
| `VITE_FIREBASE_APP_ID` | *(depuis Firebase Console)* | ID de l'app Firebase Web |
| `VITE_FIREBASE_MEASUREMENT_ID` | *(depuis Firebase Console)* | ID Google Analytics (optionnel) |
| `VITE_FIREBASE_VAPID_KEY` | *(depuis Firebase Console → Cloud Messaging)* | Clé Web Push (chemin navigateur uniquement) |

> Détail complet de la configuration FCM (récupération de chaque clé, `google-services.json`, Service Account) : voir [`frontend/README_APK_Android.md`](frontend/README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

### Changer de modèle sans rebuild

```yaml
# docker-compose.yml → service django_api → environment
- OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
```

```bash
docker compose up django_api   # redémarrage suffit, pas de rebuild
```

---

## 10. Commandes Makefile

```bash
make up            # Ollama + benchmark + django_api + frontend
make ollama        # Ollama seul
make bench         # Benchmark (Ollama doit tourner)
make django        # Django seul (avec rebuild)
make api           # Django + Frontend (sans Ollama)
make frontend      # Frontend seul (hot-reload)
make logs          # Logs Ollama en direct
make status        # État de tous les conteneurs
make down          # Arrête tout
make clean-results # Supprime les rapports benchmark
make clean-all     # Supprime tout + volumes (modèles Ollama inclus !)
```

### Windows

```bat
run.bat up
run.bat down
run.bat logs
run.bat bench
run.bat django
run.bat api
run.bat frontend
run.bat status
run.bat clean
run.bat clean-all
```

---

## 11. Application mobile (APK Android)

Le frontend peut être packagé en application Android native via **Capacitor**, avec notifications push **Firebase Cloud Messaging (FCM)**.

Procédure complète (build, configuration FCM détaillée, signature release, dépannage) : voir **[`frontend/README_APK_Android.md`](frontend/README_APK_Android.md)**.

### Résumé express

```bash
cd frontend
npm install
npm run build
cap sync android
cap open android
# Puis dans Android Studio : Build → Build Bundle(s) / APK(s) → Build APK(s)
```

Fichiers à créer manuellement avant le build (non versionnés) :

| Fichier | Rôle |
|---|---|
| `frontend/.env` | URL du backend + clés Firebase (voir `frontend/.env.example`) |
| `frontend/android/app/google-services.json` | Active les notifications push natives FCM |

### Notifications push (FCM) — résumé

- **Côté frontend** (`VITE_FIREBASE_*`, `google-services.json`) : permet à l'app de **recevoir** les notifications.
- **Côté backend** (`FCM_PROJECT_ID`, `FCM_CLIENT_EMAIL`, `FCM_PRIVATE_KEY` dans le `.env` racine) : permet à Django d'**envoyer** les notifications via `POST /api/send-fcm/`.

Détail complet de récupération de chaque clé : [`frontend/README_APK_Android.md` section 4](frontend/README_APK_Android.md#4-configuration-fcm-firebase-cloud-messaging).

---

## 12. FAQ

**Le chat répond "Ollama non joignable"**

```bash
docker compose up ollama
docker compose logs ollama
docker compose restart django_api
```

**Le modèle n'est pas téléchargé**

```bash
curl http://localhost:11434/api/tags
docker compose exec ollama ollama pull llama3.2:3b-instruct-q4_K_M
```

**Modifier le CSV de données**

Remplacer `backend/data/shoppingclub_2025_2026.csv` par votre fichier (même format). Le cache est invalidé automatiquement à la prochaine requête.

**Ajouter des documents à la base de connaissance**

Éditer `backend/dataset/knowledge_base.json` (format `{ "id", "title", "content" }`). Les embeddings sont recalculés automatiquement au prochain démarrage de `django_api`.

**Tester l'API sans le frontend**

```bash
# Swagger interactif
open http://localhost:8000/api/docs/

# curl
curl http://localhost:8000/api/history/visitors/count/?date=2026-05-30
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Historique des 7 derniers jours"}'
```

---

*Anavid Store 360 — Juin 2026*