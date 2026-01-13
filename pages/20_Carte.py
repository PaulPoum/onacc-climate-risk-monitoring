# pages/20_Carte.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from core.auth import is_logged_in
from core.supabase_client import supabase_user
from core.ui import approval_gate

st.title("Cartographie — Stations")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

uclient = supabase_user(st.session_state["access_token"])
res = uclient.table("mnocc_stations").select("localite,latitude,longitude,altitude,region,country").limit(2000).execute()

if getattr(res, "error", None):
    st.error(res.error.message)
    st.stop()

df = pd.DataFrame(res.data or [])
if df.empty:
    st.info("Aucune station trouvée dans mnocc_stations.")
    st.stop()

# Carte centrée sur Cameroun (approx)
m = folium.Map(location=[6.5, 12.5], zoom_start=6)

for _, r in df.iterrows():
    folium.CircleMarker(
        location=[r["latitude"], r["longitude"]],
        radius=4,
        popup=f"{r['localite']} ({r.get('region','')})",
        fill=True
    ).add_to(m)

st_folium(m, height=600, width=None)
