FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY django_api/requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt
COPY django_api/ .
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python manage.py runserver 0.0.0.0:8000"]