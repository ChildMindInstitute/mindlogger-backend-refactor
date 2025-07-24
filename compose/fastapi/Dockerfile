# ------------------------------
# Stage 1: Build
# ------------------------------
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.12

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# ------------------------------
# Stage 2: Runtime
# ------------------------------
FROM debian:bookworm-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="src/"
    
WORKDIR /app

# Startup dependencies
RUN apt update -y && apt install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/

# Add non-root user
RUN adduser --disabled-password --gecos '' app

# Copy the Python version
COPY --from=builder --chown=python:python /python /python

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

## Copy infrustructure scripts
# Application scripts
COPY --chown=app:app --chmod=775 ./compose/fastapi/entrypoint /fastapi-entrypoint

# Copy to fastapi-start and fastapi-start-datadog to not break current ECS task config
COPY --chown=app:app --chmod=775 ./compose/fastapi/start-backend-datadog /start-backend-datadog
COPY --chown=app:app --chmod=775 ./compose/fastapi/start-backend-datadog /fastapi-start-datadog

# Migration script
COPY --chown=app:app --chmod=775 ./compose/fastapi/migrate /fastapi-migrate

# ECS
COPY --chown=app:app --chmod=775 ./compose/fastapi/ecs-start /ecs-start
COPY --chown=app:app --chmod=775 ./compose/fastapi/ecs-start-feature /ecs-start-feature

# Scheduler and worker
COPY --chmod=775 --chown=app:app ./compose/fastapi/start-worker /start-worker
COPY --chmod=775 --chown=app:app ./compose/fastapi/start-scheduler /start-scheduler

# Copy app code
#COPY --chown=app:app . .

VOLUME /app/uploads /tmp

RUN mkdir -p /app/uploads && \
    chown -R app /app/uploads



# Switch to non-root user
USER app

# These are down here to prevent cache busting
ARG DD_GIT_REPOSITORY_URL
ARG DD_GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=${DD_GIT_REPOSITORY_URL}
ENV DD_GIT_COMMIT_SHA=${DD_GIT_COMMIT_SHA}


FROM base AS fargate
# TODO Fargate still can't run as the non-priveleged user.  Likely due to old bind mounts.
USER root

VOLUME ["/tmp"]
VOLUME ["/app/uploads"]


FROM base AS app
# This is a hack to allow Fargate to exist since docker will build the last defined target if none is specified
EXPOSE 8000


