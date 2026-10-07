"""Prueba solo client credentials (sin usuario, sin navegador). Solo lectura."""
import re
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
from music_manager.config import settings

pub = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=settings.spotipy_client_id, client_secret=settings.spotipy_client_secret), retries=0)
AID = "4q3ewBCX7sLwd24euuV69X"


def run(name, fn):
    try:
        print(f"[OK ] {name} {fn()}")
    except SpotifyException as e:
        msg = re.sub(r"\s+", " ", str(e.msg))[:200]
        print(f"[{e.http_status}] {name} {msg}")
    except Exception as e:  # noqa: BLE001
        print(f"[EXC] {name} {type(e).__name__}: {str(e)[:200]}")


run("artist(id)", lambda: f"genres={len(pub.artist(AID).get('genres', []))}")
run("artists([ids]) batch", lambda: f"n={len(pub.artists([AID])['artists'])}")
run("artist_top_tracks", lambda: f"n={len(pub.artist_top_tracks(AID)['tracks'])}")
run("search limit=10", lambda: f"n={len(pub.search('bad bunny', limit=10, type='track')['tracks']['items'])}")
run("search limit=50", lambda: f"n={len(pub.search('bad bunny', limit=50, type='track')['tracks']['items'])}")
run("recommendations", lambda: f"n={len(pub.recommendations(seed_artists=[AID], limit=5)['tracks'])}")
