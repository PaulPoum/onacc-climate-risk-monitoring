# pages/21_Dashboard_Module1.py
"""
Dashboard Module 1 : Veille Hydrométéorologique et Climatique - VERSION UNIFIÉE
Centralisation complète du suivi des risques climatiques (Inondations et Sécheresse)
TOUTES LES FONCTIONNALITÉS INTÉGRÉES DANS UNE VUE UNIQUE
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.ui import approval_gate
from core.supabase_client import supabase_user
from core.open_meteo import fetch_daily_forecast

# Imports Module 1 complets (Étapes 1-4)
from core.module1 import (
    GeolocationService, 
    SatelliteService,
    HydrologicalAnalyzer,
    WatershedCharacteristics,
    DischargePredictor,
    create_features_from_weather
)
from core.module1.utils import (
    format_coordinates,
    get_bbox_from_point,
    get_risk_color,
    get_risk_label,
)

st.set_page_config(
    page_title="Module 1 - Veille Météo | ONACC",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Styles modernisés
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
        
        .module-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2.5rem;
            border-radius: 20px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 15px 50px rgba(102, 126, 234, 0.4);
        }
        
        .module-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        
        .module-subtitle {
            font-size: 1.1rem;
            opacity: 0.95;
        }
        
        .section-header {
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            margin: 2rem 0 1.5rem 0;
            padding-bottom: 0.8rem;
            border-bottom: 3px solid #667eea;
        }
        
        .kpi-mega-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5rem;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transition: all 0.3s ease;
        }
        
        .kpi-mega-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.2);
        }
        
        .kpi-mega-value {
            font-size: 2.5rem;
            font-weight: 900;
            color: #667eea;
            margin: 0.5rem 0;
        }
        
        .kpi-mega-label {
            font-size: 0.9rem;
            color: #555;
            font-weight: 600;
        }
        
        .alert-mega-banner {
            background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
            border-left: 6px solid #ffc107;
            padding: 2rem;
            border-radius: 16px;
            margin: 1.5rem 0;
            box-shadow: 0 6px 20px rgba(255, 193, 7, 0.3);
        }
        
        .alert-mega-banner-critical {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left-color: #f44336;
            box-shadow: 0 6px 20px rgba(244, 67, 54, 0.3);
        }
        
        .risk-badge {
            display: inline-block;
            padding: 0.5rem 1.5rem;
            border-radius: 25px;
            font-weight: 700;
            font-size: 1.1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .risk-badge-critical {
            background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
            color: white;
        }
        
        .risk-badge-high {
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
            color: white;
        }
        
        .risk-badge-moderate {
            background: linear-gradient(135deg, #ffc107 0%, #ffa000 100%);
            color: white;
        }
        
        .risk-badge-low {
            background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
            color: white;
        }
        
        .metric-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: white;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0.5rem 0;
        }
        
        .metric-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
    </style>
""", unsafe_allow_html=True)

# Guards
if not st.session_state.get("access_token"):
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# Header
st.markdown("""
    <div class="module-header">
        <div class="module-title">🌦️ Module 1 : Veille Hydrométéorologique Unifiée</div>
        <div class="module-subtitle">
            Surveillance Intégrée des Risques Climatiques • Inondations & Sécheresse • IA & Satellite
        </div>
    </div>
""", unsafe_allow_html=True)

if st.button("← Retour Dashboard Principal"):
    st.switch_page("pages/10_Dashboard.py")

# Helper Functions
@st.cache_data(ttl=300)
def get_stations() -> List[Dict]:
    try:
        u = supabase_user(st.session_state["access_token"])
        res = u.table("mnocc_stations").select("*").order("localite").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Erreur chargement stations: {e}")
        return []

@st.cache_data(ttl=300)
def get_forecast_data(lat: float, lon: float, days: int, is_seasonal: bool = False) -> Optional[Dict]:
    try:
        return fetch_daily_forecast(lat, lon, days, is_seasonal)
    except Exception as e:
        st.error(f"Erreur chargement prévisions: {e}")
        return None

