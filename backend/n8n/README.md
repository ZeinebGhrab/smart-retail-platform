# `n8n/` — Orchestrateur de workflows (rapport quotidien automatisé)

Ce dossier contient la configuration du service **N8N** (`docker-compose.yml`, service `n8n`, port `5678`), utilisé pour automatiser la génération et la diffusion d'un rapport de prévision de fréquentation chaque matin.

---

## Contenu

| Élément | Description |
|---|---|
| `workflows/ShopAnalytics - OpenMeteo + Nager.json` | Le workflow N8N à importer dans l'interface |

---

## Rôle dans l'architecture

```
N8N (cron 6h00)
  │
  ├─ récupère la météo du jour (Open-Meteo) + vérifie le jour férié (Nager.Date)
  ├─ appelle le modèle LightGBM (POST /predict) → prédictions visiteurs réelles
  ├─ demande au LLM (Ollama, via le node LangChain) de rédiger un rapport structuré 4 parties
  ├─ POST http://shopanalytics-django-api:8000/api/daily-report/
  │       └─► Django persiste + diffuse en SSE → Dashboard.tsx (temps réel)
  ├─ POST http://shopanalytics-django-api:8000/api/send-fcm/
  │       └─► Notification push mobile (Firebase FCM)
  └─ POST http://shopanalytics-django-api:8000/api/chat/
          └─► Rapport injecté dans l'historique du chatbot RAG
```

N8N communique avec `django_api`, `visitor-ml-api` et `ollama` via le **réseau Docker interne** (noms de service, pas `localhost`) — voir `docker-compose.yml`, les `container_name` correspondants sont `shopanalytics-django-api`, `shopanalytics-visitor-ml-api` et `shopanalytics-ollama`.

---

## Flux des nœuds

```
Déclencheur 6h00
  └─► Réentraînement Modèle ML  ⚠️ mock
        └─► Date du Jour
              ├─► Récupérer Météo ────────────────────────┐
              └─► Vérifier Jour Férié                     │
                    └─► Interpréter Jour Férié ───────────┤
                                                          └─► Fusionner Météo + Jour
                                                                └─► Préparer Contexte Jour
                                                                      └─► HTTP Request  /predict
                                                                            └─► Prédiction Visiteurs
                                                                                  └─► Préparer Prompt Ollama
                                                                                        └─► Basic LLM Chain
                                                                                              └─► Formater Payload SSE
                                                                                                    ├─► Push SSE → Django
                                                                                                    ├─► Envoyer FCM
                                                                                                    └─► Envoyer au Chatbot
```

---

## Description de chaque nœud

### 1. `Déclencheur 6h00`
**Type :** Schedule Trigger

Déclenche le workflow automatiquement chaque matin via l'expression cron `0 6 * * *`. Aucune entrée, aucune sortie de données — c'est le point de départ de toute la chaîne.

---

### 2. `Réentraînement Modèle ML`
**Type :** Code JS

> ⚠️ **Mock** — À remplacer par un `HTTP Request POST /api/train` vers `shopanalytics-visitor-ml-api`.

Actuellement retourne une réponse statique `{ status: 'trained', model_version: '1.0.0', samples_used: 142 }`. Sa sortie n'est pas utilisée par les nœuds suivants — il sert uniquement de déclencheur en cascade vers `Date du Jour`.

---

### 3. `Date du Jour`
**Type :** Code JS

Calcule la date du jour au format ISO (`YYYY-MM-DD`) et la rend disponible pour toutes les branches suivantes via `$('Date du Jour').first().json.date`. Centralise la date pour éviter toute incohérence entre les appels API parallèles.

```json
{ "date": "2026-06-25" }
```

---

### 4. `Récupérer Météo`
**Type :** HTTP Request — `GET https://api.open-meteo.com/v1/forecast`

Récupère la météo actuelle à Sfax (latitude `34.7406`, longitude `10.7603`) sans clé API. Champs utilisés : `current.temperature_2m` (°C) et `current.wind_speed_10m` (km/h).

