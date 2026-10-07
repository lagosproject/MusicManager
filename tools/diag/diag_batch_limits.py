"""Mide cuántas canciones admite GET /me/library/contains por petición (solo lectura)."""
from spotipy.exceptions import SpotifyException
from music_manager.core.spotify_client import SpotifyClient

c = SpotifyClient()
saved = c.sp.current_user_saved_tracks(limit=50)["items"]
uris = [(i.get("track") or i.get("item"))["uri"] for i in saved]

for n in (20, 40, 41, 50):
    try:
        r = c.sp.current_user_saved_tracks_contains(uris[:n])
        print(f"{n:>3} URIs -> OK ({len(r)} respuestas, guardadas={sum(r)})")
    except SpotifyException as e:
        print(f"{n:>3} URIs -> HTTP {e.http_status} {str(e.msg)[:100]}")
