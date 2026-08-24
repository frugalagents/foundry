# Foundry authentication

`foundry-app` should support two distinct entry paths on the same Cognito user pool:

1. Internal Amazon users: default app entry goes straight to Cognito Hosted UI for enterprise SSO.
2. External guests: separate guest entry point through native Cognito accounts.

The important boundary is that internal users should not be forced into the
native Cognito username/password flow just because guest access exists.

## Internal login

- Default app URL: `/`
- Behavior: protected routes immediately redirect to Cognito Hosted UI and follow the existing enterprise SSO path
- Manual internal entry point: `/login/`
- Result: Cognito still issues the app token, so the API and browser runtime continue to trust a single token issuer

## Guest login

- Guest entry point: `/login/?mode=guest`
- Intended use: event access, external evaluators
- Behavior: routes to native Cognito sign-in instead of Midway
- Current onboarding path: `/request-access/` for admin-approved guest access
- Optional event control: set `GuestAccessExpiresAt` so the guest entry point, guest request flow, and guest API access all stop after the configured cutoff

## Operational guidance

- QR codes for events should point to `/login/?mode=guest`, not the default app URL.
- Keep guest accounts time-bounded and administrator-managed.
- If you later add a 24-hour invite or passwordless flow, build it on top of the guest path rather than changing the default internal login path.
