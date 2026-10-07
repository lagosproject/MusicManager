"""Dashboard page: metrics, library summary and cache status."""
import streamlit as st
from music_manager.core.api_calls import describe_api_error
from app_pages.ui_common import _count_user_playlists, confirm_clear_cache

st.title("Bienvenido a MusicManager")
st.write("Gestiona tu música de forma moderna e instantánea.")

col1, col2, col3 = st.columns(3)

with col1:
    try:
        playlist_total = _count_user_playlists(st.session_state.spotify)
    except Exception as e:
        playlist_total = "—"
        st.warning(describe_api_error(e))
    st.metric("Tus playlists", playlist_total)

with col2:
    st.metric("Playlists en caché local", len(st.session_state.playlist_data_cache))

with col3:
    st.metric("Merges guardados", len(st.session_state.job_manager.jobs))

st.markdown("---")
if st.button("Limpiar toda la caché de datos", icon=":material/delete:"):
    confirm_clear_cache()
