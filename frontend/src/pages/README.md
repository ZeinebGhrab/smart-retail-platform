# `pages/` — Écrans de l'application

Chaque fichier `.tsx` correspond à un écran complet routé dans `App.tsx`. Le CSS associé porte le même nom (sauf `Login`/`Register` qui partagent `Auth.css`).

## `Login.tsx` (public)

Écran de connexion (e-mail + mot de passe), avec case « se souvenir de moi » (persistance `localStorage` vs `sessionStorage`, voir `services/auth.ts`).

Inclut aussi le flux complet **mot de passe oublié** en 4 étapes locales (`ForgotStep`) gérées dans une modale, sans changer de route :
1. `email` — saisie de l'adresse, appelle `POST /api/auth/password-reset/request/`
2. `otp` — saisie du code à 6 chiffres reçu par e-mail, appelle `.../verify/`
3. `newpw` — nouveau mot de passe + confirmation, appelle `.../confirm/`
4. `done` — confirmation, retour à l'écran de connexion

## `Register.tsx` (public)

Formulaire d'inscription : prénom, nom, nom du commerce, e-mail, mot de passe + confirmation — champs strictement alignés sur `RegisterSerializer` côté Django. Validation client-side puis remontée des erreurs serveur champ par champ via `AuthApiError.fieldErrors`.

## `Dashboard.tsx` + `Dashboard.css` (protégée)

Écran d'accueil après connexion. Combine :
- KPIs (visiteurs, taux de conversion, alertes) et graphique de flux horaire (Chart.js `Line`)
- Prévision de fréquentation du jour reçue en temps réel via `useSSEPrediction()` (flux SSE)
- Cloche de notifications (`components/Notifications.tsx`)

## `ChatIA.tsx` + `ChatIA.css` (protégée)

Interface de chat avec l'assistant RAG. Envoie les questions à `POST /api/chat/` (via `API_BASE_URL`), affiche l'historique de conversation et le modèle LLM ayant répondu. S'abonne au `chatBridge` (`services/chatBridge.ts`) pour recevoir des messages pré-remplis envoyés depuis d'autres écrans (ex. clic sur une notification).

## `Historique.tsx` + `Historique.css` (protégée)

Tableau de bord analytique détaillé : historique des visites (`getVisitorHistory`), résumé KPI (`getSummary`) et prévision (`getForecast`), avec filtre par caméra (`Porte_nord` / `Porte_sud` / toutes) et graphique en barres (Chart.js `Bar`).

---

## Conventions communes

- Toutes les pages utilisent `IonPage` / `IonContent` (Ionic) comme conteneur racine.
- Les icônes des pages d'authentification sont des SVG inline (pas de dépendance externe) ; les autres pages utilisent `ionicons`.
- Les appels réseau passent exclusivement par `services/` — aucune page ne construit d'URL d'API en dur (à l'exception de petits utilitaires locaux comme `fetchLatest` dans `Notifications.tsx`).
