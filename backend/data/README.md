# `data/` — Données brutes visiteurs

Ce dossier contient les **données sources** utilisées par l'ensemble du backend ShopAnalytics. Il est monté en **volume Docker** (`./data:/app/data`) pour être partagé entre les conteneurs `backend` et `django_api` sans être inclus dans les images.

---

## Fichiers

### `shoppingclub_2025_2026.csv` (~2,7 Mo)

Données de comptage visiteurs collectées par les caméras en entrée de magasin.

| Colonne | Type | Exemples | Description |
|---|---|---|---|
| `camera` | string | `"Cam porte1"`, `"Cam_porte2"` | Identifiant caméra brut (normalisé en `Porte_nord` / `Porte_sud` à la lecture) |
| `datetime` | string | `"15/06/2025 08:00:00"` | Horodatage au format `DD/MM/YYYY HH:MM:SS` |
| `gender` | string | `"MEN"`, `"WOMEN"`, `"Male"` | Genre détecté (normalisé en `men` / `women`) |
| `age` | string | `"18-29"`, `"age_18_29"`, `"adultes"` | Tranche d'âge (normalisée en `age_18_29`, etc.) |
| `Visits` | int | `3`, `12` | Nombre de passages détectés sur la période |

**Couverture temporelle :** juin 2025 – mai 2026 (349 jours)  
**Granularité :** horaire (une ligne = 1 heure × 1 caméra × 1 genre × 1 tranche d'âge)  
**Caméras :** `Porte_nord` (entrée principale) et `Porte_sud` (entrée secondaire)

> Ce fichier est la **seule source de vérité** pour toutes les fonctions analytiques : `get_visitor_count`, `get_hourly_visitor_flow`, `forecast_visitors`, `get_visitor_history`.

---

### `SA-data.xlsx` (~7 Ko)

Fichier Excel complémentaire utilisé par l'agent standalone (`app/visitor_data.py` via `openpyxl`). Peut contenir des métadonnées de configuration ou des données de référence magasin (horaires, seuils d'alerte, etc.).

---

## Notes d'exploitation

- **Ne pas versionner** les fichiers de données dans Git (`.gitignore` conseillé). Utiliser des volumes Docker ou un stockage objet (S3, MinIO) en production.
- **Mise à jour incrémentale** : `visitor_data.py` dans `django_api` invalide son cache en mémoire dès que le `mtime` du CSV change — il suffit de remplacer le fichier pour que les nouvelles données soient prises en compte sans redémarrer le service.
- **Format de date** : le parsing utilise `dayfirst=True` ; s'assurer que tout nouveau CSV respecte le format `DD/MM/YYYY`.