from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Spotify (vacío = no configurado; ver missing_spotify_credentials)
    spotipy_client_id: str = ""
    spotipy_client_secret: str = ""
    spotipy_redirect_uri: str = "http://127.0.0.1:8978/callback"

    # Optional services
    lastfm_api_key: Optional[str] = None
    lastfm_shared_secret: Optional[str] = None

    # App Settings
    data_dir: str = "data"

    @field_validator("data_dir")
    @classmethod
    def _resolve_data_dir(cls, value: str) -> str:
        # Relative paths are anchored to the project, not to the launch directory
        path = Path(value)
        return str(path if path.is_absolute() else PROJECT_ROOT / path)

    def missing_spotify_credentials(self) -> List[str]:
        """Names of the required Spotify variables that are not set."""
        missing = []
        if not self.spotipy_client_id.strip():
            missing.append("SPOTIPY_CLIENT_ID")
        if not self.spotipy_client_secret.strip():
            missing.append("SPOTIPY_CLIENT_SECRET")
        return missing

    @property
    def cache_path(self) -> str:
        return str(Path(self.data_dir) / ".cache")

    @property
    def merges_path(self) -> str:
        return str(Path(self.data_dir) / "merges.json")

    @property
    def tracks_cache_path(self) -> str:
        return str(Path(self.data_dir) / "tracks_cache.json")

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
