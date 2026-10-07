"""
MusicManager: modern music playlist management for Spotify.
Modular entrypoint powered by Streamlit st.navigation.
"""
import streamlit as st
from loguru import logger

from music_manager.config import settings
from music_manager.core.auth import explain_login_error, clear_saved_token
from music_manager.core.cache_store import atomic_write_json, slim_cache
from music_manager.core.job_manager import JobManager
from music_manager.core.spotify_client import SpotifyClient
from app_pages.ui_common import (
    artist_cache_path,
    genre_mapping_path,
    load_json_file,
    tracks_cache_path,
)

# 1. Page Config
st.set_page_config(
    page_title="MusicManager Modern",
    page_icon="🎵",
    layout="wide",
)

# 2. Check Spotify credentials
missing_credentials = settings.missing_spotify_credentials()
if missing_credentials:
    st.error(
        f"Faltan variables en el fichero .env: {', '.join(missing_credentials)}. "
        "Copia .env.template a .env y rellénalas con los datos de tu app de Spotify."
    )
    st.stop()

# 3. Initialize Services in Session State
if 'spotify' not in st.session_state:
    try:
        st.session_state.spotify = SpotifyClient()
    except Exception as e:
        st.error(f"Error al inicializar Spotify: {e}")
        st.stop()

if 'job_manager' not in st.session_state:
    st.session_state.job_manager = JobManager()

# 4. Login Gate
if 'spotify_user' not in st.session_state:
    try:
        st.session_state.spotify_user = st.session_state.spotify.sp.current_user()
    except Exception as e:
        logger.warning(f"Spotify login failed: {type(e).__name__}: {e}")
        st.error(explain_login_error(e), icon=":material/error:")
        with st.container(horizontal=True):
            if st.button("Reintentar", icon=":material/refresh:"):
                st.rerun()
            if st.button("Borrar token y volver a autorizar", icon=":material/key:"):
                clear_saved_token()
                st.session_state.pop('spotify', None)
                st.rerun()
        st.stop()

# 5. Load Persistent Caches
if 'playlist_data_cache' not in st.session_state:
    loaded_cache = load_json_file(tracks_cache_path, {})
    st.session_state.playlist_data_cache = slim_cache(loaded_cache)
    if st.session_state.playlist_data_cache != loaded_cache:
        atomic_write_json(tracks_cache_path, st.session_state.playlist_data_cache, compact=True)

if 'artist_cache' not in st.session_state:
    st.session_state.artist_cache = load_json_file(artist_cache_path, {})

if 'genre_mapping' not in st.session_state:
    st.session_state.genre_mapping = load_json_file(genre_mapping_path, {})

st.session_state.setdefault('cache_read_at', {})
if 'initial_sync_done' not in st.session_state:
    st.session_state.initial_sync_done = len(st.session_state.playlist_data_cache) > 0

# 6. Sidebar User Info
spotify_user = st.session_state.spotify_user
user_display = spotify_user.get('display_name') or spotify_user.get('id') or "Usuario"
st.sidebar.caption(f"👤 Conectado como: **{user_display}**")

# 7. Navigation Structure
pages = [
    st.Page("app_pages/01_dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("app_pages/02_merges_manage.py", title="Gestión de Merges", icon=":material/account_tree:"),
    st.Page("app_pages/03_merges_run.py", title="Ejecución de Merges", icon=":material/play_arrow:"),
    st.Page("app_pages/04_organization.py", title="Auditoría de Organización", icon=":material/folder_open:"),
    st.Page("app_pages/05_unplaced.py", title="Guardadas sin playlist", icon=":material/playlist_add:"),
    st.Page("app_pages/06_genre_sorter.py", title="Organizador por Géneros", icon=":material/label:"),
    st.Page("app_pages/07_duplicates.py", title="Auditoría: Duplicados", icon=":material/content_copy:"),
]

pg = st.navigation(pages)
pg.run()
