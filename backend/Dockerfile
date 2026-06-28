# ============================================================
# django_api/Dockerfile — image légère, pas de torch/chromadb
# Les embeddings sont délégués à Ollama via HTTP (réseau Docker)
# ============================================================
FROM python:3.11-slim
WORKDIR /app

# Dépendances système : libgomp1 requis par lightgbm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY django_api/requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt
COPY django_api/ .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python manage.py runserver 0.0.0.0:8000"]