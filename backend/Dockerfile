# ============================================================
# django_api/Dockerfile — image avec support mysql
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système pour mysql
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY django_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY django_api/ .

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]