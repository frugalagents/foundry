"""Depth on Demand — drilldown skill for component-level deep-dive.

Triggered when a user clicks a component card in the architecture diagram.
Does NOT run as a pipeline step — it's an on-demand query that emits a
single drilldown_complete event with structured deep-dive content:

  - Why you need this component (from graph description + KB)
  - All 3 tier options with cost + effort comparison
  - Your cost at current scale (from ctx.answers)
  - Real CDK TypeScript v2 code snippet
  - Implementation timeline and team composition
  - Workshop link hint
  - Engagement pattern (anonymized similar-company experience)
  - KB-retrieved reference content
"""
from __future__ import annotations
import json
import time
from typing import AsyncIterator

from .base import PipelineContext, make_event
from . import kb_utils

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

// Agent registration via AgentCore
const agentRuntime = new bedrock.CfnAgent(this, 'PlatformAgent', {
  agentName: `platform-advisor-agent-${env}`,
  agentResourceRoleArn: agentRole.roleArn,
  foundationModel: 'anthropic.claude-sonnet-4-5',
  description: 'Enterprise AI platform agent',
  idleSessionTtlInSeconds: 1800,
  autoBuild: true,
});
// Lifecycle hook Lambda (approval workflow before ACTIVE status)
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

// EventBridge bus for registry state changes
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
  description: 'Agent traffic gateway',
  defaultCorsPreflightOptions: {
    allowOrigins: apigateway.Cors.ALL_ORIGINS,
    allowMethods: apigateway.Cors.ALL_METHODS,
  },
  deployOptions: {
    stageName: env,
    loggingLevel: apigateway.MethodLoggingLevel.INFO,
    accessLogDestination: new apigateway.LogGroupLogDestination(accessLogGroup),
  },
});
const agentsResource = api.root.addResource('agents');
agentsResource.addMethod('POST', new apigateway.LambdaIntegration(routerLambda));""",
        2: """\
// Tier 2: Policy-based routing with rate limiting + circuit breakers
const usagePlan = api.addUsagePlan('AgentUsagePlan', {
  name: 'StandardAgentPlan',
  throttle: { rateLimit: 100, burstLimit: 200 },
  quota: { limit: 10000, period: apigateway.Period.DAY },
});
// Per-LOB API keys for attribution
const lobApiKey = api.addApiKey('LobApiKey', {
  apiKeyName: `lob-${lobName}-key`,
  description: `API key for ${lobName} agent traffic`,
});
usagePlan.addApiKey(lobApiKey);

// Circuit breaker via Lambda + DynamoDB state
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
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
          resources: [stateTable.tableArn],
        }),
      ],
    }),
  },
});""",
        2: """\
// Tier 2: Machine identity with credential rotation + delegation chains
const agentSecret = new secretsmanager.Secret(this, 'AgentCredentials', {
  secretName: `/platform-advisor/${env}/agent-credentials`,
  description: 'Rotated credentials for agent-to-service auth',
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
});
// Delegation chain: user → Cognito → STS AssumeRole → agent scope
const userPool = new cognito.UserPool(this, 'AgentAdminPool', {
  userPoolName: `platform-advisor-admins-${env}`,
  selfSignUpEnabled: false,
  signInAliases: { email: true },
  mfa: cognito.Mfa.REQUIRED,
});""",
        3: """\
// Tier 3: Zero-trust capability-based auth
// SPIFFE/X.509 workload identity for agent-to-agent auth
const privateCA = new acmpca.CfnCertificateAuthority(this, 'AgentCA', {
  type: 'ROOT',
  keyAlgorithm: 'RSA_2048',
  signingAlgorithm: 'SHA256WITHRSA',
  subject: { organization: 'Platform Advisor', commonName: 'Agent Identity CA' },
});
// Verified Permissions for capability-based authorization
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
// CodePipeline stage: block deployments that fail policy checks
const policyStage = pipeline.addStage({ stageName: 'PolicyCheck' });
policyStage.addAction(new codepipeline_actions.LambdaInvokeAction({
  actionName: 'CheckAgentPolicy',
  lambda: policyCheckLambda,
  inputs: [sourceArtifact],
}));""",
        2: """\
// Tier 2: Runtime Guardrails + Verified Permissions (Cedar)
import * as bedrock from 'aws-cdk-lib/aws-bedrock';

