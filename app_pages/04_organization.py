"""Organization audit page: detect tracks in target not present in any leaf playlist."""
import streamlit as st
from music_manager.core.api_calls import describe_api_error
from music_manager.core.cache_store import slim_item
from music_manager.core.merge_tree import leaf_playlists, subtree_playlists
from music_manager.core.organization import build_artist_index, find_uncategorized, suggest
from music_manager.core.tracks import extract_track
from app_pages.ui_common import (
    get_playlist_tracks_cached,
    playlist_label,
    save_cache_to_disk,
)

st.title("Auditoría de organización")
st.write(
    "Canciones que están en el destino de un merge pero en ninguna de las playlists de debajo. "
    "Colócalas en una playlist hoja y el siguiente merge las subirá."
)

jobs = st.session_state.job_manager.jobs
if not jobs:
    st.info("Todavía no tienes merges. Crea uno en «Gestión de merges».")
    st.stop()

selected_job_name = st.selectbox("Merge", [j.name for j in jobs], key="audit_job")
job = next(j for j in jobs if j.name == selected_job_name)
refresh = st.button("Actualizar datos", icon=":material/refresh:")

below_ids = subtree_playlists(job, jobs)
leaf_ids = leaf_playlists(job, jobs)
if not leaf_ids:
    st.error("Este merge no tiene playlists de origen donde colocar canciones.")
    st.stop()

target_tracks = get_playlist_tracks_cached(job.target_id, force_refresh=refresh)
below_tracks = {pid: get_playlist_tracks_cached(pid, force_refresh=refresh) for pid in below_ids}
uncategorized = find_uncategorized(target_tracks, below_tracks.values())

if not uncategorized:
    st.success("Todo está colocado en alguna playlist de debajo.")
    st.stop()

st.warning(f"Hay {len(uncategorized)} canciones sin colocar en «{playlist_label(job.target_id)}».")
leaf_names = {pid: playlist_label(pid) for pid in leaf_ids}
artist_index = build_artist_index({pid: below_tracks[pid] for pid in leaf_ids})
destinations = list(leaf_names)
audit_limit = st.session_state.setdefault("audit_limit", 50)

for track in uncategorized[:audit_limit]:
    suggestions = suggest(track, artist_index, leaf_names)
    best = suggestions[0] if suggestions else None
    track_uri = track['uri']
    artists = ", ".join(a.get('name') or "" for a in track.get('artists') or [] if isinstance(a, dict))

    with st.container(border=True):
        col_info, col_pick, col_actions = st.columns([3, 3, 2], vertical_alignment="center")
        with col_info:
            st.markdown(f"**{track.get('name') or 'Canción sin título'}**")
            st.caption(artists or "Artista desconocido")
        with col_pick:
            choice = st.selectbox(
                "Playlist de destino",
                options=destinations,
                format_func=leaf_names.get,
                index=destinations.index(best.playlist_id) if best else None,
                placeholder="Elige una playlist",
                label_visibility="collapsed",
                key=f"audit_pick_{track_uri}",
            )
            if best:
                st.caption(best.reason)
        with col_actions:
            with st.container(horizontal=True):
                add_clicked = st.button("Añadir", key=f"audit_add_{track_uri}", icon=":material/add:", disabled=choice is None)
                with st.popover("Quitar", icon=":material/delete:"):
                    st.write(f"Se quitará de «{playlist_label(job.target_id)}». No se borra de tus guardadas.")
                    remove_clicked = st.button("Quitar del destino", key=f"audit_remove_{track_uri}")

    changed = False
    try:
        if add_clicked:
            st.session_state.spotify.add_tracks_to_playlist(choice, [track_uri])
            if choice in st.session_state.playlist_data_cache:
                st.session_state.playlist_data_cache[choice].append(slim_item(track))
                save_cache_to_disk()
            st.toast(f"Añadida a «{leaf_names[choice]}». Ejecuta el merge para subirla.")
            changed = True
        elif remove_clicked:
            st.session_state.spotify.remove_track_from_playlist(job.target_id, [track_uri])
            target_id = st.session_state.spotify.get_playlist_id(job.target_id)
            if target_id in st.session_state.playlist_data_cache:
                st.session_state.playlist_data_cache[target_id] = [
                    item for item in st.session_state.playlist_data_cache[target_id]
                    if (extract_track(item) or {}).get('uri') != track_uri
                ]
                save_cache_to_disk()
            st.toast("Quitada del destino.")
            changed = True
    except Exception as e:
        st.error(describe_api_error(e))
    if changed:
        st.rerun()

if len(uncategorized) > audit_limit:
    st.caption(f"Mostrando {audit_limit} de {len(uncategorized)}.")
    if st.button("Mostrar 50 más"):
        st.session_state.audit_limit = audit_limit + 50
        st.rerun()
