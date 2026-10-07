# MusicManager

Aplicación (Streamlit) para ordenar tus playlists de Spotify: árbol de merges que se propaga hacia arriba,
sincronización con "Me gusta", auditoría de organización y de duplicados.

> **Estado:** en estabilización. Funcionan los merges, la sincronización con "Me gusta" y las auditorías de
> duplicados y de organización. El organizador por géneros está pendiente de rehacer (Spotify ya no da los
> géneros de los artistas). El historial de commits cuenta cada paso.

## Requisitos

- Python 3.11 o superior.
- Una app de Spotify propia (ver más abajo) y, opcionalmente, una clave de Last.fm.
- `ffmpeg` en el PATH solo si usas el extra `audio`.

## Instalación (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"        # añade ".[audio]" para yt-dlp y shazamio (experimental)
copy .env.template .env        # y rellena las claves
```

## Puesta en marcha

```powershell
streamlit run main_streamlit.py
```

La primera vez se abre el navegador para autorizar la app en Spotify. El token se guarda en `data/.cache`.
Si algo falla con el login, la propia app explica la causa y ofrece borrar el token y volver a autorizar.

## Tu app de Spotify

En [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) → *Create app*:

- **Redirect URI:** `http://127.0.0.1:8978/callback` (con `127.0.0.1`, no `localhost`), igual que
  `SPOTIPY_REDIRECT_URI` en `.env`.
- Marca **Web API**.
- Copia el Client ID y el Client Secret a `.env`.

Límites del modo desarrollo de Spotify: máximo **5 usuarios**, cada uno dado de alta en *User management* con el
correo exacto de su cuenta, y **la cuenta que creó la app necesita Premium activo** (quien la usa puede ser Free).

## Tests

```powershell
pytest
```

No usan red ni tu cuenta: trabajan con un Spotify simulado y una carpeta de datos temporal.

## Estructura

| Ruta | Qué hay |
|---|---|
| `main_streamlit.py` | La aplicación |
| `music_manager/` | Lógica: cliente de Spotify, árbol de merges, duplicados, organización, cachés |
| `tests/` | Tests con `pytest` y `AppTest` |
| `tools/diag/` | Scripts para comprobar el Spotify real (ver su README; algunos escriben en tu cuenta) |
| `legacy/` | Código de la primera versión; no se usa |
| `data/` | Cachés, merges y token (no se sube a git) |
