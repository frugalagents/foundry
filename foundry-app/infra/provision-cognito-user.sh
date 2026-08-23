#!/usr/bin/env bash
# Emergency native Cognito user provisioning for foundry-app.
#
# Normal onboarding uses the public Request access page and admin approval.
# This helper is intentionally limited to brand-new email addresses. It never
# converts a Federate user in place because those users retain a Midway-prefixed
# username that cannot reliably sign in with the mapped email address.
set -euo pipefail

EMAIL="${1:-}"
PROFILE="${AWS_PROFILE:-platform-advisor}"
REGION="${AWS_REGION:-us-east-1}"
USER_POOL_ID="${COGNITO_USER_POOL_ID:-us-east-1_oSEwvKdfd}"

if [[ ! "$EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo "Usage: $0 user@example.com" >&2
  exit 2
fi

command -v aws >/dev/null || {
  echo "ERROR: aws CLI is required." >&2
  exit 1
}
command -v jq >/dev/null || {
  echo "ERROR: jq is required." >&2
  exit 1
}
command -v openssl >/dev/null || {
  echo "ERROR: openssl is required." >&2
  exit 1
}

existing_user="$(
  aws cognito-idp list-users \
    --user-pool-id "$USER_POOL_ID" \
    --filter "email = \"$EMAIL\"" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --output json
)"

username="$(jq -r '.Users[0].Username // empty' <<<"$existing_user")"
if [[ -n "$username" ]]; then
  echo "ERROR: A Cognito user already exists for $EMAIL as $username." >&2
  echo "Do not convert Federate users in place. Use the access-request workflow or migrate the identity explicitly." >&2
  exit 1
fi

temporary_password="Foundry-$(openssl rand -hex 8)Aa1!"
created="$(
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$EMAIL" \
    --temporary-password "$temporary_password" \
    --message-action SUPPRESS \
    --user-attributes \
      "Name=email,Value=$EMAIL" \
      "Name=email_verified,Value=true" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --output json
)"

created_username="$(jq -r '.User.Username' <<<"$created")"
echo "Created native Cognito user: $created_username"
echo "Email login: $EMAIL"
echo "One-time password: $temporary_password"
echo "Cognito will require a new password at first sign-in."
