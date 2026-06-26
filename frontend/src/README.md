# `src/` — Code source de l'application

## Fichiers racine

| Fichier | Rôle |
|---|---|
| `app/App.tsx` | Définit le routage (`react-router-dom`) et monte la `TabBar` globale |
| `main.tsx` | Point d'entrée — monte `<App />` dans le DOM |
| `vite-env.d.ts` | Déclarations de types pour les variables d'environnement Vite (`import.meta.env`) |

## Organisation par dossier (architecture feature-based)

| Dossier | Contenu |
|---|---|
| `app/` | Composant racine `App.tsx` (routage + montage des providers globaux) |
| `components/` | Composants UI réutilisables à travers plusieurs écrans (barre d'onglets, notifications, garde de route) |
| `hooks/` | Hooks React transverses, non liés à un écran précis (ex. messagerie Firebase) |
| `services/` | Clients HTTP génériques vers l'API Django, utilisés par plusieurs écrans (`api.ts`, `auth.ts`, `fcm.ts`) |
| `theme/` | Variables CSS globales du thème Ionic |
| `features/` | Un sous-dossier par domaine fonctionnel (écran + CSS + types + hooks/services propres à ce domaine) : `auth/`, `dashboard/`, `alerts/`, `chat/`, `historique/`. Voir `features/README.md`. |

**Convention de nommage :** chaque écran/composant avec un style spécifique a son fichier CSS associé du même nom (`Dashboard.tsx` + `Dashboard.css`), à l'exception de `Login.tsx`/`Register.tsx` qui partagent `Auth.css`.

Voir le `README.md` de chaque sous-dossier pour le détail fichier par fichier.
