#!/usr/bin/env bash


if [ ! -f copilot/environments/$ENV_NAME/manifest.yml ]; then
  # This is done in case the deploy failed but the env init succeeded on a previous run
  # The manifest may not exist
  mkdir -p copilot/environments/$ENV_NAME
  copilot env show -n $ENV_NAME --manifest > copilot/environments/$ENV_NAME/manifest.yml
fi

#Copilot checks if there are changes automatically
copilot env deploy \
    --name "$ENV_NAME" \
    --force \
    --diff-yes