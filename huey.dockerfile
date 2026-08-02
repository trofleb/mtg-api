# syntax=docker/dockerfile:1.9
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Set uv environment variables for optimization
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY common/ ./common/
COPY tasks/ ./tasks/

# Install the application
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage (minimal)
FROM python:3.13-slim

# Install process tools for health checks
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends procps && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user with a home directory. useradd -r alone records
# /home/app as HOME without creating it, and /home is root-owned, so
# anything writing under $HOME fails with "Permission denied".
#
# The uid/gid are pinned rather than left to useradd, which just takes the
# next free system id. huey-init in docker-compose chowns the huey_data
# volume to this exact id, so letting it drift - by adding another system
# user above this line, or bumping the base image - would silently hand the
# volume to the wrong owner and put back the bug this pinning prevents.
RUN groupadd -r -g 999 app && useradd -r -u 999 -g app -m -d /home/app app

# Copy application from builder
COPY --from=builder --chown=app:app /app /app

# Create and set ownership of database directory for volume mount
RUN mkdir -p /app/db && chown -R app:app /app/db

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD pgrep -f "huey_consumer" || exit 1

# Run Huey consumer
CMD ["python", "-m", "huey.bin.huey_consumer", "tasks.tasks.huey"]
