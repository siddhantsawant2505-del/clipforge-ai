"""
ClipForge AI — Local Review Dashboard
Streamlit app: browse raw clips from Google Drive,
AI-edit them, preview, and push to YouTube / Instagram.

Usage:
    streamlit run ui/dashboard.py
"""

import os
import sys
import glob
import time
import threading
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import RAW_CLIPS_DIR, EDITED_CLIPS_DIR
from editor.video_editor import VideoEditor
from publisher.youtube_uploader import YouTubeUploader
from publisher.instagram_uploader import InstagramUploader
from publisher.scheduler import PostScheduler

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title   = "ClipForge AI",
    page_icon    = "🎬",
    layout       = "wide",
    initial_sidebar_state = "expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: 900; color: #9146FF; }
    .sub-title  { color: #aaa; font-size: 1rem; margin-bottom: 1.5rem; }
    .clip-card  {
        background: #1a1a2e;
        border: 1px solid #9146FF44;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background: #9146FF;
        color: white;
        border-radius: 8px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State ────────────────────────────────────────────────────────────
if "editor" not in st.session_state:
    st.session_state.editor    = VideoEditor()
if "yt_uploader" not in st.session_state:
    st.session_state.yt        = YouTubeUploader()
if "ig_uploader" not in st.session_state:
    st.session_state.ig        = InstagramUploader()
if "scheduler" not in st.session_state:
    st.session_state.scheduler = PostScheduler(
        youtube_uploader  = st.session_state.yt,
        instagram_uploader = st.session_state.ig,
    )
    st.session_state.scheduler.start()

if "edited_clips" not in st.session_state:
    st.session_state.edited_clips = {}  # clip_id → final_path


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Edit Settings")
    vertical_mode  = st.selectbox("9:16 Mode", ["blur", "crop"], index=0)
    add_captions   = st.toggle("Animated Captions (Whisper)", value=True)
    add_hook_sfx   = st.toggle("Hook SFX (Whoosh + Pop)", value=True)
    custom_sfx_txt = st.text_area(
        "Custom SFX (JSON)",
        value='[{"sfx": "vine_boom", "at": 10.0, "volume": 1.0}]',
        height=120,
    )

    st.markdown("---")
    st.markdown("## 📢 Publish Settings")
    publish_youtube   = st.toggle("Publish to YouTube Shorts", value=True)
    publish_instagram = st.toggle("Publish to Instagram Reels", value=True)
    publish_now       = st.toggle("Post Immediately (skip scheduler)", value=False)

    st.markdown("---")
    st.markdown("## 📁 Directories")
    st.code(RAW_CLIPS_DIR,    language=None)
    st.code(EDITED_CLIPS_DIR, language=None)


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🎬 ClipForge AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Automated Twitch Clip Editor & Publisher</p>',
    unsafe_allow_html=True,
)

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab_inbox, tab_edited, tab_queue = st.tabs(
    ["📥 Raw Clip Inbox", "✅ Edited Clips", "📅 Post Queue"]
)


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — RAW CLIP INBOX
# ════════════════════════════════════════════════════════════════════════════
with tab_inbox:
    st.markdown("### Raw Clips from Google Drive")
    st.caption("These are the unedited clips captured from chat spikes.")

    raw_clips = sorted(glob.glob(os.path.join(RAW_CLIPS_DIR, "*.mp4")), reverse=True)

    if not raw_clips:
        st.info("No raw clips yet. The watcher will deposit clips here when spikes are detected.")
    else:
        for clip_path in raw_clips:
            clip_id  = os.path.splitext(os.path.basename(clip_path))[0]
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f'<div class="clip-card">', unsafe_allow_html=True)
                st.video(clip_path)
                st.caption(f"📄 `{os.path.basename(clip_path)}`")
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("#### Edit Options")

                channel   = st.text_input("Channel name", key=f"ch_{clip_id}", value="unknown")
                game      = st.text_input("Game",         key=f"gm_{clip_id}", value="unknown")

                import json as _json
                try:
                    custom_sfx = _json.loads(custom_sfx_txt)
                except Exception:
                    custom_sfx = []

                if st.button(f"🤖 AI Edit", key=f"edit_{clip_id}"):
                    with st.spinner("Editing clip... (this may take 1-3 minutes)"):
                        editor = st.session_state.editor
                        final_path = editor.edit_clip(
                            raw_clip_path  = clip_path,
                            clip_id        = clip_id,
                            channel        = channel,
                            game           = game,
                            vertical_mode  = vertical_mode,
                            add_captions   = add_captions,
                            add_hook_sfx   = add_hook_sfx,
                            custom_sfx     = custom_sfx,
                        )
                        st.session_state.edited_clips[clip_id] = final_path
                    st.success(f"✅ Edited! Check 'Edited Clips' tab.")
                    st.balloons()


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — EDITED CLIPS
# ════════════════════════════════════════════════════════════════════════════
with tab_edited:
    st.markdown("### Edited Clips — Preview & Publish")

    edited_clips = sorted(
        glob.glob(os.path.join(EDITED_CLIPS_DIR, "*_FINAL.mp4")), reverse=True
    )

    if not edited_clips:
        st.info("No edited clips yet. Edit a raw clip from the Inbox tab.")
    else:
        for clip_path in edited_clips:
            clip_name = os.path.basename(clip_path)
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f'<div class="clip-card">', unsafe_allow_html=True)
                st.video(clip_path)
                st.caption(f"✅ `{clip_name}`")
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("#### Publish Settings")
                title = st.text_input(
                    "Title",
                    value=f"Twitch Moment 🔥 #{clip_name[:20]}",
                    key=f"ttl_{clip_name}",
                )
                description = st.text_area(
                    "Caption / Description",
                    value="#Shorts #TwitchClips #Gaming #Viral",
                    key=f"desc_{clip_name}",
                    height=80,
                )

                platforms = []
                if publish_youtube:
                    platforms.append("youtube")
                if publish_instagram:
                    platforms.append("instagram")

                if st.button(f"🚀 Add to Post Queue", key=f"pub_{clip_name}"):
                    st.session_state.scheduler.add_to_queue(
                        file_path   = clip_path,
                        title       = title,
                        description = description,
                        tags        = ["Shorts", "TwitchClips", "Gaming"],
                        platforms   = platforms,
                    )
                    st.success("✅ Added to drip post queue!")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — POST QUEUE
# ════════════════════════════════════════════════════════════════════════════
with tab_queue:
    import json as _json
    st.markdown("### Scheduled Post Queue")
    st.caption("Clips are drip-posted at your configured IST times.")

    queue_file = os.path.join(
        os.path.dirname(__file__), "..", "publisher", "posting_queue.json"
    )
    if os.path.exists(queue_file):
        with open(queue_file) as f:
            queue = _json.load(f)

        pending = [c for c in queue if not c["posted"]]
        posted  = [c for c in queue if c["posted"]]

        st.metric("Pending", len(pending))
        st.metric("Posted",  len(posted))

        if pending:
            st.markdown("#### 🕐 Pending")
            for item in pending:
                st.markdown(
                    f"- `{os.path.basename(item['file_path'])}` → "
                    f"{', '.join(item['platforms'])} — _{item['title']}_"
                )

        if posted:
            st.markdown("#### ✅ Posted")
            for item in posted[-5:]:
                st.markdown(
                    f"- ~~`{os.path.basename(item['file_path'])}`~~ — posted"
                )
    else:
        st.info("Post queue is empty.")
