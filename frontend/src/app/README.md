# `app/` — Composant racine de l'application

## `App.tsx`

Composant racine monté par `../main.tsx`. Responsabilités :

- `setupIonicReact()` — initialise Ionic React au démarrage.
- `useFirebaseMessaging()` — enregistre l'appareil pour les notifications push, une seule fois au démarrage.
- Déclare toutes les routes de l'application (`react-router-dom` via `IonReactRouter` / `IonRouterOutlet`) :

| Route | Composant | Protection |
|---|---|---|
| `/login` | `features/auth/Login` | publique |
| `/register` | `features/auth/Register` | publique |
| `/dashboard` | `features/dashboard/Dashboard` | `PrivateRoute` |
| `/chat` | `features/chat/ChatIA` | `PrivateRoute` |
| `/predictions` | `features/historique/Historique` | `PrivateRoute` |
| `/alerts` | `features/alerts/Alerts` | `PrivateRoute` |
| `/alerts/:id` | `features/alerts/AlertDetail` | `PrivateRoute` |
| `/` | redirection vers `/dashboard` si connecté, sinon `/login` | — |

- Monte `../components/TabBar` globalement, en dehors du `IonRouterOutlet` (la barre d'onglets se masque elle-même sur `/login` et `/register`, voir `components/README.md`).

## Pourquoi `App.tsx` est isolé dans son propre dossier

`App.tsx` est le seul fichier qui importe simultanément tous les domaines (`features/*`) et tous les éléments transverses (`components/`, `services/`, `hooks/`). L'isoler dans `app/` évite de le mélanger avec `main.tsx` (point d'entrée Vite) à la racine de `src/`, et signale clairement qu'il s'agit du point d'assemblage de l'application plutôt que d'un écran ou d'un composant réutilisable.