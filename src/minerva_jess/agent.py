"""
Jess - Video Intelligence Agent

Jess searches video libraries for insights on markets, investments,
and financial strategy. Connects to the Orca gateway for all
video intelligence operations.

Example:
    from minerva_jess import JessAgent, Settings

    settings = Settings()
    agent = JessAgent(settings)

    result = await agent.query("What are the risks in AI investments?")
    print(result.content)
"""

import logging
import re
from typing import Optional

from minerva_jess.config import Settings, AgentConfig, get_settings, get_agent_config
from minerva_jess.orca_client import OrcaMCPClient, get_orca_client
from minerva_jess.models import AgentResponse, VideoSegment

logger = logging.getLogger(__name__)


class JessAgent:
    """
    Jess - Video Intelligence Agent.

    Searches video libraries and synthesizes answers
    using the Orca gateway.
    """

    # Patterns indicating help/recommendation requests
    HELP_PATTERNS = [
        "help",
        "what should i watch",
        "recommend",
        "suggestion",
        "popular",
        "most viewed",
        "best video",
        "what do you have",
        "what videos",
        "latest",
        "newest",
        "recent",
        "featured",
        "top video",
        "where to start",
        "what can you show",
        "what topics",
        "what content",
        "list videos",
        "available videos",
        "show videos",
    ]

    def __init__(
        self,
        settings: Optional[Settings] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize the Jess agent.

        Args:
            settings: Application settings
            config: Agent configuration (name, icon, etc.)
        """
        self.settings = settings or get_settings()
        self.config = config or get_agent_config()
        self._client: Optional[OrcaMCPClient] = None

    @property
    def client(self) -> OrcaMCPClient:
        """Get or create the Orca client."""
        if self._client is None:
            self._client = get_orca_client(self.settings)
        return self._client

    @property
    def name(self) -> str:
        """Agent display name."""
        return self.config.agent_name

    @property
    def icon(self) -> str:
        """Agent icon."""
        return self.config.agent_icon

    async def query(self, user_query: str) -> AgentResponse:
        """
        Process a user query and return a response.

        Args:
            user_query: The user's question or request

        Returns:
            AgentResponse with content and optional video embed
        """
        # Clean the query
        query = self._clean_query(user_query)

        # Check if this is a help request
        if self._is_help_query(query):
            return await self.get_recommendations(query)

        # Perform video search
        return await self._search_and_respond(query)

    async def get_recommendations(self, query: str = "") -> AgentResponse:
        """
        Get video recommendations.

        Args:
            query: Optional filter (e.g., "popular", "recent")

        Returns:
            AgentResponse with recommendations
        """
        videos = await self.client.list_videos()

        if not videos:
            return AgentResponse(
                content="No videos are currently available in the library.",
                success=True,
                clickable_examples=self._get_example_queries(),
            )

        query_lower = query.lower()

        # Sort based on query
        if "popular" in query_lower or "most viewed" in query_lower:
            sorted_videos = sorted(videos, key=lambda v: v.view_count, reverse=True)
            intro = "Here are the most popular videos:"
        elif "latest" in query_lower or "newest" in query_lower:
            sorted_videos = sorted(videos, key=lambda v: v.publish_date or "", reverse=True)
            intro = "Here are the latest videos:"
        elif "featured" in query_lower:
            sorted_videos = [v for v in videos if v.featured] or videos
            intro = "Here are the featured videos:"
        else:
            featured = [v for v in videos if v.featured]
            non_featured = sorted(
                [v for v in videos if not v.featured],
                key=lambda v: v.view_count,
                reverse=True,
            )
            sorted_videos = featured + non_featured
            intro = "Here's what's available in the video library:"

        # Build response
        content_parts = [intro, ""]

        for video in sorted_videos[:10]:
            content_parts.append(f"**{video.title}** ({video.duration_formatted})")
            if video.description:
                content_parts.append(f"  {video.description}")
            if video.topics:
                content_parts.append(f"  Topics: {', '.join(video.topics[:4])}")
            content_parts.append("")

        content_parts.append("Ask me about any topic to search the transcripts!")

        # Top video for embedding
        top_video = sorted_videos[0] if sorted_videos else None
        video_info = None
        if top_video:
            video_info = {
                "video_id": top_video.video_id,
                "start_time": 0,
                "title": top_video.title,
                "timestamp": "0:00",
                "url": top_video.youtube_url,
            }

        return AgentResponse(
            content="\n".join(content_parts),
            success=True,
            video_info=video_info,
            clickable_examples=self._get_example_queries(),
        )

    async def _search_and_respond(self, query: str) -> AgentResponse:
        """
        Search videos and synthesize a response.

        Args:
            query: The search query

        Returns:
            AgentResponse with answer
        """
        try:
            # Search via Orca
            segments = await self.client.search(query)

            if not segments:
                return AgentResponse(
                    content=self._no_results_message(query),
                    success=True,
                    clickable_examples=self._get_example_queries(),
                )

            # Get top result for video embed
            top_segment = segments[0]
            video_info = {
                "video_id": top_segment.video_id,
                "start_time": int(top_segment.start_time),
                "title": top_segment.title,
                "timestamp": top_segment.timestamp,
                "url": top_segment.url,
            }

            # Synthesize answer via Orca
            answer = await self.client.synthesize(query, segments)

            return AgentResponse(
                content=answer,
                success=True,
                video_info=video_info,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return AgentResponse(
                content=f"I encountered an error searching the video library: {e}",
                success=False,
            )

    def _no_results_message(self, query: str) -> str:
        """Message when no results found."""
        return (
            f"I searched the video library but couldn't find specific content about "
            f"'{query}'. Would you like me to search for related topics?"
        )

    def _clean_query(self, query: str) -> str:
        """Remove @jess mention and clean up."""
        cleaned = re.sub(r"@jess\s*", "", query, flags=re.IGNORECASE)
        return cleaned.strip()

    def _is_help_query(self, query: str) -> bool:
        """Check if query is asking for help."""
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in self.HELP_PATTERNS)

    def _get_example_queries(self) -> list[str]:
        """Example queries for suggestions."""
        name = self.name.lower()
        return [
            f"@{name} What did Andy say about AI?",
            f"@{name} market outlook",
            f"@{name} list videos",
        ]


# Synchronous wrapper
class JessAgentSync:
    """
    Synchronous wrapper for JessAgent.

    Use when calling from synchronous code.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize the sync wrapper."""
        self._agent = JessAgent(settings, config)

    def query(self, user_query: str) -> AgentResponse:
        """Process a query synchronously."""
        import asyncio
        return asyncio.run(self._agent.query(user_query))

    def get_recommendations(self, query: str = "") -> AgentResponse:
        """Get recommendations synchronously."""
        import asyncio
        return asyncio.run(self._agent.get_recommendations(query))
