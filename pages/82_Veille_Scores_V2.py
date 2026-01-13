# pages/82_Veille_Scores_V2.py
import streamlit as st
import pandas as pd
from datetime import date

from core.auth import is_logged_in
from core.ui import approval_gate
from core.supabase_client import supabase_user
from core.vigilance_scores import run_scores_pipeline, IC_FLOOD_SCORE, IC_DROUGHT_SCORE, SOURCE_HOURLY, RISK_FLOOD, RISK_DROUGHT

st.title("Module 1 — Veille V2 (Scores Flood/Drought → risk_indicators)")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

valid_date = st.date_input("Date (valid_date)", value=date.today()).isoformat()

if st.button("Calculer & sauvegarder (Flood/Drought scores)"):
    with st.spinner("Calcul & sauvegarde en cours..."):
        stats = run_scores_pipeline(valid_date=valid_date)
    st.success(
        f"OK — admin_units: {stats['admin_units']}, rows: {stats['rows']}, upserted: {stats['upserted']}, errors: {stats['errors']}"
    )

st.divider()
st.subheader("Lecture des zones critiques (depuis risk_indicators)")

u = supabase_user(st.session_state["access_token"])

def load_scores(risk: str, indicator_code: str) -> pd.DataFrame:
    res = (
        u.table("risk_indicators")
        .select("admin_code,value,valid_date,created_at")
        .eq("valid_date", valid_date)
        .eq("risk", risk)
        .eq("indicator_code", indicator_code)
        .eq("source", SOURCE_HOURLY)
        .execute()
    )
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.sort_values("value", ascending=False)

col1, col2 = st.columns(2)

with col1:
    st.caption("Top Flood Score")
    df_f = load_scores(RISK_FLOOD, IC_FLOOD_SCORE)
    if df_f.empty:
        st.info("Aucun Flood Score pour cette date.")
    else:
        st.dataframe(df_f.head(20), use_container_width=True)

with col2:
    st.caption("Top Drought Score")
    df_d = load_scores(RISK_DROUGHT, IC_DROUGHT_SCORE)
    if df_d.empty:
        st.info("Aucun Drought Score pour cette date.")
    else:
        st.dataframe(df_d.head(20), use_container_width=True)
