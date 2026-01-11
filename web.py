"""
Jess Video Gallery - FastAPI Backend

Browse Guinness GI videos for HeyGen translation.
Run with: uvicorn web:app --reload --port 8000
"""

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Auth client for API keys
from auth_client import get_api_key

# Paths and config
BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / "data" / "videos_cache.json"
TRANSLATIONS_FILE = BASE_DIR / "data" / "translations.json"
TRANSCRIPTS_FILE = BASE_DIR / "data" / "transcripts.json"
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = BASE_DIR / "assets"
CHANNEL_URL = "https://www.youtube.com/@GuinnessGI"

AVAILABLE_LANGUAGES = [
    "Spanish", "French", "German", "Italian",
    "Portuguese", "Japanese", "Hindi", "Polish",
]

# Video MCP for transcripts (TODO: route through Orca long-term)
VIDEO_MCP_URL = "https://video-mcp.urbancanary.workers.dev"

# FastAPI app
app = FastAPI(title="Jess Video Gallery")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount assets directory
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


# =============================================================================
# Pydantic Models
# =============================================================================

class TranslateRequest(BaseModel):
    video_id: str
    video_url: str
    title: str
    language: str


# =============================================================================
# Helper Functions (ported from app.py)
# =============================================================================

def load_cached_videos() -> tuple[list, str]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
                return data.get("videos", []), data.get("cached_at", "")
        except Exception:
            pass
    return [], ""


def save_videos_cache(videos: list):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "videos": videos,
            "cached_at": datetime.now().isoformat(),
            "channel_url": CHANNEL_URL
        }, f, indent=2)


def load_translations() -> dict:
    if TRANSLATIONS_FILE.exists():
        try:
            with open(TRANSLATIONS_FILE) as f:
                data = json.load(f)
            # Migrate old format entries
            migrated = False
            for video_id, trans in data.items():
                if "languages" not in trans:
                    lang = trans.get("language", "Unknown")
                    old_data = {
                        "job_id": trans.get("job_id"),
                        "status": trans.get("status", "unknown"),
                        "submitted_at": trans.get("submitted_at", ""),
                    }
                    if trans.get("output_url"):
                        old_data["output_url"] = trans["output_url"]
                    if trans.get("error"):
                        old_data["error"] = trans["error"]
                    data[video_id] = {
                        "title": trans.get("title", "Untitled"),
                        "original_url": trans.get("original_url", f"https://www.youtube.com/watch?v={video_id}"),
                        "languages": {lang: old_data}
                    }
                    migrated = True
            if migrated:
                with open(TRANSLATIONS_FILE, "w") as f:
                    json.dump(data, f, indent=2)
            return data
        except Exception:
            pass
    return {}


def save_translations(translations: dict):
    TRANSLATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSLATIONS_FILE, "w") as f:
        json.dump(translations, f, indent=2)


def load_transcripts() -> dict:
    """Load stored transcripts from JSON file."""
    if TRANSCRIPTS_FILE.exists():
        try:
            with open(TRANSCRIPTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_transcripts(transcripts: dict):
    """Save transcripts to JSON file."""
    TRANSCRIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSCRIPTS_FILE, "w") as f:
        json.dump(transcripts, f, indent=2)


def fetch_youtube_videos(max_results: int = 50) -> list:
    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--dump-json",
            f"{CHANNEL_URL}/videos", "--playlist-end", str(max_results)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return []
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                videos.append({
                    "video_id": data.get("id", ""),
                    "title": data.get("title", "Untitled"),
                    "description": data.get("description", ""),
                    "published_at": data.get("upload_date", ""),
                    "duration": data.get("duration", 0),
                    "view_count": data.get("view_count", 0),
                })
            except Exception:
                continue
        return videos
    except Exception:
        return []


