#!/usr/bin/env bash
# Build Next.js and deploy to S3 + CloudFront.
# Reads stack outputs to get bucket/distribution IDs automatically.
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$INFRA_DIR/../frontend"
STACK="foundry-app-dev"
PROFILE="platform-advisor"
REGION="us-east-1"

echo "→ Fetching stack outputs"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendDistributionId'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

CF_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

COGNITO_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoDomain'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

IDENTITY_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='IdentityPoolId'].OutputValue" \
  --output text \
  --profile "$PROFILE" \
  --region "$REGION")

echo "  API_URL:          $API_URL"
echo "  S3 Bucket:        $BUCKET"
echo "  CF Dist:          $DIST_ID"
echo "  CF URL:           $CF_URL"
echo "  Cognito Client:   $COGNITO_CLIENT_ID"
echo "  Cognito Domain:   $COGNITO_DOMAIN"
echo "  Identity Pool:    $IDENTITY_POOL_ID"

USER_POOL_ID="us-east-1_oSEwvKdfd"
AGENTCORE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/CodingAgentRuntime_CodingAgentRuntime-TOiVHpGwhu"

echo "  User Pool ID:     $USER_POOL_ID"
echo "  AgentCore ARN:    $AGENTCORE_RUNTIME_ARN"

echo "→ Building Next.js (static export)"
cd "$FRONTEND_DIR"
NEXT_PUBLIC_API_URL="$API_URL" \
  NEXT_PUBLIC_APP_URL="$CF_URL" \
  NEXT_PUBLIC_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
  NEXT_PUBLIC_COGNITO_DOMAIN="$COGNITO_DOMAIN" \
  NEXT_PUBLIC_IDENTITY_POOL_ID="$IDENTITY_POOL_ID" \
  NEXT_PUBLIC_USER_POOL_ID="$USER_POOL_ID" \
  NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN="$AGENTCORE_RUNTIME_ARN" \
  NEXT_PUBLIC_AWS_REGION="$REGION" \
  npm run build

echo "→ Syncing to S3"
aws s3 sync out/ "s3://$BUCKET" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --profile "$PROFILE"

aws s3 sync out/ "s3://$BUCKET" \
  --delete \
  --cache-control "no-cache, no-store, must-revalidate" \
  --include "*.html" \
  --profile "$PROFILE"

echo "→ Invalidating CloudFront"
aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*" \
  --profile "$PROFILE"

echo ""
echo "✓ Frontend deployed to $CF_URL"
