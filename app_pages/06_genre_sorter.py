"""Smart Genre Sorter page: offline artist overlap, title pattern detection, preview and manual sorter."""
import pandas as pd
import streamlit as st
from music_manager.core.cache_store import slim_item
from music_manager.core.genres import GENRE_MAPPING, detect_genre_from_title
from music_manager.core.organization import build_artist_index, suggest
from music_manager.core.tracks import extract_track
from app_pages.ui_common import (
    get_playlist_tracks_cached,
    or_stop,
    save_cache_to_disk,
    save_genre_mapping,
)

st.title("⚡ Organizador por Géneros")
st.write("Clasifica tu música rápidamente mediante solape de artistas y patrones de títulos.")

# 1. Configuración de Mapeo
with st.expander("⚙️ Configurar Destinos por Género", expanded=not st.session_state.genre_mapping):
    user_playlists = {p['name']: p['id'] for p in or_stop(st.session_state.spotify.get_user_playlists)}
    pl_names = sorted(list(user_playlists.keys()))

    cols = st.columns(2)
    for i, genre in enumerate(GENRE_MAPPING.keys()):
        col_idx = i % 2
        current_pid = st.session_state.genre_mapping.get(genre)
        current_name = None
        if current_pid:
            for n, pid in user_playlists.items():
                if pid == current_pid:
                    current_name = n
                    break

        try:
            def_idx = pl_names.index(current_name) if current_name else 0
        except ValueError:
            def_idx = 0

        selected_pl = cols[col_idx].selectbox(
            f"Playlist para {genre}:",
            options=pl_names,
            index=def_idx,
            key=f"genre_set_{genre}",
        )
        if selected_pl:
            st.session_state.genre_mapping[genre] = user_playlists[selected_pl]

    if st.button("💾 Guardar Configuración", key="save_genres"):
        save_genre_mapping()
        st.success("Configuración guardada.")

st.divider()

# 2. Selección de Playlist Origen
all_playlists = {p['name']: p['id'] for p in or_stop(st.session_state.spotify.get_user_playlists)}
if not all_playlists:
    st.info("No se han encontrado playlists en tu cuenta.")
    st.stop()

if not st.session_state.genre_mapping:
    st.warning("Configura al menos una playlist de destino por género arriba para clasificar.")
    st.stop()

col_src, col_mode = st.columns([3, 2])
source_pl_name = col_src.selectbox("Playlist origen a clasificar:", options=sorted(list(all_playlists.keys())))
source_pl_id = all_playlists[source_pl_name]

# URIs ya presentes en las playlists de destino
dest_tracks_map = {genre: get_playlist_tracks_cached(pid) for genre, pid in st.session_state.genre_mapping.items()}
categorized_uris = set()
for genre, pts in dest_tracks_map.items():
    for pt in pts:
        p_track = extract_track(pt)
        if p_track and p_track.get('uri'):
            categorized_uris.add(p_track['uri'])

dest_by_pid = {pid: genre for genre, pid in st.session_state.genre_mapping.items()}
artist_index = build_artist_index({pid: dest_tracks_map[genre] for genre, pid in st.session_state.genre_mapping.items()})

source_tracks = get_playlist_tracks_cached(source_pl_id)
uncategorized_in_source = []
for t_item in source_tracks:
    track = extract_track(t_item)
    if track and track.get('uri') and track.get('uri') not in categorized_uris:
        uncategorized_in_source.append(t_item)

st.caption(f"**{len(uncategorized_in_source)}** canciones de «{source_pl_name}» aún no están en ninguna playlist de destino.")

tab_auto, tab_manual = st.tabs(["⚡ Auto-Clasificación con Vista Previa", "🎯 Clasificación Manual"])

