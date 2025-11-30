"""
Configuration management for Minerva-Jess.

Settings are loaded from environment variables with sensible defaults.
Use a .env file for local development.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic API
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude access",
    )

    # Minerva MCP Connection
    minerva_mcp_url: str = Field(
        default="http://localhost:3000",
        description="URL of the Minerva MCP server",
    )
    minerva_mcp_token: Optional[str] = Field(
        default=None,
        description="Authentication token for Minerva MCP (if required)",
    )

    # Model Configuration
    synthesis_model: str = Field(
        default="claude-haiku-4-5",
        description="Claude model for answer synthesis",
    )
    max_synthesis_tokens: int = Field(
        default=1024,
        description="Maximum tokens for synthesized answers",
    )

    # Search Configuration
    max_search_results: int = Field(
        default=10,
        description="Maximum number of search results to return",
    )
    min_relevance_score: float = Field(
        default=0.0,
        description="Minimum relevance score to include in results",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    def configure_logging(self) -> None:
        """Configure application logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses LRU cache to ensure settings are only loaded once.
    """
    return Settings()


# Video catalog - metadata for known videos
# This can be extended or loaded from an external source
VIDEO_CATALOG: dict[str, dict] = {
    "SKfMmH9Bk4o": {
        "title": "Are we in an AI bubble?",
        "topics": ["AI", "technology", "market bubble", "valuations", "Nvidia", "semiconductors"],
        "publish_date": "2024-06-15",
        "view_count": 15420,
        "featured": True,
        "description": "Discussion of AI market dynamics, valuation concerns, and sustainability.",
    },
    "AOVpTvMW6ro": {
        "title": "Governance, Growth and Volatility: Navigating ASEAN",
        "topics": [
            "ASEAN",
            "emerging markets",
            "governance",
            "volatility",
            "Southeast Asia",
        ],
        "publish_date": "2024-05-22",
        "view_count": 8750,
        "featured": True,
        "description": "Analysis of Southeast Asian markets and investment opportunities.",
    },
    "biVXxcjM4ws": {
        "title": "China R&D Surge: From fast follower to innovation powerhouse",
        "topics": ["China", "R&D", "innovation", "technology", "patents", "EVs"],
        "publish_date": "2024-04-10",
        "view_count": 12300,
        "featured": False,
        "description": "How China became a global innovation leader.",
    },
    # Additional videos from batch transcription
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
