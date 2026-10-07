import os
import tempfile

# Must run before music_manager.config is imported: tests never touch the real data/ or credentials
DATA_DIR = tempfile.mkdtemp(prefix="mm_tests_")
os.environ["DATA_DIR"] = DATA_DIR
os.environ["SPOTIPY_CLIENT_ID"] = "test-client-id"
os.environ["SPOTIPY_CLIENT_SECRET"] = "test-client-secret"
os.environ["LASTFM_API_KEY"] = ""
os.environ["LASTFM_SHARED_SECRET"] = ""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

from music_manager.config import settings
from music_manager.core.spotify_client import SpotifyClient

APP = str(Path(__file__).resolve().parent.parent / "main_streamlit.py")
PLAYLIST = {"name": "Mi playlist", "images": [], "external_urls": {}}


def fake_spotify() -> SpotifyClient:
    client = SpotifyClient.__new__(SpotifyClient)  # skip __init__: no OAuth, no network
    client.sp = MagicMock()
    client.sp.current_user_playlists.return_value = {"items": [], "total": 0}
    client.sp.playlist.return_value = PLAYLIST
    client.sp.playlist_items.return_value = {"items": [], "total": 0}
    client.sp.current_user_saved_tracks.return_value = {"items": [], "total": 0}
    return client


@pytest.fixture(autouse=True)
def clean_streamlit_cache():
    """st.cache_data is global to the process: without this, one test would see another one's playlists."""
    import streamlit as st
    st.cache_data.clear()
    yield


@pytest.fixture
def data_dir():
    """The tests' data dir starts empty and is left empty."""
    def wipe():
        for f in Path(settings.data_dir).glob("*.json"):
            f.unlink()
    wipe()
    yield Path(settings.data_dir)
    wipe()


@pytest.fixture
def new_app(data_dir):
    """Factory for an AppTest already logged in with a fake Spotify and a finished initial sync."""
    def factory() -> AppTest:
        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state["spotify"] = fake_spotify()
        at.session_state["spotify_user"] = {"id": "test", "display_name": "Test"}
        at.session_state["initial_sync_done"] = True
        return at
    return factory
