"""Mapa de qué endpoints limita Spotify ahora. Solo lecturas, con requests directo (sin reintentos ni esperas)."""
import requests

from music_manager.core.spotify_client import SpotifyClient

token = SpotifyClient().sp.auth_manager.get_access_token(as_dict=False)
H = {"Authorization": f"Bearer {token}"}
API = "https://api.spotify.com/v1"
MACRO = "2GHIEBMJKaUqkoDVOIxFao"

CHECKS = [
    ("GET /me", f"{API}/me"),
    ("GET /me/playlists?limit=1", f"{API}/me/playlists?limit=1"),
    ("GET /me/tracks?limit=1", f"{API}/me/tracks?limit=1"),
    ("GET /me/following?type=artist&limit=1", f"{API}/me/following?type=artist&limit=1"),
    ("GET /playlists/{LA MACRO}?fields=name", f"{API}/playlists/{MACRO}?fields=name"),
    ("GET /playlists/{LA MACRO}/items?limit=1", f"{API}/playlists/{MACRO}/items?limit=1"),
    ("GET /search?q=bad bunny&limit=1", f"{API}/search?q=bad%20bunny&type=track&limit=1"),
]
for label, url in CHECKS:
    r = requests.get(url, headers=H, timeout=20)
    ra = r.headers.get("Retry-After")
    extra = f"   Retry-After={int(ra)} s (~{int(ra) / 3600:.1f} h)" if ra else ""
    print(f"{label:<44} HTTP {r.status_code}{extra}")
