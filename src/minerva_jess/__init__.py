"""
Minerva-Jess: Video Intelligence Agent SDK

Jess searches video libraries for insights on markets, investments,
and financial strategy. Connects to the Orca gateway for all
video intelligence operations.

Example:
    from minerva_jess import JessAgent, Settings

    settings = Settings()
    agent = JessAgent(settings)
    result = await agent.query("What are the key risks in emerging markets?")
"""

from minerva_jess.agent import JessAgent, JessAgentSync
from minerva_jess.config import Settings, AgentConfig
from minerva_jess.models import AgentResponse, VideoInfo, VideoSegment

__version__ = "1.0.0"
__all__ = [
    "JessAgent",
    "JessAgentSync",
    "Settings",
    "AgentConfig",
    "AgentResponse",
    "VideoInfo",
    "VideoSegment",
]
