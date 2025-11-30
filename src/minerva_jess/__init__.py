"""
Minerva-Jess: Video Intelligence Agent

Jess is a specialized AI agent that searches video libraries for insights
on markets, investments, and financial strategy. It communicates with the
Minerva video intelligence platform via MCP (Model Context Protocol).

Example usage:
    from minerva_jess import JessAgent, Settings

    settings = Settings()
    agent = JessAgent(settings)
    result = await agent.search("What are the key risks in emerging markets?")
"""

from minerva_jess.agent import JessAgent
from minerva_jess.config import Settings
from minerva_jess.models import SearchResult, VideoInfo, VideoSegment

__version__ = "1.0.0"
__all__ = [
    "JessAgent",
    "Settings",
    "SearchResult",
    "VideoInfo",
    "VideoSegment",
]
