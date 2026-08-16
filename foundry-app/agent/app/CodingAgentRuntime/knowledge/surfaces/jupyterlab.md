---
type: platform-component
title: JupyterLab Surface
description: making coding agent capability available inside JupyterLab — for quant researchers, data scientists, and ML engineers who work primarily in notebooks rather than IDE or CLI
group: surfaces
tags: [surfaces, jupyterlab, jupyter, notebook, quant, data-science, kernel, mcp-server]
timestamp: 2026-08-14T00:00:00Z
status: candidate
traversal: conditional
trigger: [jupyterlab, jupyter, notebook, quant-research, data-science, data-scientist, ml-engineer, jupyter-surface, python-research, shadow-it-jupyter]
decision-question: "Do you have a significant population of developers — quant researchers, data scientists, or ML engineers — who work primarily in JupyterLab and will not adopt a coding agent platform that requires them to leave their notebook environment?"
---

JupyterLab is the primary development environment for quantitative researchers,
data scientists, and ML engineers at many enterprises. These populations represent
some of the highest-leverage AI tool use cases — complex algorithm development,
iterative data analysis, model prototyping — but they are also the most likely
to use personal AI accounts (Claude.ai, ChatGPT) if the corporate platform
doesn't meet them in their environment.

Claude Code and most coding agent SaaS products do not have a JupyterLab extension.
The gap is real and creates a shadow-IT risk: quants who find the corporate
platform inaccessible from JupyterLab will route work through personal accounts,
bypassing all governance controls.

The solution is a **Jupyter MCP server** — an MCP-protocol server that wraps
the Jupyter Server API, giving the agent the ability to read and write notebook
cells, execute code in kernels, inspect outputs, and interact with the notebook
environment natively. This is a custom build — no off-the-shelf product exists —
but it is well-scoped and builds on the Jupyter Server REST API.

## The JupyterLab Integration Architecture

```
Developer (in JupyterLab browser UI)
  └── Jupyter MCP Client extension (JupyterLab frontend plugin)
        └── Jupyter MCP Server (Python process, sidecar to JupyterHub or local)
              ├── Jupyter Server API (REST/WebSocket to notebook server)
              │     ├── Read cell content
              │     ├── Write cell content
              │     ├── Execute cell (via kernel)
              │     └── Read cell output (stdout, stderr, rich output)
              └── MCP gateway connection → agent model (Bedrock)
```

The developer interacts with the agent through a sidebar panel or keyboard shortcut
in JupyterLab — similar to how VS Code's agent panel works. The agent reads context
from the notebook, proposes changes, and can execute cells on the developer's request.

## Decisions

**Where does the Jupyter MCP server run?**
- Sidecar to JupyterHub — for enterprise JupyterHub deployments (common at large
  quantitative finance, pharma, and research organizations); the MCP server runs
  as a sidecar container in the same pod or alongside the JupyterHub single-user
  server; it connects to the notebook server via localhost; each developer gets
  their own MCP server instance; scales with JupyterHub's user scaling
- Local process (local JupyterLab) — for developers running JupyterLab locally;
  the MCP server runs as a Python process started alongside JupyterLab; developer
  starts it via a `jupyter lab --MCP.enabled=True` flag or a startup script;
  simpler deployment; used in on-prem or local developer setups
- Centralized service (not recommended for multi-user) — a single MCP server
  serving multiple users; complex session isolation; not recommended; each user
  should have their own MCP server instance for notebook state isolation

**What notebook operations does the agent need?**
- Read-only (explanation and review) — agent reads cell content and outputs;
  can explain code, identify issues, suggest improvements in chat; does not
  modify cells or execute code; safest initial deployment
- Read + write cells (no execution) — agent can read cells and propose new or
  modified cell content; developer reviews and executes manually; similar to
  IDE plan-review mode; balanced safety and utility
