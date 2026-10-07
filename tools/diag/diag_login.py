"""Prueba de login de Spotify aislada de Streamlit. No guarda tokens ni escribe ficheros.

Uso:  python tools/diag/diag_login.py min     (scope user-read-private)
      python tools/diag/diag_login.py full    (el scope completo de la app)
      python tools/diag/diag_login.py <scope1,scope2,...>
Abre la URL que imprime (mejor en ventana privada), inicia sesión y acepta.
"""
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from music_manager.config import settings

arg = sys.argv[1] if len(sys.argv) > 1 else "min"
FULL = "user-library-read user-follow-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
scope = {"min": "user-read-private", "full": FULL}.get(arg, arg.replace(",", " "))

ru = urlparse(settings.spotipy_redirect_uri)
result = {}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        result.update({k: v[0] for k, v in q.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Listo. Puedes cerrar esta ventana y volver a la terminal.".encode())
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *a):
        pass


url = "https://accounts.spotify.com/authorize?" + urlencode({
    "client_id": settings.spotipy_client_id, "response_type": "code",
    "redirect_uri": settings.spotipy_redirect_uri, "scope": scope, "state": "diag", "show_dialog": "true"})
print(f"Scope probado: {scope}")
print("Abre esta URL (mejor en ventana privada):\n" + url + "\n")
print("Esperando respuesta de Spotify (máx. 3 min)...", flush=True)

srv = HTTPServer((ru.hostname, ru.port), H)
srv.timeout = 180
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
t.join(180)

if not result:
    print("Sin respuesta (tiempo agotado).")
    sys.exit(1)

if "error" in result:
    print("ERROR devuelto por Spotify:", {k: v for k, v in result.items() if k != "state"})
    sys.exit(1)

r = requests.post("https://accounts.spotify.com/api/token", data={
    "grant_type": "authorization_code", "code": result["code"],
    "redirect_uri": settings.spotipy_redirect_uri},
    auth=(settings.spotipy_client_id, settings.spotipy_client_secret), timeout=20)
print("Intercambio de código por token: HTTP", r.status_code, "" if r.ok else r.text[:300])
if r.ok:
    tok = r.json()
    print("scopes concedidos:", tok.get("scope"))
    me = requests.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=20)
    print("GET /me: HTTP", me.status_code, "" if me.ok else me.text[:300])
    if me.ok:
        j = me.json()
        print("usuario: product =", j.get("product"), "| country =", j.get("country"), "| claves =", sorted(j.keys()))
