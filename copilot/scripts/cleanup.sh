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


copilot svc delete service-b
copilot svc delete service-a
copilot env delete dev
copilot app delete "$APP_NAME"
rm -rf copilot