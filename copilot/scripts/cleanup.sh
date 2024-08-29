#!/usr/bin/env bash


#for env in $(copilot env ls --json | jq -r '.environments[] | .name'); do
#
#  for svc in $(copilot svc ls --json | jq -r '.services[] | .name'); do
#    echo "Deleting service $svc"
#    copilot svc delete -e $env $svc
#  done
#
#  copilot delete env $env
#done

#
#copilot svc delete service-b
#copilot svc delete service-a
#copilot env delete dev
#copilot app delete "$APP_NAME"
#rm -rf copilot

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export COPILOT_SERVICE=mindlogger-backend


for PR_NUM in $(aws ecs list-clusters  --output text | grep -E -o 'pr\-[0-9]+' | grep -E -o '[0-9]+'); do
  echo "> Checking pull request: $PR_NUM"
  PR_STATE=$(gh pr view $PR_NUM --json state | jq -r .state)
  echo "=> State: $PR_STATE"

  if [ "$PR_STATE" != "OPEN" ]; then
    echo "=> Shutting down preview env"
    export ENV_NAME="pr-$PR_NUM"
    ./copilot/scripts/env-stop.sh
    aws secretsmanager delete-secret --secret-id "cmiml-feature-pr-$PR_NUM" --force-delete-without-recovery --no-cli-pager
  else
    echo "=> No action needed"
  fi
  echo
done