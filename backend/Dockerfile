FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    STORAGE_DIR=/data/storage \
    DATABASE_URL=sqlite:////data/comptapilot.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /data/storage \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /data

USER appuser
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
