"""Sondea https://accounts.spotify.com/authorize sin sesión de usuario. No imprime secretos ni la URL completa."""
from urllib.parse import urlparse, parse_qs
import requests
from music_manager.config import settings

SCOPES = {
    "completo (el de la app)": "user-library-read user-follow-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private",
    "solo user-read-private": "user-read-private",
    "solo playlist-read-private": "playlist-read-private",
    "solo user-library-read": "user-library-read",
    "solo user-follow-read": "user-follow-read",
    "solo playlist-modify-private": "playlist-modify-private",
    "sin scope": "",
}

for label, scope in SCOPES.items():
    params = {"client_id": settings.spotipy_client_id, "response_type": "code",
              "redirect_uri": settings.spotipy_redirect_uri, "scope": scope, "state": "diag"}
    r = requests.get("https://accounts.spotify.com/authorize", params=params, allow_redirects=False, timeout=20)
    loc = r.headers.get("Location", "")
    u = urlparse(loc)
    q = parse_qs(u.query)
    host = u.netloc or "(sin redirección)"
    errs = {k: v[0] for k, v in q.items() if k in ("error", "error_description")}
    print(f"{label:<28} HTTP {r.status_code} -> {host}{u.path[:40]} {errs}")
