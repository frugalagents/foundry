from __future__ import annotations

from pathlib import Path
import re

import yaml


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "infra" / "template.yaml"


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
