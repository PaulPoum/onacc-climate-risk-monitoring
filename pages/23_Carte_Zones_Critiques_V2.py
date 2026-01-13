import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date

from core.auth import is_logged_in
from core.ui import approval_gate
from core.supabase_client import supabase_user

SOURCE = "open-meteo-dynamic-v2"

st.title("Carte — Zones critiques (V2 dynamique)")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

valid_date = st.date_input("valid_date", value=date.today()).isoformat()
risk = st.selectbox("Risque", ["inondation", "secheresse"])
indicator_code = "SCORE_INONDATION" if risk == "inondation" else "SCORE_SECHERESSE"

u = supabase_user(st.session_state["access_token"])

scores = (
    u.table("risk_indicators")
    .select("admin_code,value")
    .eq("valid_date", valid_date)
    .eq("risk", risk)
    .eq("indicator_code", indicator_code)
    .eq("source", SOURCE)
    .execute()
)
df_scores = pd.DataFrame(scores.data or [])
if df_scores.empty:
    st.info("Aucun score disponible. Lance le pipeline V2.")
    st.stop()

df_scores["value"] = pd.to_numeric(df_scores["value"], errors="coerce").fillna(0)

geo = u.table("v_admin_units_geojson").select("code,name,geojson").execute()
df_geo = pd.DataFrame(geo.data or [])
if df_geo.empty:
    st.error("Géométries absentes. Vérifie ref_admin_units.geom et la view v_admin_units_geojson.")
    st.stop()

df = df_geo.merge(df_scores, left_on="code", right_on="admin_code", how="inner")
if df.empty:
    st.warning("Aucune jointure admin_code ↔ ref_admin_units.code. Vérifie la cohérence des codes.")
    st.stop()

fc = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"code": r["code"], "name": r["name"], "score": float(r["value"])},
            "geometry": r["geojson"],
        }
        for _, r in df.iterrows()
    ],
}

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
    tooltip=folium.GeoJsonTooltip(
        fields=["name", "code", "score"],
        aliases=["Territoire", "Code", "Score"],
        localize=True,
    ),
).add_to(m)

st_folium(m, height=650, width=None)
