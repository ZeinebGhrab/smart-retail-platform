# ============================================================
# history/chat_view.py — Endpoint RAG pour le chat IA frontend
# POST /api/chat/
# Body : { "question": "Nombre de visiteurs le 2026-05-30 ?" }
# ============================================================

import re
from datetime import datetime, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from . import visitor_data as vd


# ── Helpers ────────────────────────────────────────────────
def _extract_date(text: str) -> str | None:
    """Extrait une date YYYY-MM-DD ou DD/MM/YYYY depuis le texte."""
    # Format ISO YYYY-MM-DD
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        return m.group(1)
    # Format DD/MM/YYYY ou DD-MM-YYYY
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    return None


def _extract_camera(text: str) -> str | None:
    t = text.lower()
    if "nord" in t or "porte_nord" in t or "porte nord" in t or "cam1" in t:
        return "Porte_nord"
    if "sud" in t or "porte_sud" in t or "porte sud" in t or "cam2" in t:
        return "Porte_sud"
    return None


def _extract_n_days(text: str) -> int | None:
    m = re.search(r'(\d+)\s*(jours?|days?|semaines?|weeks?)', text.lower())
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "semaine" in unit or "week" in unit:
            n *= 7
        return n
    if "semaine" in text.lower():
        return 7
    if "mois" in text.lower() or "month" in text.lower():
        return 30
    return None


def _format_count_result(result: dict, date: str | None) -> str:
    if "error" in result:
        return f"❌ Erreur : {result['error']}"
    vc = result.get("visit_count")
    cam = result.get("camera", "toutes caméras")
    d = result.get("date", date or "dernière date")
    if vc is None:
        return f"📅 Aucune donnée disponible pour le {d}."
    lines = [f"📊 **Visiteurs du {d}** ({cam})"]
    lines.append(f"  • Total : **{vc:,}** visiteurs")
    bd = result.get("breakdown") or []
    if bd:
        row = bd[0] if isinstance(bd, list) else bd
        men = row.get("gender_men", 0)
        women = row.get("gender_women", 0)
        lines.append(f"  • Hommes : {men:,}  |  Femmes : {women:,}")
        child = row.get("age_child", 0)
        teen = row.get("age_teenager", 0)
        adult = row.get("age_adult", 0)
        senior = row.get("age_senior", 0)
        if any([child, teen, adult, senior]):
            lines.append(f"  • Enfants : {child}  |  Ados : {teen}  |  Adultes : {adult}  |  Seniors : {senior}")
    return "\n".join(lines)


def _format_hourly_result(result: dict) -> str:
    if "error" in result:
        return f"❌ Erreur : {result['error']}"
    d = result.get("date", "?")
    cam = result.get("camera", "toutes caméras")
    flow = result.get("hourly_flow", [])
    if not flow:
        return f"📅 Aucun flux horaire disponible pour le {d}."
    total = result.get("total", sum(p.get("count", 0) for p in flow))
    peak = result.get("peak_hour")
    lines = [f"⏱️ **Flux horaire du {d}** ({cam}) — Total : {total:,}"]
    if peak is not None:
        lines.append(f"  🔝 Heure de pointe : **{peak}h**")
    # Top 5 heures
    sorted_flow = sorted(flow, key=lambda x: x.get("count", 0), reverse=True)[:5]
    lines.append("  Heures les plus actives :")
    for p in sorted_flow:
        h = p.get("hour", "?")
        c = p.get("count", 0)
        bar = "█" * min(int(c / max(1, total) * 20), 20)
        lines.append(f"    {h:02d}h  {bar}  {c}")
    return "\n".join(lines)


def _format_history_result(result: dict) -> str:
    if "error" in result:
        return f"❌ Erreur : {result['error']}"
    rows = result.get("results", [])
    if not rows:
        return "📅 Aucun historique disponible pour cette période."
    cam = result.get("camera", "toutes caméras")
    total = result.get("total_visits") or sum(r.get("visit_Count", 0) for r in rows)
    lines = [f"📈 **Historique visiteurs** ({cam}) — {len(rows)} jour(s), total : {total:,}"]
    for r in rows[-10:]:  # max 10 lignes
        d = r.get("date", "?")
        vc = r.get("visit_Count", 0)
        lines.append(f"  • {d} : {vc:,} visiteurs")
    return "\n".join(lines)


