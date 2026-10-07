"""Prueba real de la propagación de merges con 3 playlists PRIVADAS nuevas (mm-test-*).

Solo escribe en las playlists que crea. Usa un merges.json temporal (no toca el real).
No toca "Me gusta" ni ninguna otra playlist. Las playlists se dejan para borrarlas a mano.
"""
import tempfile
import time
from pathlib import Path

from music_manager.core.job_manager import JobManager
from music_manager.core.models import MergeJob
from music_manager.core.spotify_client import SpotifyClient

NAMES = {"hoja": "mm-test-hoja", "intermedia": "mm-test-intermedia", "raiz": "mm-test-raiz"}
c = SpotifyClient()

existing = {p["name"] for p in c.get_user_playlists()}
clash = existing & set(NAMES.values())
assert not clash, f"Ya existen playlists con estos nombres: {clash}. Abortado sin escribir nada."

# 3 canciones de prueba: las 3 primeras de "Me gusta" (solo lectura)
saved = c.sp.current_user_saved_tracks(limit=3)["items"]
uris = []
for item in saved:
    t = item.get("track") or item.get("item")
    uris.append(t["uri"])
assert len(uris) == 3, "Necesito al menos 3 canciones guardadas"


def uris_in(pid):
    out = []
    for it in c.get_playlist_tracks(pid):
        t = it.get("item") or it.get("track")
        if t and t.get("uri"):
            out.append(t["uri"])
    return out


ids = {k: c.create_playlist(v, public=False, description="Prueba de MusicManager. Borrar.") for k, v in NAMES.items()}
print("Creadas (privadas):", ", ".join(NAMES.values()))
time.sleep(2)

c.add_tracks_to_playlist(ids["hoja"], uris[:2])
time.sleep(2)

tmp = Path(tempfile.mkdtemp(prefix="mm_real_")) / "merges.json"
m = JobManager(config_path=str(tmp))
m.add_job(MergeJob(name="raiz", target_id=ids["raiz"], source_ids=[ids["intermedia"]]))
m.add_job(MergeJob(name="intermedia", target_id=ids["intermedia"], source_ids=[ids["hoja"]]))


def show(results):
    for r in results:
        print(f"   {r.name:<11} {r.status:<8} añadidas={r.added} {r.detail}")


print("\n1) Ejecutar SOLO 'intermedia' (debe propagar a 'raiz'):")
show(m.run_with_propagation("intermedia", c))
time.sleep(2)
mid, root = uris_in(ids["intermedia"]), uris_in(ids["raiz"])
print(f"   intermedia tiene {len(mid)} (esperado 2); raiz tiene {len(root)} (esperado 2)")
ok1 = sorted(mid) == sorted(uris[:2]) and sorted(root) == sorted(uris[:2])

print("\n2) Repetir sin cambios (no debe añadir nada):")
res2 = m.run_with_propagation("intermedia", c)
show(res2)
ok2 = all(r.added == 0 for r in res2)

print("\n3) Añadir 1 canción a la hoja y ejecutar de nuevo:")
c.add_tracks_to_playlist(ids["hoja"], [uris[2]])
time.sleep(2)
show(m.run_with_propagation("intermedia", c))
time.sleep(2)
mid, root = uris_in(ids["intermedia"]), uris_in(ids["raiz"])
print(f"   intermedia tiene {len(mid)} (esperado 3); raiz tiene {len(root)} (esperado 3)")
ok3 = len(mid) == 3 and len(root) == 3 and uris[2] in root

print("\n4) Ejecutar SOLO 'raiz' no debe tocar a los hijos:")
res4 = m.run_with_propagation("raiz", c)
show(res4)
ok4 = [r.name for r in res4] == ["raiz"]

print("\nRESULTADO:", "TODO OK" if all([ok1, ok2, ok3, ok4]) else f"FALLO ok1={ok1} ok2={ok2} ok3={ok3} ok4={ok4}")
print("Borra a mano de Spotify:", ", ".join(NAMES.values()))
