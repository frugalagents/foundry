import os
import logging

logger = logging.getLogger(__name__)

ADMIN_ALIASES = {
    alias.strip().lower()
    for alias in os.environ.get(
        'ADMIN_ALIASES',
        os.environ.get('ADMIN_ALIAS', ''),
    ).split(',')
    if alias.strip()
}


def handler(event, context):
    """Cognito PreTokenGeneration V1 trigger — injects custom:role into the JWT.

    Midway maps the Amazon alias into a custom Cognito attribute, which is
    matched against the configured admin allowlist.
    """
    user_attributes = event.get('request', {}).get('userAttributes', {})
    amazon_alias = user_attributes.get('custom:amazon_alias', '').strip().lower()

    role = 'admin' if amazon_alias in ADMIN_ALIASES else 'user'

    claims_override = {
        'claimsToAddOrOverride': {
            'custom:role': role,
        }
    }
    if role == 'admin':
        claims_override['groupOverrideDetails'] = {
            'groupsToOverride': ['admin', 'user'],
        }

    event['response']['claimsOverrideDetails'] = claims_override

    logger.info('PreTokenGeneration: alias=%s role=%s', amazon_alias, role)
    return event
