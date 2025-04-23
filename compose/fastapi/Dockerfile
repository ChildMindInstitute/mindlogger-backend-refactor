# ------------------------------
# Stage 1: Build
# ------------------------------
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm AS builder

ENV LIBXML2_VERSION=2.13.8

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="src/"

# Install system dependencies and pipenv
RUN apt-get update && apt-get install -y --no-install-recommends \
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
 && apt-get clean && rm -rf /var/lib/apt/lists/*


## CVE CVE-2025-24928
WORKDIR /opt

# Download and build libxml2
RUN curl -LO https://download.gnome.org/sources/libxml2/2.13/libxml2-${LIBXML2_VERSION}.tar.xz && \
    tar -xf libxml2-${LIBXML2_VERSION}.tar.xz && \
    cd libxml2-${LIBXML2_VERSION} && \
    ./configure --prefix=/usr --with-python=/usr/bin/python3 && \
    make -j"$(nproc)" && \
    make install
## CVE CVE-2025-24928

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
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

## CVE CVE-2025-24928
# Remove system libxml2 to eliminate CVE exposure
RUN apt-get update && apt-get remove -y libxml2 libxml2-dev && apt-get autoremove -y && apt-get clean

# Copy libxml2 from builder
COPY --from=builder /usr /usr

# Add libxml2 to library path
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    CPATH=/usr/local/include:$CPATH \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
## CVE CVE-2025-24928

# Worker and startup dependencies
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    imagemagick \
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
COPY --chown=code:code ./compose/fastapi/entrypoint /fastapi-entrypoint
RUN sed -i 's/\r$//g' /fastapi-entrypoint && chmod +x /fastapi-entrypoint

# Copy to fastapi-start and fastapi-start-datadog to not break current ECS task config
COPY --chown=code:code ./compose/fastapi/start-backend-datadog /start-backend-datadog
RUN sed -i 's/\r$//g' /start-backend-datadog && chmod +x /start-backend-datadog && \
    cp /start-backend-datadog /fastapi-start && cp /start-backend-datadog /fastapi-start-datadog

# Migration script
COPY --chown=code:code ./compose/fastapi/migrate /fastapi-migrate
RUN sed -i 's/\r$//g' /fastapi-migrate && chmod +x /fastapi-migrate

# ECS
COPY --chown=code:code ./compose/fastapi/ecs-start /ecs-start
RUN sed -i 's/\r$//g' /ecs-start && chmod +x /ecs-start

COPY --chown=code:code ./compose/fastapi/ecs-start-feature /ecs-start-feature
RUN sed -i 's/\r$//g' /ecs-start-feature && chmod +x /ecs-start-feature

# Scheduler and worker
COPY --chown=code:code ./compose/fastapi/start-worker /start-worker
RUN sed -i 's/\r$//g' /start-worker && chmod +x /start-worker

COPY --chown=code:code ./compose/fastapi/start-scheduler /start-scheduler
RUN sed -i 's/\r$//g' /start-worker && chmod +x /start-scheduler

# Copy app code
COPY . .

# Switch to non-root user
USER code

# These are down here to prevent cache busting
ARG DD_GIT_REPOSITORY_URL
ARG DD_GIT_COMMIT_SHA
ENV DD_GIT_REPOSITORY_URL=${DD_GIT_REPOSITORY_URL}
ENV DD_GIT_COMMIT_SHA=${DD_GIT_COMMIT_SHA}
