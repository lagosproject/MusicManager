# tools/diag

Scripts para comprobar contra el Spotify real (y otros servicios) qué funciona. Sirven para repetir las
pruebas cuando Spotify cambie otra cosa de su API. Se ejecutan **desde la raíz del proyecto** y con el
entorno virtual activo:

```powershell
python tools/diag/diag_spotify.py
```

## Solo leen

| Script | Qué comprueba |
|---|---|
| `diag_spotify.py` | Todas las operaciones de lectura que usa la app (perfil, playlists, pistas, artistas, búsqueda, endpoints retirados). Con `--write` **también escribe** (ver abajo) |
| `diag_public.py` | Catálogo con client credentials (sin usuario) |
| `diag_authorize.py` | Que Spotify acepte el Client ID, el Redirect URI y los permisos, sin iniciar sesión |
| `diag_login.py` | Login aislado de Streamlit (`min`, `full` o una lista de permisos). Muestra el error completo; no guarda el token |
| `diag_ratelimit.py` | Qué endpoints está limitando Spotify ahora y cuánto pide esperar. Usa `requests` directo: no reintenta ni duerme |
| `diag_batch_limits.py` | Cuántas canciones admite `GET /me/library/contains` por petición (40) |
| `diag_providers.py` | Last.fm, MusicBrainz, AcousticBrainz, yt-dlp + ffmpeg y shazamio. Descarga 45 s de audio en `data/temp_audio_diag` y lo borra |
| `diag_app.py` | Recorre las pantallas de la app con `AppTest` y tus datos reales, sin pulsar botones |

## Escriben en tu cuenta de Spotify (úsalos sabiendo lo que hacen)

| Script | Qué escribe |
|---|---|
| `diag_spotify.py --write` y `diag_write.py` | Crean una playlist privada `mm-diagnostico-borrar`, añaden y quitan 1 pista. **La playlist queda: bórrala a mano** |
| `diag_library.py` | Guarda 1 canción que no tengas en "Me gusta" y la quita enseguida; compara el total. Pide el permiso `user-library-modify` |
| `diag_merge_real.py` | Crea 3 playlists privadas `mm-test-hoja`, `mm-test-intermedia` y `mm-test-raiz` y prueba la propagación de merges. **Quedan: bórralas a mano** |
| `diag_sync_real.py` | Usa las `mm-test-*`: guarda 1 canción en "Me gusta" y la quita al terminar |
| `diag_dedupe_real.py` | Crea (o reutiliza) `mm-test-duplicados` y prueba el borrado de duplicados: una canción repetida, dos versiones y 101 duplicadas. **El tercer escenario hace unas 200 peticiones de playlist: ver el aviso de abajo** |

Ninguno imprime tokens ni claves.

## Aviso: Spotify limita las peticiones de playlist

La API de Spotify en modo desarrollo limita mucho las peticiones de **playlists** (`/me/playlists`,
`/playlists/{id}`, `/playlists/{id}/items`). El 2026-10-01 una tanda de pruebas (varias previsualizaciones de
cientos de peticiones y el escenario de 101 duplicados de `diag_dedupe_real.py`) hizo que Spotify respondiera
429 con `Retry-After` de **casi 22 horas** para esos endpoints, mientras `/me`, las canciones guardadas, los
artistas seguidos y la búsqueda seguían funcionando. Evita repetir scripts que lean o escriban muchas playlists
seguidas, y usa `diag_ratelimit.py` para ver si hay un límite activo antes de lanzar otra cosa.
