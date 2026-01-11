# Minerva-Jess: Next Steps

## Current State
- HTML/FastAPI web app for video translation (HeyGen)
- Transcripts tab exists but **non-functional** - Video MCP lacks transcript endpoint

## Priority Tasks

### 1. Add Transcript Tool to Video MCP
**Repo**: https://github.com/urbancanary/video-mcp
**Local**: `/Users/andyseaman/Notebooks/mcp_central/video_mcp`
**Deployed**: `video-mcp.urbancanary.workers.dev`

Add a new tool `video_get_transcript` that returns the full transcript for a video:
```json
{
  "name": "video_get_transcript",
  "arguments": {"video_id": "SKfMmH9Bk4o"}
}
```

**Returns**:
```json
{
  "video_id": "SKfMmH9Bk4o",
  "title": "Are we in an AI bubble?",
  "transcript": "Full transcript text...",
  "segments": [
    {"text": "...", "start_time": 0, "end_time": 10, "speaker": "A"}
  ]
}
```

### 2. Route Video MCP Through Orca (Long-term)
Currently: `web.py` → `video-mcp.urbancanary.workers.dev`

Target: `web.py` → `orca-gateway` → `video-mcp`

This enables:
- Unified API gateway
- Memory/reasoning capabilities
- Consistent authentication

### 3. Transcript Storage for Reports
Once transcripts are fetchable:
- Store to `data/transcripts.json`
- Build report generation features (fund analysis, topic summaries)
- Enable bulk transcript fetching

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Web App (web.py)                     │
├─────────────────┬───────────────────┬───────────────────┤
│  Browse Videos  │ Translation Lib   │   Transcripts     │
│  (YouTube)      │ (HeyGen)          │   (Video MCP)     │
└────────┬────────┴─────────┬─────────┴─────────┬─────────┘
         │                  │                   │
         ▼                  ▼                   ▼
    yt-dlp             HeyGen API         Video MCP
                                              │
                                              ▼ (future)
                                         Orca Gateway
```

## Files to Modify

| Task | File | Change |
|------|------|--------|
| Add transcript tool | Video MCP codebase | New tool endpoint |
| Route through Orca | `web.py` | Change `VIDEO_MCP_URL` |
| Report generation | `web.py` + new endpoints | Add `/api/reports/*` |

## Available Video MCP Tools (Current)
- `video_search` - Search transcript segments
- `video_synthesize` - Generate answers from segments
- `video_list` - List all videos with metadata
