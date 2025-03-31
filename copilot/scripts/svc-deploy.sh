#!/usr/bin/env bash


echo "Deploying service $COPILOT_SERVICE to $ENV_NAME"

copilot svc deploy \
    --name "$COPILOT_SERVICE" \
    --env "$ENV_NAME" \
    --force \
    --diff-yes

PR_NUM=${ENV_NAME}

# Add Datadog tags to ALB
echo "Working with ${PR_NUM}"
ALL_ALBS=$(aws elbv2 describe-load-balancers --query "LoadBalancers[*].LoadBalancerArn" --output text | tr '\t' ' ')
ALB_ARNS=$(IFS=, ; echo "${ALL_ALBS[*]}")

for ALB in ${ALB_ARNS}; do
  ARN=$(aws elbv2 describe-tags --resource-arns ${ALB} --query "TagDescriptions[?Tags[?Key=='copilot-environment' && Value=='${PR_NUM}']].ResourceArn" --output text)

  if [ -n "${ARN}" ]; then
    echo "ALB ARN: ${ARN}"

    DD_VERSION="${PR_NUM}"
    aws elbv2 add-tags \
      --resource-arns "${ARN}" \
      --tags Key=env,Value=feature Key=service,Value=backend-api Key=version,Value="${DD_VERSION}"

    # GDPR and HIPAA security group rules
    ALB_SG_ID=$(aws elbv2 describe-load-balancers --load-balancer-arns "${ARN}" --query "LoadBalancers[*].[SecurityGroups]" --output text)

    CLUSTERS=$(aws ecs list-clusters --query "clusterArns" --output text)
    for CLUSTER in ${CLUSTERS}; do
      TAGS=$(aws ecs list-tags-for-resource --resource-arn ${CLUSTER} --query "tags[?key=='copilot-environment' && value=='${PR_NUM}']" --output text)

      if [ -n "${TAGS}" ]; then
        echo "Cluster ARN: ${CLUSTER}"
        SERVICE_ARN=$(aws ecs list-services --cluster "${CLUSTER}" --query "serviceArns[0]" --output text)
        SGS=$(aws ecs describe-services --cluster "${CLUSTER}" --service "${SERVICE_ARN}"  --query "services[0].networkConfiguration.awsvpcConfiguration.securityGroups" --output text)

        for SG in ${SGS}; do
          if [[ "${SG}" = "sg-0fe1e219a0c0c5afb" ]]; then continue; fi
          echo "Processing Security group: ${SG}, limiting access from ${ALB_SG_ID}"
          echo "Removing existing inbound rules"
          IP_PERMS=$(aws ec2 describe-security-groups --group-ids "${SG}" --query "SecurityGroups[0].IpPermissions" --output json)

          aws ec2 revoke-security-group-ingress --group-id "${SG}" --ip-permissions "${IP_PERMS}" > /dev/null

          echo "Creating new ingress rules"
          # Health check
          aws ec2 authorize-security-group-ingress \
            --group-id "${SG}" \
            --protocol tcp \
            --port 1024-65535 \
            --source-group "${ALB_SG_ID}" > /dev/null
          # App
          aws ec2 authorize-security-group-ingress \
              --group-id "${SG}" \
              --protocol tcp \
              --port 80 \
              --source-group "${ALB_SG_ID}" > /dev/null
        done
      fi
    done
  fi
done
