FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Pre-download the tiktoken cl100k_base encoding at build time, so the running container never
# needs network access to openaipublic.blob.core.windows.net at runtime/cold start.
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN uv run python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.13-slim

WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn fpl_gaffer.integrations.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
