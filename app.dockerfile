# syntax=docker/dockerfile:1.9
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Set uv environment variables for optimization
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies with app extras (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --extra app --no-dev

# Copy application code
COPY app/ ./app/
COPY common/ ./common/

# Install the application
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra app --no-dev

# Runtime stage (minimal)
FROM python:3.13-slim

# Install curl for health checks
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user with a home directory. useradd -r alone records
# /home/app as HOME without creating it, and /home is root-owned, so
# anything writing under $HOME - Streamlit's machine-id file, for one -
# fails with "Permission denied: '/home/app'".
RUN groupadd -r app && useradd -r -g app -m -d /home/app app

# Copy application from builder
COPY --from=builder --chown=app:app /app /app

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

# Run Streamlit application
CMD ["python", "-m", "streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
