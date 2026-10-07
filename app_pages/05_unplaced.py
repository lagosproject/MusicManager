"""Unplaced tracks page: find Liked Songs not in any merge playlist and assign them to leaves."""
import pandas as pd
import streamlit as st
from music_manager.core.api_calls import describe_api_error
from music_manager.core.cache_store import slim_item
from music_manager.core.merge_tree import all_leaf_playlists, tree_playlist_ids
from music_manager.core.organization import (
    SAFE_SUGGESTION_SCORE,
    build_artist_index,
    find_unplaced,
    group_by_destination,
    suggest,
)
from app_pages.ui_common import (
    get_playlist_tracks_cached,
    get_saved_tracks_cached,
    playlist_label,
    save_cache_to_disk,
)

st.title("Guardadas sin playlist")
st.write(
    "Canciones de tus «Me gusta» que no están en ninguna playlist de tus merges. "
    "Colócalas en una playlist hoja y el siguiente merge las subirá."
)

jobs = st.session_state.job_manager.jobs
if not jobs:
    st.info("Todavía no tienes merges. Crea uno en «Gestión de merges».")
    st.stop()

placed_result = st.session_state.pop("placed_result", None)
if placed_result:
    placed_count, placed_errors = placed_result
    if placed_count:
        st.success(f"Colocadas {placed_count} canciones. Ejecuta los merges para que lleguen a las playlists de arriba.")
    for message in placed_errors:
        st.error(message)

leaf_ids = all_leaf_playlists(jobs)
if not leaf_ids:
    st.error("Tus merges no tienen playlists de origen donde colocar canciones.")
    st.stop()

refresh = st.button("Actualizar datos", icon=":material/refresh:", help="Vuelve a leer todo de Spotify.")
with st.spinner("Leyendo tus guardadas y tus playlists..."):
    saved_items = get_saved_tracks_cached(force_refresh=refresh)
    tree_tracks = {pid: get_playlist_tracks_cached(pid, force_refresh=refresh) for pid in tree_playlist_ids(jobs)}
unplaced = find_unplaced(saved_items, tree_tracks.values())

st.caption(f"{len(unplaced)} de tus {len(saved_items)} canciones guardadas no están en ninguna playlist del árbol.")
if not unplaced:
    st.success("Todas tus canciones guardadas están en alguna playlist del árbol.")
    st.stop()

leaf_names = {pid: playlist_label(pid) for pid in leaf_ids}
artist_index = build_artist_index({pid: tree_tracks[pid] for pid in leaf_ids})

col_search, col_confident = st.columns([3, 2], vertical_alignment="bottom")
search = col_search.text_input("Buscar", placeholder="Título o artista", key="unplaced_search").strip().lower()
confident_only = col_confident.toggle(
    "Preseleccionar solo sugerencias seguras", value=True, key="unplaced_confident",
    help="Seguras: la playlist ya tiene muchas canciones del mismo artista.",
)


def row_matches(track):
    artists = " ".join(a.get("name") or "" for a in track.get("artists") or [])
    return search in f"{track.get('name') or ''} {artists}".lower()


visible = [t for t in unplaced if row_matches(t)] if search else unplaced
unplaced_limit = st.session_state.setdefault("unplaced_limit", 25)
choices = {}

for track in visible[:unplaced_limit]:
    suggestions = suggest(track, artist_index, leaf_names)
    best = suggestions[0] if suggestions else None
    preselect = best and (best.score >= SAFE_SUGGESTION_SCORE or not confident_only)
    artists = ", ".join(a.get("name") or "" for a in track.get("artists") or [] if isinstance(a, dict))

    with st.container(border=True):
        col_info, col_pick = st.columns([3, 3], vertical_alignment="center")
        with col_info:
            st.markdown(f"**{track.get('name') or 'Canción sin título'}**")
            st.caption(artists or "Artista desconocido")
        with col_pick:
            choice = st.selectbox(
                "Playlist de destino",
                options=list(leaf_names),
                format_func=leaf_names.get,
                index=list(leaf_names).index(best.playlist_id) if preselect else None,
                placeholder="Sin colocar",
                label_visibility="collapsed",
                key=f"unplaced_{confident_only}_{track['uri']}",
            )
            if best:
                st.caption(best.reason)
    if choice:
        choices[track['uri']] = choice

if len(visible) > unplaced_limit:
    st.caption(f"Mostrando {unplaced_limit} de {len(visible)}.")
    if st.button("Mostrar 25 más"):
        st.session_state.unplaced_limit = unplaced_limit + 25
        st.rerun()

st.divider()
if st.button(f"Colocar {len(choices)} canciones", type="primary", icon=":material/playlist_add:", disabled=not choices):
    st.session_state.unplaced_pending = dict(choices)

pending = st.session_state.get("unplaced_pending")
if pending and pending != choices:
    st.session_state.pop("unplaced_pending")
    pending = None
if pending:
    grouped = group_by_destination(pending)
    with st.container(border=True):
        st.warning(f"Se añadirán **{len(pending)}** canciones a tus playlists. Esto modifica Spotify.")
        st.dataframe(
            pd.DataFrame([{"Playlist": leaf_names[pid], "Canciones": len(uris)} for pid, uris in grouped.items()]),
            hide_index=True,
        )
        with st.container(horizontal=True):
            confirmed = st.button("Confirmar", type="primary", key="unplaced_confirm")
            cancelled = st.button("Cancelar", key="unplaced_cancel")
    if confirmed:
        by_uri = {t['uri']: t for t in unplaced}
        done, errors = 0, []
        with st.spinner("Colocando canciones..."):
            for pid, uris in grouped.items():
                try:
                    st.session_state.spotify.add_tracks_to_playlist(pid, uris)
                except Exception as e:
                    errors.append(f"«{leaf_names[pid]}»: {describe_api_error(e)}")
                    continue
                done += len(uris)
                if pid in st.session_state.playlist_data_cache:
                    st.session_state.playlist_data_cache[pid] += [slim_item(by_uri[u]) for u in uris]
            save_cache_to_disk()
        st.session_state.placed_result = (done, errors)
        st.session_state.pop("unplaced_pending")
        st.rerun()
    if cancelled:
        st.session_state.pop("unplaced_pending")
        st.rerun()
