"""Shared UI and caching utilities for MusicManager pages."""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st
from loguru import logger

from music_manager.config import settings
from music_manager.core.api_calls import describe_api_error
from music_manager.core.cache_store import atomic_write_json, slim_items, slim_item
from music_manager.core.merge_tree import normalize_playlist_id
from music_manager.core.tracks import extract_track

# Global Data Paths
data_dir = Path(settings.data_dir)
data_dir.mkdir(parents=True, exist_ok=True)
tracks_cache_path = Path(settings.tracks_cache_path)
artist_cache_path = data_dir / "artist_cache.json"
genre_mapping_path = data_dir / "genre_playlist_mapping.json"

RECENT_READ_SECONDS = 30 * 60


def load_json_file(path: Path, default: Any) -> Any:
    """Reads a JSON file; a missing or corrupt file gives the default instead of crashing."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"No se pudo leer {path.name}: {e}")
        return default


def save_cache_to_disk() -> None:
    atomic_write_json(tracks_cache_path, st.session_state.playlist_data_cache, compact=True)


def save_artist_cache() -> None:
    atomic_write_json(artist_cache_path, st.session_state.artist_cache)


def save_genre_mapping() -> None:
    atomic_write_json(genre_mapping_path, st.session_state.genre_mapping)


@st.cache_data(ttl=3600, max_entries=500)
def _fetch_playlist_info(playlist_id: str, _client: Any) -> Optional[Dict[str, Any]]:
    return _client.get_playlist_info(playlist_id)


def get_cached_playlist_info(playlist_id: str) -> Optional[Dict[str, Any]]:
    """Playlist metadata, or None if it cannot be fetched."""
    try:
        return _fetch_playlist_info(playlist_id, st.session_state.spotify)
    except Exception as e:
        logger.warning(f"No se pudo leer la playlist {playlist_id}: {e}")
        return None


def or_stop(fn, *args, **kwargs):
    """Calls Spotify; if it fails, shows an error on screen and stops the page."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.error(describe_api_error(e), icon=":material/error:")
        st.stop()


def playlist_label(ref: str) -> str:
    """Playlist name for display, falling back to its bare ID."""
    info = get_cached_playlist_info(ref)
    return info['name'] if info else normalize_playlist_id(ref)


@st.cache_data(ttl=300)
def _count_user_playlists(_client: Any) -> int:
    return _client.sp.current_user_playlists(limit=1)['total']


@st.cache_data(ttl=300)
def _editable_playlists(_client: Any, user_id: str) -> List[tuple]:
    """(id, name) of the playlists the user can modify: their own and collaborative ones."""
    playlists = _client.get_user_playlists()
    mine = [p for p in playlists if p.get('collaborative') or (p.get('owner') or {}).get('id') == user_id]
    return sorted(((p['id'], p['name']) for p in mine), key=lambda pair: pair[1].lower())


def get_playlist_tracks_cached(playlist_id: str, force_refresh: bool = False, save: bool = True) -> List[Dict[str, Any]]:
    pid = st.session_state.spotify.get_playlist_id(playlist_id)
    if pid not in st.session_state.playlist_data_cache or force_refresh:
        tracks = or_stop(st.session_state.spotify.get_playlist_tracks, pid)
        st.session_state.playlist_data_cache[pid] = slim_items(tracks)
        st.session_state.cache_read_at[pid] = time.time()
        if save:
            save_cache_to_disk()
    return st.session_state.playlist_data_cache[pid]


