"""
Orca HTTP Client

Client for communicating with the Orca Video API via HTTP.
All video intelligence operations go through Orca.

Example:
    client = OrcaMCPClient(settings)
    results = await client.search("AI market risks")
"""

import logging
from typing import Any, Optional

import httpx

from minerva_jess.config import Settings, VIDEO_CATALOG
from minerva_jess.models import VideoInfo, VideoSegment

logger = logging.getLogger(__name__)


class OrcaClientError(Exception):
    """Raised when communication with Orca fails."""
    pass


class OrcaMCPClient:
    """
    Client for the Orca Video API.

    Connects to Orca via HTTP for video search, synthesis, and listing.

    Example:
        client = OrcaMCPClient(settings)
        results = await client.search("AI market risks")
    """

    def __init__(self, settings: Settings):
        """Initialize the Orca HTTP client."""
        self.settings = settings
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.settings.orca_url,
                timeout=60.0,  # Synthesis can take time
                headers=self._get_headers()
            )
        return self._client

    def _get_headers(self) -> dict:
        """Get HTTP headers including auth if configured."""
        headers = {"Content-Type": "application/json"}
        if self.settings.orca_token:
            headers["Authorization"] = f"Bearer {self.settings.orca_token}"
        return headers

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

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

        try:
            client = self._get_client()
            response = await client.post(
                "/video/search",
                json={"query": query, "max_results": max_results}
            )
            response.raise_for_status()
            data = response.json()

            segments = []
            for item in data.get("results", []):
                segment = VideoSegment.from_search_result(item)

                # Enrich with catalog metadata
                if segment.video_id in VIDEO_CATALOG:
                    catalog = VIDEO_CATALOG[segment.video_id]
                    if not segment.title or segment.title.startswith("Video "):
                        segment.title = catalog.get("title", segment.title)

                segments.append(segment)

            logger.info(f"Search returned {len(segments)} segments for '{query}'")
            return segments

        except httpx.HTTPError as e:
            logger.error(f"Orca API search failed: {e}")
            raise OrcaClientError(f"Search failed: {e}") from e
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise OrcaClientError(f"Search failed: {e}") from e

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

        try:
            client = self._get_client()

            # Convert segments to dicts for API
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

            response = await client.post(
                "/video/synthesize",
                json={
                    "query": query,
                    "video_results": video_results,
                    "tone": tone
                }
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"Synthesis error: {data['error']}")
                return self._format_fallback(segments)

            return data.get("answer", "Unable to synthesize answer.")

        except httpx.HTTPError as e:
            logger.error(f"Orca API synthesis failed: {e}")
            return self._format_fallback(segments)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return self._format_fallback(segments)

    async def list_videos(self) -> list[VideoInfo]:
        """
        List all available videos.

        Returns:
            List of video metadata
        """
        try:
            client = self._get_client()
            response = await client.get("/video/list")
            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get("videos", []):
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

        except httpx.HTTPError as e:
            logger.error(f"Orca API list failed: {e}")
            return []
        except Exception as e:
            logger.error(f"List videos failed: {e}")
            return []

    async def get_transcript(self, video_id: str) -> Optional[dict]:
        """
        Get transcript for a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript data or None
        """
        try:
            client = self._get_client()
            response = await client.get(f"/video/transcript/{video_id}")

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Get transcript failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Get transcript failed: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if Orca API is available."""
        try:
            client = self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except:
            return False

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
    """Get an Orca HTTP client instance."""
    from minerva_jess.config import get_settings
    settings = settings or get_settings()
    return OrcaMCPClient(settings)
