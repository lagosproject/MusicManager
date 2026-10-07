"""Diagnóstico de proveedores externos: Last.fm, MusicBrainz, AcousticBrainz, yt-dlp+ffmpeg, shazamio.

No escribe en data/ (no usa las cachés de la app) y no imprime claves.
Ejecutar desde la raíz:  python tools/diag/diag_providers.py
"""
import asyncio
import os
import time
from pathlib import Path

import musicbrainzngs
import requests

from music_manager.config import settings

ARTIST, TITLE = "Bad Bunny", "Tití Me Preguntó"
KEY = settings.lastfm_api_key or ""


def clean(msg):
    s = str(msg)
    for secret in (KEY, settings.lastfm_shared_secret or ""):
        if secret:
            s = s.replace(secret, "***")
    return s.replace("\n", " ")[:300]


def step(name, fn):
    t0 = time.time()
    try:
        out = fn()
        print(f"[OK ] {name} ({time.time()-t0:.1f}s) {out}", flush=True)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] {name} ({time.time()-t0:.1f}s) {type(e).__name__}: {clean(e)}", flush=True)
        return None


# 1. Last.fm: track.getTopTags (lo que usa la app vía pylast) y track.getInfo
def lastfm():
    r = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={"method": "track.getTopTags", "artist": ARTIST, "track": TITLE,
                "api_key": KEY, "format": "json"},
        timeout=15,
    )
    j = r.json()
    if "error" in j:
        return f"HTTP {r.status_code} error_lastfm={j['error']} msg={clean(j.get('message'))}"
    tags = [t["name"] for t in j.get("toptags", {}).get("tag", [])][:8]
    return f"HTTP {r.status_code} tags={tags}"

step("Last.fm track.getTopTags", lastfm)


def lastfm_similar():
    r = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={"method": "artist.getSimilar", "artist": ARTIST, "limit": 5,
                "api_key": KEY, "format": "json"},
        timeout=15,
    )
    j = r.json()
    if "error" in j:
        return f"error={j['error']} {clean(j.get('message'))}"
    return [a["name"] for a in j["similarartists"]["artist"]]

step("Last.fm artist.getSimilar", lastfm_similar)


def lastfm_track_similar():
    r = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={"method": "track.getSimilar", "artist": ARTIST, "track": TITLE, "limit": 5,
                "api_key": KEY, "format": "json"},
        timeout=15,
    )
    j = r.json()
    if "error" in j:
        return f"error={j['error']} {clean(j.get('message'))}"
    return [f"{t['artist']['name']} - {t['name']}" for t in j["similartracks"]["track"]]

step("Last.fm track.getSimilar", lastfm_track_similar)

# 2. MusicBrainz
musicbrainzngs.set_useragent("MusicManagerDiag", "0.1", "diag")
mbid = step("MusicBrainz search_recordings",
            lambda: musicbrainzngs.search_recordings(artist=ARTIST, recording=TITLE, limit=3)["recording-list"][0]["id"])

# 3. AcousticBrainz
if mbid:
    def ab():
        out = []
        for kind in ("low-level", "high-level"):
            r = requests.get(f"https://acousticbrainz.org/api/v1/{mbid}/{kind}", timeout=15)
            out.append(f"{kind}: HTTP {r.status_code}")
        return " | ".join(out)
    step("AcousticBrainz", ab)
    step("AcousticBrainz (ping raíz)", lambda: f"HTTP {requests.get('https://acousticbrainz.org/', timeout=15).status_code}")

# 4. yt-dlp + ffmpeg (AudioAnalyzer._download_track real)
from music_manager.core.audio_analyzer import AudioAnalyzer

an = AudioAnalyzer(temp_dir=str(Path(settings.data_dir) / "temp_audio_diag"))
wav = step("yt-dlp+ffmpeg _download_track", lambda: an._download_track(ARTIST, TITLE))
if wav and os.path.exists(wav):
    size = os.path.getsize(wav)
    print(f"      wav={size/1e6:.2f} MB")
    # duración con ffprobe si está
    import subprocess
    try:
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", wav], capture_output=True, text=True, timeout=30).stdout.strip()
        print(f"      duración={d}s (se pedían 45s)")
    except Exception as e:  # noqa: BLE001
        print(f"      ffprobe no disponible: {e}")

    # 5. shazamio
    async def sz():
        from shazamio import Shazam
        out = await Shazam().recognize(wav)
        t = out.get("track", {})
        return f"titulo={t.get('title')} artista={t.get('subtitle')} genero={t.get('genres', {}).get('primary')}"
    step("shazamio recognize", lambda: asyncio.run(sz()))
    try:
        os.remove(wav)
        print("      wav borrado")
    except Exception as e:  # noqa: BLE001
        print(f"      no se pudo borrar wav: {e}")
else:
    print("      (sin wav; se omite shazamio)")
