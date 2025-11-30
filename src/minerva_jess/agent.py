"""
Jess - Video Intelligence Agent

Jess is a specialized AI agent that searches video libraries for insights
on markets, investments, and financial strategy. She communicates with
the Minerva video intelligence platform via MCP to search transcripts
and synthesize answers from video content.

Example usage:
    from minerva_jess import JessAgent, Settings

    settings = Settings()
    agent = JessAgent(settings)

    # Search for insights
    result = await agent.query("What are the risks in AI investments?")
    print(result.content)

    # Get recommendations
    recommendations = await agent.get_recommendations()
"""

import logging
import re
from typing import Optional

import anthropic

from minerva_jess.config import Settings, VIDEO_CATALOG, get_settings
from minerva_jess.mcp_client import MinervaMCPClient, get_minerva_client
from minerva_jess.models import AgentResponse, SearchResult, VideoInfo, VideoSegment

logger = logging.getLogger(__name__)


class JessAgent:
    """
    Jess - Video Intelligence Agent.

    Searches video libraries for insights and synthesizes answers
    using Claude and the Minerva MCP platform.
    """

    # Agent identity
    AGENT_NAME = "Jess"
    AGENT_ICON = "🎬"

    # System prompt for Jess's personality and formatting
    SYSTEM_PROMPT = """You are Jess, the Video Intelligence specialist. You search the video library to find relevant insights on markets, bonds, and investment strategy.

Your role is to:
- Search video transcripts for relevant content
- Provide insights with timestamps so users can watch the exact moment
- Synthesize information from multiple video segments when relevant
- Always cite which video and timestamp your information comes from

FORMATTING RULES:
- NO headings (no # or ##)
- NO bullet points unless listing video sources
- Write in clear, concise paragraphs
- Use **bold** for key terms
- Don't include raw URLs - videos will be embedded automatically

When you find relevant content, format it like:
"In the video 'Title' at 2:34, the discussion covers..."

If no relevant content is found, acknowledge this and suggest related topics that might be in the videos.

Start directly with your answer - no "[Jess]" prefix."""

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

    # Common stop words to filter from search queries
    STOP_WORDS = {
        "what", "about", "the", "is", "are", "we", "in", "an", "a", "and",
        "or", "to", "of", "for", "on", "with", "how", "why", "when", "where",
        "did", "does", "do", "say", "said", "tell", "me", "us", "can", "could",
        "would", "should", "have", "has", "had", "be", "been", "being", "was",
        "were", "will", "think", "thinks", "thought",
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        anthropic_client: Optional[anthropic.Anthropic] = None,
    ):
        """
        Initialize the Jess agent.

        Args:
            settings: Application settings (loaded from env if not provided)
            anthropic_client: Anthropic client (created if not provided)
        """
        self.settings = settings or get_settings()
        self.client = anthropic_client or anthropic.Anthropic(
            api_key=self.settings.anthropic_api_key
        )
        self._mcp_client: Optional[MinervaMCPClient] = None

    async def query(self, user_query: str) -> AgentResponse:
        """
        Process a user query and return a response.

        This is the main entry point for interacting with Jess.
        Handles both content searches and help/recommendation requests.

        Args:
            user_query: The user's question or request

        Returns:
            AgentResponse with content and optional video embed info
        """
        # Clean the query (remove @jess mention if present)
        query = self._clean_query(user_query)

        # Check if this is a help/recommendation request
        if self._is_help_query(query):
            return await self.get_recommendations(query)

        # Perform video search
        return await self._search_and_respond(query)

    async def get_recommendations(self, query: str = "") -> AgentResponse:
        """
        Get video recommendations based on query context.

        Args:
            query: Optional query for context (e.g., "popular", "recent")

        Returns:
            AgentResponse with recommendation content
        """
        async with get_minerva_client(self.settings) as client:
            videos = await client.list_videos()

        if not videos:
            return AgentResponse(
                content="No videos are currently available in the library.",
                success=True,
                clickable_examples=self._get_example_queries(),
            )

        query_lower = query.lower()

        # Determine sort order based on query
        if "popular" in query_lower or "most viewed" in query_lower or "top" in query_lower:
            sorted_videos = sorted(videos, key=lambda v: v.view_count, reverse=True)
            intro = "Here are the most popular videos by view count:"
        elif "latest" in query_lower or "newest" in query_lower or "recent" in query_lower:
            sorted_videos = sorted(
                videos, key=lambda v: v.publish_date or "", reverse=True
            )
            intro = "Here are the latest videos:"
        elif "featured" in query_lower:
            sorted_videos = [v for v in videos if v.featured] or videos
            intro = "Here are the featured videos:"
        else:
            # Default: featured first, then by view count
            featured = [v for v in videos if v.featured]
            non_featured = sorted(
                [v for v in videos if not v.featured],
                key=lambda v: v.view_count,
                reverse=True,
            )
            sorted_videos = featured + non_featured
            intro = "Here's what's available in the video library:"

        # Build response content
        content_parts = [intro, ""]

        for video in sorted_videos[:10]:  # Limit to top 10
            content_parts.append(f"**{video.title}** ({video.duration_formatted})")

            if video.description:
                content_parts.append(f"  {video.description}")

            meta_parts = []
            if video.view_count:
                meta_parts.append(f"{video.view_count:,} views")
            if video.publish_date:
                meta_parts.append(video.publish_date)
            if meta_parts:
                content_parts.append(f"  📊 {' | '.join(meta_parts)}")

            if video.topics:
                content_parts.append(f"  🏷️ Topics: {', '.join(video.topics[:4])}")

            content_parts.append("")  # Blank line between videos

        content_parts.append(
            "Ask me about any of these topics to search the transcripts for specific insights!"
        )

        # Include top video for embedding
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
            clickable_examples=[
                "@jess AI bubble analysis",
                "@jess ASEAN governance insights",
                "@jess China innovation",
                "@jess most popular videos",
            ],
        )

    async def _search_and_respond(self, query: str) -> AgentResponse:
        """
        Search videos and synthesize a response.

        Args:
            query: The search query

        Returns:
            AgentResponse with synthesized answer
        """
        try:
            # Search via MCP
            async with get_minerva_client(self.settings) as client:
                segments = await client.search_videos(query)

            if not segments:
                return AgentResponse(
                    content=self._no_results_message(query),
                    success=True,
                    clickable_examples=self._get_example_queries(),
                )

            # Get the top result for video embed
            top_segment = segments[0]
            video_info = {
                "video_id": top_segment.video_id,
                "start_time": int(top_segment.start_time),
                "title": top_segment.title,
                "timestamp": top_segment.timestamp,
                "url": top_segment.url,
            }

            # Synthesize answer using Claude
            answer = await self._synthesize_answer(query, segments)

            return AgentResponse(
                content=answer,
                success=True,
                video_info=video_info,
                search_result=SearchResult(
                    query=query,
                    segments=segments,
                    answer=answer,
                ),
            )

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return AgentResponse(
                content=f"I encountered an error searching the video library: {e}",
                success=False,
            )

    async def _synthesize_answer(self, query: str, segments: list[VideoSegment]) -> str:
        """
        Use Claude to synthesize an answer from search results.

        Args:
            query: The original query
            segments: Matching video segments

        Returns:
            Synthesized answer text
        """
        if not segments:
            return self._no_results_message(query)

        # Build context from search results
        context_parts = []
        for i, segment in enumerate(segments[:5], 1):
            context_parts.append(
                f'[Source {i}] From "{segment.title}" at {segment.timestamp}:\n'
                f"{segment.full_text}\n"
                f"Watch: {segment.url}"
            )

        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""Based on these video transcript excerpts, answer this question: "{query}"

