"""Merge management page: tree visualization, creation, and deletion."""
import streamlit as st
from music_manager.core.models import MergeJob
from music_manager.core.merge_tree import (
    tree_lines,
    shared_targets,
    creates_cycle,
    is_valid_playlist_id,
    normalize_playlist_id,
)
from app_pages.ui_common import playlist_label, confirm_delete_merge

st.title("Gestión de merges")
jobs = st.session_state.job_manager.jobs

st.subheader("Árbol de merges")
if not jobs:
    st.info("Todavía no hay merges. Crea el primero más abajo.")
else:
    st.caption("Cada merge rellena su playlist destino con las de abajo. Si una playlist origen es el destino de otro merge, ese merge se ejecuta antes.")
    st.markdown("\n".join(tree_lines(jobs, playlist_label)))
    for shared in shared_targets(jobs):
        st.warning(f"Hay más de un merge con la misma playlist destino: {playlist_label(shared)}.")

st.subheader("Nuevo merge")
with st.form("new_merge_form"):
    name = st.text_input("Nombre del merge")
    target_pl = st.text_input("URL o ID de la playlist destino")
    extra_pls = st.text_area("URLs o IDs de las playlists origen (una por línea)")
    description = st.text_input("Descripción (opcional)")

    submitted = st.form_submit_button("Guardar merge")
    if submitted:
        name = name.strip()
        source_ids = list(dict.fromkeys(line.strip() for line in extra_pls.split("\n") if line.strip()))
        candidate = MergeJob(name=name, target_id=target_pl.strip(), source_ids=source_ids, description=description)
        bad_refs = [ref for ref in [candidate.target_id] + source_ids if not is_valid_playlist_id(ref)]

        if not name or not target_pl.strip() or not source_ids:
            st.error("Rellena los campos obligatorios.")
        elif any(j.name == name for j in jobs):
            st.error(f"Ya existe un merge llamado «{name}». Elimínalo antes si quieres rehacerlo.")
        elif bad_refs:
            st.error(f"No reconozco como playlist de Spotify: {', '.join(bad_refs)}")
        elif normalize_playlist_id(candidate.target_id) in [normalize_playlist_id(s) for s in source_ids]:
            st.error("La playlist destino no puede ser también una de las origen.")
        elif creates_cycle(jobs, candidate):
            st.error("Ese merge crearía un ciclo entre playlists (A alimenta a B y B a A).")
        else:
            st.session_state.job_manager.add_job(candidate)
            st.success(f"Merge «{name}» guardado.")
            st.rerun()

if jobs:
    st.subheader("Merges guardados")
    for job in jobs:
        with st.container(border=True, horizontal=True, vertical_alignment="center"):
            st.markdown(f"**{job.name}**  \n{job.description or '_Sin descripción_'}")
            if st.button("Eliminar", key=f"delete_{job.name}", icon=":material/delete:"):
                confirm_delete_merge(job.name)
