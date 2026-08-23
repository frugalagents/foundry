# Foundry authentication

`foundry-app` uses native Amazon Cognito email/password accounts. Its Cognito
app client supports only the `COGNITO` identity provider, so login does not
depend on Amazon Federate or Midway.

The Cognito user pool is shared with Platform Advisor. Other app clients may
continue to use Federate; this app-client change does not remove or modify the
shared Midway identity provider.

## Standard onboarding

1. The user opens `/request-access/`.
2. The user submits their name, email, and reason for access.
3. The request appears in **Admin Console → Access requests**. An SNS email is
   also sent after the administrator confirms the topic subscription.
4. An administrator approves or rejects the request.
5. Approval creates a native Cognito account with Cognito email delivery
   suppressed.
6. The user's saved request page changes to a password-activation form.
7. The user sets a permanent password and signs in with their email.

The browser stores a private request token locally. DynamoDB stores only its
SHA-256 hash, and access-request records expire after seven days using TTL.

## Emergency administrator provisioning

The normal path is the approval workflow. For a brand-new email address only:

```bash
./infra/provision-cognito-user.sh user@example.com
```

The command prints a one-time password and Cognito requires the user to replace
it during first sign-in. The helper refuses to modify existing or
Federate-derived users.
