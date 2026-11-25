# language-maxxer: one image = API + built frontend (ADR-1, ADR-8). State in /data.
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" LMX_DATA_DIR=/data LMX_STATIC_DIR=/app/static
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
COPY --from=web /web/build ./static

RUN useradd -u 1000 -m lmx && mkdir -p /data && chown lmx /data
USER lmx
EXPOSE 8000
VOLUME /data
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["python", "-m", "lmx", "--host", "0.0.0.0", "--port", "8000"]
