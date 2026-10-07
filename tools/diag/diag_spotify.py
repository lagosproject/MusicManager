"""Diagnóstico de la API de Spotify (SOLO LECTURA por defecto).

Usa los mismos clientes/scopes que SpotifyClient. No imprime tokens.
Ejecutar desde la raíz del repo:  python tools/diag/diag_spotify.py
Escrituras (solo con --write y permiso explícito del usuario).
"""
import re
import sys
import time

import requests
import spotipy
from spotipy.exceptions import SpotifyException

from music_manager.core.spotify_client import SpotifyClient

WRITE = "--write" in sys.argv
results = []


def clean(msg: str) -> str:
    msg = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer ***", str(msg))
    return msg.replace("\n", " ")[:300]


def run(name, fn):
    t0 = time.time()
    try:
        out = fn()
        status, detail = "OK", out if isinstance(out, str) else ""
    except SpotifyException as e:
        status = f"HTTP {e.http_status}"
        detail = clean(e.msg or e.reason)
    except requests.HTTPError as e:
        status = f"HTTP {e.response.status_code}"
        detail = clean(e.response.text)
    except Exception as e:  # noqa: BLE001
        status = f"EXC {type(e).__name__}"
        detail = clean(e)
    results.append((name, status, detail))
    print(f"[{status:>9}] {name} ({time.time()-t0:.1f}s) {detail}", flush=True)


from importlib.metadata import version
print(f"spotipy {version('spotipy')}")
c = SpotifyClient()
sp, pub = c.sp, c.sp_public
ctx = {}

# ---- Usuario (OAuth) ----
def f_user():
    u = sp.current_user()
    ctx["uid"] = u["id"]
    return f"product={u.get('product')} country={u.get('country')}"
run("sp.current_user", f_user)

def f_pls():
    r = sp.current_user_playlists(limit=50)
    ctx["pls"] = r["items"]
    mine = [p for p in r["items"] if p["owner"]["id"] == ctx.get("uid")]
    ctx["mine"] = mine
    return f"total={r['total']} devueltas={len(r['items'])} propias={len(mine)}"
run("sp.current_user_playlists", f_pls)

def f_pl():
    p = (ctx.get("mine") or ctx["pls"])[0]
    ctx["pl_id"] = p["id"]
    r = sp.playlist(p["id"], fields="name,images,external_urls")
    return f"name_ok={bool(r.get('name'))}"
run("sp.playlist(fields=name,images,external_urls)", f_pl)

def f_items():
    r = sp.playlist_items(ctx["pl_id"], limit=5, additional_types=["track"])
    ctx["items"] = r["items"]
    first = r["items"][0] if r["items"] else {}
    keys = sorted(first.keys())
    tr = first.get("track") or first.get("item") or {}
    if tr:
        ctx["track_id"] = tr.get("id")
        ctx["artist_id"] = (tr.get("artists") or [{}])[0].get("id")
        ctx["track_uri"] = tr.get("uri")
    return f"total={r['total']} claves_item={keys} track_en={'track' if first.get('track') else ('item' if first.get('item') else 'ninguno')}"
run("sp.playlist_items (playlist propia)", f_items)

# Playlist con más pistas, por si la primera estaba vacía
run("sp.current_user_saved_tracks", lambda: f"total={sp.current_user_saved_tracks(limit=5)['total']}")

def f_follow():
    r = sp.current_user_followed_artists(limit=5)
    ctx.setdefault("artist_id", (r["artists"]["items"] or [{}])[0].get("id"))
    return f"total={r['artists']['total']}"
run("sp.current_user_followed_artists", f_follow)

AID = ctx.get("artist_id") or "4q3ewBCX7sLwd24euuV69X"  # Bad Bunny como respaldo
TID = ctx.get("track_id") or "6habFhsOp2NvshLv26DqMb"

# ---- Catálogo con OAuth de usuario (sp) y con client credentials (sp_public) ----
run("sp.artist(id)", lambda: f"genres={len(sp.artist(AID).get('genres', []))}")
run("sp_public.artist(id)", lambda: f"genres={len(pub.artist(AID).get('genres', []))}")
run("sp.artists([ids]) GET /artists?ids=", lambda: f"n={len(sp.artists([AID, '4q3ewBCX7sLwd24euuV69X'])['artists'])}")
run("sp_public.artists([ids]) GET /artists?ids=", lambda: f"n={len(pub.artists([AID, '4q3ewBCX7sLwd24euuV69X'])['artists'])}")

def f_client_batch():
    r = c.get_artists_info([AID, "4q3ewBCX7sLwd24euuV69X"])
    return f"n={len(r)} con_datos={sum(1 for x in r if x)}"
run("SpotifyClient.get_artists_info (requests directo)", f_client_batch)

run("sp.track(id)", lambda: f"ok={bool(sp.track(TID).get('id'))}")
run("sp.tracks([ids]) GET /tracks?ids=", lambda: f"n={len(sp.tracks([TID])['tracks'])}")
run("sp.artist_top_tracks(id)", lambda: f"n={len(sp.artist_top_tracks(AID)['tracks'])}")
run("sp.search(limit=10)", lambda: f"n={len(sp.search('bad bunny', limit=10, type='track')['tracks']['items'])}")
run("sp.search(limit=50)", lambda: f"n={len(sp.search('bad bunny', limit=50, type='track')['tracks']['items'])}")

# ---- Endpoints retirados en nov-2024 ----
run("sp.recommendations(seed_artists=[1])", lambda: f"n={len(sp.recommendations(seed_artists=[AID], limit=5)['tracks'])}")
run("SpotifyClient.get_recommendations", lambda: f"n={len(c.get_recommendations(seed_artists=[AID], limit=5))}")
run("sp.audio_features([1 pista])", lambda: f"resp={sp.audio_features([TID])}"[:120])

# ---- Paginación real que usa la app ----
def f_pag():
    t = c.get_playlist_tracks(ctx["pl_id"], limit=150)
    return f"leidas={len(t)}"
run("SpotifyClient.get_playlist_tracks(limit=150)", f_pag)

# ---- ESCRITURA (solo con --write y permiso) ----
if WRITE:
    NAME = "mm-diagnostico-borrar"
    def w_create():
        ctx["new_id"] = c.create_playlist(NAME, public=False, description="Diagnóstico temporal. Borrar.")
        return f"id={ctx['new_id'][:4]}***"
    run("WRITE create_playlist (privada)", w_create)
    if ctx.get("new_id") and ctx.get("track_uri"):
        run("WRITE add_tracks_to_playlist (1 pista)", lambda: c.add_tracks_to_playlist(ctx["new_id"], [ctx["track_uri"]]) or "")
        run("WRITE remove_track_from_playlist (1 pista)", lambda: c.remove_track_from_playlist(ctx["new_id"], [ctx["track_uri"]]) or "")
    print(f"\n>>> Borra a mano la playlist '{NAME}' desde Spotify.")
else:
    print("\n(Escrituras omitidas: falta --write)")

print("\n=== RESUMEN ===")
for n, s, d in results:
    print(f"{s:>9} | {n}")
