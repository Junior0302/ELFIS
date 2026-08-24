FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    ELFIS_ENVIRONMENT=production \
    STORAGE_PROVIDER=local \
    STORAGE_DIR=/data/storage

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY sql ./sql
COPY scripts/__init__.py ./scripts/__init__.py
COPY scripts/rc1/__init__.py ./scripts/rc1/__init__.py
COPY scripts/rc1/migrate_sql.py ./scripts/rc1/migrate_sql.py
COPY scripts/rc1/safety.py ./scripts/rc1/safety.py
COPY docs/performance/postgres_indexes_phase_f.sql ./docs/performance/postgres_indexes_phase_f.sql

RUN mkdir -p /data/storage \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /data

USER appuser
EXPOSE 8001

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers"]
