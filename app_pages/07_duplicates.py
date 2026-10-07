"""Duplicates audit page: detect exact or title duplicates and remove extra copies with precision."""
import pandas as pd
import streamlit as st
from music_manager.core.duplicates import (
    MODE_SAME_TRACK,
    MODE_SAME_TITLE,
    copies_to_remove,
    describe_copy,
    find_duplicate_groups,
    remove_duplicates,
    track_url,
)
from app_pages.ui_common import (
    _editable_playlists,
    get_playlist_tracks_cached,
    or_stop,
)

st.title("Duplicados en una playlist")

outcome = st.session_state.pop("duplicates_result", None)
if outcome:
    if outcome.error:
        st.error(f"No se pudo completar: {outcome.error}")
    if outcome.restored:
        st.warning(
            f"Spotify quitó {outcome.restored} canción(es) que debían conservarse y las he vuelto a añadir "
            "(pueden haber cambiado de posición)."
        )
    if not outcome.error:
        st.success(f"Listo: se han quitado {outcome.removed} copias.")

editable = or_stop(_editable_playlists, st.session_state.spotify, st.session_state.spotify_user['id'])
if not editable:
    st.info("No hay playlists tuyas o colaborativas que revisar.")
    st.stop()
labels = dict(editable)

selected_pl_id = st.selectbox("Playlist", options=list(labels), format_func=labels.get, key="dup_playlist")
mode_options = {
    "Misma canción repetida": MODE_SAME_TRACK,
    "Posibles duplicados (mismo artista y título)": MODE_SAME_TITLE,
}
mode_label = st.segmented_control("Qué buscar", list(mode_options), default=list(mode_options)[0], key="dup_mode")
mode = mode_options.get(mode_label, MODE_SAME_TRACK)
if mode == MODE_SAME_TITLE:
    st.caption("Pueden ser ediciones distintas de la misma canción. Elige cuál conservar en cada una; por defecto no se toca ninguna.")

refresh = st.button("Actualizar datos", icon=":material/refresh:")
tracks = get_playlist_tracks_cached(selected_pl_id, force_refresh=refresh)
groups = find_duplicate_groups(tracks, mode)

detail_flag = f"dup_detailed_{selected_pl_id}"
if groups and not st.session_state.get(detail_flag) and any(
    not (t.get("album") or {}).get("name") for g in groups for t in g.tracks
):
    with st.spinner("Leyendo los detalles de cada versión..."):
        tracks = get_playlist_tracks_cached(selected_pl_id, force_refresh=True)
    st.session_state[detail_flag] = True
    groups = find_duplicate_groups(tracks, mode)

if not groups:
    st.success("No hay duplicados de este tipo en esta playlist.")
    st.stop()

st.caption(f"{len(groups)} canciones repetidas, {sum(g.extras for g in groups)} copias de más.")
dup_limit = st.session_state.setdefault("dup_limit", 15)
keep = {}
for group in groups[:dup_limit]:
    choice_key = f"dup_choice_{selected_pl_id}_{mode}_{group.key}"
    with st.container(border=True):
        st.markdown(f"**{group.name}** — {group.artist}  ·  {len(group.positions)} copias")
        if mode == MODE_SAME_TRACK:
            st.caption("La misma canción " + " · ".join(
                f"({describe_copy(t, a) or 'sin detalles'})" for t, a in zip(group.tracks, group.added)
            ))
            choice = st.radio(
                "Qué hacer", ["remove", "none"], key=choice_key, horizontal=True, label_visibility="collapsed",
                format_func={"remove": "Quitar las copias de más (se queda la primera)", "none": "No hacer nada"}.get,
            )
            if choice == "remove":
                keep[group.key] = group.uris[0]
        else:
            versions = {u: next(t for t, uri in zip(group.tracks, group.uris) if uri == u) for u in group.distinct_uris}
            added_by_uri = {u: next(a for a, uri in zip(group.added, group.uris) if uri == u) for u in versions}
            options = list(versions) + ["none"]
            option_labels = {"none": "Dejar todas las versiones como están"}
            for u, version in versions.items():
                copies = group.uris.count(u)
                option_labels[u] = (
                    f"Quedarme con: {version.get('name')} · {describe_copy(version, added_by_uri[u])}"
                    + (f" (×{copies})" if copies > 1 else "")
                )

            choice = st.radio("Qué versión conservar", options, index=len(options) - 1, key=choice_key,
                              format_func=option_labels.get, label_visibility="collapsed")
            st.caption("Abrir en Spotify: " + " · ".join(
                f"[{versions[u].get('name')} ({(versions[u].get('album') or {}).get('name') or '?'})]({track_url(versions[u])})"
                for u in versions
            ))
            if choice != "none":
                keep[group.key] = choice

if len(groups) > dup_limit:
    st.caption(f"Mostrando {dup_limit} de {len(groups)} canciones repetidas.")
    if st.button("Mostrar 15 más"):
        st.session_state.dup_limit = dup_limit + 15
        st.rerun()

chosen = [g for g in groups if g.key in keep]
to_remove = [(g, c) for g in chosen for c in copies_to_remove(g, keep[g.key])]
if st.button(f"Quitar {len(to_remove)} copias", type="primary", icon=":material/delete:", disabled=not to_remove):
    st.session_state.dup_pending = {"playlist": selected_pl_id, "mode": mode, "keep": dict(keep)}

pending = st.session_state.get("dup_pending")
if pending and pending != {"playlist": selected_pl_id, "mode": mode, "keep": dict(keep)}:
    st.session_state.pop("dup_pending")
    pending = None
if pending:
    with st.container(border=True):
        st.warning(
            f"Se quitarán estas **{len(to_remove)}** copias de «{labels[selected_pl_id]}». "
            "Esto modifica tu playlist en Spotify."
        )
        if any(g.uris.count(keep[g.key]) > 1 for g in chosen):
            st.caption(
                "Spotify ya no permite borrar una copia concreta. En las canciones repetidas exactamente se quitan "
                "todas las copias y se vuelve a añadir una en el mismo sitio."
            )
        st.dataframe(
            pd.DataFrame([
                {
                    "Canción": t.get("name"),
                    "Artista": ", ".join(a.get("name") or "" for a in t.get("artists") or []),
                    "Álbum": (t.get("album") or {}).get("name") or "",
                    "Año": ((t.get("album") or {}).get("release_date") or "")[:4],
                    "Añadida": added[:10],
                }
                for _, (t, added) in to_remove
            ]),
            hide_index=True,
        )
        with st.container(horizontal=True):
            confirmed = st.button("Confirmar", type="primary", key="dup_confirm")
            cancelled = st.button("Cancelar", key="dup_cancel")
    if confirmed:
        with st.spinner("Quitando copias..."):
            outcome = remove_duplicates(st.session_state.spotify, selected_pl_id, mode, keep)
        get_playlist_tracks_cached(selected_pl_id, force_refresh=True)
        st.session_state.duplicates_result = outcome
        st.session_state.pop("dup_pending")
        st.rerun()
    if cancelled:
        st.session_state.pop("dup_pending")
        st.rerun()
