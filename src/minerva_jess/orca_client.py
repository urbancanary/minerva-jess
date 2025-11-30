"""
Orca MCP Client

Client for communicating with the Orca gateway via MCP protocol.
All video intelligence operations go through Orca.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from minerva_jess.config import Settings, VIDEO_CATALOG
from minerva_jess.models import VideoInfo, VideoSegment

logger = logging.getLogger(__name__)

# Path to Orca MCP
ORCA_MCP_PATH = Path("/Users/andyseaman/Notebooks/mcp_central/orca_mcp")


class OrcaClientError(Exception):
    """Raised when communication with Orca fails."""
    pass


class OrcaMCPClient:
    """
    Client for the Orca MCP gateway.

    Connects to Orca via subprocess/stdio and calls MCP tools
    for video search, synthesis, and listing.

    Example:
        client = OrcaMCPClient(settings)
        results = await client.video_search("AI market risks")
    """

    def __init__(self, settings: Settings):
        """Initialize the Orca MCP client."""
        self.settings = settings
        self._process: Optional[subprocess.Popen] = None

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call an Orca MCP tool.

        For simplicity in same-machine deployment, we import and call
        Orca's tools directly rather than spawning subprocess.
        """
        try:
            # Add Orca to path
            if str(ORCA_MCP_PATH) not in sys.path:
                sys.path.insert(0, str(ORCA_MCP_PATH))
            if str(ORCA_MCP_PATH.parent) not in sys.path:
                sys.path.insert(0, str(ORCA_MCP_PATH.parent))

            # Import Orca's video tools
            from orca_mcp.tools.video_gateway import (
                video_search,
                video_list,
                video_synthesize,
                video_get_transcript,
                video_keyword_search
            )

            # Route to appropriate tool
            if tool_name == "video_search":
                return await video_search(
                    arguments.get("query", ""),
                    arguments.get("max_results", 10)
                )
            elif tool_name == "video_list":
                return await video_list()
            elif tool_name == "video_synthesize":
                return await video_synthesize(
                    arguments.get("query", ""),
                    arguments.get("video_results", []),
                    arguments.get("tone", "professional")
                )
            elif tool_name == "video_get_transcript":
                return await video_get_transcript(
                    arguments.get("video_id", "")
                )
            elif tool_name == "video_keyword_search":
                return await video_keyword_search(
                    arguments.get("query", ""),
                    arguments.get("max_results", 10)
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Orca tool call failed: {e}")
            raise OrcaClientError(f"Failed to call {tool_name}: {e}") from e

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
    ) -> list[VideoSegment]:
        """
        Search video transcripts.

        Args:
            query: Search query text
            max_results: Maximum number of results

        Returns:
            List of matching video segments
        """
        max_results = max_results or self.settings.max_search_results

        result = await self._call_tool("video_search", {
            "query": query,
            "max_results": max_results
        })

        segments = []
        for item in result.get("results", []):
            segment = VideoSegment.from_search_result(item)

            # Enrich with catalog metadata
            if segment.video_id in VIDEO_CATALOG:
                catalog = VIDEO_CATALOG[segment.video_id]
                if not segment.title or segment.title.startswith("Video "):
                    segment.title = catalog.get("title", segment.title)

            segments.append(segment)

        logger.info(f"Search returned {len(segments)} segments for '{query}'")
        return segments

    async def synthesize(
        self,
        query: str,
        segments: list[VideoSegment],
        tone: str = "professional"
    ) -> str:
        """
        Synthesize an answer from video segments.

        Args:
            query: The original query
            segments: Video segments to synthesize from
            tone: Response tone

        Returns:
            Synthesized answer text
        """
        if not segments:
            return f"No matching content found for '{query}'."

        # Convert segments to dicts for Orca
        video_results = [
            {
                "video_id": s.video_id,
                "title": s.title,
                "text": s.full_text or s.text,
                "timestamp": s.timestamp,
                "url": s.url,
                "start_time": s.start_time
            }
            for s in segments[:5]
        ]

        result = await self._call_tool("video_synthesize", {
            "query": query,
            "video_results": video_results,
            "tone": tone
        })

        if "error" in result:
            logger.error(f"Synthesis failed: {result['error']}")
            return self._format_fallback(segments)

        return result.get("answer", "Unable to synthesize answer.")

    async def list_videos(self) -> list[VideoInfo]:
        """
        List all available videos.

        Returns:
            List of video metadata
        """
        result = await self._call_tool("video_list", {})

        videos = []
        for item in result.get("videos", []):
            video_id = item.get("video_id", "")
            catalog = VIDEO_CATALOG.get(video_id, {})

            video = VideoInfo(
                video_id=video_id,
                title=catalog.get("title", item.get("title", f"Video {video_id}")),
                duration=item.get("duration", 0),
                duration_formatted=item.get("duration_formatted", ""),
                url=item.get("url", f"https://youtube.com/watch?v={video_id}"),
                topics=catalog.get("topics", []),
                publish_date=catalog.get("publish_date"),
                view_count=catalog.get("view_count", 0),
                featured=catalog.get("featured", False),
                description=catalog.get("description", ""),
                chapter_count=item.get("chapters", 0),
            )
            videos.append(video)

        return videos

    async def get_transcript(self, video_id: str) -> Optional[dict]:
        """
        Get transcript for a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript data or None
        """
        result = await self._call_tool("video_get_transcript", {
            "video_id": video_id
        })

        if "error" in result:
            return None

        return result

    @staticmethod
    def _format_fallback(segments: list[VideoSegment]) -> str:
        """Format segments as simple text (fallback)."""
        lines = [f"Found {len(segments)} relevant segment(s):\n"]
        for s in segments[:5]:
            lines.append(f"**{s.title}** at {s.timestamp}")
            lines.append(f"{s.text}\n")
        return "\n".join(lines)


# Convenience function for getting a client
def get_orca_client(settings: Optional[Settings] = None) -> OrcaMCPClient:
    """Get an Orca MCP client instance."""
    from minerva_jess.config import get_settings
    settings = settings or get_settings()
    return OrcaMCPClient(settings)
