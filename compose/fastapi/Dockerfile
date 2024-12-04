FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="src/"

WORKDIR /app/

RUN apt-get -y update && apt-get -y upgrade \
    && apt-get install --no-install-recommends -y build-essential curl libffi-dev \
    && rm -rf /var/lib/apt/lists/

# Add local non-root user to avoid issue with files
# created inside a container being owned by root.
ARG USERNAME=code
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash

# Install Python dependencies
RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./
ARG PIPENV_EXTRA_ARGS
RUN pipenv sync --system ${PIPENV_EXTRA_ARGS}


# Copy the whole project project
COPY ./ ./

# Copy infrustructure scripts

# Application scripts
COPY --chown=code:code ./compose/fastapi/entrypoint /fastapi-entrypoint
RUN sed -i 's/\r$//g' /fastapi-entrypoint && chmod +x /fastapi-entrypoint

COPY --chown=code:code ./compose/fastapi/start /fastapi-start
RUN sed -i 's/\r$//g' /fastapi-start && chmod +x /fastapi-start

COPY --chown=code:code ./compose/fastapi/start-datadog /fastapi-start-datadog
RUN sed -i 's/\r$//g' /start-datadog && chmod +x /fastapi-start-datadog



COPY --chown=code:code ./compose/fastapi/migrate /fastapi-migrate
RUN sed -i 's/\r$//g' /fastapi-migrate && chmod +x /fastapi-migrate

COPY --chown=code:code ./compose/fastapi/ecs-start /fastapi-ecs-start
RUN sed -i 's/\r$//g' /ecs-start && chmod +x /fastapi-ecs-start

COPY --chown=code:code ./compose/fastapi/ecs-start-feature /fastapi-ecs-start-feature
RUN sed -i 's/\r$//g' /ecs-start-feature && chmod +x /fastapi-ecs-start-feature

# Select internal user
USER code

FROM base AS fargate
# Hack for Fargate
# https://github.com/aws/containers-roadmap/issues/938
USER root
RUN chmod 777 /tmp && mkdir -p /app/uploads && chown -R code:code /app
#USER code

RUN touch /app/uploads/.test
RUN touch /tmp/.test

VOLUME ["/tmp"]
VOLUME ["/app/uploads"]

# worker instructions
FROM base AS worker

USER root
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/

USER code
