FROM --platform=linux/x86_64 python:3.10.8-slim

ARG PIPENV_EXTRA_ARGS

# https://www.uvicorn.org/settings/
ENV UVICORN_HOST="0.0.0.0"
ENV UVICORN_PORT=80

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="src/"

WORKDIR /app/

RUN apt-get update \
    # dependencies for building Python packages
    && apt-get install -y build-essential \
    # cleaning up unused files
    && rm -rf /var/lib/apt/lists/*

# Add local non-root user to avoid issue with files
# created inside a container being owned by root.
ARG USERNAME=code
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash

# Install Python dependencies
RUN pip install --upgrade pip setuptools pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv sync --system ${PIPENV_EXTRA_ARGS}


# Copy the whole project project
COPY ./ ./

# Run the application
CMD ["alembic", "upgrade", "head", "&&", "uvicorn", "src.main:app", "--proxy-headers"]
