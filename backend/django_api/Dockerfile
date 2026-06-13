FROM python:3.11-slim

WORKDIR /app

COPY django_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY django_api/ .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
