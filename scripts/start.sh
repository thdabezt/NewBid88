#!/bin/sh
# Shared by the Docker image and the Kaggle notebook, so the code we load test is the code we ship.
set -e

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${UVICORN_WORKERS:-1}"