{context}

Instructions:
- Synthesize the key insights that answer the question
- Include the specific video title and timestamp for each key point
- Be concise but comprehensive
- Don't include raw URLs - I'll embed the video directly
- If excerpts don't fully answer the question, acknowledge what's missing"""

        try:
            response = self.client.messages.create(
                model=self.settings.synthesis_model,
                max_tokens=self.settings.max_synthesis_tokens,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._format_raw_results(segments)

    def _format_raw_results(self, segments: list[VideoSegment]) -> str:
        """Format search results as a simple list (fallback)."""
        if not segments:
            return "No matching content found in the video library."

        lines = [f"Found {len(segments)} relevant segment(s):\n"]
        for segment in segments[:5]:
            lines.append(f"**{segment.title}** at {segment.timestamp}")
            lines.append(segment.text)
            lines.append(f"[Watch here]({segment.url})\n")

        return "\n".join(lines)

    def _no_results_message(self, query: str) -> str:
        """Generate a helpful message when no results are found."""
        return (
            f"I searched the video library but couldn't find specific content about "
            f"'{query}'. The available videos cover AI markets, ASEAN governance, "
            f"and China's R&D surge. Would you like me to search for related topics?"
        )

    def _clean_query(self, query: str) -> str:
        """Remove @jess mention and clean up the query."""
        cleaned = re.sub(r"@jess\s*", "", query, flags=re.IGNORECASE)
        return cleaned.strip()

    def _is_help_query(self, query: str) -> bool:
        """Check if the query is asking for help or recommendations."""
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in self.HELP_PATTERNS)

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from a query."""
        words = query.lower().split()
        return [w for w in words if w not in self.STOP_WORDS and len(w) >= 3]

    def _get_example_queries(self) -> list[str]:
        """Get clickable example queries."""
        return [
            "@jess What did Andy say about AI?",
            "@jess ASEAN market outlook",
            "@jess China R&D and innovation",
            "@jess list videos",
        ]


# Synchronous wrapper for non-async contexts
class JessAgentSync:
    """
    Synchronous wrapper for JessAgent.

    Use this when you need to call Jess from synchronous code.
    Note: This creates a new event loop for each call, which may
    have performance implications for high-frequency usage.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        anthropic_client: Optional[anthropic.Anthropic] = None,
    ):
        """Initialize the synchronous Jess agent wrapper."""
        self._agent = JessAgent(settings, anthropic_client)

    def query(self, user_query: str) -> AgentResponse:
        """Process a query synchronously."""
        import asyncio
        return asyncio.run(self._agent.query(user_query))

    def get_recommendations(self, query: str = "") -> AgentResponse:
        """Get recommendations synchronously."""
        import asyncio
        return asyncio.run(self._agent.get_recommendations(query))