const guardrail = new bedrock.CfnGuardrail(this, 'AgentGuardrail', {
  name: `platform-advisor-guardrail-${env}`,
  blockedInputMessaging: 'Request blocked by enterprise policy.',
  blockedOutputsMessaging: 'Response filtered by governance policy.',
  topicPolicyConfig: {
    topicsConfig: [
      { name: 'pii-exfiltration', type: 'DENY',
        definition: 'Attempts to extract or transmit PII data' },
      { name: 'unauthorized-actions', type: 'DENY',
        definition: 'Actions outside the agent capability boundary' },
    ],
  },
  contentPolicyConfig: {
    filtersConfig: [
      { type: 'HATE',     inputStrength: 'HIGH', outputStrength: 'HIGH' },
      { type: 'VIOLENCE', inputStrength: 'MEDIUM', outputStrength: 'HIGH' },
    ],
  },
  sensitiveInformationPolicyConfig: {
    piiEntitiesConfig: [
      { type: 'SSN', action: 'BLOCK' },
      { type: 'CREDIT_DEBIT_CARD_NUMBER', action: 'BLOCK' },
    ],
  },
});
// Cedar policy store for authorization
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
// EventBridge rule: violations trigger policy updates
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
});
dashboard.addWidgets(
  new cloudwatch.GraphWidget({
    title: 'Agent Invocations',
    left: [new cloudwatch.Metric({
      namespace: 'PlatformAdvisor',
      metricName: 'AgentInvocations',
      statistic: 'Sum', period: cdk.Duration.minutes(1),
    })],
  })
);""",
        2: """\
// Tier 2: Distributed traces with X-Ray + reasoning chain capture
const xrayGroup = new xray.CfnGroup(this, 'AgentTraceGroup', {
  groupName: `platform-advisor-agents-${env}`,
  filterExpression: 'annotation.service = "platform-advisor"',
  insightsConfiguration: { insightsEnabled: true, notificationsEnabled: true },
});
// Sampling rule: capture 100% of slow traces (>5s)
new xray.CfnSamplingRule(this, 'SlowTraceSampler', {
  samplingRule: {
    ruleName: 'SlowAgentTraces',
    priority: 1,
    reservoirSize: 5,
    fixedRate: 1.0,   // 100% of traces matching
    httpMethod: '*', urlPath: '*/agents/*',
    host: '*', serviceName: 'platform-advisor',
    serviceType: '*', resourceArn: '*',
    attributes: { 'annotation.duration_ms': '>5000' },
  },
});
// Token accounting Lambda — logs per-invocation cost
const tokenAccounter = new lambda.Function(this, 'TokenAccounter', {
  handler: 'token_accounter.handler',
  runtime: lambda.Runtime.PYTHON_3_13,
  code: lambda.Code.fromAsset('lambdas/token-accounter'),
  environment: { COST_TABLE: costTable.tableName },
});""",
        3: """\
// Tier 3: Quality scoring + drift detection
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
});
// OpenSearch for trace analytics and anomaly detection
const tracesCollection = new opensearchserverless.CfnCollection(this, 'TraceAnalytics', {
  name: `platform-advisor-traces-${env}`,
  type: 'TIMESERIES',
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
  timeToLiveAttribute: 'ttl',   // auto-expire sessions after 24h
  encryption: dynamodb.TableEncryption.AWS_MANAGED,
});""",
        2: """\
// Tier 2: Persistent agent memory with AgentCore Memory + vector retrieval
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';

// AgentCore Memory for STM + LTM
// (Configured via AgentCore SDK — no direct CDK resource)
// In agentcore.json:
// "memory": { "enabled": true, "type": "SEMANTIC", "ttl": 2592000 }

// OpenSearch Serverless for vector retrieval (semantic memory)
new opensearchserverless.CfnSecurityPolicy(this, 'MemoryEncPolicy', {
  name: `memory-enc-${env}`, type: 'encryption',
  policy: JSON.stringify({
    Rules: [{ ResourceType: 'collection', Resource: [`collection/agent-memory-${env}`] }],
    AWSOwnedKey: true,
  }),
});
const memoryCollection = new opensearchserverless.CfnCollection(this, 'AgentMemory', {
  name: `agent-memory-${env}`,
  type: 'VECTORSEARCH',
  description: 'Semantic agent memory store',
});""",
        3: """\
