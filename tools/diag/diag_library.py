"""Prueba del endpoint de guardar en "Me gusta" (PUT/DELETE /me/library) con el permiso user-library-modify.

Guarda UNA canción que NO tienes en Me gusta y la quita enseguida. Aborta si la cuenta
que autoriza no es la misma que la sesión actual. Compara el total antes y después.
"""
import re
from spotipy.exceptions import SpotifyException

from music_manager.core.spotify_client import SpotifyClient

BASE = ("user-library-read,user-follow-read,playlist-read-private,playlist-read-collaborative,"
        "playlist-modify-public,playlist-modify-private")

# 1) Cuenta de la sesión actual (token ya guardado, sin pedir permisos nuevos)
before_user = SpotifyClient(scope=BASE).sp.current_user()["id"]
print("Sesión actual leída.")

# 2) Cliente con el permiso nuevo: spotipy abrirá el navegador para autorizarlo
c = SpotifyClient(scope=BASE + ",user-library-modify")
sp = c.sp
new_user = sp.current_user()["id"]
if new_user != before_user:
    print("ABORTADO: la cuenta que has autorizado NO es la misma que la sesión actual. No se ha escrito nada.")
    raise SystemExit(1)
print("Cuenta confirmada (misma que antes).")


def short(e):
    return re.sub(r"\s+", " ", str(getattr(e, "msg", e)))[:160]


total_before = sp.current_user_saved_tracks(limit=1)["total"]
print("Canciones guardadas antes:", total_before)

# 3) Buscar una canción que NO esté guardada
candidate = None
for q in ("Tití Me Preguntó", "Gasolina Daddy Yankee", "Danza Kuduro", "Bailando Enrique Iglesias", "Despacito"):
    for t in sp.search(q, limit=10, type="track")["tracks"]["items"]:
        try:
            saved = sp.current_user_saved_tracks_contains([t["uri"]])
        except SpotifyException as e:
            print("[ERR] contains:", e.http_status, short(e))
            raise SystemExit(1)
        if saved == [False]:
            candidate = t
            break
    if candidate:
        break
assert candidate, "No he encontrado una canción no guardada para la prueba"
uri = candidate["uri"]
print(f"[OK ] GET /me/library/contains -> candidata no guardada: {candidate['name']}")

ok_add = ok_del = False
try:
    sp.current_user_saved_tracks_add([uri])
    ok_add = sp.current_user_saved_tracks_contains([uri]) == [True]
    print(f"[{'OK ' if ok_add else 'ERR'}] PUT /me/library (guardar) -> ahora guardada: {ok_add}")
except SpotifyException as e:
    print("[ERR] PUT /me/library:", e.http_status, short(e))
finally:
    # Siempre intentar dejar la biblioteca como estaba
    try:
        sp.current_user_saved_tracks_delete([uri])
        ok_del = sp.current_user_saved_tracks_contains([uri]) == [False]
        print(f"[{'OK ' if ok_del else 'ERR'}] DELETE /me/library (quitar) -> ahora NO guardada: {ok_del}")
    except SpotifyException as e:
        print("[ERR] DELETE /me/library:", e.http_status, short(e))

total_after = sp.current_user_saved_tracks(limit=1)["total"]
print("Canciones guardadas después:", total_after, "(igual que antes)" if total_after == total_before else "(¡DISTINTO!)")
print("RESULTADO:", "TODO OK" if ok_add and ok_del and total_after == total_before else "REVISAR")
