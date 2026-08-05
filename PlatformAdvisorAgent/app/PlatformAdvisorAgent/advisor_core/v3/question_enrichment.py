"""Customer-facing question enrichment for guided discovery.

Each entry maps a requirement_id to plain-English content for the UI:
- customer_question: what to ask the customer (replaces the technical description)
- why_it_matters:    one-sentence business context shown below the question
- answer_labels:     per-answer enrichment keyed by str(value) or "true"/"false"
  - label:       short display label for the answer button
  - description: one sentence explaining what this choice means
  - best_for:    who or what this option is best suited for
  - watch_out:   the main trade-off or risk to be aware of
"""
from __future__ import annotations

QUESTION_ENRICHMENT: dict[str, dict] = {
    "requirement:execution-placement": {
        "customer_question": "Where should your coding agents actually run?",
        "why_it_matters": "This is the single biggest architectural decision — it sets your data boundary, compliance posture, and determines which deployment patterns are available to you.",
        "answer_labels": {
            "local": {
                "label": "On each developer's own machine",
                "description": "Agents run inside the developer's local environment or IDE — no cloud infrastructure needed.",
                "best_for": "Teams that need maximum data locality, zero cloud dependency, or air-gapped workflows.",
                "watch_out": "Every developer machine becomes execution infrastructure — standardization and security enforcement are harder to manage at scale.",
            },
            "customer-managed": {
                "label": "In your own cloud or on-premises infrastructure",
                "description": "Your team provisions and operates the agent execution environment in your cloud account or data center.",
                "best_for": "Strict data sovereignty, regulated industries (finance, healthcare, government), or teams with strong cloud operations capability.",
                "watch_out": "Your team owns the operational burden — capacity planning, scaling, patching, and runtime security are all your responsibility.",
            },
            "vendor-managed": {
                "label": "Fully managed by the vendor",
                "description": "The vendor operates all agent execution infrastructure. You consume it as a service with no infrastructure to manage.",
                "best_for": "Teams that want to move fast without managing infrastructure, or organizations earlier in their cloud-AI journey.",
                "watch_out": "Agent execution and outputs may reside in the vendor's environment — confirm this meets your data handling and compliance policy.",
            },
            "hybrid": {
                "label": "Both developer machines and cloud (hybrid)",
                "description": "Interactive tasks run locally; async, batch, and long-running tasks offload to cloud infrastructure.",
                "best_for": "Most enterprise coding platforms — developers get fast local feedback while heavy background work scales in the cloud.",
                "watch_out": "You need clear policies defining what runs where, and both environments must independently meet your security requirements.",
            },
        },
    },
    "requirement:runtime-isolation": {
        "customer_question": "How strictly must each developer's agent session be isolated from other users?",
        "why_it_matters": "Isolation is your security boundary — it determines how far a misbehaving or compromised agent session can affect others on the same infrastructure.",
        "answer_labels": {
            "developer-endpoint": {
                "label": "No cross-user isolation needed (runs on developer's own device)",
                "description": "Each developer's agent runs on their own machine — there is no shared infrastructure requiring tenant separation.",
                "best_for": "Fully local deployments where agents never share compute with other users.",
                "watch_out": "Not appropriate if agents run on any shared cloud infrastructure — this option assumes no multi-tenancy.",
            },
            "container": {
                "label": "Container-level isolation (Docker / OCI)",
                "description": "Each agent session runs in a separate container. Standard isolation for most enterprise workloads.",
                "best_for": "Most enterprise coding platforms — cost-effective, widely supported, and sufficient for typical enterprise compliance requirements.",
                "watch_out": "Containers share an OS kernel — not appropriate for workloads where kernel-level separation is a compliance requirement.",
            },
            "microvm": {
                "label": "VM-level isolation (microVM / hardware virtualization)",
                "description": "Each agent session runs in a hardware-virtualized microVM — stronger isolation than containers with sub-second startup times.",
                "best_for": "Highly regulated environments (financial services, healthcare, government) or workloads executing externally-generated or untrusted code.",
                "watch_out": "Higher cost and operational complexity than containers — typically only needed when compliance explicitly mandates kernel-level separation.",
            },
            "dedicated-tenant": {
                "label": "Dedicated infrastructure per team or customer",
                "description": "Each major team or customer gets fully dedicated compute — no shared infrastructure whatsoever.",
                "best_for": "SaaS platforms reselling agent capacity to external customers, or enterprises with strict contractual tenant-separation requirements.",
                "watch_out": "Highest cost and operational burden of any isolation option — typically only justified for external multi-tenant SaaS, not internal enterprise platforms.",
            },
        },
    },
    "requirement:asynchronous-tasks": {
        "customer_question": "Will developers submit work and come back later — rather than watching it happen live?",
        "why_it_matters": "Async tasks require durable execution infrastructure that can run for minutes to hours without developer supervision, including state persistence and failure recovery.",
        "answer_labels": {
            "true": {
                "label": "Yes — agents will work in the background",
                "description": "Developers queue tasks and return when done. Agents run unattended through file changes, test runs, and PR creation.",
                "best_for": "Issue-to-PR automation, test generation sweeps, dependency upgrades, overnight refactors.",
                "watch_out": "Requires durable job tracking, failure recovery, and clear audit trails for what the agent did and why.",
            },
            "false": {
                "label": "No — developers watch the agent work in real time",
                "description": "All agent work happens interactively — the developer is present and can intervene at any step.",
                "best_for": "Copilot-style assistance, inline code suggestions, code review, explanations, and pair programming.",
                "watch_out": "Limits how much work an agent can do — not suited for tasks that take longer than a developer's active attention.",
            },
        },
    },
    "requirement:long-running-workspaces": {
        "customer_question": "Do developers need the agent to maintain full context and state across work that spans days or weeks?",
        "why_it_matters": "Standard agent sessions are ephemeral — the workspace is discarded when a task ends. Persistent workspaces let agents maintain a durable 'desk' for large, multi-session work.",
        "answer_labels": {
            "true": {
                "label": "Yes — we need persistent agent workspaces",
                "description": "Agents maintain their workspace state — files, environment, partial progress — across multiple sessions.",
                "best_for": "Large codebase migrations, multi-sprint refactors, long-running dependency upgrades, or teams that want agents to accumulate context over time.",
                "watch_out": "Persistent workspaces consume storage and compute even when idle — they require lifecycle management (pause, resume, expiry policies).",
            },
            "false": {
                "label": "No — each agent task starts fresh",
                "description": "Agents work on ephemeral, scoped checkouts. They check out the repo, do their work, push a branch, and the workspace is discarded.",
                "best_for": "Most task-oriented coding agent use cases — issue resolution, PR review, targeted refactoring.",
                "watch_out": "Not suitable for large migrations or multi-day tasks that require accumulated context across sessions.",
            },
        },
    },
    "requirement:multi-agent": {
        "customer_question": "Will multiple specialized agents collaborate together on a single coding task?",
        "why_it_matters": "Complex tasks — like delivering a full feature end-to-end — may need a planner, a coder, a test writer, and a security reviewer each contributing their own expertise.",
        "answer_labels": {
            "true": {
                "label": "Yes — agents will collaborate or specialize",
                "description": "Multiple agents work together: one plans, another codes, another tests, another reviews. Or a coordinator delegates to specialist sub-agents.",
                "best_for": "Complex multi-file features, full-SDLC automation, or organizations where security, QA, and engineering each contribute their own specialized agent.",
                "watch_out": "Multi-agent coordination adds latency, cost, and failure modes. Start single-agent and evolve to multi-agent only when tasks genuinely benefit from specialization.",
            },
            "false": {
                "label": "No — one agent handles each task end-to-end",
                "description": "A single agent handles each task from start to finish with no handoffs or specialization.",
                "best_for": "Most coding agent deployments — simpler, cheaper, and easier to reason about.",
                "watch_out": "If tasks grow complex enough to benefit from specialization, migrating to multi-agent later is straightforward.",
            },
        },
    },
    "requirement:multi-model-provider": {
        "customer_question": "Do you need to use more than one AI model provider simultaneously?",
        "why_it_matters": "A single provider is simpler. Multiple providers unlock cost optimization across providers, resilience when one is down, and routing different tasks to the best model for the job.",
        "answer_labels": {
            "true": {
                "label": "Yes — we need multiple model providers",
                "description": "The platform routes requests across multiple AI providers for cost optimization, resilience, compliance, or capability matching.",
                "best_for": "Enterprises that want vendor independence, need automatic failover if a provider goes down, or want to route tasks to the most cost-effective model.",
                "watch_out": "Requires a model gateway layer and adds operational complexity — model outputs may differ between providers, requiring validation.",
            },
            "false": {
                "label": "No — a single model provider is sufficient",
                "description": "All agent requests route to one model provider — simpler architecture and lower operational overhead.",
                "best_for": "Teams early in their AI journey, or where one provider meets all capability and compliance needs.",
                "watch_out": "Single-provider creates dependency risk. If provider SLAs require failover capability, you will need to revisit this.",
            },
        },
    },
    "requirement:provider-hosting": {
        "customer_question": "How will the AI models your agents use be hosted and accessed?",
        "why_it_matters": "This determines your data sovereignty posture, network path for model traffic, and who is operationally responsible for model infrastructure.",
        "answer_labels": {
            "managed": {
                "label": "Fully managed by a cloud provider (e.g., Amazon Bedrock)",
                "description": "Models are hosted by a managed cloud service — you call them via API, the provider handles all infrastructure.",
                "best_for": "Most enterprises — zero model infrastructure to operate, enterprise-grade SLAs, and built-in compliance certifications (HIPAA BAA, SOC 2, etc.).",
                "watch_out": "Your data traverses the provider's network on every model call — confirm the managed service's data handling meets your compliance requirements.",
            },
            "self-hosted": {
                "label": "Self-hosted models in your own infrastructure",
                "description": "Your team deploys and operates model infrastructure — open-source or licensed models running in your cloud account or on-premises.",
                "best_for": "Air-gapped environments, strict data sovereignty mandates, or organizations with licensed models that contractually must be self-hosted.",
                "watch_out": "Running model infrastructure is operationally expensive. GPU provisioning, scaling, patching, and model updates are all your team's responsibility.",
            },
            "multi-provider": {
                "label": "Mix of managed and self-hosted providers",
                "description": "Different models come from different sources — some from managed cloud services, some self-hosted, potentially from multiple vendors.",
                "best_for": "Enterprises with diverse model needs: proprietary models for sensitive workloads, managed models for general tasks, and specialized providers for specific capabilities.",
                "watch_out": "The most complex option — requires a gateway layer that handles authentication, rate limits, and failure modes for heterogeneous endpoints.",
            },
        },
    },
    "requirement:model-fallback": {
        "customer_question": "Should the platform automatically switch to a backup model if the primary one is unavailable or too slow?",
        "why_it_matters": "If your primary model provider has an outage or latency spike, automatic fallback keeps developers working rather than seeing failures.",
        "answer_labels": {
            "true": {
                "label": "Yes — automatically fall back to a backup model",
                "description": "If the primary model returns errors, is rate-limited, or exceeds latency thresholds, the platform automatically retries on an alternate model.",
                "best_for": "Production-grade platforms where developers rely on agents throughout their workday and uptime directly affects productivity.",
                "watch_out": "Fallback models may produce different quality outputs than the primary — ensure your fallback model meets your minimum quality bar.",
            },
            "false": {
                "label": "No — fail clearly when the primary model is unavailable",
                "description": "If the primary model is unavailable, the task fails immediately with a clear error. No silent switching.",
                "best_for": "Teams that prioritize output predictability and audit consistency, or where regulatory requirements mandate the same model for all executions.",
                "watch_out": "Developers will see task failures during provider incidents. Have a communication plan for outages.",
            },
        },
    },
    "requirement:model-residency-routing": {
        "customer_question": "Must the platform enforce that certain data never crosses geographic or jurisdictional boundaries when calling AI models?",
        "why_it_matters": "GDPR, sovereign cloud mandates, and contractual data residency commitments can require that data stays within specific regions — residency-aware routing enforces this automatically on every model call.",
        "answer_labels": {
            "true": {
                "label": "Yes — enforce data residency rules for all model calls",
                "description": "The model gateway inspects each request and routes it only to model endpoints in approved regions, based on data classification or the developer's jurisdiction.",
                "best_for": "GDPR-covered organizations, financial services with EU operations, government agencies with data sovereignty requirements, or enterprises with contractual residency commitments.",
                "watch_out": "Restricts available model options to providers with capacity in required regions — may limit fallback choices or increase latency.",
            },
            "false": {
                "label": "No — route to the best model regardless of geography",
                "description": "Model routing optimizes for cost, quality, or latency without geographic constraints.",
                "best_for": "Teams with no cross-border data restrictions, operating within a single jurisdiction, or processing non-sensitive data.",
                "watch_out": "Revisit this as your organization expands to new markets or handles more regulated data — retrofitting residency routing later is significantly harder.",
            },
        },
    },
    "requirement:restricted-egress": {
        "customer_question": "Must agent runtimes be restricted to only contacting a pre-approved list of external services — not the open internet?",
        "why_it_matters": "Unrestricted egress means a misbehaving or compromised agent could exfiltrate data or call arbitrary external APIs. Restricted egress is a foundational security control for enterprise deployments.",
        "answer_labels": {
            "true": {
                "label": "Yes — agents can only reach pre-approved destinations",
                "description": "Agent runtimes can only call services on an allowlist — model APIs, internal tools, approved registries. All other outbound traffic is blocked.",
                "best_for": "Most enterprise environments — regulated industries, security-conscious organizations, or any team where agents have access to internal systems.",
                "watch_out": "Requires maintaining an allowlist as your tool integrations grow — each new tool or API must be explicitly permitted before agents can use it.",
            },
            "false": {
                "label": "No — agents can reach any external service",
                "description": "Agent runtimes have unrestricted outbound network access to any public internet endpoint.",
                "best_for": "Development and sandbox environments, or use cases where agents need to access a wide and dynamic range of public APIs.",
                "watch_out": "Not recommended for production enterprise deployments — a compromised or misbehaving agent has no network-level containment.",
            },
        },
    },
    "requirement:private-connectivity": {
        "customer_question": "Must traffic to model providers and enterprise systems travel over a private network path — never the public internet?",
        "why_it_matters": "Even with restricted egress, traffic can still traverse the public internet. Private connectivity (VPC endpoints, PrivateLink, Direct Connect) keeps all traffic on private network paths.",
        "answer_labels": {
            "true": {
                "label": "Yes — all traffic must stay on private network paths",
                "description": "Model API calls, tool invocations, and enterprise system access all route through VPC endpoints or private connectivity — no traffic leaves your private network.",
                "best_for": "Financial services, healthcare, government, or any organization with a mandate that sensitive data never traverses the public internet.",
                "watch_out": "Requires PrivateLink or VPC endpoint configuration for every integrated service, and significantly constrains which deployment families are compatible.",
            },
            "false": {
                "label": "No — encrypted HTTPS over the public internet is acceptable",
                "description": "Traffic is strongly encrypted in transit over TLS but does traverse the public internet between your environment and external services.",
                "best_for": "Most enterprise deployments — TLS provides strong transport security that satisfies most compliance frameworks.",
                "watch_out": "Some compliance frameworks (certain FedRAMP and HIPAA interpretations) may require private connectivity — confirm with your compliance team.",
            },
        },
    },
    "requirement:source-control": {
        "customer_question": "Which Git platform do your developers use for code, branches, and pull requests?",
        "why_it_matters": "The agent integrates directly with your source control system — it clones repos, creates branches, pushes commits, and opens pull requests. The specific integration affects authentication and available features.",
        "answer_labels": {
            "gitlab-saas": {
                "label": "GitLab (cloud-hosted, gitlab.com)",
                "description": "Your team uses the vendor-hosted GitLab SaaS service at gitlab.com.",
                "best_for": "Teams already on GitLab SaaS with standard enterprise plans and API access enabled.",
                "watch_out": "Agents need a GitLab access token with appropriate scopes — confirm your GitLab plan permits API access at your expected task volume.",
            },
            "gitlab-self-managed": {
                "label": "GitLab (self-managed, on your own servers)",
                "description": "Your organization runs its own GitLab instance on-premises or in your own cloud account.",
                "best_for": "Organizations that cannot use SaaS source control for compliance or data sovereignty reasons.",
                "watch_out": "The agent needs network access to your self-managed GitLab. If restricted egress is enabled, ensure your GitLab endpoint is on the allowlist.",
            },
            "github": {
                "label": "GitHub (github.com or GitHub Enterprise)",
                "description": "Your team uses GitHub, either the public SaaS platform or a self-hosted GitHub Enterprise instance.",
                "best_for": "Teams standardized on GitHub with enterprise plans and GitHub Actions already in use.",
                "watch_out": "Define clearly where autonomous agent commits go vs. CI-triggered automation — avoid overlap between agent PRs and GitHub Actions workflows.",
            },
            "other": {
                "label": "Another Git system (Bitbucket, Azure DevOps, etc.)",
                "description": "Your team uses a source control system other than GitLab or GitHub, such as Bitbucket, Azure DevOps, or a custom Git host.",
                "best_for": "Organizations standardized on Atlassian tooling, the Microsoft DevOps stack, or other enterprise SCM platforms.",
                "watch_out": "Integration depth may vary from first-class providers — confirm API compatibility with the platform's source control adapter before committing.",
            },
        },
    },
    "requirement:approved-package-registries": {
        "customer_question": "Are agents restricted to only installing packages from your organization's approved package registries?",
        "why_it_matters": "An agent that can install packages from the public internet introduces supply chain risk — a malicious or compromised package can compromise the agent's execution environment and the code it produces.",
        "answer_labels": {
            "true": {
                "label": "Yes — only approved registries (Artifactory, CodeArtifact, etc.)",
                "description": "Agents can only install packages from your organization's curated registries — public packages must be mirrored and approved before they are available.",
                "best_for": "Most enterprise environments — supply chain security is critical when AI agents are writing and installing code autonomously.",
                "watch_out": "Requires your registry to stay current. If agents need a package your registry doesn't yet have, there is an approval process to add it — plan for this in early rollout.",
            },
            "false": {
                "label": "No — agents can pull directly from public registries",
                "description": "Agents can install packages directly from npm, PyPI, Maven Central, and other public registries without approval.",
                "best_for": "Development and sandbox environments, or teams where supply chain risk is managed through SBOM scanning or runtime monitoring.",
                "watch_out": "Not recommended for production enterprise deployments — agents can install arbitrary public packages without your security team's review.",
            },
        },
    },
    "requirement:enterprise-identity": {
        "customer_question": "Which identity system controls who can log in and what permissions they have on the platform?",
        "why_it_matters": "The platform connects to your existing identity provider to know who each developer is, which team they belong to, and what they are authorized to do — not a separate login system.",
        "answer_labels": {
            "entra": {
                "label": "Microsoft Entra ID (Azure Active Directory)",
                "description": "Your organization uses Microsoft Entra ID as its primary identity provider for workforce authentication.",
                "best_for": "Microsoft-centric organizations using M365, Azure, or Teams — native group sync and conditional access policies flow through to the agent platform.",
                "watch_out": "Ensure your Entra app registration has permissions for group membership queries at your developer population scale.",
            },
            "okta": {
                "label": "Okta",
                "description": "Your organization uses Okta as its identity provider for SSO across all enterprise tooling.",
                "best_for": "Multi-cloud, identity-forward organizations that have standardized on Okta for cross-tool single sign-on.",
                "watch_out": "Configure SCIM provisioning if you need real-time group membership sync — polling-based sync may lag behind team changes.",
            },
            "cognito": {
                "label": "Amazon Cognito",
                "description": "Developer authentication is handled by Amazon Cognito — either directly or via federation from your enterprise IdP.",
                "best_for": "AWS-native organizations that want to minimize external dependencies, or teams already using Cognito for other platform services.",
                "watch_out": "If federating to an enterprise IdP (Entra, Okta) through Cognito, ensure the SAML or OIDC federation is configured and tested before platform launch.",
            },
            "other-oidc": {
                "label": "Another OIDC-compatible provider (PingFederate, Auth0, Keycloak, etc.)",
                "description": "Your organization uses a standards-compliant OIDC identity provider not listed above.",
                "best_for": "Organizations with established identity infrastructure using OIDC or OAuth 2.0 standards.",
                "watch_out": "Standard OIDC covers authentication — confirm your IdP supports the group and role claims your authorization model requires.",
            },
        },
    },
    "requirement:developer-count": {
        "customer_question": "How many developers will use the platform at peak?",
        "why_it_matters": "Developer count drives capacity planning, licensing tier selection, and whether the infrastructure needs per-team quota enforcement and cost allocation.",
    },
    "requirement:concurrent-agent-tasks": {
        "customer_question": "At peak, how many coding-agent tasks will run simultaneously across all your developers?",
        "why_it_matters": "This determines the scale of your execution infrastructure — how many parallel agent processes must be ready at once. Under-provisioning causes developer wait time; over-provisioning wastes cost.",
    },
    "requirement:approved-regions": {
        "customer_question": "Can workloads run in any region your AWS account has approved, or only a specific fixed set of regions?",
        "why_it_matters": "Data residency requirements, compliance mandates, and cost targets all depend on which regions your workloads are permitted to use.",
        "answer_labels": {
            "fixed-regions": {
                "label": "Fixed region set only",
                "description": "All agent workloads must run within a specific, named set of regions — no flexibility to expand to others.",
                "best_for": "Organizations with regulatory data residency requirements (EU data in EU, US government data in US-Gov), or accounts restricted to specific regions by policy.",
                "watch_out": "Constrains your disaster recovery options — ensure your fixed region set includes at least two regions for resilience.",
            },
            "any-approved": {
                "label": "Any region in our approved account list",
                "description": "Workloads can run in any region your AWS account has enabled — not constrained to a specific subset.",
                "best_for": "Organizations optimizing for latency (route to nearest region), cost (route to cheapest region), or resilience (active-active multi-region).",
                "watch_out": "Ensure data residency and compliance requirements do not silently prohibit certain regions — 'any approved' should still have a governance layer defining what 'approved' means.",
            },
        },
    },
    "requirement:action-approval": {
        "customer_question": "Should agents require human approval before taking high-risk actions — like pushing commits, running migrations, or calling external APIs?",
        "why_it_matters": "Risk-based approval lets you give agents autonomy for low-risk operations while keeping humans in the loop for consequential ones, without blocking developer flow unnecessarily.",
        "answer_labels": {
            "true": {
                "label": "Yes — high-risk actions need human sign-off before executing",
                "description": "Agents classify the risk of each action. Low-risk actions proceed automatically; high-risk actions pause and await developer or team-lead approval.",
                "best_for": "Most enterprise production platforms — balances agent autonomy with human oversight. Essential for agents with write access to production systems.",
                "watch_out": "Approval workflows add latency — design your approval process carefully so it does not become a bottleneck in developer workflow.",
            },
            "false": {
                "label": "No — agents act autonomously on all actions",
                "description": "Agents execute all actions without approval gates, regardless of action risk or impact.",
                "best_for": "Tightly sandboxed environments where agent blast radius is inherently limited, or workflows where everything is reversible (agents only write to branches, never to production).",
                "watch_out": "Requires very strong sandboxing. If an agent makes a mistake in a production-accessible context with no blast-radius containment, consequences can be severe.",
            },
        },
    },
    "requirement:audit-retention-days": {
        "customer_question": "For how many days must the platform keep a complete, replayable record of every action an agent took?",
        "why_it_matters": "Retention requirements often come from your compliance frameworks — SOX requires 7 years (2555 days), HIPAA 6 years (2190 days). Longer retention means higher storage cost.",
    },
    "requirement:team-boundaries": {
        "customer_question": "Should each team or business unit have its own isolated workspace with separate policies, usage quotas, and audit logs?",
        "why_it_matters": "Without team boundaries, one team's heavy usage can starve others, policy changes affect everyone at once, and there is no per-team cost accountability or compliance audit trail.",
        "answer_labels": {
            "true": {
                "label": "Yes — teams need isolated workspaces",
                "description": "Each team gets its own namespace with separate agent policies, usage quotas, and audit logs. Team admins manage their own workspace independently.",
                "best_for": "Enterprises with multiple teams, business units, or cost centers that need independent governance, compliance tracking, or internal chargeback.",
                "watch_out": "Requires a workspace onboarding process for new teams — plan for workspace lifecycle management as teams form and dissolve.",
            },
            "false": {
                "label": "No — a single shared workspace is sufficient",
                "description": "All developers share one workspace with unified policies, pooled quotas, and a single audit log.",
                "best_for": "Small organizations, single-team deployments, or proof-of-concept rollouts where operational simplicity outweighs governance granularity.",
                "watch_out": "Retrofitting team boundaries into a shared workspace is disruptive as you grow — plan for this transition early if significant team growth is expected.",
            },
        },
    },
    "requirement:outcome-observability": {
        "customer_question": "Do you need to trace what an agent did in code all the way back to your CI/CD pipeline and Git history?",
        "why_it_matters": "Without outcome observability you have agent actions but no closed loop on results. With it you can measure: did the agent's PR get merged, did tests pass, did it introduce regressions?",
        "answer_labels": {
            "true": {
                "label": "Yes — connect agent actions to Git commits and CI outcomes",
                "description": "Agent traces are correlated with Git commits, PR status, and CI pipeline results — giving a complete audit trail from task assignment to deployment outcome.",
                "best_for": "Any organization serious about measuring and improving agent effectiveness. Essential for production deployments where you need to trust and verify agent output.",
                "watch_out": "Requires integration with your Git platform and CI system — plan for webhook setup and pipeline instrumentation as part of the deployment.",
            },
            "false": {
                "label": "No — agent execution logs are sufficient",
                "description": "Agent execution is logged independently with no linkage to Git history or CI pipeline outcomes.",
                "best_for": "Internal tooling, sandbox environments, or early pilots where rapid iteration matters more than measurement.",
                "watch_out": "You lose the ability to answer 'did the agent's changes actually work' at scale — consider enabling this before moving to production.",
            },
        },
    },
    "requirement:economic-priority": {
        "customer_question": "When choosing which AI model to use for a task, what should the platform optimize for?",
        "why_it_matters": "With multiple models available, the routing layer needs a default priority. This setting drives the default — individual task types can override it.",
        "answer_labels": {
            "balanced": {
                "label": "Balance quality, cost, and speed equally",
                "description": "The router uses a weighted combination of all three factors — routing expensive tasks to capable models and cheap tasks to smaller ones.",
                "best_for": "Most enterprise deployments — good outputs without paying for maximum quality on every request, and without sacrificing too much for cost savings.",
                "watch_out": "The weights are opinionated defaults. If your task mix is unusual (all complex, or all trivially simple), tune them for your workload.",
            },
            "quality": {
                "label": "Always use the best available model",
                "description": "Route every request to the highest-capability model available — cost and latency are secondary.",
                "best_for": "Code review, security analysis, architecture generation, or tasks where model quality directly impacts developer trust in the output.",
                "watch_out": "Premium models are expensive at scale. Run a cost analysis before selecting quality-first as your default — consider reserving it for explicitly high-stakes tasks.",
            },
            "cost": {
                "label": "Minimize cost above all",
                "description": "Route to the cheapest model that meets a minimum quality threshold — maximize token efficiency using smaller models where possible.",
                "best_for": "High-volume, repetitive tasks (test generation, docstring writing, simple refactors) where cost compounds quickly at scale.",
                "watch_out": "Cost-optimized routing can produce noticeably lower quality on complex tasks. Monitor developer feedback closely when using cost-first as the default.",
            },
            "latency": {
                "label": "Minimize response time",
                "description": "Route to whichever model responds fastest — prioritize low latency for interactive developer experiences.",
                "best_for": "Interactive coding assistance where developer flow is broken by waiting — inline completions, quick explanations, fast feedback loops.",
                "watch_out": "Fast models are often smaller and less capable. Ensure your latency-optimized default doesn't frustrate developers with poor quality on complex tasks.",
            },
        },
    },
    "requirement:orchestration-mode": {
        "customer_question": "When multiple agents work together on a task, how should they coordinate their work?",
        "why_it_matters": "The coordination pattern determines latency, cost, quality, and failure modes. Choose the pattern that matches how your human teams actually collaborate today.",
        "answer_labels": {
            "independent": {
                "label": "Each agent works independently on separate tasks",
                "description": "Agents don't coordinate — each handles its own scoped task from start to finish with no handoffs or dependencies.",
                "best_for": "Parallelizable work queues where tasks are independent — for example, fixing 10 separate bugs simultaneously.",
                "watch_out": "Does not work for tasks with ordering dependencies. If agent A must complete before agent B can start, sequential mode is the right choice.",
            },
            "sequential": {
                "label": "Agents hand off work in a pipeline",
                "description": "Work moves through a chain of agents: a planner writes a spec, a coder implements it, a tester writes tests, a reviewer checks it.",
                "best_for": "End-to-end feature development where each step depends on the previous one, or workflows that need specialized expertise at each stage.",
                "watch_out": "Sequential pipelines fail loudly if any agent in the chain fails. You need retry and error handling at each handoff, and latency compounds across the chain.",
            },
            "parallel-review": {
                "label": "Multiple agents compete, then a reviewer picks the best",
                "description": "Multiple 'candidate' agents each attempt the same task independently. A reviewer agent compares outputs and selects or merges the best one.",
                "best_for": "High-stakes tasks with significant solution variance — security-sensitive code, architectural decisions, or tasks where you want competing approaches evaluated.",
                "watch_out": "The most expensive pattern — you run N agents per task plus a reviewer. Reserve for genuinely high-value tasks where quality improvement justifies the cost.",
            },
        },
    },
    "requirement:model-routing-mode": {
        "customer_question": "Should the platform use fixed model assignments, or pick the best model automatically for each request?",
        "why_it_matters": "Static routing is predictable and auditable. Dynamic routing optimizes for cost, quality, and latency at runtime but adds decision-making complexity.",
        "answer_labels": {
            "static": {
                "label": "Fixed — always route to the same model per task type",
                "description": "Each task type is pre-assigned to a specific model. No runtime routing decisions are made.",
                "best_for": "Teams that need deterministic, auditable behavior where the same input always routes to the same model, or compliance requirements around model consistency.",
                "watch_out": "Misses optimization opportunities — you pay the same rate regardless of task complexity and cannot adapt automatically to provider availability changes.",
            },
            "dynamic": {
                "label": "Dynamic — pick the best model at runtime based on policy",
                "description": "A routing policy evaluates each request and selects the best model based on task complexity, provider availability, cost, and latency targets.",
                "best_for": "Cost optimization, resilience, and performance tuning at scale — dynamic routing is what makes multi-provider infrastructure pay off.",
                "watch_out": "Outputs may vary between similar requests if different models are selected. Routing policies need thorough testing and monitoring — routing bugs are hard to trace.",
            },
        },
    },
    "requirement:warm-runtime-capacity": {
        "customer_question": "Must agent tasks start almost instantly, or is a 30–60 second initialization wait acceptable?",
        "why_it_matters": "Warm capacity keeps pre-initialized agent runtimes ready so tasks start in seconds rather than waiting for a cold container or VM to provision.",
        "answer_labels": {
            "true": {
                "label": "Yes — tasks must start in seconds (keep warm runtimes ready)",
                "description": "The platform maintains a pool of pre-warmed, ready-to-use agent runtimes. Tasks start immediately when a developer submits them.",
                "best_for": "Interactive workflows where cold-start delays would break developer flow, or high-frequency task submission patterns.",
                "watch_out": "Warm runtimes consume compute and cost money even when idle. Size your warm pool carefully — idle capacity in off-hours is pure waste.",
            },
            "false": {
                "label": "No — cold starts are acceptable (provision on demand)",
                "description": "Runtimes are provisioned when a task is submitted. Tasks may wait 30–90 seconds before starting.",
                "best_for": "Background and async task queues where latency is not critical, cost-sensitive deployments, or low task frequency where warm capacity would mostly sit idle.",
                "watch_out": "If developers use the platform for interactive tasks and experience consistent 60-second waits, adoption will suffer. Revisit this if interactive usage grows.",
            },
        },
    },
}


def get_enrichment(requirement_id: str) -> dict:
    """Return enrichment for a requirement, or an empty dict if not found."""
    return QUESTION_ENRICHMENT.get(requirement_id, {})


def get_answer_label(requirement_id: str, answer: object) -> dict | None:
    """Return label/description/best_for/watch_out for a specific answer value."""
    enrichment = get_enrichment(requirement_id)
    answer_labels = enrichment.get("answer_labels", {})
    if isinstance(answer, bool):
        key = "true" if answer else "false"
    elif answer is None:
        return None
    else:
        key = str(answer)
    return answer_labels.get(key)