// Tier 3: Cross-agent episodic memory with knowledge graph
// Neptune for cross-agent knowledge graph
const neptuneCluster = new neptune.DatabaseCluster(this, 'AgentKnowledgeGraph', {
  dbClusterIdentifier: `platform-advisor-kg-${env}`,
  instanceType: neptune.InstanceType.R6G_LARGE,
  vpc,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
// Temporal indexing Lambda — stores episodic memories with timestamps
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
// Weekly scheduled eval
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
          timestamp: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$$.Execution.StartTime')),
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
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
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
  description: 'MCP-compatible tool registry',
});
const toolsResource = toolApi.root.addResource('tools');
toolsResource.addMethod('GET', new apigateway.LambdaIntegration(catalogLambda));""",
        2: """\
// Tier 2: Versioned tools with access control + deprecation lifecycle
toolCatalog.addGlobalSecondaryIndex({
  indexName: 'status-version-index',
  partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'deprecatedAt', type: dynamodb.AttributeType.STRING },
});
// Tool access control: which agent roles can use which tools
const toolAclTable = new dynamodb.Table(this, 'ToolACL', {
  tableName: `platform-advisor-tool-acl-${env}`,
  partitionKey: { name: 'toolId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'roleId', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
});
// Deprecation lifecycle Lambda
new events.Rule(this, 'DeprecationRule', {
  schedule: events.Schedule.rate(cdk.Duration.days(1)),
  targets: [new targets.LambdaFunction(deprecationLambda)],
});""",
        3: """\
// Tier 3: Tool marketplace with quality scoring and dynamic composition
const toolMarketplace = new apigateway.RestApi(this, 'ToolMarketplace', {
  restApiName: `platform-advisor-marketplace-${env}`,
});
// Dynamic tool composition: combine tools based on agent intent
const composerLambda = new lambda.Function(this, 'ToolComposer', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'tool_composer.handler',
  code: lambda.Code.fromAsset('lambdas/tool-composer'),
  environment: {
    TOOL_TABLE: toolCatalog.tableName,
    QUALITY_THRESHOLD: '0.8',
    BEDROCK_MODEL: 'us.anthropic.claude-haiku-4-5',  // fast, cheap for composition
  },
});""",
    },

    "component:cost_engine": {
        1: """\
