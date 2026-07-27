import os
import logging

logger = logging.getLogger(__name__)

ADMIN_ALIAS = os.environ.get('ADMIN_ALIAS', '')


def handler(event, context):
    """Cognito PreTokenGeneration V1 trigger — injects custom:role into the JWT.

    Midway maps sub (Amazon alias) → email in Cognito attribute mapping,
    so we check the email attribute against ADMIN_ALIAS to determine role.
    """
    user_attributes = event.get('request', {}).get('userAttributes', {})
    amazon_alias = user_attributes.get('custom:amazon_alias', '')

    role = 'admin' if ADMIN_ALIAS and amazon_alias == ADMIN_ALIAS else 'user'

    event['response']['claimsOverrideDetails'] = {
        'claimsToAddOrOverride': {
            'custom:role': role,
        }
    }

    logger.info('PreTokenGeneration: alias=%s role=%s', amazon_alias, role)
    return event
