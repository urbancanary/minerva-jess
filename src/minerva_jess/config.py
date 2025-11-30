"""
Configuration for Minerva-Jess.

Settings are loaded from environment variables and optional config.yaml file.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Orca connection
    orca_url: str = Field(
        default="http://localhost:3000",
        description="URL of the Orca gateway",
    )
    orca_token: Optional[str] = Field(
        default=None,
        description="Authentication token for Orca",
    )

    # Search settings
    max_search_results: int = Field(
        default=10,
        description="Maximum number of search results",
    )
    min_relevance_score: float = Field(
        default=0.0,
        description="Minimum relevance score for results",
    )

    # Synthesis settings
    max_synthesis_tokens: int = Field(
        default=1024,
        description="Maximum tokens for synthesized answers",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    def configure_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


class AgentConfig:
    """
    Agent configuration loaded from config.yaml.

    This contains customizable settings that can be changed
    without modifying code.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml (defaults to ./config.yaml)
        """
        self._config: dict = {}

        if config_path is None:
            config_path = Path("config.yaml")

        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f) or {}

    # Agent identity
    @property
    def agent_name(self) -> str:
        """Display name for the agent."""
        return self._config.get("agent", {}).get("name", "Jess")

    @property
    def agent_icon(self) -> str:
        """Icon/emoji for the agent."""
        return self._config.get("agent", {}).get("icon", "🎬")

    # Response settings
    @property
    def language(self) -> str:
        """Response language."""
        return self._config.get("response", {}).get("language", "en")

    @property
    def include_timestamps(self) -> bool:
        """Whether to include timestamps in responses."""
        return self._config.get("response", {}).get("include_timestamps", True)

    @property
    def include_urls(self) -> bool:
        """Whether to include URLs in responses."""
        return self._config.get("response", {}).get("include_urls", True)

    # Search settings
    @property
    def max_results(self) -> int:
        """Maximum search results to return."""
        return self._config.get("search", {}).get("max_results", 10)

    @property
    def min_relevance(self) -> float:
        """Minimum relevance threshold."""
        return self._config.get("search", {}).get("min_relevance", 0.0)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


@lru_cache
def get_agent_config() -> AgentConfig:
    """Get cached agent configuration."""
    return AgentConfig()


# Video catalog - metadata for known videos
VIDEO_CATALOG: dict[str, dict] = {
    "SKfMmH9Bk4o": {
        "title": "Are we in an AI bubble?",
        "topics": ["AI", "technology", "market bubble", "valuations", "Nvidia"],
        "publish_date": "2024-06-15",
        "view_count": 15420,
        "featured": True,
        "description": "Discussion of AI market dynamics and valuation concerns.",
    },
    "AOVpTvMW6ro": {
        "title": "Governance, Growth and Volatility: Navigating ASEAN",
        "topics": ["ASEAN", "emerging markets", "governance", "Southeast Asia"],
        "publish_date": "2024-05-22",
        "view_count": 8750,
        "featured": True,
        "description": "Analysis of Southeast Asian markets and opportunities.",
    },
    "biVXxcjM4ws": {
        "title": "China R&D Surge: From fast follower to innovation powerhouse",
        "topics": ["China", "R&D", "innovation", "technology", "EVs"],
        "publish_date": "2024-04-10",
        "view_count": 12300,
        "featured": False,
        "description": "How China became a global innovation leader.",
    },
    "J9izUotQ6Ls": {"title": "China's two-part strategy and the shifting global landscape"},
    "L5P2q3Ffazg": {"title": "Apple's dependence on China and the 'Catfish effect'"},
    "pLHDv--lr4U": {"title": "Fighting inflation with real assets"},
    "Khp3B8cXKbk": {"title": "Building the backbone of the AI revolution"},
    "WLXPgQUS4UI": {"title": "AI After the Magnificent Seven"},
    "d6-oSabOAEI": {"title": "Real Assets in an Unstable World"},
    "A9kV-HZjinQ": {"title": "What investors should know about the current US Budget Deficit"},
    "p3eHt8PiN_I": {"title": "A Quick Take on Tariffs"},
    "NXpheKdhwwc": {"title": "Revisiting the case for the Magnificent Seven"},
    "gmWLTbzVtp8": {"title": "Asia's manufacturing resilience"},
    "e4rJqlZZ_RI": {"title": "Asia's growth story revived"},
    "2CbZXBn4QlM": {"title": "Understanding China's Economic Transition"},
    "kkpz7Z1ut38": {"title": "Global Equity Income - 2025 Outlook"},
    "sKUAKjRk-2Q": {"title": "Global Innovators - 2025 Outlook"},
    "XpLfQzLGn2U": {"title": "Global Energy - 2025 Outlook"},
    "d2WY9i1E1mw": {"title": "The Magnificent Seven"},
    "S4KGXIY2AGw": {"title": "Opportunities across the Semiconductor industry"},
}
