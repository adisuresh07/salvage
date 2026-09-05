# syntax=docker/dockerfile:1.7
FROM node:24.20-alpine AS console-build
WORKDIR /build/console
RUN corepack enable
COPY console/package.json console/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY console/ ./
RUN pnpm build

FROM ghcr.io/astral-sh/uv:0.12.7 AS uv

FROM python:3.14.7-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
COPY policy/ ./policy/
COPY migrations/ ./migrations/
COPY fixtures/ ./fixtures/
COPY --from=console-build /build/console/dist/ ./console/dist/
RUN uv sync --frozen --no-dev \
    && groupadd --system --gid 10001 salvage \
    && useradd --system --uid 10001 --gid salvage --home /app salvage \
    && mkdir -p /app/data /app/reports \
    && chown -R salvage:salvage /app/data /app/reports
USER salvage
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]
CMD ["salvage", "serve"]
