# Foundry authentication

`foundry-app` uses native Amazon Cognito email/password accounts. Its Cognito
app client supports only the `COGNITO` identity provider, so login does not
depend on Amazon Federate or Midway.

The Cognito user pool is shared with Platform Advisor. Other app clients may
continue to use Federate; this app-client change does not remove or modify the
shared Midway identity provider.

## Create or enable a user

From `foundry-app`:

```bash
./infra/provision-cognito-user.sh user@example.com
```

- A new user receives an email containing a temporary password.
- An existing Federate-only user is converted in place to native Cognito
  login, preserving the Cognito `sub` used to own Foundry records. The user
  selects **Forgot password** on the Cognito login page to choose a password.
- An existing native user remains unchanged.

Self-registration stays disabled. Administrators control who can access the
application by provisioning users with this command.