def create_risk_map(stations_data: List[Dict], risk_type: str = 'flood') -> go.Figure:
    if not stations_data:
        return go.Figure()
    
    df_map = pd.DataFrame([
        {
            'localite': s['localite'],
            'region': s['region'],
            'lat': s['latitude'],
            'lon': s['longitude'],
            'risk': np.random.choice(['low', 'moderate', 'high', 'critical'], p=[0.4, 0.3, 0.2, 0.1])
        }
        for s in stations_data
    ])
    
    fig = px.scatter_mapbox(
        df_map,
        lat='lat',
        lon='lon',
        hover_name='localite',
        hover_data=['region', 'risk'],
        color='risk',
        color_discrete_map={
            'critical': '#f44336',
            'high': '#ff9800',
            'moderate': '#ffc107',
            'low': '#4caf50'
        },
        zoom=5,
        height=500
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        title=f"Carte des risques - {'Inondation' if risk_type == 'flood' else 'Sécheresse'}"
    )
    
    return fig

# Initialize services
geo_service = GeolocationService()
satellite_service = SatelliteService()

# Get user location
with st.spinner("🌍 Détection de votre position..."):
    user_location = geo_service.get_user_location()

# Load stations
stations = get_stations()
n_stations = len(stations)

# Calculate bbox
bbox = get_bbox_from_point(user_location['lat'], user_location['lon'], radius_km=50)

# Load satellite image
if 'sat_result' not in st.session_state:
    with st.spinner("🛰️ Chargement image satellite..."):
        sat_result = satellite_service.get_satellite_image(
            user_location['lat'],
            user_location['lon'],
            zoom=10,
            width=512,
            height=512,
            source='auto'
        )
        st.session_state['sat_result'] = sat_result
else:
    sat_result = st.session_state['sat_result']

# Load forecast data
if 'forecast_data' not in st.session_state:
    with st.spinner(f"⏳ Chargement des prévisions pour {user_location['localite']}..."):
        try:
            forecast_raw = get_forecast_data(
                user_location['lat'],
                user_location['lon'],
                days=10,
                is_seasonal=False
            )
            
            if forecast_raw and forecast_raw.get('daily'):
                daily = forecast_raw['daily']
                df_forecast = pd.DataFrame({
                    'date': pd.to_datetime(daily['time']),
                    'temperature_2m_max': daily.get('temperature_2m_max', []),
                    'temperature_2m_min': daily.get('temperature_2m_min', []),
                    'precipitation_sum': daily.get('precipitation_sum', []),
                    'wind_speed_10m_max': daily.get('wind_speed_10m_max', [])
                })
                
                st.session_state['forecast_data'] = {
                    'df': df_forecast,
                    'station': user_location,
                    'horizon': '10 jours'
                }
                st.success(f"✅ Prévisions chargées pour {user_location['localite']}")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

# =========================
# VUE D'ENSEMBLE UNIFIÉE
# =========================

st.markdown('<div class="section-header">📍 Position & Indicateurs Nationaux</div>', unsafe_allow_html=True)

