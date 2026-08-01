import os
import logging
import json

logger = logging.getLogger(__name__)

ADMIN_GROUP = os.environ.get('ADMIN_GROUP', 'admin').strip().lower()
ADMIN_ALIAS_MIGRATION_ENABLED = (
    os.environ.get('ADMIN_ALIAS_MIGRATION_ENABLED', 'false').lower() == 'true'
)
ADMIN_ALIASES = {
    alias.strip().lower()
    for alias in os.environ.get('ADMIN_ALIASES', '').split(',')
    if alias.strip()
}


def handler(event, context):
    """Cognito PreTokenGeneration V1 trigger — injects custom:role into the JWT.

    Administration is derived only from Cognito group membership, which is
    managed by administrators and cannot be self-asserted through user
    attributes.
    """
    request = event.get('request', {})
    group_configuration = request.get('groupConfiguration') or {}
    configured_groups = group_configuration.get('groupsToOverride') or []
    if isinstance(configured_groups, str):
        configured_groups = [configured_groups]
    groups = {
        str(group).strip().lower()
        for group in configured_groups
        if str(group).strip()
    }
    user_attributes = request.get('userAttributes') or {}
    amazon_alias = str(
        user_attributes.get('custom:amazon_alias') or ''
    ).strip().lower()
    username = str(
        event.get('userName')
        or user_attributes.get('cognito:username')
        or ''
    ).strip().lower()
    try:
        identities = json.loads(user_attributes.get('identities') or '[]')
    except (TypeError, json.JSONDecodeError):
        identities = []
    midway_subjects = {
        str(identity.get('userId') or '').strip().lower()
        for identity in identities
        if str(identity.get('providerName') or '').strip().lower() == 'midway'
    } - {''}
    verified_migration_identities = {username} - {''}
    if amazon_alias in midway_subjects:
        verified_migration_identities.add(amazon_alias)

    group_admin = bool(ADMIN_GROUP and ADMIN_GROUP in groups)
    migration_admin = bool(
        ADMIN_ALIAS_MIGRATION_ENABLED
        and ADMIN_ALIASES.intersection(verified_migration_identities)
    )
    role = 'admin' if group_admin or migration_admin else 'user'

    claims_override = {
        'claimsToAddOrOverride': {
            'custom:role': role,
        }
    }

    event.setdefault('response', {})['claimsOverrideDetails'] = claims_override

    logger.info(
        'PreTokenGeneration: admin_group_member=%s migration_fallback=%s role=%s',
        group_admin,
        migration_admin,
        role,
    )
    return event
