"""
Data models for Minerva-Jess.
"""

from typing import Optional
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """Metadata about a video."""

    video_id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    duration: float = Field(0.0, description="Duration in seconds")
    duration_formatted: str = Field("", description="Human-readable duration")
    url: str = Field("", description="Video URL")
    topics: list[str] = Field(default_factory=list, description="Topic tags")
    publish_date: Optional[str] = Field(None, description="Publication date")
    view_count: int = Field(0, description="Number of views")
    featured: bool = Field(False, description="Featured video flag")
    description: str = Field("", description="Video description")
    chapter_count: int = Field(0, description="Number of chapters")

    @property
    def youtube_url(self) -> str:
        """Get YouTube watch URL."""
        return f"https://youtube.com/watch?v={self.video_id}"

    def youtube_url_at_time(self, seconds: int) -> str:
        """Get YouTube URL at specific timestamp."""
        return f"https://youtube.com/watch?v={self.video_id}&t={seconds}s"


class VideoSegment(BaseModel):
    """A segment of a video transcript with timing."""

    video_id: str = Field(..., description="Video identifier")
    title: str = Field(..., description="Video title")
    text: str = Field(..., description="Transcript text (truncated)")
    full_text: str = Field("", description="Complete transcript text")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    timestamp: str = Field(..., description="Human-readable timestamp")
    url: str = Field(..., description="URL to video at timestamp")
    relevance: float = Field(0.0, description="Search relevance score")

    @classmethod
    def from_search_result(cls, data: dict) -> "VideoSegment":
        """Create VideoSegment from search result data."""
        start = data.get("start_time", data.get("start", 0))
        end = data.get("end_time", data.get("end", start))
        video_id = data.get("video_id", "")
        text = data.get("text", "")

        return cls(
            video_id=video_id,
            title=data.get("title", f"Video {video_id}"),
            text=text[:300] if len(text) > 300 else text,
            full_text=text,
            start_time=start,
            end_time=end,
            timestamp=f"{int(start // 60)}:{int(start % 60):02d}",
            url=f"https://youtube.com/watch?v={video_id}&t={int(start)}s",
            relevance=data.get("score", data.get("relevance", 0.0)),
        )


class SearchResult(BaseModel):
    """Result from a video search."""

    query: str = Field(..., description="Original search query")
    segments: list[VideoSegment] = Field(default_factory=list, description="Matching segments")
    answer: str = Field("", description="Synthesized answer")
    success: bool = Field(True, description="Whether search succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")

    @property
    def has_results(self) -> bool:
        """Check if any results found."""
        return len(self.segments) > 0

    @property
    def top_segment(self) -> Optional[VideoSegment]:
        """Get highest-relevance segment."""
        if not self.segments:
            return None
        return max(self.segments, key=lambda s: s.relevance)


class AgentResponse(BaseModel):
    """Response from the Jess agent."""

    content: str = Field(..., description="Response text")
    success: bool = Field(True, description="Whether request succeeded")
    video_info: Optional[dict] = Field(None, description="Video embed information")
    clickable_examples: Optional[list[str]] = Field(None, description="Follow-up suggestions")

    class Config:
        extra = "allow"