def get_saved_tracks_cached(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Saved tracks from the local cache, read again only if Spotify's count differs."""
    key = "__saved_tracks__"
    cache = st.session_state.playlist_data_cache
    if force_refresh or key not in cache or len(cache[key]) != or_stop(st.session_state.spotify.get_saved_total):
        tracks = or_stop(st.session_state.spotify.get_saved_tracks)
        cache[key] = slim_items(tracks)
        save_cache_to_disk()
    return cache[key]


def get_saved_uris(force_refresh: bool = False) -> set:
    """URIs of the saved tracks (Liked Songs)."""
    return {t["uri"] for t in (extract_track(i) for i in get_saved_tracks_cached(force_refresh)) if t and t.get("uri")}


def recent_playlists_seed() -> Dict[str, List[Dict[str, Any]]]:
    """Playlists read from Spotify in the last 30 minutes, as slim tracks."""
    now = time.time()
    cache = st.session_state.playlist_data_cache
    return {
        pid: [i["item"] for i in cache[pid] if i.get("item")]
        for pid, read_at in st.session_state.cache_read_at.items()
        if pid in cache and now - read_at < RECENT_READ_SECONDS
    }


def _tracks_table(tracks: List[Dict[str, Any]], show_origin: bool = False) -> None:
    rows = []
    for t in tracks[:300]:
        row = {"Canción": t.get("name") or t.get("uri"), "Artista": ", ".join(a.get("name") or "" for a in t.get("artists") or [])}
        if show_origin:
            row["Viene de"] = playlist_label(t["from"]) if t.get("from") else ""
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    if len(tracks) > 300:
        st.caption(f"…y {len(tracks) - 300} más.")


def show_run_results(results) -> None:
    """Drops the cached tracks of the playlists that were updated and shows what happened."""
    st.session_state.pop("merge_preview", None)
    jobs_by_name = {j.name: j for j in st.session_state.job_manager.jobs}
    for result in results:
        job = jobs_by_name.get(result.name)
        if job and result.status == "ok" and result.added:
            st.session_state.playlist_data_cache.pop(st.session_state.spotify.get_playlist_id(job.target_id), None)
    save_cache_to_disk()

    labels = {"ok": "Hecho", "error": "Error", "skipped": "Omitido"}
    st.dataframe(
        pd.DataFrame([
            {"Merge": r.name, "Resultado": labels[r.status], "Canciones añadidas": r.added, "Detalle": r.detail}
            for r in results
        ]),
        hide_index=True,
    )
    if any(r.status != "ok" for r in results):
        st.error("Algún merge no se ha completado. Revisa el detalle.")
    else:
        st.success(f"Listo: {sum(r.added for r in results)} canciones añadidas en total.")


def compute_merge_preview(scope: Optional[str], sync_saved: bool, fresh: bool = False) -> None:
    """Calculates what a run would do and stores it in session state."""
    manager, client = st.session_state.job_manager, st.session_state.spotify
    try:
        with st.spinner("Leyendo tus playlists para calcular los cambios..."):
            reuse = {
                "seed": None if fresh else recent_playlists_seed(),
                "saved_uris": get_saved_uris(force_refresh=fresh) if sync_saved else None,
            }
            if scope:
                preview = manager.preview_with_propagation(scope, client, sync_saved, **reuse)
            else:
                preview = manager.preview_tree(client, sync_saved, **reuse)
        for playlist_id, tracks in preview.read.items():
            st.session_state.playlist_data_cache[playlist_id] = [{"item": t} for t in tracks]
            st.session_state.cache_read_at[playlist_id] = time.time()
        if preview.read:
            save_cache_to_disk()
        st.session_state.merge_preview = preview
    except Exception as e:
        st.session_state.pop("merge_preview", None)
        st.error(describe_api_error(e))


def show_merge_preview() -> None:
    """Renders the preview card with execute, reread and discard buttons."""
    preview = st.session_state.get("merge_preview")
    if not preview:
        return
    total_added = sum(len(j.to_add) for j in preview.jobs)
    scope = f"«{preview.scope}» y los merges que dependen de él" if preview.scope else "todo el árbol"

    with st.container(border=True):
        st.subheader(f"Vista previa: {scope}")
        st.caption("Todavía no se ha cambiado nada. Reutiliza lo leído de Spotify hace menos de 30 minutos.")
        for name in preview.cyclic:
            st.warning(f"«{name}» forma parte de un ciclo entre playlists y no se ejecutará.")

        st.dataframe(
            pd.DataFrame([
                {"Merge": j.name, "Playlist destino": playlist_label(j.target_id), "Canciones que se añadirían": len(j.to_add)}
                for j in preview.jobs
            ]),
            hide_index=True,
        )
        if preview.sync_saved:
            st.markdown(f"**«Me gusta»:** se guardarían **{len(preview.to_save)}** canciones que ahora no tienes guardadas.")
        else:
            st.markdown("**«Me gusta»:** no se tocará (el interruptor está apagado).")

        for j in preview.jobs:
            if j.to_add:
                with st.expander(f"{j.name}: {len(j.to_add)} canciones nuevas en «{playlist_label(j.target_id)}»"):
                    _tracks_table(j.to_add, show_origin=True)
            if j.local_skipped:
                st.caption(f"{j.name}: {j.local_skipped} archivos locales no se pueden añadir con la API y se omiten.")
        if preview.to_save:
            with st.expander(f"{len(preview.to_save)} canciones que se guardarían en «Me gusta»"):
                _tracks_table(preview.to_save, show_origin=False)

        if not total_added and not preview.to_save:
            st.success("No hay nada que añadir: todo está al día.")

        with st.container(horizontal=True):
            run_it = st.button("Ejecutar estos cambios", type="primary", key="preview_run",
                               icon=":material/play_arrow:", disabled=not (total_added or preview.to_save))
            reread = st.button("Releer de Spotify", key="preview_reread", icon=":material/refresh:")
            discard = st.button("Descartar", key="preview_discard")

    if discard:
        st.session_state.pop("merge_preview")
        st.rerun()
    if reread:
        compute_merge_preview(preview.scope or None, preview.sync_saved, fresh=True)
        st.rerun()
    if run_it:
        manager, client = st.session_state.job_manager, st.session_state.spotify
        with st.spinner("Ejecutando..."):
            if preview.scope:
                results = manager.run_with_propagation(preview.scope, client, sync_saved=preview.sync_saved,
                                                       saved_uris=get_saved_uris() if preview.sync_saved else None)
            else:
                results = manager.run_tree_intelligent(client, sync_saved=preview.sync_saved,
                                                       saved_uris=get_saved_uris() if preview.sync_saved else None)
        st.session_state.pending_run_results = results
        st.rerun()


@st.dialog("Borrar la caché local")
def confirm_clear_cache() -> None:
    st.write("Se borrará la caché de pistas y se volverá a sincronizar todo. No se modifica nada en Spotify.")
    with st.container(horizontal=True):
        if st.button("Borrar caché", type="primary"):
            st.session_state.playlist_data_cache = {}
            if tracks_cache_path.exists():
                tracks_cache_path.unlink()
            st.session_state.initial_sync_done = False
            st.rerun()
        if st.button("Cancelar"):
            st.rerun()


@st.dialog("Eliminar merge")
def confirm_delete_merge(name: str) -> None:
    st.write(f"¿Eliminar el merge «{name}»? Solo se borra la regla guardada: las playlists de Spotify no se tocan.")
    with st.container(horizontal=True):
        if st.button("Eliminar", type="primary"):
            st.session_state.job_manager.delete_job(name)
            st.rerun()
        if st.button("Cancelar"):
            st.rerun()
