# Minerva-Jess

Jess is a video intelligence SDK that enables semantic search across video libraries. It returns relevant video segments with precise timestamps for embedding.

## Installation

```bash
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
ORCA_URL=http://localhost:8080
ORCA_TOKEN=your-token  # Optional, for authenticated APIs
```

### Agent Configuration

Create `config.yaml` to customize the agent:

```yaml
agent:
  name: "Jess"
  icon: "🎬"

search:
  max_results: 10

response:
  language: "en"
  include_timestamps: true
```

## Usage

### Basic Search

```python
import asyncio
from minerva_jess import JessAgent, Settings

async def main():
    settings = Settings()
    agent = JessAgent(settings)

    result = await agent.query("What are the risks in AI investments?")

    print(result.content)

    if result.video_info:
        print(f"Watch: {result.video_info['url']}")

asyncio.run(main())
```

### Website Integration

Return video embed information for your website:

```python
from minerva_jess import JessAgent, Settings

async def search_videos(query: str) -> dict:
    """Search videos and return embed info."""
    settings = Settings()
    agent = JessAgent(settings)

    result = await agent.query(query)

    if result.video_info:
        return {
            "video_id": result.video_info["video_id"],
            "start_time": result.video_info["start_time"],
            "timestamp": result.video_info["timestamp"],
            "title": result.video_info["title"],
            "summary": result.content
        }

    return {"error": "No matching videos found"}
```

**Frontend embed (JavaScript):**

```javascript
async function searchAndEmbed(query) {
    const response = await fetch('/api/video-search', {
        method: 'POST',
        body: JSON.stringify({ query })
    });

    const data = await response.json();

    if (data.video_id) {
        const embedUrl = `https://www.youtube.com/embed/${data.video_id}?start=${data.start_time}`;
        document.getElementById('player').innerHTML =
            `<iframe src="${embedUrl}" frameborder="0" allowfullscreen></iframe>`;
        document.getElementById('summary').innerText = data.summary;
    }
}
```

### Synchronous Usage

```python
from minerva_jess import JessAgentSync

agent = JessAgentSync()
result = agent.query("market outlook")
print(result.content)
```

### Get Video Recommendations

```python
result = await agent.get_recommendations()
print(result.content)

# Or filter
result = await agent.get_recommendations("popular")
result = await agent.get_recommendations("latest")
```

## API Reference

### JessAgent

```python
class JessAgent:
    async def query(self, user_query: str) -> AgentResponse:
        """Process a search query."""

    async def get_recommendations(self, query: str = "") -> AgentResponse:
        """Get video recommendations."""
```

### AgentResponse

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Response text |
| `success` | `bool` | Whether request succeeded |
| `video_info` | `dict` | Video embed information |
| `clickable_examples` | `list[str]` | Suggested queries |

**video_info structure:**

```python
{
    "video_id": "abc123",
    "start_time": 125,
    "timestamp": "2:05",
    "title": "Video Title",
    "url": "https://youtube.com/watch?v=abc123&t=125s"
}
```

## Architecture

```
┌─────────────────────────────────────┐
│         Your Application            │
│    (Website, API, Integration)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│          Minerva-Jess               │
│  ┌───────────┐  ┌────────────────┐  │
│  │ JessAgent │  │  HTTP Client   │  │
│  └─────┬─────┘  └───────┬────────┘  │
└────────┼────────────────┼───────────┘
         │                │
         └────────┬───────┘
                  │ HTTP
                  ▼
        ┌─────────────────┐
        │ Orca Video API  │
        └─────────────────┘
```

## Customization

### Rebrand the Agent

Edit `config.yaml`:

```yaml
agent:
  name: "VideoBot"
  icon: "📺"
```

### Adjust Search Results

```yaml
search:
  max_results: 5
  min_relevance: 0.3
```

## Requirements

- Python 3.10+
- Orca gateway access

## Dependencies

```
pydantic>=2.0.0
pydantic-settings>=2.0.0
PyYAML>=6.0.0
httpx>=0.27.0
```
