FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

FROM base AS api
CMD ["uvicorn", "vibehouse.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS worker
CMD ["celery", "-A", "vibehouse.tasks.celery_app", "worker", "--loglevel=info"]

FROM base AS beat
CMD ["celery", "-A", "vibehouse.tasks.celery_app", "beat", "--loglevel=info"]