def _format_forecast_result(result: dict) -> str:
    if "error" in result:
        return f"❌ Erreur : {result['error']}"
    d = result.get("target_date", "?")
    pred = result.get("predicted_visit_count")
    conf = result.get("confidence", "?")
    method = result.get("method", "régression linéaire")
    if pred is None:
        return f"⚠️ Prévision indisponible pour le {d}."
    return (
        f"🔮 **Prévision pour le {d}**\n"
        f"  • Visiteurs prévus : **{int(pred):,}**\n"
        f"  • Méthode : {method}\n"
        f"  • Confiance : {conf}"
    )


def _format_summary_result(result: dict) -> str:
    if "error" in result:
        return f"❌ Erreur : {result['error']}"
    period = result.get("period", {})
    total = result.get("total_visits", 0)
    n_days = period.get("n_days", "?")
    start = period.get("start_date", "?")
    end = period.get("end_date", "?")
    by_g = result.get("by_gender", {})
    by_cam = result.get("by_camera", [])
    lines = [
        f"📋 **Résumé global** ({start} → {end}, {n_days} jours)",
        f"  • Total visiteurs : **{total:,}**",
    ]
    if by_g:
        lines.append(f"  • Hommes : {by_g.get('men', 0):,}  |  Femmes : {by_g.get('women', 0):,}")
    for cam_row in by_cam:
        lines.append(f"  • {cam_row['camera']} : {cam_row['visit_Count']:,}")
    return "\n".join(lines)


# ── Routing intelligent ────────────────────────────────────
def _route_and_answer(question: str) -> str:
    """Détermine l'outil à appeler et formate la réponse en langage naturel."""
    q = question.lower()
    date = _extract_date(question)
    camera = _extract_camera(question)
    n_days = _extract_n_days(question)

    # Prévision
    if any(k in q for k in ["prév", "prédi", "predict", "forecast", "demain", "prochain"]):
        if date is None:
            date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = vd.forecast_visitors(target_date=date, camera=camera)
        return _format_forecast_result(result)

    # Résumé global
    if any(k in q for k in ["résumé", "bilan", "kpi", "global", "summary", "total général"]):
        result = vd.get_summary()
        return _format_summary_result(result)

    # Flux horaire
    if any(k in q for k in ["horaire", "heure", "flux", "hour", "pic", "pointe"]):
        result = vd.get_hourly_visitor_flow(date=date, camera=camera)
        return _format_hourly_result(result)

    # Historique / tendance
    if any(k in q for k in ["historique", "évolution", "tendance", "période", "semaine", "mois", "derniers jours", "dernier"]):
        result = vd.get_visitor_history(
            start_date=None, end_date=date, camera=camera, n_days=n_days or 7
        )
        return _format_history_result(result)

    # Nombre de visiteurs (cas principal : date précise ou pas)
    if any(k in q for k in ["visiteur", "visite", "combien", "nombre", "count", "fréquentation"]):
        result = vd.get_visitor_count(date=date, camera=camera)
        return _format_count_result(result, date)

    # Caméras disponibles
    if any(k in q for k in ["caméra", "camera", "porte", "entrée"]):
        cams = vd.list_cameras()
        return f"📷 Caméras disponibles : {', '.join(cams)}"

    # Fallback — essai sur le count
    result = vd.get_visitor_count(date=date, camera=camera)
    return _format_count_result(result, date)


# ── Vue Django ─────────────────────────────────────────────
@extend_schema(
    tags=["Chat IA"],
    summary="Chat RAG — Question en langage naturel sur les visiteurs",
    description="Reçoit une question en français et retourne une réponse basée sur les données réelles.",
)
@api_view(["POST"])
def chat(request):
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"error": "Champ 'question' manquant."}, status=400)

    try:
        answer = _route_and_answer(question)
    except Exception as exc:
        answer = f"⚠️ Erreur lors du traitement : {exc}"

    return Response({"question": question, "answer": answer})