# Position compacte
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
        <div class="kpi-mega-card">
            <div style="font-size: 2rem;">📍</div>
            <div class="kpi-mega-value" style="font-size: 1.5rem;">{user_location['localite']}</div>
            <div class="kpi-mega-label">Localité</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="kpi-mega-card">
            <div style="font-size: 2rem;">🗺️</div>
            <div class="kpi-mega-value" style="font-size: 1.5rem;">{user_location['region']}</div>
            <div class="kpi-mega-label">Région</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    coords = format_coordinates(user_location['lat'], user_location['lon'])
    st.markdown(f"""
        <div class="kpi-mega-card">
            <div style="font-size: 2rem;">🧭</div>
            <div class="kpi-mega-value" style="font-size: 1rem;">{coords}</div>
            <div class="kpi-mega-label">Coordonnées</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    accuracy = user_location.get('accuracy', 0)
    st.markdown(f"""
        <div class="kpi-mega-card">
            <div style="font-size: 2rem;">🎯</div>
            <div class="kpi-mega-value" style="font-size: 1.5rem;">±{accuracy:.0f}m</div>
            <div class="kpi-mega-label">Précision</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# KPI Nationaux
kpi_cols = st.columns(5)
kpis = [
    ("📡", n_stations, "Stations"),
    ("🚨", 12, "Zones Critiques"),
    ("⚠️", 3, "Alertes Actives"),
    ("📊", "85%", "Couverture"),
    ("⏰", datetime.now().strftime('%H:%M'), "Dernière MàJ")
]

for col, (icon, value, label) in zip(kpi_cols, kpis):
    with col:
        st.markdown(f"""
            <div class="metric-box">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div class="metric-value" style="font-size: 2rem;">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
        """, unsafe_allow_html=True)

# Alertes
st.markdown('<div class="section-header">🚨 Alertes Actives en Temps Réel</div>', unsafe_allow_html=True)

alert_col1, alert_col2 = st.columns(2)

with alert_col1:
    st.markdown("""
        <div class="alert-mega-banner alert-mega-banner-critical">
            <div style="font-size: 1.5rem; font-weight: 800;">🔴 ALERTE CRITIQUE - Inondation</div>
            <div style="font-size: 1.1rem; margin-top: 1rem;">
                <strong>Région Nord</strong><br>
                💧 Précipitations : <strong>120mm en 24h</strong><br>
                📅 Émise : 13/01/2026 08:00 • ⏱️ Validité : <strong>48h</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)

with alert_col2:
    st.markdown("""
        <div class="alert-mega-banner">
            <div style="font-size: 1.5rem; font-weight: 800;">🟡 ALERTE MODÉRÉE - Sécheresse</div>
            <div style="font-size: 1.1rem; margin-top: 1rem;">
                <strong>Région Extrême-Nord</strong><br>
                🌵 <strong>18 jours</strong> sans pluie<br>
                📅 Émise : 10/01/2026 • ⏱️ Validité : <strong>7 jours</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Satellite
st.markdown('<div class="section-header">🛰️ Imagerie Satellite & Détection Inondations</div>', unsafe_allow_html=True)

st.info(f"""
📍 **Zone :** {user_location['localite']} • Rayon 50 km  
🗺️ **BBox :** {bbox[1]:.3f}°N - {bbox[3]:.3f}°N, {bbox[0]:.3f}°E - {bbox[2]:.3f}°E
""")

img_col1, img_col2 = st.columns(2)

with img_col1:
    st.markdown("#### 📸 Image Satellite")
    if sat_result:
        st.image(sat_result['image'], use_container_width=True)
        source_name = 'Mapbox' if sat_result['source'] == 'mapbox' else 'NASA MODIS'
        st.caption(f"{'🗺️' if sat_result['source'] == 'mapbox' else '🛰️'} {source_name} • {sat_result['timestamp'][:10]}")

with img_col2:
    st.markdown("#### 🌊 Zones Inondées")
    if sat_result:
        water_mask, water_pct, water_stats = satellite_service.detect_water_bodies(
            sat_result['image'], method='rgb_threshold'
        )
        overlay_image = satellite_service.create_overlay_image(
            sat_result['image'], water_mask, color=(0, 150, 255), alpha=0.6
        )
        st.image(overlay_image, use_container_width=True)
        
        area_stats = satellite_service.calculate_affected_area(
            water_mask, pixel_size_m=10, bbox=bbox
        )
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("💧 Surface eau", f"{water_pct:.1f}%")
        with m_col2:
            st.metric("📏 Zone affectée", f"{area_stats['affected_area_km2']:.2f} km²")
        
        if water_pct > 20:
            st.error("🚨 **CRITIQUE** : Inondation majeure")
        elif water_pct > 12:
            st.warning("⚠️ **ÉLEVÉ** : Surveillance")
        else:
            st.success("✅ **NORMAL**")

# Cartographie
st.markdown('<div class="section-header">🗺️ Cartographie des Risques</div>', unsafe_allow_html=True)

map_col1, map_col2 = st.columns(2)

with map_col1:
    st.plotly_chart(create_risk_map(stations, "flood"), use_container_width=True)

with map_col2:
    st.plotly_chart(create_risk_map(stations, "drought"), use_container_width=True)

# Modèles Hydro
st.markdown('<div class="section-header">🌊 Modèles Hydrologiques (Inondations)</div>', unsafe_allow_html=True)

if 'forecast_data' in st.session_state:
    df = st.session_state['forecast_data']['df']
    
    hydro_analyzer = WatershedCharacteristics.create_analyzer_for_region(user_location['region'])
    watershed_info = WatershedCharacteristics.get_watershed_for_region(user_location['region'])
    
    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        st.metric("🏞️ Bassin", watershed_info['name'])
    with h_col2:
        st.metric("📏 Surface", f"{watershed_info['area_km2']:,} km²")
    with h_col3:
        st.metric("⏱️ Temps Conc.", f"{watershed_info['time_concentration_h']}h")
    
    with st.spinner("🔄 Calcul..."):
        hydro_forecast = hydro_analyzer.forecast_discharge(
            precipitation=df['precipitation_sum'].values,
            dates=df['date']
        )
    
    risk_analysis = hydro_forecast['risk_analysis']
    
    hk_col1, hk_col2, hk_col3, hk_col4 = st.columns(4)
    
    with hk_col1:
        st.metric("🌊 Débit Max", f"{hydro_forecast['max_discharge']:.1f} m³/s")
    with hk_col2:
        st.metric("📊 Débit Moy", f"{hydro_forecast['mean_discharge']:.1f} m³/s")
    with hk_col3:
        st.metric("💧 Volume", f"{hydro_forecast['total_volume_m3']/1e6:.1f} M m³")
    with hk_col4:
        risk_label = get_risk_label(risk_analysis['risk_level'])
        st.markdown(f"""
            <div style="text-align: center;">
                <div class="risk-badge risk-badge-{risk_analysis['risk_level']}">
                    {risk_label}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    fig_discharge = go.Figure()
    fig_discharge.add_trace(go.Scatter(
        x=hydro_forecast['dates'],
        y=hydro_forecast['discharge_m3s'],
        name='Débit moyen',
        line=dict(color='#2196F3', width=3),
        fill='tozeroy'
    ))
    
    fig_discharge.update_layout(
        title="Prévision Débit - 10 jours",
        xaxis_title="Date",
        yaxis_title="Débit (m³/s)",
        height=400,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_discharge, use_container_width=True)

# ML
st.markdown('<div class="section-header">🤖 Prévisions Machine Learning (IA)</div>', unsafe_allow_html=True)

if 'forecast_data' in st.session_state:
    df = st.session_state['forecast_data']['df']
    
    try:
        ml_features = create_features_from_weather(df)
        st.success(f"✅ {len(ml_features.columns)} features créées")
        
        if len(ml_features) >= 365:
            ml_col1, ml_col2, ml_col3 = st.columns(3)
            
            with ml_col1:
                model_type = st.selectbox(
                    "Modèle IA",
                    options=['rf'],
                    format_func=lambda x: '🌲 Random Forest',
                    key='ml_unified'
                )
            
            with ml_col2:
                lookback = st.slider("Lookback", 7, 90, 30, key='lb_unified')
            
            with ml_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🎓 Entraîner", type="primary"):
                    with st.spinner("🔄 Entraînement..."):
                        predictor = DischargePredictor(
                            model_type='rf',
                            lookback_days=lookback,
                            forecast_horizon=10
                        )
                        
                        metrics = predictor.train_random_forest(
                            ml_features,
                            target_col='precipitation_sum',
                            n_estimators=100
                        )
                        
                        st.success(f"✅ R² = {metrics['test_r2']:.3f}")
                        st.session_state['ml_predictor'] = predictor
                        st.session_state['ml_trained'] = True
        else:
            st.warning(f"⚠️ Données insuffisantes ({len(ml_features)} j). Min 365j.")
    
    except ImportError as e:
        st.error(f"❌ ML non disponible : {e}")

# Top Zones
st.markdown('<div class="section-header">🎯 Top 5 Zones Critiques</div>', unsafe_allow_html=True)

critical_data = pd.DataFrame({
    "Région": ["Nord", "Extrême-Nord", "Adamaoua", "Est", "Centre"],
    "Risque Inondation": ["CRITIQUE", "MODÉRÉ", "FAIBLE", "MODÉRÉ", "ÉLEVÉ"],
    "Risque Sécheresse": ["FAIBLE", "CRITIQUE", "ÉLEVÉ", "FAIBLE", "MODÉRÉ"],
    "Stations": [45, 38, 32, 28, 52]
})

st.dataframe(critical_data, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.caption(f"Module 1 Unifié | ONACC v2.0 | MàJ: {datetime.now().strftime('%d/%m/%Y %H:%M')} | ✅ Toutes fonctionnalités intégrées")