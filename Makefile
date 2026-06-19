# ============================================================
# Makefile — ShopAnalytics
# ============================================================

.PHONY: up down ollama bench django frontend api n8n postgres logs status clean-results clean-all

# Postgres + Ollama + benchmark + API Django + Frontend + n8n
up:
	docker compose up -d postgres ollama
	@echo "⏳ Attente Postgres + Ollama prêts..."
	@until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do sleep 2; done
	@until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
	@echo "✅ Postgres + Ollama prêts."
	docker compose run --rm benchmark
	docker compose up -d django_api frontend n8n

# Lancer uniquement Postgres
postgres:
	docker compose up -d postgres

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

# Lancer n8n seul (http://localhost:5678)
n8n:
	docker compose up -d n8n

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

# Tout supprimer (volumes inclus — supprime les modèles téléchargés et les données Postgres/n8n !)
clean-all:
	docker compose down -v
	rm -f backend/results/*.json