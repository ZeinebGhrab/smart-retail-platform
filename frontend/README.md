# `frontend/` — Application Ionic React (Anavid Store 360)

Application web/mobile **Ionic + React + Vite** consommée par les commerçants : authentification, tableau de bord analytique en temps réel, assistant IA conversationnel (RAG) et historique des prédictions de fréquentation.

---

## Stack technique

| Brique | Choix |
|---|---|
| Framework UI | Ionic React 8 (composants mobiles natifs) |
| Bundler | Vite 5 |
| Routage | `react-router-dom` v5 via `@ionic/react-router` |
| Graphiques | Chart.js + `react-chartjs-2` |
| Mobile natif | Capacitor (Android) + `@capacitor-firebase/messaging` (push notifications) |
| Langage | TypeScript |

---

## Structure

```
frontend/
├── Dockerfile               # Image dev (node:20-alpine + vite --host 0.0.0.0)
├── nginx.conf                # Config nginx (déploiement prod statique — non utilisée par le Dockerfile dev actuel)
├── vite.config.ts            # Plugins React + legacy, serveur 0.0.0.0:5173, config Vitest
├── ionic.config.json
├── .env                      # VITE_API_URL — URL de l'API Django
├── public/                   # Assets statiques (favicon, manifest PWA)
└── src/
    ├── App.tsx                # Routage racine (voir src/README.md)
    ├── main.tsx                # Point d'entrée React
    ├── components/             # TabBar, Notifications, PrivateRoute
    ├── hooks/                  # useSSEPrediction.ts
    ├── pages/                  # Login, Register, Dashboard, ChatIA, Historique
    ├── services/                # Clients HTTP (api.ts, auth.ts, chatBridge.ts)
    ├── theme/                  # Variables CSS Ionic
    └── types/                  # Types TypeScript partagés
```

Chaque sous-dossier de `src/` a son propre `README.md` détaillant son contenu.

---

## Routage (`App.tsx`)

| Route | Accès | Page |
|---|---|---|
| `/login` | Public | `Login.tsx` |
| `/register` | Public | `Register.tsx` |
| `/dashboard` | Protégée (JWT) | `Dashboard.tsx` |
| `/chat` | Protégée (JWT) | `ChatIA.tsx` |
| `/predictions` | Protégée (JWT) | `Historique.tsx` |
| `/` | — | Redirige vers `/dashboard` si connecté, sinon `/login` |

Les routes protégées passent par `PrivateRoute.tsx`, qui vérifie la présence d'un token d'accès local (`isAuthenticated()` dans `services/auth.ts`) et redirige vers `/login` sinon.

---

## Variables d'environnement (`.env`)

| Variable | Valeur par défaut | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | URL de base de l'API Django consommée par `services/api.ts` et `services/auth.ts` |

> Ce `.env` ne contient **aucun secret** (juste une URL) — il peut rester versionné. Les vrais secrets (Gmail SMTP) sont gérés côté backend, dans le `.env` à la racine du repo (voir `README.md` racine, section 9).

---

## Lancement

```bash
# Dans le conteneur Docker (recommandé, hot-reload via volume monté)
docker compose up frontend

# En local, sans Docker
npm install
npm run dev          # http://localhost:5173
```

### Autres commandes (`package.json`)

| Commande | Action |
|---|---|
| `npm run build` | Build de production (`tsc` + `vite build`) |
| `npm run preview` | Sert le build de production en local |
| `npm run lint` | ESLint |
| `npm run test.unit` | Tests unitaires (Vitest) |
| `npm run test.e2e` | Tests end-to-end (Cypress) |

---

## Notes

- `nginx.conf` prépare un déploiement de production (build statique servi par nginx avec SPA fallback), mais le `Dockerfile` actuel sert uniquement le serveur de dev Vite — à adapter si un build de production conteneurisé est nécessaire.
- Les tokens JWT sont stockés côté client dans `localStorage` (case "se souvenir de moi" cochée) ou `sessionStorage` sinon — voir `src/services/README.md`.
