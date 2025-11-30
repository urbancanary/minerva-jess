"""Tests for the Jess agent."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from minerva_jess.agent import JessAgent
from minerva_jess.models import AgentResponse, VideoSegment


class TestJessAgent:
    """Test cases for JessAgent."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.orca_url = "http://localhost:3000"
        settings.orca_token = None
        settings.max_search_results = 10
        settings.min_relevance_score = 0.0
        settings.max_synthesis_tokens = 1024
        return settings

    @pytest.fixture
    def mock_config(self):
        """Create mock agent config."""
        config = MagicMock()
        config.agent_name = "Jess"
        config.agent_icon = "🎬"
        config.language = "en"
        config.include_timestamps = True
        return config

    def test_clean_query_removes_mention(self, mock_settings, mock_config):
        """Test that @jess mention is removed from queries."""
        agent = JessAgent(mock_settings, mock_config)

        assert agent._clean_query("@jess What about AI?") == "What about AI?"
        assert agent._clean_query("@JESS AI bubble") == "AI bubble"
        assert agent._clean_query("What about AI?") == "What about AI?"

    def test_is_help_query_detection(self, mock_settings, mock_config):
        """Test help query detection."""
        agent = JessAgent(mock_settings, mock_config)

        # Should be detected as help queries
        assert agent._is_help_query("help")
        assert agent._is_help_query("What videos do you have?")
        assert agent._is_help_query("list videos")

        # Should NOT be detected as help queries
        assert not agent._is_help_query("What are AI bubble risks?")
        assert not agent._is_help_query("Tell me about ASEAN markets")

    def test_agent_properties(self, mock_settings, mock_config):
        """Test agent name and icon properties."""
        agent = JessAgent(mock_settings, mock_config)

        assert agent.name == "Jess"
        assert agent.icon == "🎬"


class TestVideoSegment:
    """Test cases for VideoSegment model."""

    def test_from_search_result(self):
        """Test creating VideoSegment from search result."""
        data = {
            "video_id": "abc123",
            "title": "Test Video",
            "text": "This is the transcript text",
            "start_time": 65.5,
            "end_time": 90.0,
            "score": 0.85,
        }

        segment = VideoSegment.from_search_result(data)

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
