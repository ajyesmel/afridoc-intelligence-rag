#!/usr/bin/env bash
set -euo pipefail
# Requires AWS CLI v2, Docker, access to ECR and App Runner; existing IAM roles + Secrets Manager secrets.
: "${AWS_REGION:=eu-west-3}"
: "${AWS_APP_NAME:=afridoc-api}"
: "${APPRUNNER_ECR_ROLE_ARN:?IAM role granting App Runner access to ECR}"
: "${APPRUNNER_INSTANCE_ROLE_ARN:?IAM runtime role granting secretsmanager:GetSecretValue}"
: "${APP_API_KEY_SECRET_ARN:?Secrets Manager ARN containing the API key}"
: "${DATABASE_URL_SECRET_ARN:?Secrets Manager ARN containing the PostgreSQL URL}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"
aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$AWS_APP_NAME" >/dev/null 2>&1 || \
  aws ecr create-repository --region "$AWS_REGION" --repository-name "$AWS_APP_NAME" >/dev/null
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
IMAGE="$REGISTRY/$AWS_APP_NAME:latest"
docker build -t "$IMAGE" .
docker push "$IMAGE"
export IMAGE AWS_APP_NAME APPRUNNER_ECR_ROLE_ARN APPRUNNER_INSTANCE_ROLE_ARN APP_API_KEY_SECRET_ARN DATABASE_URL_SECRET_ARN GROQ_API_KEY_SECRET_ARN
PAYLOAD=$(mktemp)
trap 'rm -f "$PAYLOAD"' EXIT
python - "$PAYLOAD" <<'EOFJSON'
import os, sys, json
secrets = {'APP_API_KEY': os.environ['APP_API_KEY_SECRET_ARN'], 'DATABASE_URL': os.environ['DATABASE_URL_SECRET_ARN']}
if os.environ.get('GROQ_API_KEY_SECRET_ARN'):
    secrets['GROQ_API_KEY'] = os.environ['GROQ_API_KEY_SECRET_ARN']
config = {'ServiceName': os.environ['AWS_APP_NAME'],
    'SourceConfiguration': {'ImageRepository': {'ImageIdentifier': os.environ['IMAGE'],
      'ImageRepositoryType': 'ECR', 'ImageConfiguration': {'Port': '8000',
      'RuntimeEnvironmentSecrets': secrets}},
      'AuthenticationConfiguration': {'AccessRoleArn': os.environ['APPRUNNER_ECR_ROLE_ARN']},
      'AutoDeploymentsEnabled': True},
    'InstanceConfiguration': {'InstanceRoleArn': os.environ['APPRUNNER_INSTANCE_ROLE_ARN']}}
with open(sys.argv[1], 'w') as file:
    json.dump(config, file)
EOFJSON
ARN=$(aws apprunner list-services --region "$AWS_REGION" \
  --query "ServiceSummaryList[?ServiceName=='$AWS_APP_NAME'].ServiceArn | [0]" --output text)
if [[ -n "$ARN" && "$ARN" != "None" ]]; then
  aws apprunner start-deployment --region "$AWS_REGION" --service-arn "$ARN"
else
  aws apprunner create-service --region "$AWS_REGION" --cli-input-json "file://$PAYLOAD" \
    --query 'Service.ServiceArn' --output text
fi
