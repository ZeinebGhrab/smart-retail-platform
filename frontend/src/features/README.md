# `features/` — Domaines fonctionnels de l'application

## Principe de l'architecture

Ce dossier regroupe le code **par domaine métier** (feature) plutôt que par type technique. Chaque sous-dossier correspond à un écran ou un flux complet de l'application, et contient tout ce qui lui est propre :

```
features/<domaine>/
├── EcranA.tsx          # composant écran (page Ionic)
├── EcranA.css          # style associé
├── modele.ts           # types/modèle propres au domaine (si nécessaire)
└── service.ts          # appels API propres au domaine (si nécessaire)
```

### Pourquoi cette structure ?

La logique appliquée ici — **"colocaliser ce qui change ensemble"** — est l'approche standard recommandée pour les applications React/Ionic de taille moyenne à grande (parfois appelée *feature-based* ou *screaming architecture*, par opposition à une organisation purement technique *layer-based*) :

- **Un domaine = un dossier.** Pour comprendre ou modifier l'écran "Alertes", un seul dossier à ouvrir : `features/alerts/`.
- **Couplage fort = même dossier ; couplage faible = dossier séparé.** `alert.model.ts` et `alerts.api.ts` ne sont utilisés que par `Alerts.tsx`/`AlertDetail.tsx` → ils vivent avec eux. À l'inverse, `services/api.ts` (client HTTP générique) ou `services/auth.ts` (session) sont utilisés par plusieurs domaines → ils restent dans `services/` à la racine de `src/`.
- **Limite claire entre "transverse" et "spécifique à un écran".** Voir le tableau ci-dessous.

## Ce qui reste hors de `features/` (code transverse)

| Dossier racine | Reste à la racine car... |
|---|---|
| `components/` | Composants UI réutilisés par plusieurs écrans (`TabBar`, `Notifications`, `PrivateRoute`) |
| `hooks/` | Hooks utilisés indépendamment d'un écran précis (`useFirebaseMessaging`, appelé une seule fois dans `App.tsx`) |
| `services/` | Clients HTTP génériques consommés par plusieurs domaines (`api.ts`, `auth.ts`, `fcm.ts`) |
| `theme/` | Variables CSS globales, appliquées à toute l'application |
| `app/` | Composant racine `App.tsx` (routage global) |

## Domaines présents

| Domaine | Dossier | Écran(s) | Routes |
|---|---|---|---|
| Authentification | `features/auth/` | `Login.tsx`, `Register.tsx` | `/login`, `/register` |
| Tableau de bord | `features/dashboard/` | `Dashboard.tsx` | `/dashboard` |
| Alertes sécurité | `features/alerts/` | `Alerts.tsx`, `AlertDetail.tsx` | `/alerts`, `/alerts/:id` |
| Assistant IA | `features/chat/` | `ChatIA.tsx` | `/chat` |
| Historique analytique | `features/historique/` | `Historique.tsx` | `/predictions` |

Chaque sous-dossier a son propre `README.md` détaillant ses fichiers.

## Conventions communes à tous les domaines

- Tous les écrans utilisent `IonPage` / `IonContent` (Ionic) comme conteneur racine.
- Chaque écran avec un style propre a son fichier `.css` associé du même nom, importé directement dans le `.tsx` (sauf `Login`/`Register` qui partagent `Auth.css`).
- Les appels réseau passent exclusivement par un fichier `*.api.ts` (local au domaine) ou par `services/` (transverse) — aucun écran ne construit d'URL d'API en dur, à l'exception de petits utilitaires locaux documentés individuellement.

## Note de migration

Cette structure remplace l'ancienne organisation plate suivante (chemins avant → après) :

| Avant | Après |
|---|---|
| `pages/Login.tsx`, `Register.tsx`, `Auth.css` | `features/auth/` |
| `pages/Dashboard.tsx` + `.css`, `hooks/useSSEPrediction.ts`, `types/dashboard.types.ts` | `features/dashboard/` |
| `pages/Alerts.tsx`, `AlertDetail.tsx` + `.css`, `services/alert.ts`, `services/alerts.ts` | `features/alerts/` (avec `alert.ts` → `alert.model.ts` et `alerts.ts` → `alerts.api.ts`) |
| `pages/ChatIA.tsx` + `.css`, `services/chatBridge.ts` | `features/chat/` |
| `pages/Historique.tsx` + `.css` | `features/historique/` |

Seuls les chemins d'import ont changé lors de cette migration — aucune logique applicative, JSX ou style n'a été modifié.