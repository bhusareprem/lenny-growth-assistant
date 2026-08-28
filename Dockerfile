# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 - build the React SPA.
# Kept separate so Node never ships in the runtime image; the API serves the
# static bundle, which means one container, one port, one origin.
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build
# Copy manifests first so `npm ci` is cached until dependencies actually change.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 - runtime.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# git is a runtime dependency, not a build one: the corpus is cloned at
# ingestion time because its licence forbids redistributing the raw files.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY --from=frontend /build/dist ./frontend/dist

# Run unprivileged. /srv/data is the only path the app writes to.
RUN useradd --create-home --uid 10001 lenny \
    && mkdir -p /srv/data \
    && chown -R lenny:lenny /srv
USER lenny

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ---------------------------------------------------------------------------
# Stage 3 - test runner.
# Not part of the runtime image: an evaluator with only Docker installed still
# needs a way to run the suite, but shipping pytest and the test corpus into
# production would be wrong. `docker compose run --rm test` builds this target.
# ---------------------------------------------------------------------------
FROM runtime AS test

USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
COPY pytest.ini ./
RUN chown -R lenny:lenny /srv
USER lenny

# SQLite in-memory and no embeddings: the suite must not need Postgres or Ollama.
ENV DATABASE_URL=sqlite+aiosqlite:///:memory:     EMBEDDINGS_ENABLED=false     LOG_LEVEL=warning

CMD ["python", "-m", "pytest", "-q"]
