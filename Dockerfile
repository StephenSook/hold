# syntax=docker/dockerfile:1
# HOLD - two-stage build
# Stage 1: build the web app (Node)
# Stage 2: Python runtime with the built web/dist copied in

# ---- Stage 1: web build ----
FROM node:22-slim AS web-build
WORKDIR /app/web

# Copy package files first for layer caching
COPY web/package.json web/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY web/ ./
RUN npm run build
# Output: /app/web/dist/

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim AS runtime

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy Python project files
COPY pyproject.toml uv.lock ./
COPY api/ api/
COPY bench/ bench/
COPY data/ data/
COPY rules/ rules/
COPY docs/ docs/

# Copy built web assets from stage 1
COPY --from=web-build /app/web/dist web/dist

# Install Python dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Cloud Run injects PORT; uvicorn binds to it.
# D11: --max-instances=1 is set in deploy.yml, not here.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
