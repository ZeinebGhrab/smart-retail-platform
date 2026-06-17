# ============================================================
# django_api/Dockerfile — image légère, pas de torch/chromadb
# Les embeddings sont délégués à Ollama via HTTP (réseau Docker)
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Aucune dépendance système lourde requise
COPY django_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY django_api/ .

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python manage.py runserver 0.0.0.0:8000"]