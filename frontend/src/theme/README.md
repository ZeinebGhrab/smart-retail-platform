# `theme/` — Thème global Ionic

## `variables.css`

Surcharge des variables CSS natives d'Ionic (`--ion-*`) pour appliquer le design system clair de ShopAnalytics à l'ensemble de l'application (sans toucher au CSS de chaque composant Ionic individuellement).

| Catégorie | Variables clés | Valeur |
|---|---|---|
| Fond / texte | `--ion-background-color`, `--ion-text-color` | `#f3f5f9` / `#111827` |
| Couleur primaire | `--ion-color-primary` (+ shade/tint) | `#2563eb` (bleu) |
| Sémantique | `--ion-color-success` / `-warning` / `-danger` | vert `#15803d` / orange `#b45309` / rouge `#dc2626` |
| Surfaces | `--ion-toolbar-background`, `--ion-card-background`, `--ion-item-background` | blanc / fond clair |
| TabBar | `--ion-tab-bar-*` | fond blanc, accent bleu sur l'onglet actif |
| Typographie | `--ion-font-family` | `Inter` (+ fallback système) |

> ⚠️ `--ion-background-color` doit rester synchronisé avec la variable `--db-bg` définie dans `pages/Dashboard.css` — les deux représentent le même fond global et sont dupliquées pour des raisons de portée CSS.

Ce fichier est importé une seule fois, globalement, au démarrage de l'application (voir `main.tsx`).
