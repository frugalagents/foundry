# Platform Advisor — Monthly Knowledge Update Sources

> **Purpose:** Defines ALL sources that feed the Platform Advisor KB, organized by tier and cadence. Used for monthly update pipeline.

---

## Update Cadence

```
Week 1: Scan sources → identify changes (what's new/changed since last update)
Week 2: Draft new/updated content (create entries, update docs)
Week 3: Review + approve (human gate)
Week 4: Upload to Space + update graph (publish)
```

---

## Tier 1: AWS-Specific (Service Mappings, Implementation Details)

| Source | Access Method | What It Feeds | Scan Cadence |
|--------|-------------|---------------|--------------|
| AWS What's New | Web (aws.amazon.com/new/) + filter: Bedrock, AgentCore, AI/ML | Service launches that alter implementation options | Weekly |
| AWS Documentation | MCP: `aws_documentation__Query` | AgentCore, Bedrock — authoritative specs | On launch |
| AWS Prescriptive Guidance | MCP: `aws_knowledge_mcp_server__aws_search_documentation` | Reference architectures, patterns | Monthly |
| AWS Workshops | workshops.aws + MCP | Hands-on labs for customer recommendations | Quarterly |
| AWS Knowledge MCP | MCP: `aws_knowledge_mcp_server` | Workshops, blogs, solutions | Monthly |
| AWS Highspot | MCP: `aws_highspot_mcp` | Internal sales positioning, competitive intel | Monthly |
| AWS re:Invent / re:Inforce / Summit Recordings | youtube.com/@AWSEventsChannel | Keynotes, breakout sessions, architectural deep-dives | Annually + Summits |
| AWS Solutions Library | aws.amazon.com/solutions/ | Deployable reference architectures | Monthly |

---

## Tier 2: Industry / Vendor-Neutral (Patterns, Innovations, Competitive)

| Source | URL | What It Feeds | Scan Cadence |
|--------|-----|---------------|--------------|
| Anthropic Engineering Blog | anthropic.com/engineering | Advanced tool use, MCP spec updates, model capabilities | Bi-weekly |
| OpenAI Blog/Research | openai.com/blog | Agent reasoning, function calling advances, Swarm patterns | Bi-weekly |
| Google DeepMind / Vertex AI | deepmind.google, cloud.google.com/vertex-ai | Multi-agent research, Gemini agent patterns, A2A protocol | Monthly |
| Microsoft AI / Semantic Kernel Blog | devblogs.microsoft.com | AutoGen, Copilot Studio, enterprise agent patterns | Monthly |
| Hugging Face Blog | huggingface.co/blog | Open-source model releases, agent tooling | Monthly |
| LangChain / LangGraph Blog | blog.langchain.dev | LangGraph updates, orchestration patterns, LangSmith | Bi-weekly |
| CrewAI Blog/Changelog | docs.crewai.com/changelog | Multi-agent patterns, new features | Monthly |
| LlamaIndex Blog | blog.llamaindex.ai | Data agent patterns, RAG innovations | Monthly |
| Cohere Blog | cohere.com/blog | Enterprise RAG, reranking, agent patterns | Monthly |
| MCP Specification | github.com/modelcontextprotocol/specification | Protocol changes, new capabilities | Monthly |
| A2A Protocol | github.com/google/A2A | Agent-to-agent interop standard | Monthly |

---

## Tier 3: Research & Academic (Empirical Laws, New Coordination Patterns)

| Source | URL | What It Feeds | Scan Cadence |
|--------|-----|---------------|--------------|
| arXiv — cs.AI, cs.MA | arxiv.org/list/cs.AI, arxiv.org/list/cs.MA | Multi-agent coordination, planning algorithms, new patterns | Monthly |
| arXiv — cs.SE | arxiv.org/list/cs.SE | Software engineering for AI agents, AIDLC research | Quarterly |
| Amazon Science | amazon.science (repo.amazon.science) | Amazon's research papers on agents | Monthly |
| Papers With Code | paperswithcode.com | State-of-art benchmarks for agent tasks | Quarterly |
| NeurIPS / ICML / ICLR proceedings | Conference sites | Foundational agent architecture papers | Annually |
| Semantic Scholar (AI Agents) | semanticscholar.org | Cross-referencing cited research | Quarterly |

---

## Tier 4: Industry Analyst & Market (Trends, Competitive, Customer Framing)

