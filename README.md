# Minerva-Jess

**Jess** is a Video Intelligence Agent that searches video libraries for insights on markets, investments, and financial strategy. Powered by [Minerva MCP](https://minerva.example.com) for video transcription and semantic search.

## Features

- **Semantic Video Search** - Find relevant content across video transcripts using natural language queries
- **Answer Synthesis** - Get synthesized answers with video timestamps, powered by Claude
- **Video Recommendations** - Discover videos by popularity, recency, or topic
- **MCP Integration** - Clean separation via Model Context Protocol for Minerva communication

## Installation

```bash
# Clone the repository
git clone https://github.com/yourcompany/minerva-jess.git
cd minerva-jess

# Install with pip
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the project root:

```env
# Required: Anthropic API key for Claude
ANTHROPIC_API_KEY=sk-ant-...

# Minerva MCP server connection
MINERVA_MCP_URL=http://localhost:3000
MINERVA_MCP_TOKEN=your-token-here

# Optional: Model configuration
SYNTHESIS_MODEL=claude-haiku-4-5
MAX_SYNTHESIS_TOKENS=1024
MAX_SEARCH_RESULTS=10

# Logging
LOG_LEVEL=INFO
```

## Usage

### Command Line

```bash
# Ask a question
jess "What are the key risks in AI investments?"

# List available videos
jess --list-videos

# Get recommendations
jess --recommendations

# Interactive mode
jess --interactive
```

### Python API

```python
import asyncio
from minerva_jess import JessAgent, Settings

async def main():
    settings = Settings()
    agent = JessAgent(settings)

    # Search for insights
    result = await agent.query("What did Andy say about AI bubbles?")
    print(result.content)

    # Get video recommendations
    recommendations = await agent.get_recommendations()
    print(recommendations.content)

asyncio.run(main())
```

### Synchronous Usage

```python
from minerva_jess.agent import JessAgentSync

agent = JessAgentSync()
result = agent.query("ASEAN market outlook")
print(result.content)
```

## Architecture

```
minerva-jess/
├── src/minerva_jess/
│   ├── __init__.py      # Package exports
│   ├── agent.py         # JessAgent - main intelligence agent
│   ├── mcp_client.py    # MinervaMCPClient - Minerva communication
│   ├── config.py        # Settings and configuration
│   ├── models.py        # Pydantic data models
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
└── README.md
```

### Key Components

| Component | Description |
|-----------|-------------|
| `JessAgent` | Main agent class - processes queries, synthesizes answers |
| `MinervaMCPClient` | MCP client for Minerva communication |
| `Settings` | Configuration via environment variables |
| `VideoSegment` | Search result with timestamp and transcript |
| `AgentResponse` | Complete agent response with content and metadata |

## Minerva MCP Integration

Jess communicates with Minerva exclusively through MCP (Model Context Protocol). The following MCP tools are used:

| Tool | Description |
|------|-------------|
| `minerva_search` | Semantic search across video transcripts |
| `minerva_list_videos` | List available videos with metadata |
| `minerva_get_video` | Get detailed video information |
| `minerva_get_transcript` | Retrieve transcript segments |

### MCP Connection

Ensure the Minerva MCP server is running and accessible:

```bash
# Check connection
curl http://localhost:3000/health

# The client will connect automatically when queries are made
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/minerva_jess

# Linting
ruff check src/
```

## API Reference

### JessAgent

```python
class JessAgent:
    async def query(self, user_query: str) -> AgentResponse:
        """Process a user query and return a response."""

    async def get_recommendations(self, query: str = "") -> AgentResponse:
        """Get video recommendations based on query context."""
```

### AgentResponse

```python
class AgentResponse:
    content: str              # Response text content
    success: bool             # Whether the request succeeded
    video_info: dict | None   # Video embed information
    clickable_examples: list  # Suggested follow-up queries
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For issues and feature requests, please contact your account representative or open an issue in the repository.
