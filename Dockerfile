FROM python:3.12-slim

WORKDIR /app

COPY backend/ ./backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/backend:/app

WORKDIR /app/backend/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
