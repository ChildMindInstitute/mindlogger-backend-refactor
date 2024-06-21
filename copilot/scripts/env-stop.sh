#!/usr/bin/env bash

#if [ "$CI_COMMIT_REF_SLUG" == 'main' ]; then ENV="dev"; else ENV=$CI_COMMIT_REF_SLUG; fi

#if [ "$CI_MERGE_REQUEST_TARGET_BRANCH_NAME" == 'main' ]; then printf "Target branch is main.\n"; else printf "Target branch is not main.\n" && return 1; fi

if copilot env ls | grep -q "$ENV_NAME"; then

    echo "Deleting $COPILOT_SERVICE in env $ENV_NAME:"
    copilot svc delete --name $COPILOT_SERVICE --env $ENV_NAME --yes

    echo "Deleting environment $ENV_NAME"
    copilot env delete \
        --name "$ENV_NAME" \
        --yes
else
    echo "Environment doesn't exists!"
    exit 0
fi

