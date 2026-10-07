"""Spotify client wrapping music_core.SpotifyClient with user auth mode and local settings."""
from typing import Optional, List, Any, Iterable
import sys
from music_core import SpotifyClient as CoreSpotifyClient
import music_core.core.spotify_client as _mc_sc
from ..config import settings

SAVED_BATCH_SIZE = _mc_sc.SAVED_BATCH_SIZE
FULL_SAVED_READ_THRESHOLD = _mc_sc.FULL_SAVED_READ_THRESHOLD

class SpotifyClient(CoreSpotifyClient):
    """
    Subclass of music_core.SpotifyClient configured for MusicManager:
    - Default auth_mode = 'user'
    - Anchored to MusicManager's data_dir/.cache and redirect_uri
    """
    def __init__(
        self,
        scope: Optional[str] = None,
        auth_mode: str = "user",
        requests_timeout: int = 15,
        cache_path: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        super().__init__(
            auth_mode=auth_mode,
            scope=scope,
            requests_timeout=requests_timeout,
            cache_path=cache_path or settings.cache_path,
            redirect_uri=redirect_uri or settings.spotipy_redirect_uri,
            client_id=client_id or settings.spotipy_client_id,
            client_secret=client_secret or settings.spotipy_client_secret,
        )

    def filter_unsaved(self, track_uris: Iterable[str], saved_uris: Optional[Any] = None) -> List[str]:
        current_threshold = getattr(sys.modules[__name__], "FULL_SAVED_READ_THRESHOLD", _mc_sc.FULL_SAVED_READ_THRESHOLD)
        orig = _mc_sc.FULL_SAVED_READ_THRESHOLD
        try:
            _mc_sc.FULL_SAVED_READ_THRESHOLD = current_threshold
            return super().filter_unsaved(track_uris, saved_uris=saved_uris)
        finally:
            _mc_sc.FULL_SAVED_READ_THRESHOLD = orig

__all__ = ["SpotifyClient", "SAVED_BATCH_SIZE", "FULL_SAVED_READ_THRESHOLD"]