| Source | URL | What It Feeds | Scan Cadence |
|--------|-----|---------------|--------------|
| Gartner Hype Cycle for AI | (internal access) | Market framing, pattern maturity stages | Annually |
| Gartner MQ: AI Platforms | (internal access) | Vendor positioning | Annually |
| Forrester Wave: AI Agents | (internal access) | Enterprise adoption maturity | Annually |
| McKinsey AI Reports | mckinsey.com/capabilities/ai | Executive-level framing, ROI data, adoption curves | Quarterly |
| BCG AI Reports | bcg.com/capabilities/artificial-intelligence | Enterprise transformation patterns | Quarterly |
| a16z AI Blog | a16z.com/ai | Emerging patterns, startup ecosystem, investment signals | Monthly |
| Sequoia AI perspectives | sequoiacap.com/article | Investment thesis → where industry is heading | Quarterly |
| The Information / Semafor | theinformation.com | Industry intel, company strategies | Weekly (scan) |

---

## Tier 5: Community / Practitioner (Real-World Patterns, Edge Cases)

| Source | URL | What It Feeds | Scan Cadence |
|--------|-----|---------------|--------------|
| Hacker News (filtered: AI agents) | news.ycombinator.com | Practitioner feedback on what works/breaks | Weekly (scan) |
| Reddit r/MachineLearning, r/LangChain | reddit.com | Community patterns, failure reports | Bi-weekly |
| AI Engineer podcast / newsletter | aiengineer.com | Practitioner interviews, pattern discussions | Bi-weekly |
| Latent Space podcast | latent.space | Deep technical interviews with agent builders | Bi-weekly |
| FrugalAgents (your own!) | frugalagents.substack.com | Your published patterns — track what resonates | Monthly |
| AWS Quick Community | community.amazonquicksight.com | Quick Automate patterns, user workflows | Monthly |
| GitHub Trending (AI/agents) | github.com/trending | New frameworks, tools, emerging patterns | Weekly |
| Dev.to / Medium (AI agents tag) | dev.to, medium.com | Tutorial-level patterns, beginner implementations | Monthly |

---

## Tier 6: Competitive / Alternative Platforms

| Source | Access | What It Feeds | Scan Cadence |
|--------|--------|---------------|--------------|
| Azure AI Agent Service docs | learn.microsoft.com | Competitive positioning, multi-cloud patterns | Monthly |
| Google Vertex AI Agent Builder | cloud.google.com/vertex-ai | Same | Monthly |
| Salesforce Agentforce | salesforce.com/agentforce | Enterprise SaaS agent platform patterns | Quarterly |
| ServiceNow AI Agents | servicenow.com | Enterprise workflow agent patterns | Quarterly |
| Databricks Mosaic AI | databricks.com | Data platform → agent platform evolution | Quarterly |
| Snowflake Cortex Agents | snowflake.com | Data-centric agent approach | Quarterly |
| Palantir AIP | palantir.com | Ontology-driven agent architecture | Quarterly |

---

## What Each Tier Feeds in the KB

| KB Content | Primary Tiers |
|------------|---------------|
| **Decision Logic** (constraints → patterns) | Tiers 3, 4, 5 (research, market, practitioner) |
| **Architecture Patterns** | Tiers 2, 3 (agnostic) + Tier 1 (AWS implementation) |
| **Constraint→Innovation Map** | Tiers 2, 3, 4 (ENTIRE industry, not just AWS) |
| **Anti-Patterns** | Tiers 5, 6 (community reports, competitive failures) + your engagements |
| **AWS Service Mapping** | Tier 1 only |
| **AgentCore Component Mapping** | Tier 1 only |
| **Compliance Overlays** | Tier 4 (analyst reports) + regulatory body publications |
| **Competitive Context** | Tier 6 |
| **Framework Comparison** | Tier 2 (vendor blogs, changelogs) |
| **Graph Edge Weights** | Tiers 5 + your engagements (calibration from field) |

---

## Automation Approach

| Phase | Method | Tool |
|-------|--------|------|
| **Now (Manual)** | You + Quick scan sources monthly | Quick Chat Agent with MCP |
| **Next (Semi-auto)** | Scheduled Agent scans sources → surfaces "what's new" → you approve | Quick Scheduled Agent |
| **Future (Agentic)** | Agent monitors RSS/APIs → drafts KB updates → you approve in pipeline | Quick Automate + Scheduled Agent |

---

## Access Methods Summary

| Method | Sources It Reaches | Available Today? |
|--------|-------------------|-----------------|
| Web Search (built-in) | Tiers 1-5 (whatever's publicly indexed) | ✅ Yes |
| AWS Documentation MCP | Tier 1 (AWS docs) | ✅ Yes |
| AWS Knowledge MCP | Tier 1 (workshops, guides, blogs) | ✅ Yes |
| AWS Highspot MCP | Tier 1 (internal sales) | ✅ Yes |
| Browser automation | Tiers 2-6 (any website) | ✅ Yes (load browser skill) |
| GitHub API / MCP | Tier 2 (framework repos, changelogs) | ⚠️ No MCP — use web search |
| Amazon Science | Tier 3 (research papers) | ❌ No MCP — use web search |
| Analyst reports | Tier 4 (Gartner, Forrester) | ❌ Paywalled — manual only |
