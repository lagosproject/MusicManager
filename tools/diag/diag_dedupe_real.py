"""Prueba REAL del borrado de duplicados, en una playlist privada nueva: mm-test-duplicados.

Spotify ignora las posiciones al borrar y solo quita una canción por URI (todas las copias), así que
remove_duplicates quita todas las copias y vuelve a insertar una en el sitio de la primera.
Solo escribe en esa playlist (que crea el script). Usa canciones de tus "Me gusta" únicamente para leerlas.
Comprueba el resultado leyendo la playlist por separado, sin fiarse de remove_duplicates.
Al terminar deja la playlist vacía: bórrala a mano.
"""
import time

from music_manager.core.duplicates import MODE_SAME_TITLE, MODE_SAME_TRACK, find_duplicate_groups, remove_duplicates, title_key
from music_manager.core.spotify_client import SpotifyClient
from music_manager.core.tracks import extract_track

NAME = "mm-test-duplicados"
c = SpotifyClient()
sp = c.sp

existing = [p for p in c.get_user_playlists() if p["name"] == NAME]
assert len(existing) <= 1, f"Hay varias playlists llamadas '{NAME}'. Abortado sin escribir nada."


def uris_in(pid):
    return [t["uri"] for t in (extract_track(i) for i in c.get_playlist_tracks(pid)) if t and t.get("uri")]


def reset(pid, uris):
    """Deja la playlist exactamente con `uris`."""
    sp.playlist_replace_items(pid, [])
    if uris:
        c.add_tracks_to_playlist(pid, uris)
    time.sleep(2)
    assert uris_in(pid) == uris, "la playlist de prueba no quedó como se esperaba"


# Canciones para montar los escenarios: 101 únicas de tus guardadas (solo lectura)
saved, offset = [], 0
while len(saved) < 101:
    page = sp.current_user_saved_tracks(limit=50, offset=offset)["items"]
    saved += [t["uri"] for t in (extract_track(i) for i in page) if t and t["uri"].startswith("spotify:track:")]
    offset += 50
saved = list(dict.fromkeys(saved))[:101]
A, B, C = saved[0], saved[1], saved[2]

if existing:
    pid = existing[0]["id"]
    print(f"Reutilizo la playlist de prueba '{NAME}' que ya existe.\n")
else:
    pid = c.create_playlist(NAME, public=False, description="Prueba de borrado de duplicados. Borrar.")
    time.sleep(2)
    print(f"Creada la playlist privada '{NAME}'.\n")
results = {}

# --- 1) La misma canción tres veces ---
reset(pid, [A, B, A, C, A])
r = remove_duplicates(c, pid, MODE_SAME_TRACK, {A: A})
time.sleep(2)
got = uris_in(pid)
results["1) misma canción x3 -> deja una, en su sitio"] = (got == [A, B, C], r)
print("1)", "OK " if got == [A, B, C] else "MAL", f"esperado [A,B,C] -> {len(got)} pistas; quitadas={r.removed} restauradas={r.restored} error={r.error}")

# --- 2) Dos versiones de la misma canción: conservar la segunda ---
pair = None
for query in ("Gasolina Daddy Yankee", "Niña Bonita Chino Nacho", "El Rey del Mambo La Banda Gorda", "Despacito Luis Fonsi", "Danza Kuduro Don Omar"):
    found = {}
    for t in sp.search(query, limit=10, type="track")["tracks"]["items"]:
        key = title_key(t)
        if key:
            found.setdefault(key, {})[t["uri"]] = t
    pair = next((list(v.values())[:2] for v in found.values() if len(v) >= 2), None)
    if pair:
        break
if pair:
    v1, v2 = pair[0]["uri"], pair[1]["uri"]
    reset(pid, [v1, B, v2])
    group = find_duplicate_groups(c.get_playlist_tracks(pid), MODE_SAME_TITLE)
    assert len(group) == 1, "no detecté el par como posibles duplicados"
    r = remove_duplicates(c, pid, MODE_SAME_TITLE, {group[0].key: v2})
    time.sleep(2)
    got = uris_in(pid)
    results["2) dos versiones -> conservar la segunda"] = (got == [B, v2], r)
    print("2)", "OK " if got == [B, v2] else "MAL", f"({pair[0]['name']} / {pair[1]['name']}) esperado [B, v2] -> {len(got)} pistas; quitadas={r.removed} restauradas={r.restored} error={r.error}")
else:
    print("2) OMITIDO: no encontré dos versiones de una misma canción en la búsqueda")

# --- 3) 101 canciones duplicadas: obliga a dos peticiones de borrado ---
reset(pid, saved + saved)
r = remove_duplicates(c, pid, MODE_SAME_TRACK, {u: u for u in saved})
time.sleep(3)
got = uris_in(pid)
results["3) 101 duplicadas (2 peticiones)"] = (got == saved, r)
print("3)", "OK " if got == saved else "MAL", f"esperado las 101 únicas en su orden -> {len(got)} pistas; quitadas={r.removed} restauradas={r.restored} error={r.error}")

sp.playlist_replace_items(pid, [])
print(f"\nPlaylist '{NAME}' dejada vacía. Bórrala a mano.")
bad = [k for k, (ok, _) in results.items() if not ok]
restored = sum(r.restored for _, r in results.values())
print("RESULTADO:", "TODO OK" if not bad else f"FALLOS: {bad}", "| la red de seguridad (restaurar) se usó", restored, "veces")
