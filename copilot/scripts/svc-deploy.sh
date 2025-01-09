#!/usr/bin/env bash


echo "Deploying service $COPILOT_SERVICE to $ENV_NAME"

DOCKER_DEFAULT_PLATFORM=linux/arm64 copilot svc deploy \
    --name "$COPILOT_SERVICE" \
    --env "$ENV_NAME" \
    --force \
    --diff-yes