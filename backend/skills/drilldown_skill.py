"""Depth on Demand — drilldown skill for component-level deep-dive.

Local-dev version: no KB retrieval (kb_context always empty string).
Production uses the AgentCore version which has real KB retrieval.
"""
from __future__ import annotations

from .base import PipelineContext

# ── CDK snippets (TypeScript CDK v2 — realistic, copy-paste ready) ───────────

_CDK_SNIPPETS: dict[str, dict[int, str]] = {
    "component:registry": {
        1: """\
// Tier 1: Static agent catalog with DynamoDB
const agentRegistry = new dynamodb.Table(this, 'AgentRegistry', {
  tableName: `platform-advisor-agents-${env}`,
  partitionKey: { name: 'agentId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'version', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  pointInTimeRecovery: true,
  encryption: dynamodb.TableEncryption.AWS_MANAGED,
});
agentRegistry.addGlobalSecondaryIndex({
  indexName: 'status-index',
  partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
  projectionType: dynamodb.ProjectionType.ALL,
});""",
        2: """\
// Tier 2: AgentCore Runtime with lifecycle hooks + approval workflows
import * as bedrock from 'aws-cdk-lib/aws-bedrock';

const agentRuntime = new bedrock.CfnAgent(this, 'PlatformAgent', {
  agentName: `platform-advisor-agent-${env}`,
  agentResourceRoleArn: agentRole.roleArn,
  foundationModel: 'anthropic.claude-sonnet-4-5',
  description: 'Enterprise AI platform agent',
  idleSessionTtlInSeconds: 1800,
  autoBuild: true,
});
const lifecycleHook = new lambda.Function(this, 'RegistryLifecycleHook', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambdas/registry-lifecycle'),
  environment: { REGISTRY_TABLE: agentRegistry.tableName },
});""",
        3: """\
// Tier 3: Self-healing registry with EventBridge and auto-discovery
const discoveryRule = new events.Rule(this, 'AgentDiscoveryRule', {
  schedule: events.Schedule.rate(cdk.Duration.minutes(5)),
  description: 'Auto-discover new AgentCore runtimes',
});
discoveryRule.addTarget(new targets.LambdaFunction(discoveryLambda));

const registryBus = new events.EventBus(this, 'RegistryBus', {
  eventBusName: `platform-advisor-registry-${env}`,
});
new events.Rule(this, 'AgentHealthRule', {
  eventBus: registryBus,
  eventPattern: { source: ['platform.registry'], detailType: ['AgentUnhealthy'] },
  targets: [new targets.LambdaFunction(selfHealLambda)],
});""",
    },
    "component:gateway": {
        1: """\
// Tier 1: API Gateway REST API with static routing table
const api = new apigateway.RestApi(this, 'AgentGateway', {
  restApiName: `platform-advisor-gateway-${env}`,
  defaultCorsPreflightOptions: {
    allowOrigins: apigateway.Cors.ALL_ORIGINS,
    allowMethods: apigateway.Cors.ALL_METHODS,
  },
  deployOptions: {
    stageName: env,
    loggingLevel: apigateway.MethodLoggingLevel.INFO,
    accessLogDestination: new apigateway.LogGroupLogDestination(accessLogGroup),
  },
});""",
        2: """\
// Tier 2: Policy-based routing with rate limiting + circuit breakers
const usagePlan = api.addUsagePlan('AgentUsagePlan', {
  name: 'StandardAgentPlan',
  throttle: { rateLimit: 100, burstLimit: 200 },
  quota: { limit: 10000, period: apigateway.Period.DAY },
});
const circuitBreaker = new lambda.Function(this, 'CircuitBreaker', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'circuit_breaker.handler',
  code: lambda.Code.fromAsset('lambdas/circuit-breaker'),
  environment: { FAILURE_THRESHOLD: '5', TIMEOUT_SECONDS: '30' },
});""",
        3: """\
// Tier 3: Intent-based routing with dynamic load shaping
const routingStateMachine = new sfn.StateMachine(this, 'IntentRouter', {
  stateMachineName: `platform-advisor-router-${env}`,
  definition: sfn.Chain.start(
    new tasks.LambdaInvoke(this, 'ClassifyIntent', {
      lambdaFunction: intentClassifierLambda,
    }).next(
      new sfn.Choice(this, 'RouteByIntent')
        .when(sfn.Condition.stringEquals('$.intent', 'analytical'), analyticalState)
        .when(sfn.Condition.stringEquals('$.intent', 'transactional'), txnState)
        .otherwise(defaultRouteState)
    )
  ),
});""",
    },
    "component:identity": {
        1: """\
// Tier 1: IAM service accounts for agents
const agentRole = new iam.Role(this, 'AgentExecutionRole', {
  roleName: `platform-advisor-agent-${env}`,
  assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
  inlinePolicies: {
    AgentPolicy: new iam.PolicyDocument({
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
          resources: [`arn:aws:bedrock:${region}::foundation-model/*`],
        }),
      ],
    }),
  },
});""",
        2: """\
// Tier 2: Machine identity with credential rotation + delegation chains
const agentSecret = new secretsmanager.Secret(this, 'AgentCredentials', {
  secretName: `/platform-advisor/${env}/agent-credentials`,
  generateSecretString: {
    secretStringTemplate: JSON.stringify({ agentId: agentId }),
    generateStringKey: 'apiKey',
    excludePunctuation: true,
    passwordLength: 32,
  },
});
agentSecret.addRotationSchedule('RotationSchedule', {
  rotationLambda: credRotationLambda,
  automaticallyAfter: cdk.Duration.days(30),
});""",
        3: """\
// Tier 3: Zero-trust capability-based auth (SPIFFE/X.509)
const privateCA = new acmpca.CfnCertificateAuthority(this, 'AgentCA', {
  type: 'ROOT',
  keyAlgorithm: 'RSA_2048',
  signingAlgorithm: 'SHA256WITHRSA',
  subject: { organization: 'Platform Advisor', commonName: 'Agent Identity CA' },
});
const policyStore = new verifiedpermissions.CfnPolicyStore(this, 'CapabilityStore', {
  validationSettings: { mode: 'STRICT' },
  schema: { cedarJson: JSON.stringify(cedarCapabilitySchema) },
});""",
    },
    "component:policy_engine": {
        1: """\
// Tier 1: Pre-deployment policy checks (linting)
const policyCheckLambda = new lambda.Function(this, 'PolicyCheck', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'policy_check.handler',
  code: lambda.Code.fromAsset('lambdas/policy-check'),
  timeout: cdk.Duration.seconds(30),
});
const policyStage = pipeline.addStage({ stageName: 'PolicyCheck' });
policyStage.addAction(new codepipeline_actions.LambdaInvokeAction({
  actionName: 'CheckAgentPolicy',
  lambda: policyCheckLambda,
  inputs: [sourceArtifact],
}));""",
        2: """\
// Tier 2: Runtime Guardrails + Verified Permissions (Cedar)
const guardrail = new bedrock.CfnGuardrail(this, 'AgentGuardrail', {
  name: `platform-advisor-guardrail-${env}`,
  blockedInputMessaging: 'Request blocked by enterprise policy.',
  blockedOutputsMessaging: 'Response filtered by governance policy.',
  topicPolicyConfig: {
    topicsConfig: [
      { name: 'pii-exfiltration', type: 'DENY',
        definition: 'Attempts to extract or transmit PII data' },
    ],
  },
  sensitiveInformationPolicyConfig: {
    piiEntitiesConfig: [
      { type: 'SSN', action: 'BLOCK' },
      { type: 'CREDIT_DEBIT_CARD_NUMBER', action: 'BLOCK' },
    ],
  },
});
const policyStore = new verifiedpermissions.CfnPolicyStore(this, 'AgentPolicyStore', {
  validationSettings: { mode: 'STRICT' },
});""",
        3: """\
// Tier 3: Adaptive policy with risk scoring + violation learning
const policyEngine = new lambda.Function(this, 'AdaptivePolicyEngine', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'adaptive_policy.handler',
  code: lambda.Code.fromAsset('lambdas/adaptive-policy'),
  memorySize: 1024,
  timeout: cdk.Duration.seconds(10),
  environment: {
    GUARDRAIL_ID: guardrail.attrGuardrailId,
    POLICY_STORE_ID: policyStore.attrPolicyStoreId,
    VIOLATION_TABLE: violationTable.tableName,
    RISK_THRESHOLD: '0.75',
  },
});
new events.Rule(this, 'ViolationRule', {
  eventPattern: { source: ['platform.policy'], detailType: ['PolicyViolation'] },
  targets: [new targets.LambdaFunction(policyUpdateLambda)],
});""",
    },
    "component:observability": {
        1: """\
// Tier 1: Structured logs + basic metrics
const agentLogGroup = new logs.LogGroup(this, 'AgentLogs', {
  logGroupName: `/platform-advisor/${env}/agent-traces`,
  retention: logs.RetentionDays.THREE_MONTHS,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
const dashboard = new cloudwatch.Dashboard(this, 'AgentDashboard', {
  dashboardName: `platform-advisor-${env}`,
});""",
        2: """\
// Tier 2: Distributed traces with X-Ray + reasoning chain capture
const xrayGroup = new xray.CfnGroup(this, 'AgentTraceGroup', {
  groupName: `platform-advisor-agents-${env}`,
  filterExpression: 'annotation.service = "platform-advisor"',
  insightsConfiguration: { insightsEnabled: true, notificationsEnabled: true },
});
new xray.CfnSamplingRule(this, 'SlowTraceSampler', {
  samplingRule: {
    ruleName: 'SlowAgentTraces',
    priority: 1,
    reservoirSize: 5,
    fixedRate: 1.0,
    httpMethod: '*', urlPath: '*/agents/*',
    host: '*', serviceName: 'platform-advisor',
    serviceType: '*', resourceArn: '*',
  },
});""",
        3: """\
// Tier 3: Quality scoring + drift detection
const tracesCollection = new opensearchserverless.CfnCollection(this, 'TraceAnalytics', {
  name: `platform-advisor-traces-${env}`,
  type: 'TIMESERIES',
});
const qualityPipeline = new sfn.StateMachine(this, 'QualityScorer', {
  definition: sfn.Chain.start(
    new tasks.LambdaInvoke(this, 'ScoreQuality', {
      lambdaFunction: qualityScorerLambda,
      resultPath: '$.qualityScore',
    }).next(
      new sfn.Choice(this, 'CheckDrift')
        .when(sfn.Condition.numberLessThan('$.qualityScore.score', 0.8), alertState)
        .otherwise(okState)
    )
  ),
});""",
    },
    "component:memory_state": {
        1: """\
// Tier 1: Per-session key-value state with DynamoDB
const sessionTable = new dynamodb.Table(this, 'AgentSessionState', {
  tableName: `platform-advisor-sessions-${env}`,
  partitionKey: { name: 'sessionId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'agentId', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  timeToLiveAttribute: 'ttl',
  encryption: dynamodb.TableEncryption.AWS_MANAGED,
});""",
        2: """\
// Tier 2: Persistent agent memory with AgentCore Memory + vector retrieval
// AgentCore Memory configured via agentcore.json:
// "memory": { "enabled": true, "type": "SEMANTIC", "ttl": 2592000 }

const memoryCollection = new opensearchserverless.CfnCollection(this, 'AgentMemory', {
  name: `agent-memory-${env}`,
  type: 'VECTORSEARCH',
  description: 'Semantic agent memory store',
});""",
        3: """\
// Tier 3: Cross-agent episodic memory with knowledge graph
const neptuneCluster = new neptune.DatabaseCluster(this, 'AgentKnowledgeGraph', {
  dbClusterIdentifier: `platform-advisor-kg-${env}`,
  instanceType: neptune.InstanceType.R6G_LARGE,
  vpc,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
new events.Rule(this, 'EpisodicMemoryRule', {
  schedule: events.Schedule.rate(cdk.Duration.minutes(15)),
  targets: [new targets.LambdaFunction(temporalIndexerLambda)],
});""",
    },
    "component:eval_pipeline": {
        1: """\
// Tier 1: Offline batch eval with Bedrock Model Evaluation
const evalJobLambda = new lambda.Function(this, 'EvalJobStarter', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'eval_starter.handler',
  code: lambda.Code.fromAsset('lambdas/eval-starter'),
  timeout: cdk.Duration.minutes(5),
  environment: {
    EVAL_ROLE_ARN: evalRole.roleArn,
    OUTPUT_BUCKET: evalBucket.bucketName,
    JUDGE_MODEL: 'us.anthropic.claude-sonnet-4-5',
  },
});
new events.Rule(this, 'WeeklyEvalRule', {
  schedule: events.Schedule.cron({ weekDay: 'MON', hour: '2', minute: '0' }),
  targets: [new targets.LambdaFunction(evalJobLambda)],
});""",
        2: """\
// Tier 2: Shadow evaluation — judge every production response
const evalStateMachine = new sfn.StateMachine(this, 'ShadowEval', {
  stateMachineName: `platform-advisor-shadow-eval-${env}`,
  definition: sfn.Chain.start(
    new tasks.LambdaInvoke(this, 'RunJudge', {
      lambdaFunction: judgeLambda,
      resultPath: '$.evalResult',
    }).next(
      new tasks.DynamoPutItem(this, 'StoreEvalResult', {
        table: evalResultTable,
        item: {
          sessionId: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$.sessionId')),
          score: tasks.DynamoAttributeValue.numberFromString(sfn.JsonPath.stringAt('$.evalResult.score')),
        },
      })
    )
  ),
});""",
        3: """\
// Tier 3: Continuous online eval with auto model rotation
const qualityMonitor = new cloudwatch.Alarm(this, 'QualityDrop', {
  alarmName: `agent-quality-drop-${env}`,
  metric: new cloudwatch.Metric({
    namespace: 'PlatformAdvisor', metricName: 'AgentQualityScore',
    statistic: 'Average', period: cdk.Duration.minutes(10),
  }),
  threshold: 0.75, evaluationPeriods: 3,
  comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
});
qualityMonitor.addAlarmAction(new cw_actions.LambdaAction(modelRotatorLambda));""",
    },
    "component:tool_registry": {
        1: """\
// Tier 1: Static tool catalog with schemas
const toolCatalog = new dynamodb.Table(this, 'ToolRegistry', {
  tableName: `platform-advisor-tools-${env}`,
  partitionKey: { name: 'toolId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'version', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
});
const toolApi = new apigateway.RestApi(this, 'ToolRegistryApi', {
  restApiName: `platform-advisor-tools-${env}`,
});""",
        2: """\
// Tier 2: Versioned tools with access control + deprecation lifecycle
const toolAclTable = new dynamodb.Table(this, 'ToolACL', {
  tableName: `platform-advisor-tool-acl-${env}`,
  partitionKey: { name: 'toolId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'roleId', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
});
new events.Rule(this, 'DeprecationRule', {
  schedule: events.Schedule.rate(cdk.Duration.days(1)),
  targets: [new targets.LambdaFunction(deprecationLambda)],
});""",
        3: """\
// Tier 3: Tool marketplace with quality scoring and dynamic composition
const composerLambda = new lambda.Function(this, 'ToolComposer', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'tool_composer.handler',
  code: lambda.Code.fromAsset('lambdas/tool-composer'),
  environment: {
    TOOL_TABLE: toolCatalog.tableName,
    QUALITY_THRESHOLD: '0.8',
    BEDROCK_MODEL: 'us.anthropic.claude-haiku-4-5',
  },
});""",
    },
    "component:cost_engine": {
        1: """\
// Tier 1: Aggregate billing visibility
const tokenUsageAlarm = new cloudwatch.Alarm(this, 'TokenBudgetAlarm', {
  alarmName: `token-budget-warning-${env}`,
  metric: new cloudwatch.Metric({
    namespace: 'PlatformAdvisor', metricName: 'TotalTokensUsed',
    statistic: 'Sum', period: cdk.Duration.hours(1),
  }),
  threshold: 1_000_000,
  evaluationPeriods: 1,
});""",
        2: """\
// Tier 2: Per-agent metering + LOB allocation + budget alerts
const meterTable = new dynamodb.Table(this, 'TokenMeter', {
  tableName: `platform-advisor-metering-${env}`,
  partitionKey: { name: 'lobId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'date#agentId', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  timeToLiveAttribute: 'ttl',
});
const budgetAlertLambda = new lambda.Function(this, 'BudgetAlert', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'budget_alert.handler',
  code: lambda.Code.fromAsset('lambdas/budget-alert'),
  environment: {
    SNS_TOPIC_ARN: budgetAlertTopic.topicArn,
    BUDGET_TABLE: meterTable.tableName,
  },
});""",
        3: """\
// Tier 3: Intelligent model routing + semantic caching
const semanticCache = new elasticache.CfnReplicationGroup(this, 'SemanticCache', {
  replicationGroupDescription: 'Platform Advisor semantic cache',
  numCacheClusters: 2,
  cacheNodeType: 'cache.r7g.large',
  engine: 'redis',
  atRestEncryptionEnabled: true,
  transitEncryptionEnabled: true,
});
const modelRouter = new lambda.Function(this, 'ModelRouter', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'model_router.handler',
  code: lambda.Code.fromAsset('lambdas/model-router'),
  environment: {
    CACHE_ENDPOINT: semanticCache.attrPrimaryEndPointAddress,
    COMPLEXITY_THRESHOLD_HIGH: '0.8',
    COMPLEXITY_THRESHOLD_LOW: '0.3',
  },
});""",
    },
}


