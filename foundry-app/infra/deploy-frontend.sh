#!/usr/bin/env bash
# Build Next.js and deploy to S3 + CloudFront.
# Reads stack outputs to get bucket/distribution IDs automatically.
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$INFRA_DIR/../frontend"
STACK="${STACK:-foundry-app-dev}"
PROFILE="${PROFILE:-platform-advisor}"
REGION="${REGION:-us-east-1}"

stack_output() {
  local key="$1"
  aws cloudformation describe-stacks \
    --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='${key}'].OutputValue" \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION"
}

stack_parameter() {
  local key="$1"
  aws cloudformation describe-stacks \
    --stack-name "$STACK" \
    --query "Stacks[0].Parameters[?ParameterKey=='${key}'].ParameterValue" \
    --output text \
    --profile "$PROFILE" \
    --region "$REGION"
}

echo "→ Fetching stack outputs"
API_URL=$(stack_output "ApiUrl")
BUCKET=$(stack_output "FrontendBucketName")
DIST_ID=$(stack_output "FrontendDistributionId")
CF_URL=$(stack_output "FrontendURL")
COGNITO_CLIENT_ID=$(stack_output "BrowserAuthClientId")

if [[ -z "$COGNITO_CLIENT_ID" || "$COGNITO_CLIENT_ID" == "None" ]]; then
  COGNITO_CLIENT_ID=$(stack_output "UserPoolClientId")
fi

COGNITO_DOMAIN=$(stack_output "CognitoDomain")
GUEST_ACCESS_EXPIRES_AT=$(stack_output "GuestAccessExpiresAtValue")
IDENTITY_POOL_ID=$(stack_output "IdentityPoolId")
USER_POOL_ID="${USER_POOL_ID:-$(stack_output "UserPoolId")}"
if [[ -z "$USER_POOL_ID" || "$USER_POOL_ID" == "None" ]]; then
  USER_POOL_ID=$(stack_parameter "UserPoolId")
fi

AGENTCORE_RUNTIME_ARN="${AGENTCORE_RUNTIME_ARN:-$(stack_output "AgentCoreRuntimeArn")}"
if [[ -z "$AGENTCORE_RUNTIME_ARN" || "$AGENTCORE_RUNTIME_ARN" == "None" ]]; then
  AGENTCORE_RUNTIME_ARN=$(stack_parameter "AgentCoreRuntimeArn")
fi
if [[ -z "$AGENTCORE_RUNTIME_ARN" || "$AGENTCORE_RUNTIME_ARN" == "None" ]]; then
  AGENTCORE_RUNTIME_ARN=$(stack_parameter "AgentCoreEndpointArn")
fi

require_value() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "✗ Missing required deploy value: $name" >&2
    echo "  Check stack outputs on $STACK or override via environment variable." >&2
    exit 1
  fi
}

require_value "ApiUrl" "$API_URL"
require_value "FrontendBucketName" "$BUCKET"
require_value "FrontendDistributionId" "$DIST_ID"
require_value "FrontendURL" "$CF_URL"
require_value "BrowserAuthClientId/UserPoolClientId" "$COGNITO_CLIENT_ID"
require_value "CognitoDomain" "$COGNITO_DOMAIN"
require_value "IdentityPoolId" "$IDENTITY_POOL_ID"
require_value "UserPoolId" "$USER_POOL_ID"
require_value "AgentCoreRuntimeArn" "$AGENTCORE_RUNTIME_ARN"

echo "  API_URL:          $API_URL"
echo "  S3 Bucket:        $BUCKET"
echo "  CF Dist:          $DIST_ID"
echo "  CF URL:           $CF_URL"
echo "  Cognito Client:   $COGNITO_CLIENT_ID"
echo "  Cognito Domain:   $COGNITO_DOMAIN"
echo "  Identity Pool:    $IDENTITY_POOL_ID"
echo "  Guest cutoff:     $GUEST_ACCESS_EXPIRES_AT"

echo "  User Pool ID:     $USER_POOL_ID"
echo "  AgentCore ARN:    $AGENTCORE_RUNTIME_ARN"

echo "→ Building Next.js (static export)"
cd "$FRONTEND_DIR"
rm -rf .next out
NEXT_PUBLIC_API_URL="$API_URL" \
  NEXT_PUBLIC_APP_URL="$CF_URL" \
  NEXT_PUBLIC_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
  NEXT_PUBLIC_COGNITO_DOMAIN="$COGNITO_DOMAIN" \
  NEXT_PUBLIC_GUEST_ACCESS_EXPIRES_AT="$GUEST_ACCESS_EXPIRES_AT" \
  NEXT_PUBLIC_GUEST_GROUP_NAME="foundry-guests" \
  NEXT_PUBLIC_IDENTITY_POOL_ID="$IDENTITY_POOL_ID" \
  NEXT_PUBLIC_USER_POOL_ID="$USER_POOL_ID" \
  NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN="$AGENTCORE_RUNTIME_ARN" \
  NEXT_PUBLIC_AWS_REGION="$REGION" \
  npm run build

SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/foundry-frontend.XXXXXX")"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

echo "→ Snapshotting export output"
rsync -a --delete out/ "$SNAPSHOT_DIR"/

echo "→ Syncing to S3"
aws s3 sync "$SNAPSHOT_DIR"/ "s3://$BUCKET" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.txt" \
  --no-progress \
  --profile "$PROFILE"

aws s3 sync "$SNAPSHOT_DIR"/ "s3://$BUCKET" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --exclude "*" \
  --include "*.txt" \
  --no-progress \
  --profile "$PROFILE"

aws s3 sync "$SNAPSHOT_DIR"/ "s3://$BUCKET" \
  --delete \
  --cache-control "no-cache, no-store, must-revalidate" \
  --exclude "*" \
  --include "*.html" \
  --no-progress \
  --profile "$PROFILE"

echo "→ Invalidating CloudFront"
aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*" \
  --profile "$PROFILE"

echo ""
echo "✓ Frontend deployed to $CF_URL"
