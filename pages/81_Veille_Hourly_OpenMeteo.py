# pages/81_Veille_Hourly_OpenMeteo.py
import streamlit as st
from core.auth import is_logged_in
from core.ui import approval_gate
from core.vigilance_hourly import ingest_hourly_observations, compute_vigilance_indicators_today

st.title("Module 1 — Veille hydro-météorologique (Open-Meteo hourly)")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

st.caption("Ingestion hourly + synthèse 24h/72h. Réservez cette page aux profils techniques/analystes.")

c1, c2, c3 = st.columns(3)
limit = c1.number_input("Stations (max)", min_value=10, max_value=5000, value=200, step=50)
past_days = c2.number_input("Past days", min_value=1, max_value=7, value=3, step=1)
forecast_days = c3.number_input("Forecast days", min_value=1, max_value=16, value=1, step=1)

if st.button("1) Lancer ingestion hourly"):
    with st.spinner("Ingestion en cours..."):
        stats = ingest_hourly_observations(limit_stations=int(limit), past_days=int(past_days), forecast_days=int(forecast_days))
    st.success(f"OK — Stations: {stats['stations']}, Observations upsertées: {stats['observations']}, Erreurs: {stats['errors']}")

st.divider()
st.subheader("2) Synthèse du jour (zones critiques)")

df = compute_vigilance_indicators_today()
if df.empty:
    st.info("Aucune observation disponible. Lancez l’ingestion hourly.")
else:
    st.dataframe(df, use_container_width=True)

    colA, colB = st.columns(2)
    with colA:
        st.caption("Top 10 — Excès de pluie (24h)")
        st.dataframe(df.sort_values("prcp_24h_mm", ascending=False).head(10), use_container_width=True)
    with colB:
        st.caption("Top 10 — Stress thermique (Heat Index max 24h)")
        st.dataframe(df.sort_values("heat_index_max_24h_c", ascending=False).head(10), use_container_width=True)
