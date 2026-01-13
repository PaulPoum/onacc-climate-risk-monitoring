# pages/22_Carte_Zones_Critiques.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date

from core.auth import is_logged_in
from core.ui import approval_gate
from core.supabase_client import supabase_user
from core.vigilance_scores import (
    IC_FLOOD_SCORE, IC_DROUGHT_SCORE, SOURCE_HOURLY,
    RISK_FLOOD, RISK_DROUGHT
)

st.title("Carte — Zones critiques (choroplèthe par admin_code)")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

risk_label = st.selectbox("Risque", ["Inondation (Flood)", "Sécheresse (Drought)"])
valid_date = st.date_input("Date (valid_date)", value=date.today()).isoformat()

risk = RISK_FLOOD if "Flood" in risk_label else RISK_DROUGHT
indicator_code = IC_FLOOD_SCORE if risk == RISK_FLOOD else IC_DROUGHT_SCORE

u = supabase_user(st.session_state["access_token"])

# 1) Scores
res_scores = (
    u.table("risk_indicators")
    .select("admin_code,value")
    .eq("valid_date", valid_date)
    .eq("risk", risk)
    .eq("indicator_code", indicator_code)
    .eq("source", SOURCE_HOURLY)
    .execute()
)
df_scores = pd.DataFrame(res_scores.data or [])
if df_scores.empty:
    st.info("Aucun score disponible. Lancez la page V2 de calcul/sauvegarde.")
    st.stop()

df_scores["value"] = pd.to_numeric(df_scores["value"], errors="coerce").fillna(0)

# 2) GeoJSON territoires
res_geo = u.table("v_admin_units_geojson").select("code,name,geojson").execute()
df_geo = pd.DataFrame(res_geo.data or [])
if df_geo.empty:
    st.error("Aucune géométrie disponible. Vérifiez ref_admin_units.geom et la view v_admin_units_geojson.")
    st.stop()

# 3) Jointure
df = df_geo.merge(df_scores, left_on="code", right_on="admin_code", how="inner")
if df.empty:
    st.warning("Aucune correspondance code ↔ score. Vérifiez que mnocc_stations.admin_code correspond à ref_admin_units.code.")
    st.stop()

# FeatureCollection
features = []
for _, r in df.iterrows():
    features.append({
        "type": "Feature",
        "properties": {
            "code": r["code"],
            "name": r["name"],
            "score": float(r["value"]),
        },
        "geometry": r["geojson"],
    })
fc = {"type": "FeatureCollection", "features": features}

# Carte
m = folium.Map(location=[6.5, 12.5], zoom_start=6, tiles="cartodbpositron")

folium.Choropleth(
    geo_data=fc,
    data=df,
    columns=["code", "value"],
    key_on="feature.properties.code",
    fill_opacity=0.75,
    line_opacity=0.2,
    legend_name=f"{indicator_code} — {valid_date}",
).add_to(m)

folium.GeoJson(
    fc,
    name="Zones",
    tooltip=folium.GeoJsonTooltip(
        fields=["name", "code", "score"],
        aliases=["Territoire", "Code", "Score"],
        localize=True
    )
).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, height=650, width=None)

st.caption("Astuce: si la carte est vide, vérifiez la correspondance mnocc_stations.admin_code ↔ ref_admin_units.code.")