- Read + write + execute — agent can read cells, write new cells, and trigger
  cell execution; full agentic loop within the notebook; most powerful; requires
  strong guardrails (execution limits, output size caps, kernel restart protection)
- Recommended phased rollout: read-only for 4-6 weeks, then read+write, then
  evaluate execution capability based on observed behavior

**How is notebook state managed in the agent context?**
- Active notebook context — the agent sees the currently open notebook: cell
  source, cell outputs, kernel state variables; this is the minimum viable context
  for useful assistance; does not require indexing the full notebook history
- Extended context (notebook + imports + data shapes) — the agent additionally
  reads the kernel's namespace (variable names and types), the output of the most
  recent data loading cells (e.g., `df.head()`), and the import block; gives the
  agent enough context to reason about the data and make relevant suggestions;
  requires a kernel introspection tool call
- Notebook + connected codebase — the agent can also read Python modules imported
  into the notebook from the project codebase; requires the code intelligence
  (RAG) layer to be active; most powerful for research-to-production workflows

**How is the JupyterLab frontend plugin delivered?**
- JupyterLab extension (npm package) — a JupyterLab frontend extension that adds
  the agent sidebar panel and keyboard shortcuts; installed via `pip install
  jupyter-coding-agent` (extension bundled with Python package) or `jupyter labextension
  install`; compatible with JupyterLab 3.x and 4.x; delivered to all users via
  the JupyterHub Docker image or a shared extension registry
- Server-side notebook extension (no frontend build) — a Jupyter server extension
  that adds an API endpoint to the notebook server; developers access the agent
  via a separate browser tab or HTTP client; lower UX quality but no frontend
  build required; useful for environments where JupyterLab extension installation
  is restricted

**What guardrails apply specifically to the Jupyter surface?**
- Kernel execution limits — if the agent can trigger cell execution, cap the
  number of cells executable per session (e.g., 10 cells) and total execution
  time (e.g., 60 seconds); prevent runaway computations
- Output size cap — large cell outputs (accidentally printing a full dataframe,
  a model training log) should be truncated before entering agent context;
  prevents context flooding and token cost explosion
- No kernel restart or shutdown — the agent should never be able to restart or
  shut down the Jupyter kernel; this would destroy in-memory state the developer
  may have spent hours building; enforced as a tool restriction in the MCP server
- No file system writes outside the notebook directory — the agent's file system
  tools (if enabled) should be scoped to the notebook working directory; it should
  not write to system paths or other user directories

**How is the Jupyter surface authenticated to the platform?**
- JupyterHub OAuth → platform IdP — JupyterHub's OAuthenticator connects to the
  corporate IdP (Okta, Entra); the MCP server inherits the authenticated user
  identity from the JupyterHub session; no separate login for the agent
- Jupyter Server token + platform JWT — the MCP server authenticates to the
  Jupyter Server using the server's token (local trust); authenticates to the
  MCP gateway using the developer's platform JWT (from IdP); two auth boundaries
  that must both be satisfied; ensures the gateway knows who is using the agent

## Principles

- The Jupyter surface is a shadow-IT prevention measure, not a feature addition —
  if quants can't use the corporate platform from JupyterLab, they will use
  personal accounts; building this surface is primarily a governance decision,
  not a productivity optimization
- Execution capability requires additional trust-building — reading and writing
  cells is reversible (undo exists); executing code has side effects (API calls,
  data mutations, model training); introduce execution capability only after
  the population has established trust with the read/write phase
- Notebook context is rich and sensitive — notebooks often contain in-memory
  dataframes with customer or sensitive data, authentication tokens assigned to
  variables, and intermediate model outputs; the agent's context window management
  must be careful about what it reads and what gets logged in the session audit trail
- The Jupyter MCP server is a platform-maintained component — it cannot be a
  developer-run sidecar with no governance; it must be deployed and versioned by
  the platform team, authenticate to the MCP gateway using platform credentials,
  and produce audit-trail-compatible session logs