def _get_cdk_snippet(component_id: str, tier: int) -> str:
    comp_snippets = _CDK_SNIPPETS.get(component_id, {})
    if tier in comp_snippets:
        return comp_snippets[tier]
    for t in [max(1, tier - 1), min(3, tier + 1), 1, 2, 3]:
        if t in comp_snippets:
            return comp_snippets[t]
    return "// No CDK snippet available for this component."


_LOB_TO_AGENT_COUNT = {
    "1": 50, "2": 50, "1-2": 50, "2-5": 200, "3-5": 200,
    "6-10": 500, "10+": 1500, "11+": 1500,
}
_TIER_MULT = {1: 1.0, 2: 1.6, 3: 2.8}


def _at_scale_cost(cost_model: dict, agent_count: int, tier: int) -> float:
    at_scale = cost_model.get("at_scale", {})
    bucket_map = {
        50: "100", 100: "100", 200: "500", 500: "500",
        1000: "1000", 1500: "5000",
    }
    key_hint = bucket_map.get(agent_count, "500")
    for k, v in at_scale.items():
        if key_hint in k:
            return float(v) * _TIER_MULT.get(tier, 1.0)
    return float(cost_model.get("base_monthly_usd", 0)) * _TIER_MULT.get(tier, 1.0)


def _fmt_usd(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


def _load_component_from_graph(component_id: str) -> dict:
    import pathlib, json as _json
    skill_dir = pathlib.Path(__file__).parent
    search_paths = [
        skill_dir / "../../knowledge-base/graph.json",     # repo root
        skill_dir / "../../../knowledge-base/graph.json",  # deeper nesting
    ]
    for p in search_paths:
        if p.exists():
            data = _json.loads(p.read_text())
            for node in data.get("nodes", []):
                if node.get("id") == component_id:
                    return node.get("props", {})
    return {}


_WHY_NEEDED: dict[str, str] = {
    "component:registry": (
        "Without a Registry, agent proliferation becomes unmanageable — teams can't discover "
        "what agents exist, duplicate agents get built, and lifecycle management (deprecation, "
        "versioning, ownership) breaks down. The Registry is the single source of truth for "
        "your agent catalog and is required before any other governance component can function."
    ),
    "component:gateway": (
        "The Gateway is the traffic control plane for all agent-to-tool and agent-to-agent "
        "communication. Without it, every agent hard-codes its own connectivity, creating "
        "security gaps, no rate limiting, no circuit breakers, and zero visibility into "
        "inter-agent traffic. It's the network layer of your agent platform."
    ),
    "component:identity": (
        "Agents need machine identities to access AWS services, call APIs, and communicate "
        "with each other. Without a proper Identity component, teams use static credentials "
        "or overly-permissive IAM roles — the #1 security risk in enterprise AI platforms. "
        "Identity enables least-privilege access, credential rotation, and audit trails."
    ),
    "component:policy_engine": (
        "The Policy Engine is your compliance and risk control point. Without it, agents can "
        "generate harmful content, leak PII, exceed authorization boundaries, and create "
        "SOX/HIPAA/PCI audit failures. For regulated industries, this component is non-negotiable — "
        "the business risk of NOT having it far exceeds its implementation cost."
    ),
    "component:observability": (
        "You can't manage what you can't measure. Without Observability, you have no visibility "
        "into agent reasoning chains, token costs, latency patterns, or quality drift. When "
        "something goes wrong (wrong answer, runaway spend, slow response), you're debugging "
        "blind. This component is the foundation for everything that comes after."
    ),
    "component:memory_state": (
        "Stateless agents forget everything between invocations — users repeat themselves, "
        "agents can't build on previous context, and multi-step workflows break. Memory/State "
        "enables agents to maintain working memory within a session (STM) and accumulate "
        "knowledge across sessions (LTM), making them genuinely more capable over time."
    ),
    "component:eval_pipeline": (
        "Agent quality degrades silently — model updates, prompt drift, and changing data "
        "patterns all cause silent regression. Without an Eval Pipeline, you discover quality "
        "problems when a VP complains, not before. This component provides automated quality "
        "gates that catch regressions before they reach production users."
    ),
    "component:tool_registry": (
        "Tool sprawl is the agent equivalent of API chaos. Without a Tool Registry, teams "
        "duplicate tool implementations, use different versions of the same tool, and have "
        "no access control over which agents can call which tools. The Tool Registry is the "
        "single source of truth for all MCP-compatible tools in your platform."
    ),
    "component:cost_engine": (
        "Bedrock costs scale non-linearly with agent activity — a single badly-prompted agent "
        "can burn through a monthly budget in hours. Without a Cost Engine, you have aggregate "
        "AWS bills but no per-LOB, per-agent, or per-task attribution. Intelligent routing "
        "and semantic caching typically reduce total Bedrock spend by 55-70%."
    ),
}


def _why_needed(component_id: str, ctx: PipelineContext) -> str:
    base = _WHY_NEEDED.get(component_id, "")
    compliance = ctx.answers.get("compliance_regime", "")
    if "SOX" in compliance and component_id == "component:policy_engine":
        base += " SOX Section 404 requires automated audit trails for all automated decision-making — this component is your compliance evidence generator."
    if "HIPAA" in compliance and component_id in ("component:policy_engine", "component:identity"):
        base += " HIPAA requires access controls and audit logging for any system that processes PHI."
    return base


async def run_drilldown(
    ctx: PipelineContext,
    component_id: str,
    component_name: str,
) -> dict:
    """
    Assemble and return a drilldown payload dict for a specific component.

    Local-dev version: KB context is always empty (no Bedrock KB in local dev).
    """
    props = _load_component_from_graph(component_id)
    tier = next(
        (c.get("final_tier", 1) for c in ctx.components if c.get("id") == component_id),
        props.get("base_tier", 1),
    )
    cost_model = props.get("cost_model") or {}
    impl = props.get("implementation") or {}

    lob_raw = ctx.answers.get("lob_count", ctx.answers.get("team_count", "2-5"))
    agent_count = _LOB_TO_AGENT_COUNT.get(str(lob_raw).strip(), 200)

    tier_options = []
    for t in [1, 2, 3]:
        t_cost = _at_scale_cost(cost_model, agent_count, t)
        tier_descs = {
            1: props.get("tier_1", "Basic implementation"),
            2: props.get("tier_2", "Enhanced implementation"),
            3: props.get("tier_3", "Advanced implementation"),
        }
        tier_efforts = {1: "low", 2: "medium", 3: "high"}
        tier_weeks = {
            1: f"{impl.get('weeks_min', 1)}-{impl.get('weeks_max', 2)}w",
            2: f"{impl.get('weeks_min', 2)}-{impl.get('weeks_max', 4)}w",
            3: f"{impl.get('weeks_max', 4)+1}-{impl.get('weeks_max', 4)*2}w",
        }
        tier_options.append({
            "tier":        t,
            "label":       f"Tier {t}",
            "description": tier_descs[t],
            "monthly_usd": round(t_cost, 0),
            "monthly_fmt": _fmt_usd(t_cost),
            "effort":      tier_efforts[t],
            "weeks_range": tier_weeks[t],
            "is_current":  t == tier,
        })

    your_cost = _at_scale_cost(cost_model, agent_count, tier)
    return {
        "component_id":       component_id,
        "component_name":     component_name,
        "tier":               tier,
        "description":        props.get("description", ""),
        "why_needed":         _why_needed(component_id, ctx),
        "aws_service":        props.get("primary_aws_service", ""),
        "layer":              props.get("layer", ""),
        "tier_options":       tier_options,
        "your_cost": {
            "monthly_usd":  round(your_cost, 0),
            "monthly_fmt":  _fmt_usd(your_cost),
            "annual_fmt":   _fmt_usd(your_cost * 12),
            "at_agents":    agent_count,
            "cost_drivers": cost_model.get("cost_drivers", ""),
            "notes":        cost_model.get("notes", ""),
        },
        "implementation": {
            "weeks_min":     impl.get("weeks_min", 1),
            "weeks_max":     impl.get("weeks_max", 4),
            "weeks_range":   f"{impl.get('weeks_min', 1)}–{impl.get('weeks_max', 4)} weeks",
            "team_size":     impl.get("team_size", 2),
            "role_mix":      impl.get("role_mix", ""),
            "complexity":    impl.get("complexity", "medium"),
            "cdk_construct": impl.get("cdk_construct", ""),
        },
        "cdk_snippet":        _get_cdk_snippet(component_id, tier),
        "workshop":           {"hint": impl.get("workshop_hint", ""), "url": None},
        "engagement_pattern": impl.get("engagement_pattern", ""),
        "kb_context":         "",   # KB not available in local dev
    }
