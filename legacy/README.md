# legacy

Código de la primera versión del proyecto (scripts sueltos para Spotify, YouTube Music, Deezer y Tidal).
**No lo usa la aplicación actual** (`main_streamlit.py` y el paquete `music_manager/`) y no se mantiene.
Se conserva por si hace falta consultar algo.

- `app.py` es el punto de entrada antiguo. Se ejecuta **desde esta carpeta** (`cd legacy`), porque importa
  `spoManager`, `ytManager`, `deezManager` y `tidalManager` desde el directorio actual y lee sus ficheros de
  sesión (`headers_auth.json`, `datos_tidal.json`, ignorados por git) también desde ahí.
- `artistas` y `recomendaciones` son volcados de datos de aquella época.
- `getToken.bat` y `spoManager.py` pueden contener credenciales antiguas. No las uses; si siguen activas,
  revócalas en el panel del servicio correspondiente.
