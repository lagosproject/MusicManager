"""Prueba real: merge + sincronización con Me gusta, usando las playlists mm-test-* ya creadas.

Añade a mm-test-hoja una canción que NO está en Me gusta, ejecuta el merge con sync_saved=True,
comprueba que se guardó, y la QUITA de Me gusta al terminar (el total debe quedar igual).
"""
import tempfile
import time
from pathlib import Path

from music_manager.core.job_manager import SAVED_LABEL, JobManager
from music_manager.core.models import MergeJob
from music_manager.core.spotify_client import SpotifyClient

c = SpotifyClient()
sp = c.sp
by_name = {p["name"]: p["id"] for p in c.get_user_playlists() if p["name"].startswith("mm-test-")}
hoja, mid, root = (by_name[n] for n in ("mm-test-hoja", "mm-test-intermedia", "mm-test-raiz"))

total_before = sp.current_user_saved_tracks(limit=1)["total"]
print("Guardadas antes:", total_before)

candidate = None
for q in ("Despacito", "Danza Kuduro", "Bailando Enrique Iglesias"):
    for t in sp.search(q, limit=10, type="track")["tracks"]["items"]:
        if sp.current_user_saved_tracks_contains([t["uri"]]) == [False]:
            candidate = t
            break
    if candidate:
        break
assert candidate, "No he encontrado una canción no guardada"
uri = candidate["uri"]

try:
    c.add_tracks_to_playlist(hoja, [uri])
    time.sleep(2)
    tmp = Path(tempfile.mkdtemp(prefix="mm_real_")) / "merges.json"
    m = JobManager(config_path=str(tmp))
    m.add_job(MergeJob(name="raiz", target_id=root, source_ids=[mid]))
    m.add_job(MergeJob(name="intermedia", target_id=mid, source_ids=[hoja]))

    results = m.run_with_propagation("intermedia", c, sync_saved=True)
    for r in results:
        print(f"   {r.name:<11} {r.status:<7} añadidas={r.added} {r.detail[:60]}")
    time.sleep(2)
    now_saved = sp.current_user_saved_tracks_contains([uri]) == [True]
    row = next(r for r in results if r.name == SAVED_LABEL)
    print("La canción ahora está en Me gusta:", now_saved, "| fila Me gusta:", row.status, row.added)
finally:
    # Dejar la biblioteca como estaba
    sp.current_user_saved_tracks_delete([uri])

time.sleep(2)
total_after = sp.current_user_saved_tracks(limit=1)["total"]
print("Guardadas después de restaurar:", total_after, "(igual que antes)" if total_after == total_before else "(¡DISTINTO!)")
print("RESULTADO:", "TODO OK" if now_saved and row.added == 1 and total_after == total_before else "REVISAR")
