# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.14 AS uv-bin

FROM python:3.12-slim-bookworm AS api-builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build

COPY --from=uv-bin /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra api --no-editable

FROM python:3.12-slim-bookworm AS api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    MWANGAZA_ENV=demo \
    MWANGAZA_MODE=demo \
    MWANGAZA_API_DATA_MODE=demo \
    MWANGAZA_CACHE_REQUIRED=false \
    MWANGAZA_DATA_DIR=/app/data \
    MWANGAZA_CACHE_DIR=/app/.cache/mwangaza \
    MWANGAZA_DEMO_FIXTURE_DIR=/app/demo_data \
    MWANGAZA_DROUGHT_CONTINUATION_SNAPSHOT=/app/demo_data/drought-continuation-probabilities.json \
    PORT=8080

RUN groupadd --system --gid 10001 mwangaza \
    && useradd --system --uid 10001 --gid mwangaza --home-dir /app --create-home mwangaza
WORKDIR /app

COPY --from=api-builder --chown=mwangaza:mwangaza /opt/venv /opt/venv
COPY --chown=mwangaza:mwangaza src ./src
COPY --chown=mwangaza:mwangaza demo_data ./demo_data
COPY --chown=mwangaza:mwangaza data/regions ./data/regions
COPY --chown=mwangaza:mwangaza frontend/public/maps ./frontend/public/maps
RUN mkdir -p /app/data /app/.cache/mwangaza \
    && chown -R mwangaza:mwangaza /app/data /app/.cache

USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/ready', timeout=3)"
CMD ["sh", "-c", "exec uvicorn mwangaza.api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]

FROM node:20-alpine AS web-builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY demo_data ./demo_data
COPY frontend ./frontend
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS web

ENV API_UPSTREAM=http://api:8080 \
    PORT=8080
COPY infrastructure/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=web-builder /build/dist/frontend /usr/share/nginx/html

USER 101:101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q -T 3 -O - "http://127.0.0.1:${PORT:-8080}/healthz" >/dev/null || exit 1
