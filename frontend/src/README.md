# `src/` — Code source de l'application

## Fichiers racine

| Fichier | Rôle |
|---|---|
| `App.tsx` | Définit le routage (`react-router-dom`) et monte la `TabBar` globale |
| `main.tsx` | Point d'entrée — monte `<App />` dans le DOM |
| `vite-env.d.ts` | Déclarations de types pour les variables d'environnement Vite (`import.meta.env`) |

## Organisation par dossier

| Dossier | Contenu |
|---|---|
| `components/` | Composants UI réutilisables à travers plusieurs pages (barre d'onglets, notifications, garde de route) |
| `hooks/` | Hooks React personnalisés (connexion SSE temps réel) |
| `pages/` | Une page = un écran complet de l'application (auth, dashboard, chat, historique) |
| `services/` | Clients HTTP vers l'API Django — aucune logique UI, uniquement des fonctions `fetch` typées |
| `theme/` | Variables CSS globales du thème Ionic |
| `types/` | Types TypeScript partagés entre plusieurs composants/pages |

**Convention de nommage :** chaque page/composant avec un style spécifique a son fichier CSS associé du même nom (`Dashboard.tsx` + `Dashboard.css`), à l'exception de `Login.tsx`/`Register.tsx` qui partagent `Auth.css`.

Voir le `README.md` de chaque sous-dossier pour le détail fichier par fichier.