## Stack Options

**Jupyter MCP server (custom build)**
- Python + `jupyter_server` extension — build as a Jupyter server extension
  (Python package); accesses the Jupyter Server API via `tornado` HTTP client
  to `localhost:8888`; implements the MCP protocol over stdio or HTTP; deploy
  alongside JupyterHub single-user server; ~500-800 lines of Python for the
  core implementation
- `jupyter_client` library — for kernel interaction (variable inspection,
  cell execution); `jupyter_client.KernelManager` manages kernel connections;
  `execute_request` messages over ZeroMQ to the IPython kernel; capture
  `execute_reply` and `stream` messages as cell output
- MCP Python SDK (`mcp` package from Anthropic) — implements the MCP server
  protocol; tool definitions map to Jupyter Server API calls; tool results
  return cell content and outputs in the MCP tool result format

**JupyterLab frontend extension**
- JupyterLab extension (TypeScript/React) — sidebar panel with a chat interface;
  keyboard shortcut to send selected cell to agent; diff view for proposed cell
  changes; built with `@jupyterlab/extension` scaffold; distributed as a Python
  package that installs the lab extension automatically
- `@jupyter-widgets/base` (ipywidgets) — for a lower-friction approach that
  works in classic Notebook and JupyterLab without a full extension build;
  a widget-based UI in a notebook cell; less polished but deployable without
  admin rights to install lab extensions

**JupyterHub deployment**
- Zero to JupyterHub on Kubernetes — standard enterprise JupyterHub on EKS;
  single-user servers as pods; MCP server as an extra container in the pod spec
  (`singleuser.extraContainers`); shares network namespace with the notebook server;
  scales with JupyterHub's pod autoscaling
- SageMaker Studio (alternative) — AWS-native JupyterLab environment; does not
  support arbitrary sidecar containers; the Jupyter MCP server would need to run
  as a system terminal process; more constrained but no EKS infrastructure required

**Notebook-aware RAG (extended context)**
- Bedrock Knowledge Bases — index the Python codebase that notebooks import from;
  the MCP server calls the Knowledge Base at session start to retrieve relevant
  module documentation and function signatures; gives the agent project-level
  context beyond the open notebook

## Connects to

- [IDE Surface](ide.md) — the JupyterLab surface is a distinct surface from the
  IDE; developers may use both (IDE for production code, JupyterLab for research);
  the platform should support both simultaneously with consistent identity and
  policy enforcement
- [Code Intelligence](../knowledge-layer/code-intelligence.md) — notebooks that
  import from a codebase benefit from RAG over the codebase; code intelligence
  layer provides the indexed context the agent needs to understand imported modules
- [Policy Tiers](../access/policy-tiers.md) — quant researchers often need the
  innovation lab policy tier (broader tool access, experimental features); the
  Jupyter surface is the delivery mechanism for that tier in the notebook environment
- [MNPI](../access/mnpi.md) — quant notebooks frequently contain MNPI-adjacent
  code (trading strategies, model parameters, client position logic); session
  log sequestration rules for MNPI repos must extend to Jupyter sessions; notebook
  cell content containing MNPI must be handled under the same enhanced access controls

## Sources

- [Jupyter Server REST API](https://jupyter-server.readthedocs.io/en/latest/developers/rest-api.html) — to verify on first use — kernel management, content API, session API
- [jupyter_client — kernel protocol](https://jupyter-client.readthedocs.io/en/stable/) — to verify on first use — ZeroMQ messaging; execute_request; output capture
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — to verify on first use — MCP server implementation in Python
- [Zero to JupyterHub on Kubernetes](https://z2jh.jupyter.org/) — to verify on first use — JupyterHub on EKS; single-user pod configuration; sidecar containers
- [JupyterLab extension development](https://jupyterlab.readthedocs.io/en/stable/extension/extension_tutorial.html) — to verify on first use — TypeScript extension scaffold; lab extension packaging
