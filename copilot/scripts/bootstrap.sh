#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. ${SCRIPT_DIR}/funcs.sh

DEV_ENV_NAME=${DEV_ENV_NAME:-dev}

if [[ -z "$APP_NAME" ]]; then
  echo "APP_NAME must be set"
fi

if [[ -z "$DEV_VPC_ID" ]]; then
  echo "VPC_ID must be set"
fi

if [[ -z "$DEV_PROFILE" ]]; then
  echo "DEV_PROFILE must be set"
fi

copilot app init "$APP_NAME"
# --domain cmiml.net

get_public_subnets "$DEV_VPC_ID"
export DEV_PUBLIC_SUBNETS="$retval"

get_private_subnets "$DEV_VPC_ID"
export DEV_PRIVATE_SUBNETS="$retval"

#query='Subnets[?MapPublicIpOnLaunch==`false`].SubnetId'
#get_subnets "$DEV_VPC_ID" "$query" "$DEV_PROFILE"
#export DEV_PRIVATE_SUBNETS="$retval"
#
#query='Subnets[?AssignIpv6AddressOnCreation==`true`].SubnetId'
#get_subnets "$DEV_VPC_ID" "$query" "$DEV_PROFILE"
#export DEV_PUBLIC_SUBNETS="$retval"

echo "DEV VPC_ID: $DEV_VPC_ID"
echo "DEV PUBLIC_SUBNETS: $DEV_PUBLIC_SUBNETS"
echo "DEV PRIVATE_SUBNETS: $DEV_PRIVATE_SUBNETS"

copilot env init --app "$APP_NAME" --name "$DEV_ENV_NAME" --profile "$DEV_PROFILE" \
 --import-public-subnets $DEV_PUBLIC_SUBNETS --import-private-subnets $DEV_PRIVATE_SUBNETS \
 --import-vpc-id $DEV_VPC_ID \
 --container-insights

# --import-cert-arns arn:aws:acm:us-east-1:017925157769:certificate/d58df2e9-1c16-42ed-9923-cf9fc2fd588c \

copilot env deploy --name "$DEV_ENV_NAME"

copilot svc init --app "$APP_NAME" --name "mindlogger-backend" --svc-type "Load Balanced Web Service" --ingress-type "Internet" -d "compose/fastapi/Dockerfile"
copilot svc deploy --name "mindlogger-backend" --env "$DEV_ENV_NAME"


