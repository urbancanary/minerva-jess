"""
Stub auth_client for local development.
Reads API keys from environment variables.
"""

import os


def get_api_key(key_name: str, requester: str = "") -> str:
    """Get API key from environment variable."""
    return os.environ.get(key_name, "")
