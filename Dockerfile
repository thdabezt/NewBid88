FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY scripts ./scripts
COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Phase 1 runs a single worker; UVICORN_WORKERS is the knob for phase 2.
CMD ["sh", "scripts/start.sh"]
