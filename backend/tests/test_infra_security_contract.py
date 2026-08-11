from __future__ import annotations

from pathlib import Path
import json
import re

import yaml


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "infra" / "template.yaml"
REPO_ROOT = TEMPLATE_PATH.parents[1]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
AGENTCORE_CONFIG_PATH = (
    REPO_ROOT / "PlatformAdvisorAgent" / "agentcore" / "agentcore.json"
)
KNOWLEDGE_RELEASE_MANIFEST_PATH = (
    REPO_ROOT
    / "knowledge"
    / "releases"
    / "coding-platform"
    / "1.3.0"
    / "manifest.json"
)


class _CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_intrinsic(loader, _tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


_CloudFormationLoader.add_multi_constructor("!", _construct_intrinsic)


def _template() -> dict:
    with TEMPLATE_PATH.open(encoding="utf-8") as template_file:
        return yaml.load(template_file, Loader=_CloudFormationLoader)


def test_http_api_requires_cognito_jwt_by_default():
    template = _template()
    http_api = template["Resources"]["HttpApi"]["Properties"]
    auth = http_api["Auth"]
    authorizer = auth["Authorizers"]["CognitoAuthorizer"]

    assert auth["DefaultAuthorizer"] == "CognitoAuthorizer"
    assert authorizer["IdentitySource"] == "$request.header.Authorization"
    assert authorizer["JwtConfiguration"]["audience"] == ["UserPoolClient"]
    assert authorizer["JwtConfiguration"]["issuer"] == (
        "https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}"
    )


def test_only_health_and_cors_preflight_opt_out_of_default_authorizer():
    template = _template()
    events = template["Resources"]["AdvisorFunction"]["Properties"]["Events"]

    assert events["HealthCheck"]["Properties"]["Auth"] == {"Authorizer": "NONE"}
    assert events["CorsPreflight"]["Properties"] == {
        "ApiId": "HttpApi",
        "Path": "/{proxy+}",
        "Method": "OPTIONS",
        "Auth": {"Authorizer": "NONE"},
    }
    assert "Auth" not in events["ApiProxy"]["Properties"]
    assert events["ApiProxy"]["Properties"]["Path"] == "/{proxy+}"
    assert events["ApiProxy"]["Properties"]["Method"] == "ANY"
    assert not any(
        event["Properties"].get("Path", "").endswith("/run")
        for event in events.values()
    )


def test_agentcore_invoke_is_disabled_until_runtime_arn_is_configured():
    template = _template()

    parameter = template["Parameters"]["AgentCoreRuntimeArn"]
    assert parameter["Default"] == ""
    assert re.fullmatch(
        parameter["AllowedPattern"],
        "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/Advisor_runtime-123",
    )
    assert re.fullmatch(parameter["AllowedPattern"], "")
    assert not re.fullmatch(parameter["AllowedPattern"], "*")
    assert template["Conditions"]["HasAgentCoreRuntimeArn"] == [
        ["AgentCoreRuntimeArn", ""]
    ]


def test_agentcore_invoke_permission_is_scoped_to_configured_runtime():
    template = _template()
    policies = template["Resources"]["IdentityPoolAuthRole"]["Properties"]["Policies"]
    condition_name, policy, no_value = policies[0]
    statement = policy["PolicyDocument"]["Statement"][0]

    assert condition_name == "HasAgentCoreRuntimeArn"
    assert no_value == "AWS::NoValue"
    assert statement["Action"] == [
        "bedrock-agentcore:InvokeAgentRuntime",
        "bedrock-agentcore:InvokeAgentRuntimeForUser",
    ]
    assert statement["Resource"] == "AgentCoreRuntimeArn"
    assert statement["Resource"] != "*"


def test_main_table_is_retained_when_replaced_or_deleted():
    table = _template()["Resources"]["MainTable"]

    assert table["DeletionPolicy"] == "Retain"
    assert table["UpdateReplacePolicy"] == "Retain"


def test_admin_access_comes_from_administrator_managed_cognito_group():
    template = _template()
    resources = template["Resources"]
    admin_group = resources["UserPoolAdminGroup"]["Properties"]
    pre_token = resources["PreTokenFunction"]["Properties"]

    assert admin_group["UserPoolId"] == "UserPool"
    assert admin_group["GroupName"] == "AdminGroupName"
    assert pre_token["Environment"]["Variables"]["ADMIN_GROUP"] == "AdminGroupName"
    assert pre_token["Environment"]["Variables"][
        "ADMIN_ALIAS_MIGRATION_ENABLED"
    ] == "AdminAliasMigrationEnabled"


def test_app_client_preserves_midway_mapping_but_cannot_write_role():
    template = _template()
    user_pool = template["Resources"]["UserPool"]["Properties"]
    idp = template["Resources"]["UserPoolMidwayIdP"]["Properties"]
    client = template["Resources"]["UserPoolClient"]["Properties"]

    schema_names = {attribute["Name"] for attribute in user_pool["Schema"]}
    assert {"email", "role", "amazon_alias"} <= schema_names
    assert idp["AttributeMapping"]["email"] == "email"
    assert idp["AttributeMapping"]["custom:amazon_alias"] == "sub"
    assert client["WriteAttributes"] == ["email", "custom:amazon_alias"]
    assert "custom:role" not in client["WriteAttributes"]


def test_admin_alias_migration_has_no_built_in_identity_and_is_live_verified():
    template = _template()
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert template["Parameters"]["AdminAlias"]["Default"] == ""
    assert re.search(r"^ADMIN_ALIASES\s+\?=\s*$", makefile, re.MULTILINE)
    assert "ADMIN_ALIAS_MIGRATION_ACK" in makefile
    assert "dev-temporary-alias-fallback" in makefile
    assert "cognito-idp list-users-in-group" in makefile
    assert "cognito-idp list-users" in makefile
    assert "check-admin-migration" in makefile
    assert "deploy-admin-migration-phase1" in makefile
    assert "deploy-admin-migration-phase2" in makefile


def test_sam_deploy_is_linted_and_requires_change_set_review():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "sam validate --lint" in makefile
    assert "--confirm-changeset" in makefile
    assert "--no-confirm-changeset" not in makefile


def test_wire_agentcore_live_validates_runtime_and_reuses_full_deploy_path():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    target = makefile.split("wire-agentcore:", 1)[1].split(
        "# ── Clean", 1
    )[0]

    assert "bedrock-agentcore-control get-agent-runtime" in target
    assert "agentRuntimeArn" in target
    assert 'get("networkMode")' in target
    assert "$(MAKE) deploy" in target
    assert "sam deploy" not in target


def test_dev_agentcore_network_mode_remains_public_and_is_not_rewritten():
    config = json.loads(AGENTCORE_CONFIG_PATH.read_text(encoding="utf-8"))
    runtimes = config["runtimes"]

    assert len(runtimes) == 1
    assert runtimes[0]["networkMode"] == "PUBLIC"


def test_lambda_and_agentcore_pin_the_same_packaged_knowledge_release():
    template = _template()
    config = json.loads(AGENTCORE_CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(
        KNOWLEDGE_RELEASE_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    globals_env = template["Globals"]["Function"]["Environment"]["Variables"]
    runtime_env = {
        item["name"]: item["value"]
        for item in config["runtimes"][0]["envVars"]
    }

    assert template["Parameters"]["KnowledgeReleaseVersion"]["Default"] == (
        manifest["release_version"]
    )
    assert template["Parameters"]["KnowledgeReleaseManifestHash"][
        "Default"
    ] == manifest["manifest_hash"]
    assert globals_env[
        "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_VERSION"
    ] == "KnowledgeReleaseVersion"
    assert globals_env[
        "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_MANIFEST_HASH"
    ] == "KnowledgeReleaseManifestHash"
    assert runtime_env[
        "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_VERSION"
    ] == manifest["release_version"]
    assert runtime_env[
        "PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_MANIFEST_HASH"
    ] == manifest["manifest_hash"]
    assert runtime_env["PLATFORM_ADVISOR_KNOWLEDGE_RELEASE_ROOT"] == (
        "runtime_releases"
    )


def test_deployment_builds_include_and_verify_the_pinned_release():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "validate-knowledge-release:" in makefile
    assert "verify_runtime_release.py" in makefile
    assert "prepare-agentcore-release:" in makefile
    assert "deploy-agentcore: check-agentcore-cli prepare-agentcore-release" in (
        makefile
    )
    assert (
        "$(LAMBDA_STAGE)/runtime_releases/$(KNOWLEDGE_RELEASE_PLATFORM)"
        in makefile
    )


def test_frontend_bucket_is_private_versioned_and_retained_for_rollback():
    bucket = _template()["Resources"]["FrontendBucket"]
    properties = bucket["Properties"]

    assert bucket["DeletionPolicy"] == "Retain"
    assert bucket["UpdateReplacePolicy"] == "Retain"
    assert properties["VersioningConfiguration"]["Status"] == "Enabled"
    assert all(properties["PublicAccessBlockConfiguration"].values())
    lifecycle = properties["LifecycleConfiguration"]["Rules"][0]
    assert lifecycle["NoncurrentVersionExpiration"]["NoncurrentDays"] >= 30


def test_non_dev_table_is_not_the_fixed_dev_table():
    template = _template()
    table_name = template["Resources"]["MainTable"]["Properties"]["TableName"]

    assert template["Conditions"]["IsDev"] == ["Env", "dev"]
    assert table_name == [
        "IsDev",
        "platform-advisor-main",
        "platform-advisor-main-${Env}",
    ]


def test_midway_secret_is_required_and_api_resource_scopes_are_defined():
    template = _template()
    resources = template["Resources"]
    secret = template["Parameters"]["MidwayClientSecret"]
    resource_server = resources["UserPoolResourceServer"]["Properties"]
    client = resources["UserPoolClient"]["Properties"]
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert secret["NoEcho"] is True
    assert "Default" not in secret
    assert "MIDWAY_CLIENT_SECRET" in makefile
    assert "Preserving the existing NoEcho Midway client secret." in makefile
    assert "masked placeholder, not a deployable secret" in makefile
    assert 'midway_override="MidwayClientSecret=$${MIDWAY_CLIENT_SECRET}"' in (
        makefile
    )
    assert resource_server["Identifier"] == "platform-advisor-api"
    assert {scope["ScopeName"] for scope in resource_server["Scopes"]} == {
        "read",
        "write",
        "admin",
    }
    assert {
        "platform-advisor-api/read",
        "platform-advisor-api/write",
        "platform-advisor-api/admin",
    } <= set(client["AllowedOAuthScopes"])


def test_non_dev_make_preflight_rejects_fixed_dev_estate():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "ALLOW_NON_DEV_DEPLOY" in makefile
    assert "still points at the fixed dev estate" in makefile
    assert "frontend publish still points at the fixed dev estate" in makefile
    assert "agentcore/aws-targets.json currently defines only the dev" in makefile
    assert "platform-advisor-dev" in makefile


def test_lambda_logs_have_bounded_retention_and_practical_alarms():
    template = _template()
    resources = template["Resources"]
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "configure-log-retention" in makefile
    assert "aws logs put-retention-policy" in makefile
    assert 'LOG_RETENTION_DAYS ?= 30' in makefile
    assert "AdvisorFunctionLogGroup" not in resources
    assert "PreTokenFunctionLogGroup" not in resources

    error_alarm = resources["AdvisorErrorAlarm"]["Properties"]
    throttle_alarm = resources["AdvisorThrottleAlarm"]["Properties"]
    duration_alarm = resources["AdvisorDurationAlarm"]["Properties"]
    pre_token_alarm = resources["PreTokenErrorAlarm"]["Properties"]

    assert error_alarm["MetricName"] == "Errors"
    assert error_alarm["DatapointsToAlarm"] < error_alarm["EvaluationPeriods"]
    assert throttle_alarm["MetricName"] == "Throttles"
    assert duration_alarm["ExtendedStatistic"] == "p99"
    assert duration_alarm["Threshold"] == 720000
    assert pre_token_alarm["MetricName"] == "Errors"
    assert all(
        alarm["TreatMissingData"] == "notBreaching"
        for alarm in (
            error_alarm,
            throttle_alarm,
            duration_alarm,
            pre_token_alarm,
        )
    )