| Paramètre | Valeur |
|---|---|
| `current` | `temperature_2m,wind_speed_10m` |
| `timezone` | `Africa/Tunis` |
| timeout | 10 000 ms |

> ⚠️ Les coordonnées sont codées en dur pour Sfax. À paramétrer via variable d'environnement pour un déploiement multi-magasin.

---

### 5. `Vérifier Jour Férié`
**Type :** HTTP Request — `GET https://date.nager.at/api/v3/IsTodayPublicHoliday/TN`

Interroge Nager.Date pour savoir si aujourd'hui est un jour férié en Tunisie. L'API retourne uniquement un code HTTP, sans body :

| Code HTTP | Signification |
|---|---|
| `200` | Jour férié |
| `204` | Jour ouvrable normal |

> ⚠️ Le pays `TN` est codé en dur dans l'URL. Modifier ce nœud pour changer de pays cible.

---

### 6. `Interpréter Jour Férié`
**Type :** Code JS

Lit le `statusCode` HTTP brut retourné par le nœud précédent et le convertit en valeur métier :

```js
const type_jour = statusCode === 200 ? 'ferie' : 'normal';
```

```json
{ "type_jour": "normal" }
```

---

### 7. `Fusionner Météo + Jour`
**Type :** Merge (mode `combineAll`)

Combine les sorties de `Récupérer Météo` (input 0) et `Interpréter Jour Férié` (input 1) en un seul item JSON pour le nœud suivant.

---

### 8. `Préparer Contexte Jour`
**Type :** Code JS

Extrait et normalise les données fusionnées pour construire le payload envoyé au modèle ML. Gère les deux formats de réponse possibles d'Open-Meteo (`current.temperature_2m` ou `temperature` à plat).

```json
{
  "date": "2026-06-25",
  "temperature": 32.0,
  "wind_speed": 18.0,
  "type_jour": "normal"
}
```

---

### 9. `HTTP Request` — `/predict`
**Type :** HTTP Request — `POST http://shopanalytics-visitor-ml-api:8000/predict`

Appelle l'API FastAPI LightGBM avec le contexte du jour. C'est ici que les **vraies prédictions ML** sont générées.

```json
// Body envoyé
{ "date": "2026-06-25", "temperature": 32.0, "wind_speed": 18.0, "type_jour": "normal" }

// Réponse reçue
{
  "date": "2026-06-25",
  "predictions": [
    { "hour": 10, "camera": "Cam_porte1", "total_visits": 42,
      "profile": [{ "gender": "Female", "age": "18-29", "visits_predicted": 5 }, ...] },
    ...
  ]
}
```

