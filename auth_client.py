"""
Auth client for API key retrieval.
Calls auth-mcp.urbancanary.workers.dev with fallback to environment variables.
"""

import os
import httpx

AUTH_MCP_URL = "https://auth-mcp.urbancanary.workers.dev"


def get_api_key(key_name: str, requester: str = "") -> str:
    """Get API key from auth-mcp service or environment variable fallback."""
    auth_token = os.environ.get("AUTH_MCP_TOKEN", "")

    if auth_token:
        try:
            response = httpx.get(
                f"{AUTH_MCP_URL}/key/{key_name}",
                params={"requester": requester} if requester else {},
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("key", data.get("value", ""))
        except Exception:
            pass  # Fall back to environment variable

    # Fallback to environment variable
    return os.environ.get(key_name, "")