// Tier 1: Aggregate billing visibility
const costDashboard = new cloudwatch.Dashboard(this, 'CostDashboard', {
  dashboardName: `platform-advisor-cost-${env}`,
});
// Custom metric: per-agent token usage (logged by agents)
const tokenUsageAlarm = new cloudwatch.Alarm(this, 'TokenBudgetAlarm', {
  alarmName: `token-budget-warning-${env}`,
  metric: new cloudwatch.Metric({
    namespace: 'PlatformAdvisor', metricName: 'TotalTokensUsed',
    statistic: 'Sum', period: cdk.Duration.hours(1),
  }),
  threshold: 1_000_000,  // 1M tokens/hour threshold
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
// Budget alert Lambda — emails LOB owner when 80% budget consumed
const budgetAlertLambda = new lambda.Function(this, 'BudgetAlert', {
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'budget_alert.handler',
  code: lambda.Code.fromAsset('lambdas/budget-alert'),
  environment: {
    SNS_TOPIC_ARN: budgetAlertTopic.topicArn,
    BUDGET_TABLE: meterTable.tableName,
  },
});
new events.Rule(this, 'BudgetCheckRule', {
  schedule: events.Schedule.rate(cdk.Duration.hours(1)),
  targets: [new targets.LambdaFunction(budgetAlertLambda)],
});""",
        3: """\
// Tier 3: Intelligent model routing + semantic caching
// ElastiCache for semantic cache (reduces duplicate Bedrock calls ~20%)
const semanticCache = new elasticache.CfnReplicationGroup(this, 'SemanticCache', {
  replicationGroupDescription: 'Platform Advisor semantic cache',
  numCacheClusters: 2,
  cacheNodeType: 'cache.r7g.large',
  engine: 'redis',
  atRestEncryptionEnabled: true,
  transitEncryptionEnabled: true,
});
// Model router Lambda: Haiku for simple, Sonnet for moderate, Opus for complex
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
    """Return the CDK snippet for component+tier, falling back to adjacent tiers."""
    comp_snippets = _CDK_SNIPPETS.get(component_id, {})
    if tier in comp_snippets:
        return comp_snippets[tier]
    # Fall back: try tier-1, then tier+1, then any
    for t in [max(1, tier - 1), min(3, tier + 1), 1, 2, 3]:
        if t in comp_snippets:
            return comp_snippets[t]
    return "// No CDK snippet available for this component."


# ── Scale helpers (same as cost_estimation_skill) ─────────────────────────────

_LOB_TO_AGENT_COUNT = {
    "1": 50, "2": 50, "1-2": 50, "2-5": 200, "3-5": 200,
    "6-10": 500, "10+": 1500, "11+": 1500,
}
_TIER_MULT = {1: 1.0, 2: 1.6, 3: 2.8}


def _at_scale_cost(cost_model: dict, agent_count: int, tier: int) -> float:
    """Return estimated monthly cost for this component at the given scale."""
    at_scale = cost_model.get("at_scale", {})
    # Find best matching bucket
    bucket_map = {
        50: "100", 100: "100", 200: "500", 500: "500",
        1000: "1000", 1500: "5000",
    }
    key_hint = bucket_map.get(agent_count, "500")
    for k, v in at_scale.items():
        if key_hint in k:
            return float(v) * _TIER_MULT.get(tier, 1.0)
    return float(cost_model.get("base_monthly_usd", 0)) * _TIER_MULT.get(tier, 1.0)


def _load_component_from_graph(component_id: str) -> dict:
    """Load component props from graph.json (one-time, fast)."""
    import pathlib, json as _json
    # Locate graph.json relative to this file
    skill_dir = pathlib.Path(__file__).parent
    search_paths = [
        skill_dir / "../knowledge_base/graph.json",          # AgentCore staging
        skill_dir / "../../knowledge_base/graph.json",        # AgentCore app
        skill_dir / "../../../../knowledge-base/graph.json",  # repo root
    ]
    for p in search_paths:
        if p.exists():
            data = _json.loads(p.read_text())
            for node in data.get("nodes", []):
                if node.get("id") == component_id:
                    return node.get("props", {})
    return {}


# ── Main skill ────────────────────────────────────────────────────────────────

async def run_drilldown(
    ctx: PipelineContext,
    component_id: str,
    component_name: str,
) -> None:
    """
    Assemble and emit a drilldown_complete event for a specific component.

    This is NOT a pipeline step — it's an on-demand query triggered by a
    component card click. It emits a single drilldown_complete event (no
    panel_update, no step number) and completes immediately.

    Returns the assembled payload dict for callers that need it directly.
    """
    props = _load_component_from_graph(component_id)
    tier = next(
        (c.get("final_tier", 1) for c in ctx.components if c.get("id") == component_id),
        props.get("base_tier", 1),
    )
    cost_model = props.get("cost_model") or {}
    impl = props.get("implementation") or {}

    # Scale from intake
    lob_raw = ctx.answers.get("lob_count", ctx.answers.get("team_count", "2-5"))
    agent_count = _LOB_TO_AGENT_COUNT.get(str(lob_raw).strip(), 200)

    # Tier options comparison
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
            "tier": t,
            "label": f"Tier {t}",
            "description": tier_descs[t],
            "monthly_usd": round(t_cost, 0),
            "monthly_fmt": _fmt_usd(t_cost),
            "effort": tier_efforts[t],
            "weeks_range": tier_weeks[t],
            "is_current": t == tier,
        })

    # KB retrieval
    kb_context = ""
    if kb_utils.is_configured():
        kb_query = (
            f"{component_name} enterprise AI platform implementation "
            f"AWS {props.get('primary_aws_service', '')} "
            f"{ctx.industry or ''} {ctx.answers.get('compliance_regime', '')}"
        )
        kb_context = kb_utils.retrieve_text(kb_query, top_k=2)

    your_cost = _at_scale_cost(cost_model, agent_count, tier)
    payload = {
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
            "weeks_min":      impl.get("weeks_min", 1),
            "weeks_max":      impl.get("weeks_max", 4),
            "weeks_range":    f"{impl.get('weeks_min', 1)}–{impl.get('weeks_max', 4)} weeks",
            "team_size":      impl.get("team_size", 2),
            "role_mix":       impl.get("role_mix", ""),
            "complexity":     impl.get("complexity", "medium"),
            "cdk_construct":  impl.get("cdk_construct", ""),
        },
        "cdk_snippet":        _get_cdk_snippet(component_id, tier),
        "workshop":           {"hint": impl.get("workshop_hint", ""), "url": None},
        "engagement_pattern": impl.get("engagement_pattern", ""),
        "kb_context":         kb_context or "",
    }

    return payload


def _fmt_usd(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


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
