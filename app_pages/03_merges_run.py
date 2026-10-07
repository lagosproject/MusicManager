"""Merge execution page: intelligent tree running, propagation, and Liked Songs sync."""
import streamlit as st
from music_manager.core.merge_tree import propagation_plan
from app_pages.ui_common import (
    compute_merge_preview,
    get_saved_uris,
    playlist_label,
    show_merge_preview,
    show_run_results,
)

st.title("Ejecución de merges")
jobs = st.session_state.job_manager.jobs

if not jobs:
    st.info("Todavía no hay merges. Crea uno en «Gestión de merges».")
    st.stop()

sync_saved = st.toggle(
    "Añadir a «Me gusta» lo que falte",
    value=True,
    key="sync_saved",
    help="Tras cada ejecución, las canciones de las playlists que no estén en tus canciones guardadas se guardan.",
)
preview_slot = st.container()

with st.container(horizontal=True):
    if st.button("Previsualizar todo el árbol", icon=":material/preview:", key="preview_tree"):
        compute_merge_preview(None, sync_saved)
    if st.button("Ejecutar todo el árbol", type="primary", icon=":material/account_tree:"):
        with st.spinner("Ejecutando los merges en orden..."):
            results = st.session_state.job_manager.run_tree_intelligent(
                st.session_state.spotify,
                sync_saved=sync_saved,
                saved_uris=get_saved_uris() if sync_saved else None,
            )
        show_run_results(results)

st.divider()
for job in jobs:
    plan = propagation_plan(jobs, job.name)
    with st.expander(job.name):
        col_info, col_actions = st.columns([3, 1])
        with col_info:
            st.markdown(f"**Destino:** {playlist_label(job.target_id)}")
            if job.source_ids:
                st.markdown("**Orígenes:** " + ", ".join(playlist_label(s) for s in job.source_ids))
            if len(plan) > 1:
                st.caption("Al ejecutarlo se actualizarán después: " + " → ".join(j.name for j in plan[1:]))

        with col_actions:
            if st.button("Previsualizar", key=f"preview_{job.name}", icon=":material/preview:"):
                compute_merge_preview(job.name, sync_saved)
            if st.button("Ejecutar", key=f"run_{job.name}", icon=":material/play_arrow:"):
                with st.spinner("Ejecutando..."):
                    results = st.session_state.job_manager.run_with_propagation(
                        job.name,
                        st.session_state.spotify,
                        sync_saved=sync_saved,
                        saved_uris=get_saved_uris() if sync_saved else None,
                    )
                show_run_results(results)

with preview_slot:
    finished = st.session_state.pop("pending_run_results", None)
    if finished:
        show_run_results(finished)
    shown = st.session_state.get("merge_preview")
    if shown and shown.sync_saved != sync_saved:
        st.session_state.pop("merge_preview")
    show_merge_preview()
