# ============================================================
# Makefile — ShopAnalytics LLM Benchmark
# ============================================================

.PHONY: up down ollama bench frontend reindex ask logs status clean-results clean-all

# Lancer Ollama en background + benchmark complet
up:
	docker compose up -d ollama
	@echo "⏳ Attente Ollama prêt..."
	@until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
	@echo "✅ Ollama prêt."
	docker compose run --rm benchmark

# Lancer uniquement Ollama
ollama:
	docker compose up -d ollama

# Lancer uniquement le benchmark (Ollama doit déjà tourner)
bench:
	docker compose run --rm benchmark

# Lancer le frontend seul (hot-reload sur http://localhost:5173)
frontend:
	docker compose up frontend

# Lancer l'API Django (historique visiteurs) seule (http://localhost:8000)
django:
	docker compose up --build django_api

# Lancer Django + Frontend (sans Ollama)
backend:
	docker compose up --build django_api frontend

# (Re)construire l'index de la base vectorielle
reindex:
	docker compose run --rm agent bash -c "python vector_store.py --reindex"

# Poser une question à l'agent RAG
# Usage : make ask Q="Combien de visiteurs hier ?"
ask:
	docker compose run --rm agent bash -c "python visitor_agent.py \"$(Q)\""

# Logs Ollama en live
logs:
	docker compose logs -f ollama

# Statut des containers
status:
	docker compose ps

# Arrêter tout
down:
	docker compose down

# Nettoyer résultats benchmark (garder les modèles)
clean-results:
	rm -f backend/results/*.json

# Tout supprimer (volumes inclus — supprime les modèles téléchargés !)
clean-all:
	docker compose down -v
	rm -f backend/results/*.json