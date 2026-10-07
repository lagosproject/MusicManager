"""Recorre las 7 opciones del menú con streamlit AppTest SIN pulsar botones.

Ejecutar desde la raíz:  python tools/diag/diag_app.py
"""
import re
from pathlib import Path
from streamlit.testing.v1 import AppTest

OPTS = ["Dashboard", "Gestión de Merges", "Ejecución de Merges", "Auditoría de Organización",
        "Organizador por Géneros", "Auditoría: Duplicados"]


def short(s):
    return re.sub(r"\s+", " ", str(s))[:260]


for opt in OPTS:
    at = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "main_streamlit.py"), default_timeout=90)
    at.run()
    stage = "arranque"
    if not at.exception:
        stage = f"menú={opt}"
        at.sidebar.selectbox[0].set_value(opt).run()
    print(f"\n=== {opt} ({stage}) ===")
    print(f"  excepciones: {len(at.exception)}")
    for e in at.exception:
        print("   -", short(e.value))
    print(f"  st.error: {[short(e.value) for e in at.error]}")
    print(f"  st.warning: {[short(w.value) for w in at.warning]}")
    print(f"  titulos: {[t.value for t in at.title][:3]}  botones: {len(at.button)}")
