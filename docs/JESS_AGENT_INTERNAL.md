# Jess Agent - Internal Implementation

> Summary of the internal Jess agent from `claude_agent_master/claude_agent_new_v11/agents/jess_agent.py`

## Overview

Jess is a **Video Intelligence Agent** that searches a video library for insights on markets, bonds, and investment strategy. It connects to a **Video MCP** (Cloudflare Worker) for all video operations.

**Architecture Note**: There are two Jess implementations:
- **Internal**: `jess_agent.py` in the claude_agent system (this document)
- **External SDK**: `github.com/urbancanary/minerva-jess` (this repo)

Both connect to the same Video MCP backend.

## Video MCP Endpoint

```
VIDEO_MCP_URL = https://video-mcp.urbancanary.workers.dev
```

## Key Capabilities

### 1. Video Search
Searches video transcripts via Video MCP:
```python
await self._call_mcp_tool("video_search", {
    "query": query,
    "max_results": max_results
})
```

### 2. Answer Synthesis
Synthesizes natural language answers from search results:
```python
await self._call_mcp_tool("video_synthesize", {
    "query": query,
    "video_results": video_results,
    "tone": "professional"
})
```

### 3. Video Listing
Lists all available videos with metadata:
```python
await self._call_mcp_tool("video_list", {})
```

### 4. Recommendations
Provides video recommendations based on:
- **Popular**: Sorted by view count
- **Latest**: Sorted by publish date
- **Featured**: Curated featured videos

## Video Catalog

The agent maintains a local `VIDEO_CATALOG` with metadata for ~45 videos including:
- Title
- Topics (tags)
- Publish date
- View count
- Featured flag
- Description

Example entry:
```python
'SKfMmH9Bk4o': {
    'title': 'Are we in an AI bubble?',
    'topics': ['AI', 'technology', 'market bubble', 'valuations', 'Nvidia'],
    'publish_date': '2024-06-15',
    'view_count': 15420,
    'featured': True,
    'description': 'Discussion of AI market dynamics and valuation concerns.'
}
```

## Query Handling

### Help Queries
Detected patterns trigger recommendations instead of search:
- "help", "recommend", "what videos", "list videos"
- "most popular", "latest", "featured"
- "what should I watch", "where to start"

### Search Queries
All other queries trigger:
1. Search via Video MCP
2. Synthesis of answer from results
3. Return with video embed info for top result

## Response Format

```python
{
    "content": "Answer text...",
    "is_streaming": False,
    "success": True,
    "video_info": {
        "video_id": "SKfMmH9Bk4o",
        "start_time": 45,
        "title": "Are we in an AI bubble?",
        "timestamp": "0:45",
        "url": "https://youtube.com/watch?v=SKfMmH9Bk4o"
    },
    "clickable_examples": [
        "@jess What did Andy say about AI?",
        "@jess ASEAN market outlook"
    ]
}
```

## Key Topics Covered

Based on the video catalog:
- AI and technology (bubble, semiconductors, Magnificent Seven)
- China (R&D, innovation, EVs, trade strategy)
- ASEAN / Asia (governance, manufacturing, growth)
- Real assets and energy
- Market outlooks and fund updates
- Tariffs and trade policy

## Integration with This Repo

The `minerva-jess` SDK provides a standalone Python client that mirrors the internal agent's capabilities:
- `JessAgent` / `JessAgentSync` classes
- Same Video MCP backend
- Can be embedded in other applications

The web app (`web.py`) in this repo is separate - it's a video translation tool using HeyGen, not the video search functionality.
