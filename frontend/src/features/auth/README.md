# `features/auth/` — Authentification

Écrans publics (non protégés par `PrivateRoute`) gérant la connexion et l'inscription.

## `Login.tsx` + `Auth.css`

Écran de connexion (e-mail + mot de passe). Inclut aussi le flux complet **mot de passe oublié** en 4 étapes locales (`ForgotStep`) gérées dans une modale, sans changer de route :

1. `email` — saisie de l'adresse, appelle `POST /api/auth/password-reset/request/`
2. `otp` — saisie du code à 6 chiffres reçu par e-mail, appelle `.../verify/`
3. `newpw` — nouveau mot de passe + confirmation, appelle `.../confirm/`
4. `done` — confirmation, retour à l'écran de connexion

Appelle aussi `useFirebaseMessaging()` au montage (enregistrement du token push après connexion).

> **Correctif sprint 2** — La case « se souvenir de moi » et toute logique de persistance `localStorage`/`sessionStorage` ont été supprimées. Les tokens ne sont plus stockés côté client : ils voyagent exclusivement dans des **cookies HttpOnly** posés et gérés par le backend. Le frontend ne conserve en mémoire que le profil utilisateur (non-sensible), réinitialisé par `bootstrapAuth()` au démarrage.

## `Register.tsx` (partage `Auth.css`)

Formulaire d'inscription : prénom, nom, nom du commerce, e-mail, mot de passe + confirmation — champs strictement alignés sur `RegisterSerializer` côté Django. Validation client-side puis remontée des erreurs serveur champ par champ via `AuthApiError.fieldErrors`.

## Dépendances transverses utilisées

- `../../services/auth.ts` — `login`, `register`, `requestPasswordReset`, `verifyResetCode`, `confirmPasswordReset`, `AuthApiError`
- `../../hooks/useFirebaseMessaging.ts` — enregistrement du token push (uniquement dans `Login.tsx`)

## Pourquoi `auth/` est un domaine séparé

Login et Register n'ont pas de service ou de type qui leur soit propre (tout passe par le service transverse `services/auth.ts`, utilisé aussi par `PrivateRoute` et `TabBar`) : ce dossier ne contient donc que les deux écrans + leur CSS partagé, sans fichier `*.api.ts` ou `*.model.ts` local.