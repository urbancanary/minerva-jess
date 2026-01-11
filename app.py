"""
Jess Video Gallery - Video Translation Tool

Browse Guinness GI videos for HeyGen translation.
"""

import json
import subprocess
import streamlit as st
from datetime import datetime
from pathlib import Path
import base64
import sys
import requests

# Add auth_mcp to path
sys.path.insert(0, "/Users/andyseaman/Notebooks/mcp_central/auth_mcp")
from auth_client import get_api_key

st.set_page_config(
    page_title="Jess - Video Translation",
    page_icon="🎬",
    layout="wide"
)

# Paths and config
CACHE_FILE = Path(__file__).parent / "data" / "videos_cache.json"
TRANSLATIONS_FILE = Path(__file__).parent / "data" / "translations.json"
CHANNEL_URL = "https://www.youtube.com/@GuinnessGI"
ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_LANGUAGE = "Spanish"
AVAILABLE_LANGUAGES = [
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Japanese",
    "Hindi",
    "Polish",
]

# ============================================================================
# Custom CSS
# ============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    .main .block-container { max-width: 1200px; padding-left: 2rem; padding-right: 2rem; }

    /* Modern Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #161b22;
        border-radius: 12px;
        padding: 6px;
        gap: 6px;
        border: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 12px 24px;
        color: #8b949e;
        font-weight: 500;
        font-size: 14px;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: #21262d;
        color: #e6edf3;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(35, 134, 54, 0.3);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }

    .header-card {
        background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 30px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .header-avatar { width: 80px; height: 80px; border-radius: 50%; border: 2px solid #30363d; }
    .header-title { color: #e6edf3; font-size: 28px; font-weight: 600; margin: 0; }
    .header-subtitle { color: #8b949e; font-size: 14px; margin: 4px 0 0 0; }
    .header-stats { display: flex; gap: 20px; margin-left: auto; }
    .stat-box { background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px 20px; text-align: center; }
    .stat-number { color: #58a6ff; font-size: 24px; font-weight: 600; }
    .stat-label { color: #8b949e; font-size: 12px; text-transform: uppercase; }

    .video-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 16px;
        transition: border-color 0.2s;
    }
    .video-card:hover { border-color: #58a6ff; }
    .video-thumbnail { width: 100%; border-radius: 6px; cursor: pointer; }
    .video-title { color: #e6edf3; font-size: 13px; font-weight: 500; margin: 10px 0 4px 0; line-height: 1.3; }
    .video-meta { color: #8b949e; font-size: 11px; margin-bottom: 8px; }

    .status-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 500; margin-right: 6px; }
    .status-original { background: #21262d; color: #8b949e; }
    .status-processing { background: #1f3a1f; color: #3fb950; animation: pulse 2s infinite; }
    .status-complete { background: #0d419d; color: #58a6ff; }
    .status-failed { background: #3d1f1f; color: #f85149; }

    .lang-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; background: #238636; color: white; margin: 2px; }

    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stColumn > div { padding: 0 6px; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Helper Functions
# ============================================================================

def get_base64_image(image_path: Path) -> str:
    if image_path.exists():
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def load_cached_videos():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
                return data.get("videos", []), data.get("cached_at", "")
        except:
            pass
    return [], ""

def save_videos_cache(videos: list):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"videos": videos, "cached_at": datetime.now().isoformat(), "channel_url": CHANNEL_URL}, f, indent=2)

def load_translations():
    if TRANSLATIONS_FILE.exists():
        try:
            with open(TRANSLATIONS_FILE) as f:
                data = json.load(f)
            # Migrate old format entries (flat structure) to new format (nested languages)
            migrated = False
            for video_id, trans in data.items():
                if "languages" not in trans:
                    # Old format: {video_id: {job_id, status, language, ...}}
                    # Convert to: {video_id: {title, original_url, languages: {lang: {...}}}}
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
            # Save migrated data
            if migrated:
                with open(TRANSLATIONS_FILE, "w") as f:
                    json.dump(data, f, indent=2)
            return data
        except:
            pass
    return {}

def save_translations(translations: dict):
    TRANSLATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRANSLATIONS_FILE, "w") as f:
        json.dump(translations, f, indent=2)

def fetch_youtube_videos(channel_url: str = CHANNEL_URL, max_results: int = 50):
    try:
        cmd = ["yt-dlp", "--flat-playlist", "--dump-json", f"{channel_url}/videos", "--playlist-end", str(max_results)]
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
            except:
                continue
        return videos
    except:
        return []

def submit_translation(video_url: str, video_id: str, title: str, language: str) -> dict:
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
        resp = requests.get(f"https://api.heygen.com/v2/video_translate/{job_id}", headers={"X-Api-Key": api_key}, timeout=30)
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

def get_translation_status(video_id: str, translations: dict) -> tuple:
    if video_id not in translations:
        return "original", None, []
    trans = translations[video_id]
    # Get list of completed languages
    completed_langs = []
    for lang, data in trans.get("languages", {}).items():
        if data.get("status") == "completed":
            completed_langs.append(lang)
    # Get current processing status
    for lang, data in trans.get("languages", {}).items():
        if data.get("status") == "processing":
            return "processing", None, completed_langs
    if completed_langs:
        return "completed", None, completed_langs
    return "original", None, completed_langs


# ============================================================================
# Load Data
# ============================================================================

jess_avatar = get_base64_image(ASSETS_DIR / "jess.png")
videos, cached_at = load_cached_videos()
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


# ============================================================================
# TABS
# ============================================================================

tab_browse, tab_library = st.tabs(["🎬 Browse Videos", "📚 Translation Library"])

# ============================================================================
# TAB 1: Browse Videos
# ============================================================================
with tab_browse:
    # Header
    st.markdown(f"""
    <div class="header-card">
        <img src="data:image/png;base64,{jess_avatar}" class="header-avatar" alt="Jess">
        <div>
            <h1 class="header-title">Video Translation</h1>
            <p class="header-subtitle">Guinness Global Investors · HeyGen Translation Tool</p>
        </div>
        <div class="header-stats">
            <div class="stat-box"><div class="stat-number">{len(videos)}</div><div class="stat-label">Videos</div></div>
            <div class="stat-box"><div class="stat-number">{complete_count}</div><div class="stat-label">Translated</div></div>
            <div class="stat-box"><div class="stat-number">{processing_count}</div><div class="stat-label">Processing</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Controls
    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 2.5])
    with col1:
        if st.button("🔄 Refresh Videos", use_container_width=True):
            with st.spinner("Fetching from YouTube..."):
                videos = fetch_youtube_videos()
                if videos:
                    save_videos_cache(videos)
                    st.rerun()
    with col2:
        if st.button("🔍 Check Status", use_container_width=True):
            updated = False
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
            if updated:
                save_translations(translations)
                st.rerun()
            else:
                st.info("No status changes")
    with col3:
        selected_language = st.selectbox("Target language", AVAILABLE_LANGUAGES, index=0, label_visibility="collapsed")

    # Load videos if needed
    if not videos:
        with st.spinner("Loading videos from YouTube..."):
            videos = fetch_youtube_videos()
            if videos:
                save_videos_cache(videos)
                st.rerun()

    if not videos:
        st.warning("No videos found. Click Refresh to load from YouTube.")
        st.stop()

    # Sort videos
    videos_sorted = sorted(videos, key=lambda v: v.get("published_at", ""), reverse=True)

    st.markdown("---")

    # Video grid
    cols_per_row = 4
    for i in range(0, len(videos_sorted), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(videos_sorted):
                break

            video = videos_sorted[idx]
            video_id = video.get("video_id", "")
            title = video.get("title", "Untitled")
            duration = video.get("duration", 0)

            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            watch_url = f"https://www.youtube.com/watch?v={video_id}"

            status, output_url, completed_langs = get_translation_status(video_id, translations)

            duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else ""

            # Status badge
            if status == "processing":
                status_html = '<span class="status-badge status-processing">⏳ Processing</span>'
            elif completed_langs:
                status_html = '<span class="status-badge status-complete">✅ ' + f'{len(completed_langs)} lang</span>'
            else:
                status_html = '<span class="status-badge status-original">🎬 Original</span>'

            with col:
                st.markdown(f"""
                <div class="video-card">
                    <a href="{watch_url}" target="_blank"><img src="{thumbnail_url}" class="video-thumbnail"></a>
                    <div class="video-title">{title[:55]}{"..." if len(title) > 55 else ""}</div>
                    <div class="video-meta">{duration_str}</div>
                    {status_html}
                </div>
                """, unsafe_allow_html=True)

                if status == "processing":
                    st.button("⏳ Processing...", key=f"proc_{video_id}", disabled=True, use_container_width=True)
                else:
                    if st.button(f"🌐 Translate", key=f"trans_{video_id}", use_container_width=True):
                        with st.spinner(f"Submitting to {selected_language}..."):
                            result = submit_translation(watch_url, video_id, title, selected_language)
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                if video_id not in translations:
                                    translations[video_id] = {"title": title, "original_url": watch_url, "languages": {}}
                                translations[video_id]["languages"][selected_language] = {
                                    "job_id": result["job_id"],
                                    "status": "processing",
                                    "submitted_at": result["submitted_at"]
                                }
                                save_translations(translations)
                                st.success(f"Submitted for {selected_language}!")
                                st.rerun()


# ============================================================================
# TAB 2: Translation Library
# ============================================================================
with tab_library:
    st.markdown(f"""
    <div class="header-card">
        <img src="data:image/png;base64,{jess_avatar}" class="header-avatar" alt="Jess">
        <div>
            <h1 class="header-title">Translation Library</h1>
            <p class="header-subtitle">All translated videos organized by language</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get all translations grouped by language
    by_language = {}
    for video_id, trans in translations.items():
        for lang, data in trans.get("languages", {}).items():
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append({
                "video_id": video_id,
                "title": trans.get("title", "Untitled"),
                "original_url": trans.get("original_url", ""),
                "status": data.get("status", "unknown"),
                "output_url": data.get("output_url"),
                "error": data.get("error"),
                "submitted_at": data.get("submitted_at", "")
            })

    if not by_language:
        st.info("No translations yet. Go to Browse Videos to submit videos for translation.")
    else:
        # Language filter
        all_langs = list(by_language.keys())
        selected_filter = st.selectbox("Filter by language", ["All Languages"] + all_langs)

        st.markdown("---")

        # Show translations
        langs_to_show = all_langs if selected_filter == "All Languages" else [selected_filter]

        for lang in langs_to_show:
            if lang not in by_language:
                continue

            st.markdown(f"### 🌐 {lang}")

            videos_in_lang = by_language[lang]
            cols = st.columns(3)

            for idx, video in enumerate(videos_in_lang):
                with cols[idx % 3]:
                    video_id = video["video_id"]
                    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

                    status = video["status"]
                    if status == "completed":
                        status_html = '<span class="status-badge status-complete">✅ Ready</span>'
                    elif status == "processing":
                        status_html = '<span class="status-badge status-processing">⏳ Processing</span>'
                    elif status == "failed":
                        status_html = f'<span class="status-badge status-failed">❌ {video.get("error", "Failed")[:20]}</span>'
                    else:
                        status_html = '<span class="status-badge status-original">Unknown</span>'

                    st.markdown(f"""
                    <div class="video-card">
                        <img src="{thumbnail_url}" class="video-thumbnail">
                        <div class="video-title">{video["title"][:50]}{"..." if len(video["title"]) > 50 else ""}</div>
                        {status_html}
                    </div>
                    """, unsafe_allow_html=True)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.link_button("Original", video["original_url"], use_container_width=True)
                    with col_b:
                        if video["output_url"]:
                            st.link_button(f"🌐 {lang}", video["output_url"], use_container_width=True)
                        else:
                            st.button("Not ready", disabled=True, use_container_width=True, key=f"lib_{video_id}_{lang}")

            st.markdown("---")
