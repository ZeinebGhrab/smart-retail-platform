# ============================================================
# Makefile — ShopAnalytics LLM Benchmark
# ============================================================

.PHONY: up down bench logs clean status agent-build agent-shell reindex ask

# Lancer Ollama en background + exécuter le benchmark complet
up:
	docker compose up -d ollama
	@echo "⏳ Attente Ollama prêt..."
	@until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 2; done
	@echo "✅ Ollama prêt."
	docker compose run --rm benchmark

# Lancer uniquement Ollama (sans benchmark)
ollama:
	docker compose up -d ollama

# Lancer uniquement le benchmark (Ollama doit déjà tourner)
bench:
	docker compose run --rm benchmark

# (Re)construire l'index de la base vectorielle (FAQ / connaissances métier)
reindex:
	docker compose run --rm agent bash -c "pip install -q -r requirements.txt && python vector_store.py --reindex"

# Poser une question à l'agent RAG (visiteurs + FAQ)
# Usage : make ask Q="Combien de visiteurs hier ?"
ask:
	docker compose run --rm agent bash -c "pip install -q -r requirements.txt && python visitor_agent.py \"$(Q)\""

# Voir les logs Ollama en live
logs:
	docker compose logs -f ollama

# Statut des containers
status:
	docker compose ps

# Arrêter tout
down:
	docker compose down

# Nettoyer résultats (garder les modèles)
clean-results:
	rm -f results/*.json

# Tout supprimer (volumes inclus — supprime les modèles téléchargés !)
clean-all:
	docker compose down -v
	rm -f results/*.json