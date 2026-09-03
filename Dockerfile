# syntax=docker/dockerfile:1
# HOLD - two-stage build
# Stage 1: build the web app (Node)
# Stage 2: Python runtime with the built web/dist copied in

# ---- Stage 1: web build ----
# The web app is task 0.10 onward (Deem's lane). Until web/package.json exists the stage writes a
# placeholder index.html so the API image still builds and /api/status serves; with the web app
# present it runs the real build. Docker cannot COPY a missing directory, so the whole context is
# copied and the check happens in the shell (.dockerignore keeps the context small).
FROM node:22-slim AS web-build
WORKDIR /src
COPY . /src
RUN if [ -f web/package.json ]; then \
      cd web && npm ci --ignore-scripts && npm run build; \
    else \
      mkdir -p web/dist && printf '%s\n' \
        '<!doctype html><meta charset="utf-8"><title>HOLD</title>' \
        '<p>HOLD API is running. The web app has not been built into this image yet; see /api/status and /api/docs.</p>' \
        > web/dist/index.html; \
    fi
# Output: /src/web/dist/

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
COPY --from=web-build /src/web/dist web/dist

# Install Python dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Cloud Run injects PORT; uvicorn binds to it.
# D11: --max-instances=1 is set in deploy.yml, not here.
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
