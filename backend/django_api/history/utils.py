# ============================================================
# history/utils.py — Utilitaires partagés
# ============================================================


def get_pagination_params(query_params, default_limit=50, max_limit=200):
    """
    Extrait et valide les paramètres de pagination depuis query_params.

    - Protège contre les valeurs non-entières (ValueError/TypeError).
    - Empêche un limit négatif ou nul (min 1).
    - Plafonne limit à max_limit pour éviter les requêtes massives.
    - Empêche un offset négatif.

    Usage :
        limit, offset = get_pagination_params(request.query_params)
        total = qs.count()
        page  = qs[offset:offset + limit]
    """
    try:
        limit = max(1, min(int(query_params.get("limit", default_limit)), max_limit))
    except (ValueError, TypeError):
        limit = default_limit

    try:
        offset = max(0, int(query_params.get("offset", 0)))
    except (ValueError, TypeError):
        offset = 0

    return limit, offset