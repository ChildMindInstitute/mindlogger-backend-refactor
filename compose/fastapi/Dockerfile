# ------------------------------
# Stage 1: Build
# ------------------------------
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm AS builder


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="src/"

# Install system dependencies and pipenv
RUN apt update && apt install -y --no-install-recommends \
    build-essential \
    curl \
    libtool \
    autoconf \
    automake \
    pkg-config \
    zlib1g-dev \
    python3-dev \
    ca-certificates \
    git \
    python3-pip \
 && apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir pipenv

# Copy Pipenv files and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv requirements > requirements.txt && \
    pipenv requirements --dev >> requirements.txt && \
    pip wheel --wheel-dir=/wheels -r requirements.txt



# ------------------------------
# Stage 2: Runtime
# ------------------------------
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="src/"

# Startup dependencies
RUN apt update -y && apt install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/

# Add non-root user
RUN adduser --disabled-password --gecos '' code

WORKDIR /app

# Install runtime dependencies from wheelhouse
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

## Copy infrustructure scripts
# Application scripts
COPY --chown=code:code --chmod=775 ./compose/fastapi/entrypoint /fastapi-entrypoint

# Copy to fastapi-start and fastapi-start-datadog to not break current ECS task config
COPY --chown=code:code --chmod=775 ./compose/fastapi/start-backend-datadog /start-backend-datadog

# Migration script
COPY --chown=code:code --chmod=775 ./compose/fastapi/migrate /fastapi-migrate

# ECS
COPY --chown=code:code --chmod=775 ./compose/fastapi/ecs-start /ecs-start
COPY --chown=code:code --chmod=775 ./compose/fastapi/ecs-start-feature /ecs-start-feature

# Scheduler and worker
COPY --chmod=775 --chown=code:code ./compose/fastapi/start-worker /start-worker
COPY --chmod=775 --chown=code:code ./compose/fastapi/start-scheduler /start-scheduler

# Copy app code
COPY --chown=code:code . .

VOLUME /app/uploads /tmp

RUN mkdir -p /app/uploads && \
    chown -R code /app/uploads

# Switch to non-root user
USER code

FROM base AS fargate
# TODO Fargate still can't run as the non-priveleged user.  Likely due to old bind mounts.
USER root

FROM base AS app
# This is a hack to allow Fargate to exist since docker will build the last defined target if none is specified
EXPOSE 8080


# These are down here to prevent cache busting
#ARG DD_GIT_REPOSITORY_URL
#ARG DD_GIT_COMMIT_SHA
#ENV DD_GIT_REPOSITORY_URL=${DD_GIT_REPOSITORY_URL}
#ENV DD_GIT_COMMIT_SHA=${DD_GIT_COMMIT_SHA}
