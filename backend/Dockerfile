# ============================================================
# Backend — Agent RAG Python (Ollama + ChromaDB)
# ============================================================
FROM python:3.11-slim

WORKDIR /workspace

# Dépendances système minimales pour sentence-transformers et chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python (couche cachée séparément)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY dataset/ ./dataset/

# Les dossiers data/ vector_db/ results/ sont montés via volumes
# (données persistées hors image)

ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://ollama:11434

WORKDIR /workspace/app

CMD ["python", "visitor_agent.py"]