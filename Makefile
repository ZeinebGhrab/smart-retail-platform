# ============================================================
# Makefile — ShopAnalytics
# ============================================================

.PHONY: up down ollama bench django frontend api logs status clean-results clean-all

# Ollama + benchmark + API Django + Frontend
up:
	docker compose up -d ollama
	@echo "⏳ Attente Ollama prêt..."
	@until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
	@echo "✅ Ollama prêt."
	docker compose run --rm benchmark
	docker compose up -d django_api frontend

# Lancer uniquement Ollama
ollama:
	docker compose up -d ollama

# Lancer uniquement le benchmark (Ollama doit déjà tourner)
bench:
	docker compose run --rm benchmark

# Lancer l'API Django seule (http://localhost:8000)
django:
	docker compose up --build django_api

# Lancer Django + Frontend (sans Ollama)
api:
	docker compose up --build django_api frontend

# Lancer le frontend seul (http://localhost:5173)
frontend:
	docker compose up frontend

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