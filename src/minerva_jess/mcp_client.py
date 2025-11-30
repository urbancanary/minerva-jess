"""
Minerva MCP Client

This module provides a client for communicating with the Minerva video
intelligence platform via the Model Context Protocol (MCP).

All video search, transcript access, and metadata operations go through
this client, ensuring clean separation between Jess and Minerva.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from minerva_jess.config import Settings, VIDEO_CATALOG
from minerva_jess.models import VideoInfo, VideoSegment

logger = logging.getLogger(__name__)


class MinervaClientError(Exception):
    """Raised when communication with Minerva MCP fails."""

    pass


class MinervaMCPClient:
    """
    Client for the Minerva MCP server.

    Provides methods for searching video transcripts, listing videos,
    and retrieving video metadata through the MCP protocol.

    Example:
        async with MinervaMCPClient(settings) as client:
            results = await client.search_videos("AI bubble risks")
            for segment in results:
                print(f"{segment.title} at {segment.timestamp}")
    """

    def __init__(self, settings: Settings):
        """
        Initialize the Minerva MCP client.

        Args:
            settings: Application settings containing MCP connection details
        """
        self.settings = settings
        self._session: Optional[ClientSession] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "MinervaMCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """
        Establish connection to the Minerva MCP server.

        Raises:
            MinervaClientError: If connection fails
        """
        try:
            self._http_client = httpx.AsyncClient(
                base_url=self.settings.minerva_mcp_url,
                timeout=30.0,
                headers=self._build_headers(),
            )
            logger.info(f"Connected to Minerva MCP at {self.settings.minerva_mcp_url}")
        except Exception as e:
            raise MinervaClientError(f"Failed to connect to Minerva MCP: {e}") from e

    async def disconnect(self) -> None:
        """Close the connection to Minerva MCP."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("Disconnected from Minerva MCP")

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for MCP requests."""
        headers = {"Content-Type": "application/json"}
        if self.settings.minerva_mcp_token:
            headers["Authorization"] = f"Bearer {self.settings.minerva_mcp_token}"
        return headers

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call an MCP tool on the Minerva server.

        Args:
            tool_name: Name of the MCP tool to invoke
            arguments: Tool arguments

        Returns:
            Tool result as a dictionary

        Raises:
            MinervaClientError: If the tool call fails
        """
        if not self._http_client:
            raise MinervaClientError("Not connected to Minerva MCP")

        try:
            response = await self._http_client.post(
                "/mcp/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise MinervaClientError(
                f"MCP tool call failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise MinervaClientError(f"MCP tool call error: {e}") from e

    async def search_videos(
        self,
        query: str,
        max_results: Optional[int] = None,
        use_semantic: bool = True,
    ) -> list[VideoSegment]:
        """
        Search video transcripts for relevant content.

        Uses Minerva's hybrid search (FTS5 + embeddings) to find
        the most relevant video segments matching the query.

        Args:
            query: Search query text
            max_results: Maximum number of results (default from settings)
            use_semantic: Whether to use semantic/embedding search

        Returns:
            List of matching video segments, sorted by relevance
        """
        max_results = max_results or self.settings.max_search_results

        try:
            result = await self._call_tool(
                "minerva_search",
                {
                    "query": query,
                    "limit": max_results,
                    "use_semantic": use_semantic,
                },
            )

            segments = []
            for item in result.get("results", []):
                segment = VideoSegment.from_mcp_result(item)

                # Enrich with catalog metadata if available
                if segment.video_id in VIDEO_CATALOG:
                    catalog = VIDEO_CATALOG[segment.video_id]
                    if not segment.title or segment.title.startswith("Video "):
                        segment.title = catalog.get("title", segment.title)

                if segment.relevance >= self.settings.min_relevance_score:
                    segments.append(segment)

            logger.info(f"Search returned {len(segments)} segments for '{query}'")
            return segments

        except MinervaClientError:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise MinervaClientError(f"Video search failed: {e}") from e

    async def list_videos(self) -> list[VideoInfo]:
        """
        List all available videos in the library.

        Returns:
            List of video metadata objects
        """
        try:
            result = await self._call_tool("minerva_list_videos", {})

            videos = []
            for item in result.get("videos", []):
                video_id = item.get("video_id", "")
                catalog = VIDEO_CATALOG.get(video_id, {})

                video = VideoInfo(
                    video_id=video_id,
                    title=catalog.get("title", item.get("title", f"Video {video_id}")),
                    duration=item.get("duration", 0),
                    duration_formatted=self._format_duration(item.get("duration", 0)),
                    url=f"https://youtube.com/watch?v={video_id}",
                    topics=catalog.get("topics", []),
                    publish_date=catalog.get("publish_date"),
                    view_count=catalog.get("view_count", 0),
                    featured=catalog.get("featured", False),
                    description=catalog.get("description", ""),
                    chapter_count=item.get("chapters", 0),
                )
                videos.append(video)

            return videos

        except Exception as e:
            logger.error(f"Failed to list videos: {e}")
            raise MinervaClientError(f"Failed to list videos: {e}") from e

    async def get_video_info(self, video_id: str) -> Optional[VideoInfo]:
        """
        Get detailed information about a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoInfo if found, None otherwise
        """
        try:
            result = await self._call_tool(
                "minerva_get_video",
                {"video_id": video_id},
            )

            if not result.get("found"):
                return None

            catalog = VIDEO_CATALOG.get(video_id, {})

            return VideoInfo(
                video_id=video_id,
                title=catalog.get("title", result.get("title", f"Video {video_id}")),
                duration=result.get("duration", 0),
                duration_formatted=self._format_duration(result.get("duration", 0)),
                url=f"https://youtube.com/watch?v={video_id}",
                topics=catalog.get("topics", []),
                publish_date=catalog.get("publish_date"),
                view_count=catalog.get("view_count", 0),
                featured=catalog.get("featured", False),
                description=catalog.get("description", ""),
                chapter_count=result.get("chapters", 0),
            )

        except Exception as e:
            logger.warning(f"Failed to get video info for {video_id}: {e}")
            return None

    async def get_transcript_segment(
        self,
        video_id: str,
        start_time: float,
        end_time: Optional[float] = None,
    ) -> Optional[str]:
        """
        Get transcript text for a specific time range.

        Args:
            video_id: YouTube video ID
            start_time: Start time in seconds
            end_time: End time in seconds (optional)

        Returns:
            Transcript text for the time range, or None if not found
        """
        try:
            result = await self._call_tool(
                "minerva_get_transcript",
                {
                    "video_id": video_id,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            return result.get("text")

        except Exception as e:
            logger.warning(f"Failed to get transcript segment: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if the Minerva MCP server is healthy.

        Returns:
            True if server is responding, False otherwise
        """
        try:
            if not self._http_client:
                return False

            response = await self._http_client.get("/health")
            return response.status_code == 200

        except Exception:
            return False

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


@asynccontextmanager
async def get_minerva_client(
    settings: Optional[Settings] = None,
) -> AsyncGenerator[MinervaMCPClient, None]:
    """
    Context manager for creating a Minerva MCP client.

    Example:
        async with get_minerva_client() as client:
            results = await client.search_videos("market trends")
    """
    from minerva_jess.config import get_settings

    settings = settings or get_settings()
    client = MinervaMCPClient(settings)

    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
