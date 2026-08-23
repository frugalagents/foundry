#!/usr/bin/env bash
# Provision a native Cognito login for foundry-app.
#
# New users receive Cognito's temporary-password invitation email.
# Existing Federate-only users are converted in place so their Cognito sub
# (and therefore ownership of existing Foundry records) is preserved. They can
# then use "Forgot password" on the Cognito login page to choose a password.
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
user_status="$(jq -r '.Users[0].UserStatus // empty' <<<"$existing_user")"

if [[ -z "$username" ]]; then
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$EMAIL" \
    --user-attributes \
      "Name=email,Value=$EMAIL" \
      "Name=email_verified,Value=true" \
    --desired-delivery-mediums EMAIL \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'User.{Username:Username,Status:UserStatus}' \
    --output table

  echo "Cognito emailed a temporary password to $EMAIL."
  echo "The user must choose a new password on first sign-in."
  exit 0
fi

if [[ "$user_status" == "EXTERNAL_PROVIDER" ]]; then
  generated_password="$(openssl rand -hex 16)Aa1"
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$USER_POOL_ID" \
    --username "$username" \
    --password "$generated_password" \
    --permanent \
    --profile "$PROFILE" \
    --region "$REGION"
  unset generated_password

  echo "Converted $EMAIL to native Cognito login without changing its user identity."
  echo "Use 'Forgot password' on the login page to choose a password."
  exit 0
fi

if [[ "$user_status" == "FORCE_CHANGE_PASSWORD" ]]; then
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$username" \
    --message-action RESEND \
    --desired-delivery-mediums EMAIL \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'User.{Username:Username,Status:UserStatus}' \
    --output table

  echo "Cognito resent the temporary password to $EMAIL."
  exit 0
fi

echo "$EMAIL already has a native Cognito account with status $user_status."
echo "Use 'Forgot password' on the login page if the password is unknown."
