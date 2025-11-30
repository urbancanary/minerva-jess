"""
Data models for Minerva-Jess.

These models define the structure of video metadata, search results,
and agent responses used throughout the system.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """Metadata about a video in the library."""

    video_id: str = Field(..., description="Unique identifier for the video")
    title: str = Field(..., description="Video title")
    duration: float = Field(0.0, description="Duration in seconds")
    duration_formatted: str = Field("", description="Human-readable duration (e.g., '5m 30s')")
    url: str = Field("", description="URL to watch the video")
    topics: list[str] = Field(default_factory=list, description="Topic tags")
    publish_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    view_count: int = Field(0, description="Number of views")
    featured: bool = Field(False, description="Whether this is a featured video")
    description: str = Field("", description="Video description")
    chapter_count: int = Field(0, description="Number of chapters in the video")

    @property
    def youtube_url(self) -> str:
        """Get the YouTube watch URL."""
        return f"https://youtube.com/watch?v={self.video_id}"

    def youtube_url_at_time(self, seconds: int) -> str:
        """Get YouTube URL starting at a specific timestamp."""
        return f"https://youtube.com/watch?v={self.video_id}&t={seconds}s"


class VideoSegment(BaseModel):
    """A segment of a video transcript with timing information."""

    video_id: str = Field(..., description="Video this segment belongs to")
    title: str = Field(..., description="Video title")
    text: str = Field(..., description="Transcript text (may be truncated)")
    full_text: str = Field("", description="Complete transcript text")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    timestamp: str = Field(..., description="Human-readable timestamp (e.g., '2:34')")
    url: str = Field(..., description="URL to video at this timestamp")
    relevance: float = Field(0.0, description="Relevance score from search")

    @classmethod
    def from_mcp_result(cls, data: dict) -> "VideoSegment":
        """Create a VideoSegment from MCP search result data."""
        start = data.get("start_time", data.get("start", 0))
        end = data.get("end_time", data.get("end", start))
        video_id = data.get("video_id", "")

        return cls(
            video_id=video_id,
            title=data.get("title", f"Video {video_id}"),
            text=data.get("text", "")[:300],
            full_text=data.get("text", data.get("full_text", "")),
            start_time=start,
            end_time=end,
            timestamp=f"{int(start // 60)}:{int(start % 60):02d}",
            url=f"https://youtube.com/watch?v={video_id}&t={int(start)}s",
            relevance=data.get("score", data.get("relevance", 0.0)),
        )


class SearchResult(BaseModel):
    """Result from a video search query."""

    query: str = Field(..., description="The original search query")
    segments: list[VideoSegment] = Field(
        default_factory=list, description="Matching video segments"
    )
    answer: str = Field("", description="Synthesized answer from the segments")
    video_embed: Optional[VideoInfo] = Field(
        None, description="Primary video to embed in response"
    )
    success: bool = Field(True, description="Whether the search succeeded")
    error: Optional[str] = Field(None, description="Error message if search failed")

    @property
    def has_results(self) -> bool:
        """Check if any results were found."""
        return len(self.segments) > 0

    @property
    def top_segment(self) -> Optional[VideoSegment]:
        """Get the highest-relevance segment."""
        if not self.segments:
            return None
        return max(self.segments, key=lambda s: s.relevance)


class AgentResponse(BaseModel):
    """Complete response from the Jess agent."""

    content: str = Field(..., description="The response text content")
    success: bool = Field(True, description="Whether the request succeeded")
    video_info: Optional[dict] = Field(
        None, description="Video embed information for UI rendering"
    )
    clickable_examples: Optional[list[str]] = Field(
        None, description="Suggested follow-up queries"
    )
    search_result: Optional[SearchResult] = Field(
        None, description="Underlying search result data"
    )

    class Config:
        extra = "allow"  # Allow additional fields for extensibility
