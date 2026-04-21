FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen --no-editable --no-dev

EXPOSE 8002

CMD ["uv", "run", "uvicorn", "graphwash.api.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
