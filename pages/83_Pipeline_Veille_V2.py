import streamlit as st
from datetime import date

from core.auth import is_logged_in
from core.ui import approval_gate
from core.indicator_engine_v2 import run_pipeline_v2

st.title("Module 1 — V2 dynamique (indicateurs + scores → risk_indicators)")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

valid_date = st.date_input("valid_date", value=date.today()).isoformat()

if st.button("Exécuter pipeline V2"):
    with st.spinner("Calcul et sauvegarde en cours..."):
        stats = run_pipeline_v2(valid_date=valid_date)
    st.success(f"OK — rows={stats['rows']} | upserted={stats['upserted']} | errors={stats['errors']}")
