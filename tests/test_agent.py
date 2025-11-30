"""Tests for the Jess agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from minerva_jess.agent import JessAgent
from minerva_jess.models import AgentResponse, VideoSegment


class TestJessAgent:
    """Test cases for JessAgent."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        settings.minerva_mcp_url = "http://localhost:3000"
        settings.minerva_mcp_token = None
        settings.synthesis_model = "claude-haiku-4-5"
        settings.max_synthesis_tokens = 1024
        settings.max_search_results = 10
        settings.min_relevance_score = 0.0
        return settings

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create mock Anthropic client."""
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text="Test response from Claude")]
        client.messages.create.return_value = response
        return client

    def test_clean_query_removes_mention(self, mock_settings, mock_anthropic_client):
        """Test that @jess mention is removed from queries."""
        agent = JessAgent(mock_settings, mock_anthropic_client)

        assert agent._clean_query("@jess What about AI?") == "What about AI?"
        assert agent._clean_query("@JESS AI bubble") == "AI bubble"
        assert agent._clean_query("What about AI?") == "What about AI?"

    def test_is_help_query_detection(self, mock_settings, mock_anthropic_client):
        """Test help query detection."""
        agent = JessAgent(mock_settings, mock_anthropic_client)

        # Should be detected as help queries
        assert agent._is_help_query("help")
        assert agent._is_help_query("What videos do you have?")
        assert agent._is_help_query("Show me the most popular videos")
        assert agent._is_help_query("list videos")

        # Should NOT be detected as help queries
        assert not agent._is_help_query("What are AI bubble risks?")
        assert not agent._is_help_query("Tell me about ASEAN markets")

    def test_extract_keywords(self, mock_settings, mock_anthropic_client):
        """Test keyword extraction from queries."""
        agent = JessAgent(mock_settings, mock_anthropic_client)

        keywords = agent._extract_keywords("What did Andy say about AI bubbles?")
        assert "bubbles" in keywords
        assert "what" not in keywords  # Stop word
        assert "about" not in keywords  # Stop word

    def test_get_example_queries(self, mock_settings, mock_anthropic_client):
        """Test example queries are returned."""
        agent = JessAgent(mock_settings, mock_anthropic_client)

        examples = agent._get_example_queries()
        assert len(examples) > 0
        assert all(isinstance(e, str) for e in examples)


class TestVideoSegment:
    """Test cases for VideoSegment model."""

    def test_from_mcp_result(self):
        """Test creating VideoSegment from MCP result."""
        data = {
            "video_id": "abc123",
            "title": "Test Video",
            "text": "This is the transcript text",
            "start_time": 65.5,
            "end_time": 90.0,
            "score": 0.85,
        }

        segment = VideoSegment.from_mcp_result(data)

        assert segment.video_id == "abc123"
        assert segment.title == "Test Video"
        assert segment.start_time == 65.5
        assert segment.timestamp == "1:05"
        assert segment.relevance == 0.85
        assert "abc123" in segment.url
        assert "t=65s" in segment.url


class TestAgentResponse:
    """Test cases for AgentResponse model."""

    def test_response_creation(self):
        """Test creating an agent response."""
        response = AgentResponse(
            content="Test content",
            success=True,
            video_info={"video_id": "abc123"},
        )

        assert response.content == "Test content"
        assert response.success is True
        assert response.video_info is not None

    def test_response_allows_extra_fields(self):
        """Test that extra fields are allowed."""
        response = AgentResponse(
            content="Test",
            success=True,
            custom_field="custom value",
        )

        assert response.content == "Test"
