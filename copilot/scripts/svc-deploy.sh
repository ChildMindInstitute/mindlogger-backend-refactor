#!/usr/bin/env bash


echo "Deploying service $COPILOT_SERVICE to $ENV_NAME"

copilot svc deploy \
    --name "$COPILOT_SERVICE" \
    --env "$ENV_NAME" \
    --force \
    --diff-yes