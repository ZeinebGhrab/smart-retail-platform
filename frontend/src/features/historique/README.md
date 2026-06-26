# `features/historique/` — Historique analytique

Écran protégé d'analyse détaillée de fréquentation.

## `Historique.tsx` + `Historique.css` (route `/predictions`)

Tableau de bord analytique détaillé : historique des visites (`getVisitorHistory`), résumé KPI (`getSummary`) et prévision (`getForecast`), avec filtre par caméra (`Porte_nord` / `Porte_sud` / toutes) et graphique en barres (Chart.js `Bar`).

## Dépendances transverses utilisées

- `../../services/api.ts` — `getVisitorHistory`, `getSummary`, `getForecast`, `getCameras`, et les types de réponse associés (`VisitorHistoryResponse`, `SummaryResponse`, etc.)

## Pourquoi ce domaine n'a pas de fichier `*.api.ts` ou `*.model.ts` local

Toute la logique d'accès aux données analytiques (`getVisitorHistory`, `getSummary`, `getForecast`, `getCameras`) est déjà centralisée dans `services/api.ts`, car ces mêmes fonctions sont aussi consommées par `../dashboard/Dashboard.tsx` (graphique de flux horaire). Dupliquer ce client dans `features/historique/` créerait deux sources de vérité pour les mêmes endpoints — il reste donc dans le service transverse.