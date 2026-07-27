import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# AWS Documentation MCP server endpoint.
# Set AWS_DOCS_MCP_ENDPOINT in the AgentCore runtime env vars to activate.
_AWS_DOCS_MCP_ENDPOINT = os.environ.get("AWS_DOCS_MCP_ENDPOINT", "")


def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCPClient pointing to the AWS Documentation MCP server.

    Raises RuntimeError if AWS_DOCS_MCP_ENDPOINT is not configured.
    """
    if not _AWS_DOCS_MCP_ENDPOINT:
        raise RuntimeError(
            "AWS_DOCS_MCP_ENDPOINT is not set — cannot create MCP client"
        )
    return MCPClient(lambda: streamablehttp_client(_AWS_DOCS_MCP_ENDPOINT))


def is_mcp_configured() -> bool:
    """Returns True when an MCP endpoint has been configured via env var."""
    return bool(_AWS_DOCS_MCP_ENDPOINT)
