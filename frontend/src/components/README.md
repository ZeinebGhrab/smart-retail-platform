# `components/` — Composants UI partagés

Composants réutilisés à travers plusieurs pages, par opposition à `pages/` qui contient des écrans complets.

## Fichiers

### `TabBar.tsx` / `TabBar.css`
Barre de navigation par onglets en bas d'écran (Dashboard / Chat IA / Prédictions), avec bouton de déconnexion (confirmation avant d'appeler `logout()` depuis `services/auth.ts`). Masquée automatiquement sur les écrans `/login` et `/register`.

### `Notifications.tsx` / `Notifications.css`
Cloche de notifications affichant les rapports quotidiens générés par le workflow N8N (prévision de fréquentation). Fonctionne par **polling** : interroge `GET /api/notifications/latest/` et `GET /api/notifications/history/` toutes les 5 secondes (`POLL_MS`), et permet d'envoyer le contenu d'une notification vers le Chat IA via `sendToChat()` (`services/chatBridge.ts`).

> Différence avec le Dashboard : `Notifications.tsx` utilise du polling HTTP classique, tandis que `Dashboard.tsx` utilise le flux **SSE** temps réel via `useSSEPrediction.ts` — deux mécanismes consomment la même source de données (`/api/notifications/*` et `/api/prediction/stream/`) de façon indépendante.

### `PrivateRoute.tsx`
Garde d'accès aux routes protégées. Enveloppe une `Route` de `react-router-dom` : si `isAuthenticated()` (présence d'un token d'accès local) est faux, redirige vers `/login` en conservant l'URL d'origine (`state: { from }`) pour une redirection post-connexion.

---

## Conventions

- Chaque composant avec un style propre a son fichier `.css` associé du même nom, importé directement dans le `.tsx`.
- Les icônes utilisent soit `ionicons` (composants Ionic), soit des SVG inline pour les besoins spécifiques (voir `pages/`).