La réponse contient 34 entrées (17 heures d'ouverture × 2 caméras : `Cam_porte1` et `Cam_porte2`).

---

### 10. `Prédiction Visiteurs`
**Type :** Code JS

Parse la réponse réelle de `/predict` et calcule les métriques agrégées utilisées par le LLM. Lève une erreur explicite si la réponse est vide ou malformée.

| Sortie | Calcul |
|---|---|
| `visiteurs_prevus_total` | Somme de tous les `total_visits` |
| `heure_pointe` | Heure avec le plus grand total cumulé (toutes caméras) |
| `visiteurs_heure_pointe` | Nombre de visiteurs à l'heure de pointe |
| `profil_dominant` | Profil `gender + age` le plus cumulé sur la journée |
| `profils_par_volume` | Tableau de tous les profils, triés par volume décroissant |
| `detail_par_heure` | Objet `{ total, cameras, profils_actifs }` pour chaque heure |

---

### 11. `Préparer Prompt Ollama`
**Type :** Code JS

Nœud central — construit le prompt envoyé au LLM en calculant lui-même tous les éléments structurels **avant** la génération, pour éviter toute hallucination sur les chiffres.

Calculs effectués dans ce nœud :

| Calcul | Logique |
|---|---|
| Niveau d'affluence | `< 50` → Faible · `< 150` → Modéré · `< 350` → Élevé · `≥ 350` → Très élevé |
| Charge horaire | `< 4%` → Minimal · `< 7%` → Standard · `< 9%` → Renforce · `≥ 9%` → MAXIMUM |
| Tableau horaire | 17 lignes (7h–23h) avec colonnes : Prédit · % journée · Charge |
| Staffing par créneau | Dérivé automatiquement de la charge (1 collab / standard / renforcer / MAXIMUM) |
| % rush | `totalRush (top 3 heures) / totalJour × 100` |

Le prompt instruit le LLM de produire un rapport en **4 parties** :
1. Tableau heure par heure + encadré POINT CLÉ
2. Analyse du profil clientèle dominant + recommandation rayon
3. Recommandations opérationnelles (staffing, rayons, logistique)
4. Message motivationnel adapté au niveau d'affluence

> Le prompt contient l'instruction explicite : *"N'invente aucun chiffre absent de ces données."*

---

### 12. `Ollama Model`
**Type :** LM Ollama (nœud LangChain)

Modèle LLM local utilisé pour la génération.

| Paramètre | Valeur |
|---|---|
| `model` | `llama3.2:3b-instruct-q4_K_M` |
| `temperature` | `0.1` (quasi-déterministe — reformulation fidèle sans créativité) |
| `numCtx` | `4096` tokens |
| `numPredict` | `300` tokens (augmenter à 500–600 si le rapport est tronqué) |
| Credential | `Ollama account` → pointer vers `http://ollama:11434` |

---

### 13. `Basic LLM Chain`
**Type :** LangChain Chain LLM

Reçoit le prompt depuis `Préparer Prompt Ollama` via `$('Préparer Prompt Ollama').item.json.prompt` et le transmet au modèle `Ollama Model`. Retourne `{ text: "<rapport généré>" }`.

---

### 14. `Formater Payload SSE`
**Type :** Code JS

Assemble la structure finale envoyée aux 3 sorties. Calcule également le `niveau_affluence` à partir du total journalier.

```json
{
  "type": "llm_report",
  "date": "2026-06-25",
  "generated_at": "2026-06-25T06:00:42.000Z",
  "message": "<rapport 4 parties généré par Ollama>",
  "prediction": {
    "visiteurs_prevus": 1711,
    "profil_dominant": "Female 18-29",
    "niveau_affluence": "Très élevé",
    "heure_pointe": "17h00",
    "visiteurs_heure_pointe": 275,
    "profils_par_volume": [...],
    "detail_par_heure": {...}
  }
}
```

---

### 15. `Push SSE → Django`
**Type :** HTTP Request — `POST http://shopanalytics-django-api:8000/api/daily-report/`

Envoie le payload complet à Django. Django persiste le rapport en base et notifie tous les clients SSE connectés (Dashboard.tsx + ChatIA) en temps réel.

---

### 16. `Envoyer FCM`
**Type :** HTTP Request — `POST http://shopanalytics-django-api:8000/api/send-fcm/`

Envoie une notification push mobile via Firebase Cloud Messaging. Le titre inclut la date (`📊 Rapport Quotidien - 2026-06-25`), le body contient le message LLM, et le champ `data` transporte les métriques clés pour l'affichage dans l'app.

---

### 17. `Envoyer au Chatbot`
**Type :** Code JS

Injecte le rapport dans l'historique du chatbot RAG Django via `POST /api/chat/`. Si Django est indisponible, utilise le texte LLM directement en fallback (le rapport n'est pas perdu).

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
3. Sélectionner `workflows/ShopAnalytics - OpenMeteo + Nager.json`
4. Configurer les credentials du node Ollama (`Ollama Model`) pour pointer vers `http://ollama:11434`
5. Activer le workflow (`Active`)

> Aucun secret n'est stocké dans le fichier `.json` du workflow lui-même — les credentials N8N (si besoin) se configurent depuis l'interface et sont chiffrées dans le volume `n8n_data`.