def submit_translation_job(video_url: str, video_id: str, title: str, language: str) -> dict:
    api_key = get_api_key("HEYGEN_API_KEY", requester="jess")
    if not api_key:
        return {"error": "HEYGEN_API_KEY not available"}
    try:
        resp = requests.post(
            "https://api.heygen.com/v2/video_translate",
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json={"video_url": video_url, "output_language": language},
            timeout=30
        )
        if resp.status_code in [200, 202]:
            data = resp.json()
            return {
                "job_id": data.get("data", {}).get("video_translate_id"),
                "status": "processing",
                "language": language,
                "title": title,
                "video_id": video_id,
                "original_url": video_url,
                "submitted_at": datetime.now().isoformat()
            }
        else:
            return {"error": f"API error {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def check_translation_status(job_id: str) -> dict:
    api_key = get_api_key("HEYGEN_API_KEY", requester="jess")
    if not api_key:
        return {"status": "error", "error": "HEYGEN_API_KEY not available"}
    try:
        resp = requests.get(
            f"https://api.heygen.com/v2/video_translate/{job_id}",
            headers={"X-Api-Key": api_key},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            status = data.get("status", "unknown")
            result = {"status": status}
            if status == "completed":
                result["output_url"] = data.get("url")
            elif status == "failed":
                result["error"] = data.get("message", "Unknown error")
            return result
        else:
            return {"status": "error", "error": f"API error {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.get("/api/videos")
async def get_videos():
    """Get list of videos (from cache or fetch from YouTube)."""
    videos, cached_at = load_cached_videos()
    if not videos:
        videos = fetch_youtube_videos()
        if videos:
            save_videos_cache(videos)
            cached_at = datetime.now().isoformat()

    # Sort by date
    videos_sorted = sorted(videos, key=lambda v: v.get("published_at", ""), reverse=True)

    return {
        "videos": videos_sorted,
        "cached_at": cached_at,
        "count": len(videos_sorted)
    }


@app.post("/api/videos/refresh")
async def refresh_videos():
    """Force refresh videos from YouTube."""
    videos = fetch_youtube_videos()
    if videos:
        save_videos_cache(videos)
        return {"success": True, "count": len(videos)}
    return {"success": False, "error": "Failed to fetch videos"}


@app.get("/api/translations")
async def get_translations():
    """Get all translations."""
    translations = load_translations()

    # Count stats
    processing_count = 0
    complete_count = 0
    for vid, trans in translations.items():
        for lang, data in trans.get("languages", {}).items():
            if data.get("status") == "processing":
                processing_count += 1
            elif data.get("status") == "completed":
                complete_count += 1

    return {
        "translations": translations,
        "stats": {
            "processing": processing_count,
            "completed": complete_count
        }
    }


@app.post("/api/translate")
async def translate_video(req: TranslateRequest):
    """Submit a video for translation."""
    result = submit_translation_job(req.video_url, req.video_id, req.title, req.language)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Save to translations
    translations = load_translations()
    if req.video_id not in translations:
        translations[req.video_id] = {
            "title": req.title,
            "original_url": req.video_url,
            "languages": {}
        }
    translations[req.video_id]["languages"][req.language] = {
        "job_id": result["job_id"],
        "status": "processing",
        "submitted_at": result["submitted_at"]
    }
    save_translations(translations)

    return {"success": True, "job_id": result["job_id"]}


@app.post("/api/translations/check")
async def check_translations():
    """Check status of all processing translations."""
    translations = load_translations()
    updated = False
    updates = []

    for video_id, trans in translations.items():
        for lang, data in trans.get("languages", {}).items():
            if data.get("status") == "processing" and data.get("job_id"):
                result = check_translation_status(data["job_id"])
                if result.get("status") != "processing":
                    translations[video_id]["languages"][lang]["status"] = result.get("status")
                    if result.get("output_url"):
                        translations[video_id]["languages"][lang]["output_url"] = result["output_url"]
                    if result.get("error"):
                        translations[video_id]["languages"][lang]["error"] = result["error"]
                    updated = True
                    updates.append({
                        "video_id": video_id,
                        "language": lang,
                        "status": result.get("status")
                    })

    if updated:
        save_translations(translations)

    return {"updated": updated, "updates": updates}


@app.get("/api/languages")
async def get_languages():
    """Get available languages."""
    return {"languages": AVAILABLE_LANGUAGES}


@app.get("/api/transcripts")
async def get_all_transcripts():
    """Get all stored transcripts."""
    transcripts = load_transcripts()
    return {
        "transcripts": transcripts,
        "count": len(transcripts)
    }


@app.get("/api/transcript/{video_id}")
async def get_transcript(video_id: str, lang: Optional[str] = None, refresh: bool = False):
    """Get transcript for a video (from storage or Orca API)."""

    # Check stored transcripts first (unless refresh requested)
    if not refresh:
        stored = load_transcripts()
        if video_id in stored:
            return stored[video_id]

    # Check if we have a HeyGen translated version for this language
    translations = load_translations()
    if video_id in translations and lang:
        trans = translations[video_id]
        lang_data = trans.get("languages", {}).get(lang)
        if lang_data and lang_data.get("status") == "completed" and lang_data.get("output_url"):
            return {
                "source": "heygen",
                "language": lang,
                "video_url": lang_data["output_url"],
                "transcript": None,
                "message": "Translated video available - transcript embedded in video"
            }

    # Get video title from cache
    videos, _ = load_cached_videos()
    video_title = "Unknown"
    for v in videos:
        if v.get("video_id") == video_id:
            video_title = v.get("title", "Unknown")
            break

    # Fetch from Video MCP
    try:
        resp = requests.post(
            f"{VIDEO_MCP_URL}/mcp/tools/call",
            json={"name": "video_get_transcript", "arguments": {"video_id": video_id}},
            timeout=30
        )

        if resp.status_code == 404:
            return {
                "video_id": video_id,
                "source": "video_mcp",
                "language": "en",
                "transcript": None,
                "error": "Transcript not available"
            }

        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return {
                "video_id": video_id,
                "source": "video_mcp",
                "language": "en",
                "transcript": None,
                "error": data.get("error", "Unknown error")
            }

        # Extract transcript text - MCP returns segments with text
        segments = data.get("segments", [])
        if segments:
            transcript_text = " ".join(seg.get("text", "") for seg in segments)
        else:
            transcript_text = data.get("transcript", data.get("text", ""))

        if not transcript_text:
            return {
                "video_id": video_id,
                "source": "video_mcp",
                "language": "en",
                "transcript": None,
                "error": "No transcript content in response"
            }

        # Build result and save to storage
        result = {
            "video_id": video_id,
            "title": video_title,
            "source": "video_mcp",
            "language": "en",
            "transcript": transcript_text,
            "fetched_at": datetime.now().isoformat(),
            "word_count": len(transcript_text.split())
        }

        # Save to storage
        stored = load_transcripts()
        stored[video_id] = result
        save_transcripts(stored)

        return result

    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Cannot connect to Video MCP")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout fetching transcript")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcripts/fetch-all")
async def fetch_all_transcripts():
    """Fetch and store transcripts for all videos from Orca."""
    videos, _ = load_cached_videos()
    stored = load_transcripts()

    fetched = []
    failed = []
    skipped = 0

    for video in videos:
        video_id = video.get("video_id")
        if not video_id:
            continue
        if video_id in stored:
            skipped += 1
            continue

        try:
            resp = requests.post(
                f"{VIDEO_MCP_URL}/mcp/tools/call",
                json={"name": "video_get_transcript", "arguments": {"video_id": video_id}},
                timeout=30
            )

            if resp.status_code == 404:
                failed.append({"video_id": video_id, "error": "Not found"})
                continue

            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                failed.append({"video_id": video_id, "error": data.get("error", "Unknown")})
                continue

            # Extract transcript text
            segments = data.get("segments", [])
            if segments:
                transcript_text = " ".join(seg.get("text", "") for seg in segments)
            else:
                transcript_text = data.get("transcript", data.get("text", ""))

            if transcript_text:
                stored[video_id] = {
                    "video_id": video_id,
                    "title": video.get("title", "Unknown"),
                    "source": "video_mcp",
                    "language": "en",
                    "transcript": transcript_text,
                    "fetched_at": datetime.now().isoformat(),
                    "word_count": len(transcript_text.split())
                }
                fetched.append(video_id)
            else:
                failed.append({"video_id": video_id, "error": "Empty transcript"})

        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to Video MCP"}
        except Exception as e:
            failed.append({"video_id": video_id, "error": str(e)})

    # Save all fetched transcripts
    if fetched:
        save_transcripts(stored)

    return {
        "fetched": len(fetched),
        "failed": len(failed),
        "already_stored": skipped,
        "total_stored": len(stored),
        "failures": failed[:5]
    }
