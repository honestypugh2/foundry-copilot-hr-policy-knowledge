# Backend (FastAPI) container — Pattern C /api/lookup + Pattern B2 /api/chat host.
# Built and pushed by `azd deploy` (azure.yaml service `backend`, host: containerapp).
# Build context is the repo root. Serves on port 8000.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# uv for fast, lockfile-pinned installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install runtime dependencies from the pinned lockfile (no project build needed)
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt

# Application source (includes src/config/*.json read at runtime)
COPY src ./src

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