# --- TAB 1: Auto-Clasificación con Vista Previa ---
with tab_auto:
    st.markdown("#### Propuesta de Clasificación (Solape de Artistas + Título)")
    st.caption("Analiza las canciones sin clasificarse y sugiere destinos sin llamadas externas.")

    if not uncategorized_in_source:
        st.success("Todas las canciones de esta playlist ya están asignadas a los destinos.")
    else:
        # Calcular propuestas
        proposals = []
        for t_item in uncategorized_in_source:
            track = extract_track(t_item)
            if not track:
                continue
            title = track.get("name") or ""
            artists_str = ", ".join(a.get("name") or "" for a in track.get("artists") or [])

            # 1. Coincidencia por título
            title_genre = detect_genre_from_title(title)
            if title_genre and title_genre in st.session_state.genre_mapping:
                proposals.append({
                    "item": t_item,
                    "uri": track["uri"],
                    "Canción": title,
                    "Artista": artists_str,
                    "Destino": title_genre,
                    "target_id": st.session_state.genre_mapping[title_genre],
                    "Razón": "Patrón en título",
                })
                continue

            # 2. Solape de artistas
            suggestions = suggest(track, artist_index, dest_by_pid)
            if suggestions and suggestions[0].score >= 2:
                best = suggestions[0]
                target_genre = dest_by_pid.get(best.playlist_id)
                if target_genre:
                    proposals.append({
                        "item": t_item,
                        "uri": track["uri"],
                        "Canción": title,
                        "Artista": artists_str,
                        "Destino": target_genre,
                        "target_id": best.playlist_id,
                        "Razón": best.reason,
                    })

        if not proposals:
            st.info("No se encontraron coincidencias evidentes por artista o título para las canciones restantes.")
        else:
            st.dataframe(
                pd.DataFrame([
                    {"Canción": p["Canción"], "Artista": p["Artista"], "Destino sugerido": p["Destino"], "Motivo": p["Razón"]}
                    for p in proposals
                ]),
                hide_index=True,
            )

            st.write(f"Se proponen **{len(proposals)}** canciones para mover.")
            if st.button(f"Aplicar clasificación de {len(proposals)} canciones", type="primary", key="apply_genre_auto"):
                with st.spinner("Copiando canciones a sus destinos correspondientes..."):
                    by_dest = {}
                    for p in proposals:
                        by_dest.setdefault(p["target_id"], []).append(p)

                    moved_total = 0
                    for tid, p_list in by_dest.items():
                        uris = [p["uri"] for p in p_list]
                        for i in range(0, len(uris), 100):
                            batch = uris[i:i + 100]
                            st.session_state.spotify.add_tracks_to_playlist(tid, batch)
                        if tid in st.session_state.playlist_data_cache:
                            st.session_state.playlist_data_cache[tid] += [slim_item(p["item"]) for p in p_list]
                        moved_total += len(uris)

                    save_cache_to_disk()
                    st.success(f"¡Listo! Se han añadido {moved_total} canciones a sus playlists correspondientes.")
                    st.rerun()

# --- TAB 2: Clasificador Manual ---
with tab_manual:
    if "sorter_index" not in st.session_state:
        st.session_state.sorter_index = 0

    if not uncategorized_in_source:
        st.success("No quedan canciones pendientes de clasificar en esta playlist.")
    elif st.session_state.sorter_index >= len(uncategorized_in_source):
        st.balloons()
        st.success("¡Has revisado todas las canciones de esta tanda!")
        if st.button("Reiniciar clasificador"):
            st.session_state.sorter_index = 0
            st.rerun()
    else:
        current_item = uncategorized_in_source[st.session_state.sorter_index]
        cur_track = extract_track(current_item)

        if not cur_track or not cur_track.get('name'):
            st.session_state.sorter_index += 1
            st.rerun()

        # Sugerencia para resaltar
        suggestions = suggest(cur_track, artist_index, dest_by_pid)
        suggested_genre = dest_by_pid.get(suggestions[0].playlist_id) if suggestions else None

        with st.container(border=True):
            c_img, c_detail = st.columns([1, 2])
            with c_img:
                album = cur_track.get('album', {})
                images = album.get('images', [])
                if images:
                    st.image(images[0]['url'], use_container_width=True)
            with c_detail:
                st.subheader(cur_track['name'])
                artist_names = ", ".join([a['name'] for a in cur_track.get('artists', [])])
                st.markdown(f"**Artista:** {artist_names}")
                if album.get("name"):
                    st.caption(f"Álbum: {album['name']}")
                if suggestions:
                    st.info(f"💡 Sugerencia: **{suggested_genre}** ({suggestions[0].reason})")
                st.caption(f"Progreso: {st.session_state.sorter_index + 1} de {len(uncategorized_in_source)}")

        st.markdown("### Enviar a:")
        genre_cols = st.columns(len(st.session_state.genre_mapping))
        for i, (genre, target_id) in enumerate(st.session_state.genre_mapping.items()):
            is_suggested = (genre == suggested_genre)
            btn_label = f"🔥 {genre}" if is_suggested else genre
            if genre_cols[i].button(btn_label, use_container_width=True, key=f"btn_manual_{genre}_{cur_track['id']}"):
                st.session_state.spotify.add_tracks_to_playlist(target_id, [cur_track['uri']])
                if target_id in st.session_state.playlist_data_cache:
                    st.session_state.playlist_data_cache[target_id].append(slim_item(current_item))
                    save_cache_to_disk()
                st.session_state.sorter_index += 1
                st.rerun()

        c_skip, c_del = st.columns(2)
        if c_skip.button("➡️ Saltar", use_container_width=True, key="manual_skip"):
            st.session_state.sorter_index += 1
            st.rerun()

        if c_del.button("🗑️ Quitar de esta playlist", use_container_width=True, key="manual_del"):
            st.session_state.spotify.remove_track_from_playlist(source_pl_id, [cur_track['uri']])
            target_source_id = st.session_state.spotify.get_playlist_id(source_pl_id)
            if target_source_id in st.session_state.playlist_data_cache:
                st.session_state.playlist_data_cache[target_source_id] = [
                    item for item in st.session_state.playlist_data_cache[target_source_id]
                    if (extract_track(item) or {}).get('uri') != cur_track['uri']
                ]
                save_cache_to_disk()
            st.rerun()
