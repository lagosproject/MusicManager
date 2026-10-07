"""Prueba de escritura mínima y acotada. Solo toca la playlist privada que crea: mm-diagnostico-borrar.
Usa POST /me/playlists (spotipy.current_user_playlist_create) y comprueba add/remove.
"""
import re
from spotipy.exceptions import SpotifyException
from music_manager.core.spotify_client import SpotifyClient

NAME = "mm-diagnostico-borrar"
c = SpotifyClient()
sp = c.sp


def clean(e):
    return re.sub(r"\s+", " ", str(getattr(e, "msg", e)))[:200]


def step(name, fn):
    try:
        out = fn()
        print(f"[OK ] {name} {out if isinstance(out, str) else ''}")
        return out
    except SpotifyException as e:
        print(f"[{e.http_status}] {name} {clean(e)}")
    except Exception as e:  # noqa: BLE001
        print(f"[EXC] {name} {type(e).__name__}: {clean(e)}")


# Estado previo: ¿existe ya alguna playlist con ese nombre?
existing = []
off = 0
while True:
    r = sp.current_user_playlists(limit=50, offset=off)
    existing += [p for p in r["items"] if p["name"] == NAME]
    off += 50
    if off >= r["total"]:
        break
print(f"Playlists previas llamadas '{NAME}': {len(existing)}")

# Pista de prueba: primera pista de la primera playlist propia (solo lectura)
uid = sp.current_user()["id"]
mine = [p for p in sp.current_user_playlists(limit=50)["items"] if p["owner"]["id"] == uid]
first = sp.playlist_items(mine[0]["id"], limit=1)["items"][0]
uri = (first.get("item") or first.get("track"))["uri"]

new = step("current_user_playlist_create (POST /me/playlists, privada)",
           lambda: sp.current_user_playlist_create(NAME, public=False, description="Diagnóstico temporal. Borrar."))
if new:
    pid = new["id"]
    print(f"      id={pid[:4]}*** public={new.get('public')}")
    step("playlist_add_items (1 pista)", lambda: sp.playlist_add_items(pid, [uri]) and "")
    n = step("comprobar 1 pista dentro", lambda: str(sp.playlist_items(pid)["total"]))
    step("playlist_remove_all_occurrences_of_items", lambda: sp.playlist_remove_all_occurrences_of_items(pid, [uri]) and "")
    step("comprobar 0 pistas", lambda: str(sp.playlist_items(pid)["total"]))
    print(f"\n>>> Se creó la playlist PRIVADA '{NAME}'. Bórrala a mano desde Spotify.")
else:
    print("\nNo se creó ninguna playlist.")
