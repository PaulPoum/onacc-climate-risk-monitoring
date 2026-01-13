# pages/22_Dashboard_Module2.py
"""
Dashboard Module 2 : Cartes de risques et catastrophes climatiques
==================================================================

Système d'Information Géographique (SIG) pour la visualisation spatiale
des risques climatiques multi-types (inondations, sécheresses, etc.)

Fonctionnalités :
- Cartographie interactive des zones à risque
- Filtres temporels et thématiques
- Fiches détaillées par zone
- Comparaison multi-zones
- Export des données
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
import requests

from core.ui import approval_gate
from core.supabase_client import supabase_user

# Import Module 2
from core.module2 import (
    RiskMapper,
    FloodZoneAnalyzer,
    FloodRiskLevel,
    DroughtZoneAnalyzer,
    DroughtSeverity,
    MultiRiskAnalyzer,
    RiskType,
    TemporalFilter,
    TemporalPeriod,
    RiskFilter,
    AlertLevelFilter,
    CompositeFilter,
    ZoneInfoProvider,
    ZoneDetails,
    ZoneType,
    ClimateIndices,
    ActiveAlert,
    HistoricalEvent
)

from core.module2.utils import (
    get_risk_color_scale,
    get_risk_level_label,
    format_area,
    create_choropleth_map
)

st.set_page_config(
    page_title="Module 2 - SIG Risques | ONACC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# STYLES CSS
# ========================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
        
        .module-header {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(67, 233, 123, 0.3);
        }
        
        .module-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        
        .module-subtitle {
            font-size: 1rem;
            opacity: 0.9;
        }
        
        .risk-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            border-left: 4px solid;
            transition: transform 0.3s ease;
            height: 100%;
        }
        
        .risk-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        }
        
        .risk-card-critical { border-left-color: #dc3545; }
        .risk-card-high { border-left-color: #fd7e14; }
        .risk-card-moderate { border-left-color: #ffc107; }
        .risk-card-low { border-left-color: #28a745; }
        
        .zone-card {
            background: white;
            padding: 1.2rem;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .zone-card:hover {
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
            transform: translateX(4px);
        }
        
        .zone-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0.5rem;
        }
        
        .zone-meta {
            font-size: 0.85rem;
            color: #666;
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
        
        .filter-section {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
        }
        
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1a1a1a;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .alert-banner {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .alert-banner-critical {
            background: #f8d7da;
            border-left-color: #dc3545;
        }
        
        .legend-item {
            display: inline-flex;
            align-items: center;
            margin-right: 1.5rem;
            font-size: 0.9rem;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            margin-right: 0.5rem;
        }
        
        .custom-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, #43e97b, transparent);
            margin: 2rem 0;
            border: none;
        }
    </style>
""", unsafe_allow_html=True)

# ========================================
# GUARDS & INITIALIZATION
# ========================================
if not st.session_state.get("access_token"):
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# Header
st.markdown("""
    <div class="module-header">
        <div class="module-title">🗺️ Module 2 : Cartes de Risques et Catastrophes Climatiques</div>
        <div class="module-subtitle">
            Système d'Information Géographique (SIG) - Visualisation multi-risques
        </div>
    </div>
""", unsafe_allow_html=True)

# Bouton retour
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("← Retour", key="back_main"):
        st.switch_page("pages/10_Dashboard.py")

# ========================================
# HELPER FUNCTIONS
# ========================================

@st.cache_data(ttl=300)
def get_stations() -> pd.DataFrame:
    """Récupère toutes les stations depuis Supabase"""
    try:
        u = supabase_user(st.session_state["access_token"])
        res = u.table("mnocc_stations").select("*").order("localite").execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # Nettoyer les données
            df = df.dropna(subset=['id', 'localite', 'latitude', 'longitude'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur chargement stations: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def fetch_open_meteo_forecast(lat: float, lon: float, forecast_days: int = 16) -> Dict:
    """
    Récupère prévisions Open-Meteo
    
    Args:
        lat: Latitude
        lon: Longitude
        forecast_days: Nombre de jours (max 16 pour API gratuite)
    
    Returns:
        Données météorologiques
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,windspeed_10m_max",
            "forecast_days": min(forecast_days, 16),
            "timezone": "Africa/Douala"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    except Exception as e:
        st.warning(f"⚠️ Impossible de récupérer les prévisions Open-Meteo: {e}")
        return {}

def analyze_flood_risk_from_forecast(forecast_data: Dict) -> Dict:
    """
    Analyse risque inondation depuis prévisions Open-Meteo
    
    Returns:
        Analyse du risque avec périodes critiques
    """
    try:
        daily = forecast_data.get('daily', {})
        precipitation = daily.get('precipitation_sum', [])
        dates = daily.get('time', [])
        
        if not precipitation:
            return {'risk_level': 'low', 'confidence': 0, 'periods': []}
        
        # Analyser cumul et intensité
        total_precip = sum(precipitation)
        max_precip = max(precipitation)
        
        # Détecter épisodes intenses
        intense_days = [(dates[i], p) for i, p in enumerate(precipitation) if p > 50 and i < len(dates)]
        critical_days = [(dates[i], p) for i, p in enumerate(precipitation) if p > 100 and i < len(dates)]
        
        # Classification
        risk_level = 'low'
        confidence = 0.5
        periods = []
        
        if critical_days:
            risk_level = 'critical'
            confidence = 0.9
            for date_str, intensity in critical_days:
                periods.append({
                    'date': date_str,
                    'intensity_mm': intensity,
                    'type': 'critical'
                })
        elif intense_days:
            risk_level = 'high' if len(intense_days) > 2 else 'moderate'
            confidence = 0.75
            for date_str, intensity in intense_days:
                periods.append({
                    'date': date_str,
                    'intensity_mm': intensity,
                    'type': 'intense'
                })
        elif total_precip > 200:
            risk_level = 'moderate'
            confidence = 0.6
        
        return {
            'risk_level': risk_level,
            'confidence': confidence,
            'total_precipitation_mm': total_precip,
            'max_intensity_mm': max_precip,
            'periods': periods,
            'analysis_days': len(precipitation)
        }
    
    except Exception as e:
        return {'risk_level': 'unknown', 'confidence': 0, 'periods': []}

def analyze_drought_risk_from_forecast(forecast_data: Dict) -> Dict:
    """
    Analyse risque sécheresse depuis prévisions Open-Meteo
    
    Returns:
        Analyse du risque avec périodes sèches
    """
    try:
        daily = forecast_data.get('daily', {})
        precipitation = daily.get('precipitation_sum', [])
        temp_max = daily.get('temperature_2m_max', [])
        dates = daily.get('time', [])
        
        if not precipitation:
            return {'severity': 'normal', 'confidence': 0, 'periods': []}
        
        # Jours secs consécutifs
        max_dry_streak = 0
        current_streak = 0
        dry_periods = []
        streak_start = None
        
        for i, p in enumerate(precipitation):
            if p < 1:  # Jour sec
                if current_streak == 0:
                    streak_start = dates[i] if i < len(dates) else None
                current_streak += 1
                max_dry_streak = max(max_dry_streak, current_streak)
            else:
                if current_streak >= 5:
                    dry_periods.append({
                        'start_date': streak_start,
                        'duration_days': current_streak
                    })
                current_streak = 0
                streak_start = None
        
        # Dernière période si en cours
        if current_streak >= 5:
            dry_periods.append({
                'start_date': streak_start,
                'duration_days': current_streak
            })
        
        # Classification
        severity = 'normal'
        confidence = 0.5
        
        if max_dry_streak >= 14:
            severity = 'extreme'
            confidence = 0.9
        elif max_dry_streak >= 10:
            severity = 'severe'
            confidence = 0.8
        elif max_dry_streak >= 7:
            severity = 'moderate'
            confidence = 0.7
        
        avg_temp = sum(temp_max) / len(temp_max) if temp_max else 0
        
        return {
            'severity': severity,
            'confidence': confidence,
            'max_dry_streak': max_dry_streak,
            'avg_temp_max_c': avg_temp,
            'periods': dry_periods,
            'analysis_days': len(precipitation)
        }
    
    except Exception as e:
        return {'severity': 'unknown', 'confidence': 0, 'periods': []}

def initialize_demo_data():
    """Initialise les données avec les vraies stations de Supabase"""
    
    # Récupérer stations réelles
    stations_df = get_stations()
    
    if stations_df.empty:
        st.error("❌ Aucune station disponible")
        return None, None
    
    # Créer RiskMapper
    risk_mapper = RiskMapper()
    
    # Créer ZoneInfoProvider
    zone_provider = ZoneInfoProvider()
    
    # Utiliser les stations réelles
    for _, station in stations_df.iterrows():
        region_name = station.get('region', station['localite'])
        
        # Récupérer prévisions pour cette station
        forecast = fetch_open_meteo_forecast(
            station['latitude'],
            station['longitude'],
            forecast_days=16
        )
        
        # Analyser risques depuis prévisions
        flood_analysis = analyze_flood_risk_from_forecast(forecast)
        drought_analysis = analyze_drought_risk_from_forecast(forecast)
        
        flood_risk = flood_analysis.get('risk_level', 'low')
        drought_risk = drought_analysis.get('severity', 'normal')
        
        # Créer couche inondation
        risk_mapper.create_flood_layer(
            zone_name=station['localite'],
            center_lat=station['latitude'],
            center_lon=station['longitude'],
            radius_km=30,
            risk_level=flood_risk,
            properties={
                'station_id': station['id'],
                'region': region_name,
                'altitude': station.get('altitude')
            }
        )
        
        # Créer couche sécheresse
        if drought_risk in ['moderate', 'severe', 'extreme', 'exceptional']:
            risk_mapper.create_drought_layer(
                zone_name=station['localite'],
                center_lat=station['latitude'],
                center_lon=station['longitude'],
                radius_km=30,
                severity=drought_risk,
                properties={
                    'station_id': station['id'],
                    'region': region_name
                }
            )
        
        # Créer ZoneDetails
        spi = -drought_analysis.get('max_dry_streak', 0) / 10  # Approximation SPI
        
        climate_indices = ClimateIndices(
            spi=spi,
            spei=spi - 0.1,
            temperature_anomaly=drought_analysis.get('avg_temp_max_c', 0) - 28,  # Anomalie vs moyenne
            precipitation_anomaly=flood_analysis.get('total_precipitation_mm', 0) - 100
        )
        
        # Alertes actives basées sur analyses
        active_alerts = []
        
        if flood_risk in ['high', 'critical']:
            for period in flood_analysis.get('periods', []):
                active_alerts.append(ActiveAlert(
                    alert_type='flood',
                    level='red' if flood_risk == 'critical' else 'orange',
                    issued_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=3),
                    description=f"Risque inondation {flood_risk} - {station['localite']}",
                    recommendations=[
                        "Surveiller les prévisions",
                        "Préparer un plan d'évacuation",
                        "Éviter les zones basses"
                    ]
                ))
                break  # Une alerte par zone
        
        if drought_risk in ['severe', 'extreme']:
            active_alerts.append(ActiveAlert(
                alert_type='drought',
                level='red' if drought_risk == 'extreme' else 'orange',
                issued_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=14),
                description=f"Sécheresse {drought_risk} - {station['localite']}",
                recommendations=[
                    "Économiser l'eau",
                    "Surveiller les cultures",
                    "Préparer irrigation"
                ]
            ))
        
        # Geometry
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [station['longitude'] - 0.3, station['latitude'] - 0.3],
                [station['longitude'] + 0.3, station['latitude'] - 0.3],
                [station['longitude'] + 0.3, station['latitude'] + 0.3],
                [station['longitude'] - 0.3, station['latitude'] + 0.3],
                [station['longitude'] - 0.3, station['latitude'] - 0.3]
            ]]
        }
        
        zone = ZoneDetails(
            zone_id=f"station_{station['id']}",
            zone_name=station['localite'],
            zone_type=ZoneType.COMMUNE,
            geometry=geometry,
            center_lat=station['latitude'],
            center_lon=station['longitude'],
            area_km2=900,  # Rayon 30km approximatif
            population=None,  # À enrichir avec API Banque Mondiale
            climate_indices=climate_indices,
            historical_events=[],
            active_alerts=active_alerts,
            metadata={
                'country': 'Cameroun',
                'region': region_name,
                'station_id': station['id'],
                'data_source': 'Open-Meteo + Supabase',
                'last_updated': datetime.now().isoformat()
            }
        )
        
        zone_provider.add_zone(zone)
    
    return risk_mapper, zone_provider

# Initialiser données
if 'risk_mapper' not in st.session_state or 'zone_provider' not in st.session_state:
    with st.spinner("🔄 Initialisation des données cartographiques..."):
        risk_mapper, zone_provider = initialize_demo_data()
        st.session_state['risk_mapper'] = risk_mapper
        st.session_state['zone_provider'] = zone_provider

risk_mapper = st.session_state['risk_mapper']
zone_provider = st.session_state['zone_provider']

# ========================================
# KPIs PRINCIPAUX
# ========================================

st.markdown('<div class="section-title">📊 Vue d\'Ensemble Nationale</div>', unsafe_allow_html=True)

stats = risk_mapper.get_statistics()
critical_zones = risk_mapper.get_critical_zones()
zones_critiques = zone_provider.get_critical_zones()

kpi_cols = st.columns(5)

with kpi_cols[0]:
    st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{len(zone_provider)}</div>
            <div class="metric-label">Zones Surveillées</div>
        </div>
    """, unsafe_allow_html=True)

with kpi_cols[1]:
    st.markdown(f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="metric-value">{len(zones_critiques)}</div>
            <div class="metric-label">Zones Critiques</div>
        </div>
    """, unsafe_allow_html=True)

with kpi_cols[2]:
    total_alerts = sum(
        len([a for a in zone.active_alerts if a.is_active()])
        for zone in zone_provider.zones.values()
    )
    
    st.markdown(f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <div class="metric-value">{total_alerts}</div>
            <div class="metric-label">Alertes Actives</div>
        </div>
    """, unsafe_allow_html=True)

with kpi_cols[3]:
    st.markdown(f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
            <div class="metric-value">{stats['total_layers']}</div>
            <div class="metric-label">Couches Cartographiques</div>
        </div>
    """, unsafe_allow_html=True)

with kpi_cols[4]:
    st.markdown(f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333;">
            <div class="metric-value">{stats['formatted_area']}</div>
            <div class="metric-label">Surface Totale</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# SECTION PRÉVISIONS OPEN-METEO
# ========================================

st.markdown('<div class="section-title">🌤️ Prévisions Météorologiques</div>', unsafe_allow_html=True)

# Sélection station pour prévisions
stations_df = get_stations()

if not stations_df.empty:
    prev_col1, prev_col2 = st.columns([2, 1])
    
    with prev_col1:
        # Créer options
        station_options = [
            f"{row['localite']} - {row.get('region', 'N/A')}"
            for _, row in stations_df.iterrows()
        ]
        
        selected_station_label = st.selectbox(
            "📍 Station",
            options=station_options,
            key="forecast_station"
        )
        
        # Récupérer station
        selected_idx = station_options.index(selected_station_label)
        selected_station = stations_df.iloc[selected_idx]
    
    with prev_col2:
        forecast_days = st.select_slider(
            "📅 Horizon",
            options=[7, 10, 14, 16],
            value=14,
            key="forecast_days",
            help="Nombre de jours de prévision"
        )
    
    # Récupérer prévisions
    with st.spinner(f"🔄 Chargement prévisions pour {selected_station['localite']}..."):
        forecast_data = fetch_open_meteo_forecast(
            selected_station['latitude'],
            selected_station['longitude'],
            forecast_days
        )
    
    if forecast_data and 'daily' in forecast_data:
        daily = forecast_data['daily']
        
        # Analyser risques
        flood_risk = analyze_flood_risk_from_forecast(forecast_data)
        drought_risk = analyze_drought_risk_from_forecast(forecast_data)
        
        # KPIs Risques
        risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)
        
        with risk_col1:
            flood_color = {
                'low': '#28a745',
                'moderate': '#ffc107',
                'high': '#fd7e14',
                'critical': '#dc3545'
            }.get(flood_risk['risk_level'], '#6c757d')
            
            st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 12px; border-top: 4px solid {flood_color}; text-align: center;">
                    <div style="font-size: 2rem;">🌊</div>
                    <div style="font-size: 0.75rem; color: #666;">Risque Inondation</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: {flood_color};">
                        {flood_risk['risk_level'].upper()}
                    </div>
                    <div style="font-size: 0.7rem; color: #999;">
                        Confiance: {flood_risk.get('confidence', 0)*100:.0f}%
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with risk_col2:
            drought_color = {
                'normal': '#28a745',
                'moderate': '#ffc107',
                'severe': '#fd7e14',
                'extreme': '#dc3545'
            }.get(drought_risk['severity'], '#6c757d')
            
            st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 12px; border-top: 4px solid {drought_color}; text-align: center;">
                    <div style="font-size: 2rem;">🌵</div>
                    <div style="font-size: 0.75rem; color: #666;">Risque Sécheresse</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: {drought_color};">
                        {drought_risk['severity'].upper()}
                    </div>
                    <div style="font-size: 0.7rem; color: #999;">
                        Confiance: {drought_risk.get('confidence', 0)*100:.0f}%
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with risk_col3:
            st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 12px; border-top: 4px solid #2196F3; text-align: center;">
                    <div style="font-size: 2rem;">💧</div>
                    <div style="font-size: 0.75rem; color: #666;">Précip. Totales</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: #2196F3;">
                        {flood_risk.get('total_precipitation_mm', 0):.1f} mm
                    </div>
                    <div style="font-size: 0.7rem; color: #999;">
                        {forecast_days} jours
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with risk_col4:
            st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 12px; border-top: 4px solid #ff9800; text-align: center;">
                    <div style="font-size: 2rem;">☀️</div>
                    <div style="font-size: 0.75rem; color: #666;">Jours Secs Consécutifs</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: #ff9800;">
                        {drought_risk.get('max_dry_streak', 0)}
                    </div>
                    <div style="font-size: 0.7rem; color: #999;">
                        Maximum
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Timeline prévisions
        if 'time' in daily and 'precipitation_sum' in daily:
            dates = pd.to_datetime(daily['time'])
            precipitation = daily['precipitation_sum']
            temp_max = daily.get('temperature_2m_max', [])
            temp_min = daily.get('temperature_2m_min', [])
            
            # Créer subplot
            fig_forecast = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Précipitations Prévues', 'Températures Prévues'),
                vertical_spacing=0.12,
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            # Précipitations
            fig_forecast.add_trace(
                go.Bar(
                    x=dates,
                    y=precipitation,
                    name='Précipitations',
                    marker_color='#2196F3',
                    hovertemplate='%{x|%d/%m}<br>%{y:.1f} mm<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Températures
            if temp_max:
                fig_forecast.add_trace(
                    go.Scatter(
                        x=dates,
                        y=temp_max,
                        name='Temp. Max',
                        line=dict(color='#f44336', width=2),
                        hovertemplate='%{x|%d/%m}<br>%{y:.1f}°C<extra></extra>'
                    ),
                    row=2, col=1
                )
            
            if temp_min:
                fig_forecast.add_trace(
                    go.Scatter(
                        x=dates,
                        y=temp_min,
                        name='Temp. Min',
                        line=dict(color='#2196F3', width=2),
                        hovertemplate='%{x|%d/%m}<br>%{y:.1f}°C<extra></extra>'
                    ),
                    row=2, col=1
                )
            
            # Layout
            fig_forecast.update_xaxes(title_text="Date", row=2, col=1)
            fig_forecast.update_yaxes(title_text="Précipitations (mm)", row=1, col=1)
            fig_forecast.update_yaxes(title_text="Température (°C)", row=2, col=1)
            
            fig_forecast.update_layout(
                height=500,
                showlegend=True,
                template='plotly_white',
                hovermode='x unified',
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            st.plotly_chart(fig_forecast, use_container_width=True)
        
        # Périodes critiques
        if flood_risk['periods'] or drought_risk['periods']:
            st.markdown("#### ⚠️ Périodes Critiques Identifiées")
            
            period_col1, period_col2 = st.columns(2)
            
            with period_col1:
                if flood_risk['periods']:
                    st.markdown("**🌊 Risque Inondation**")
                    for period in flood_risk['periods']:
                        st.warning(f"""
                        📅 **{period['date']}**  
                        💧 Intensité: **{period['intensity_mm']:.1f} mm**  
                        ⚠️ Type: **{period['type'].upper()}**
                        """)
                else:
                    st.success("✅ Aucune période critique inondation")
            
            with period_col2:
                if drought_risk['periods']:
                    st.markdown("**🌵 Risque Sécheresse**")
                    for period in drought_risk['periods']:
                        st.warning(f"""
                        📅 Début: **{period['start_date']}**  
                        ⏱️ Durée: **{period['duration_days']} jours secs**
                        """)
                else:
                    st.success("✅ Aucune période critique sécheresse")
    
    else:
        st.error("❌ Impossible de charger les prévisions Open-Meteo")

else:
    st.warning("⚠️ Aucune station disponible pour les prévisions")

st.markdown("<br>", unsafe_allow_html=True)

# ========================================
# FILTRES
# ========================================

st.markdown('<div class="section-title">🔍 Filtres de Visualisation</div>', unsafe_allow_html=True)

with st.expander("⚙️ Configurer les filtres", expanded=True):
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        st.markdown("**📅 Période Temporelle**")
        
        temporal_period = st.selectbox(
            "Période",
            options=[
                "Aujourd'hui",
                "7 derniers jours",
                "30 derniers jours",
                "3 derniers mois",
                "Personnalisée"
            ],
            key="temporal_period"
        )
        
        # Mapping vers TemporalPeriod
        period_map = {
            "Aujourd'hui": TemporalPeriod.TODAY,
            "7 derniers jours": TemporalPeriod.WEEK,
            "30 derniers jours": TemporalPeriod.MONTH,
            "3 derniers mois": TemporalPeriod.QUARTER,
            "Personnalisée": TemporalPeriod.CUSTOM
        }
        
        selected_period = period_map[temporal_period]
        
        # Si période custom
        start_date = None
        end_date = None
        
        if selected_period == TemporalPeriod.CUSTOM:
            start_date = st.date_input("Date début", value=date.today() - timedelta(days=30))
            end_date = st.date_input("Date fin", value=date.today())
    
    with filter_col2:
        st.markdown("**🎯 Types de Risque**")
        
        risk_types = st.multiselect(
            "Types",
            options=['Inondation', 'Sécheresse', 'Tempête', 'Érosion', 'Chaleur'],
            default=['Inondation', 'Sécheresse'],
            key="risk_types"
        )
        
        # Mapping
        risk_type_map = {
            'Inondation': 'flood',
            'Sécheresse': 'drought',
            'Tempête': 'storm',
            'Érosion': 'erosion',
            'Chaleur': 'heat'
        }
        
        selected_risks = set(risk_type_map[rt] for rt in risk_types)
    
    with filter_col3:
        st.markdown("**⚠️ Niveaux d'Alerte**")
        
        alert_levels = st.multiselect(
            "Niveaux",
            options=['🟢 Faible', '🟡 Modéré', '🟠 Élevé', '🔴 Critique'],
            default=['🟠 Élevé', '🔴 Critique'],
            key="alert_levels"
        )
        
        # Mapping
        level_map = {
            '🟢 Faible': 'low',
            '🟡 Modéré': 'moderate',
            '🟠 Élevé': 'high',
            '🔴 Critique': 'critical'
        }
        
        selected_levels = {level_map[al] for al in alert_levels}
    
    st.markdown('</div>', unsafe_allow_html=True)

# Créer filtre composite
temporal_filter = TemporalFilter(
    period=selected_period,
    start_date=start_date,
    end_date=end_date
)

risk_filter = RiskFilter(risk_types=selected_risks)

# Créer AlertLevelFilter avec les niveaux sélectionnés
from core.module2.filters import AlertLevel

alert_level_filter = AlertLevelFilter(
    levels={
        AlertLevel.GREEN if 'low' in selected_levels else None,
        AlertLevel.YELLOW if 'moderate' in selected_levels else None,
        AlertLevel.ORANGE if 'high' in selected_levels else None,
        AlertLevel.RED if 'critical' in selected_levels else None
    } - {None}
)

composite_filter = CompositeFilter(
    temporal=temporal_filter,
    risk=risk_filter,
    alert_level=alert_level_filter
)

# Appliquer filtres
filtered_layers = composite_filter.apply(risk_mapper.layers)

st.info(f"""
📊 **Résultats du filtrage**

🎯 Période : {temporal_filter.get_period_label()}  
🗺️ Types de risque : {', '.join(risk_types)}  
⚠️ Niveaux : {', '.join(alert_levels)}  
📍 Couches affichées : **{len(filtered_layers)}/{len(risk_mapper.layers)}**
""")

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# ========================================
# TABS PRINCIPALES
# ========================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Carte Interactive",
    "📋 Zones Critiques",
    "📊 Analyses Détaillées",
    "📈 Statistiques & Tendances"
])

# ========================================
# TAB 1: CARTE INTERACTIVE
# ========================================

with tab1:
    st.markdown("### 🗺️ Cartographie Multi-Risques")
    
    # Sélection du type de carte
    map_col1, map_col2, map_col3 = st.columns([2, 2, 1])
    
    with map_col1:
        map_type = st.radio(
            "Type de visualisation",
            options=['Risque Inondation', 'Risque Sécheresse', 'Multi-Risques'],
            horizontal=True,
            key="map_type"
        )
    
    with map_col2:
        satellite_style = st.selectbox(
            "🛰️ Style Carte",
            options=[
                "OpenStreetMap Standard",
                "OpenStreetMap Satellite",
                "Satellite Streets (Mapbox)",
                "Outdoor (Mapbox)"
            ],
            index=1,
            key="satellite_style"
        )
        
        # Mapping vers style Mapbox
        style_map = {
            "OpenStreetMap Standard": "open-street-map",
            "OpenStreetMap Satellite": "satellite",
            "Satellite Streets (Mapbox)": "satellite-streets",
            "Outdoor (Mapbox)": "outdoors"
        }
        
        mapbox_style = style_map[satellite_style]
    
    with map_col3:
        show_labels = st.checkbox("Labels", value=True, key="show_labels")
    
    # Créer carte basée sur le type sélectionné
    if map_type == 'Risque Inondation':
        flood_layers = [l for l in filtered_layers if hasattr(l, 'risk_type') and l.risk_type.value == 'flood']
        
        if flood_layers:
            # Créer carte Plotly
            fig = go.Figure()
            
            for layer in flood_layers:
                coords = layer.geometry['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                
                color_scale = get_risk_color_scale('flood')
                color = color_scale.get(layer.level, '#999999')
                
                fig.add_trace(go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    fill='toself',
                    fillcolor=color + '66',  # Transparence
                    line=dict(color=color, width=2),
                    name=layer.properties.get('zone_name', 'Zone'),
                    text=f"{layer.properties.get('zone_name')}<br>Risque: {get_risk_level_label(layer.level, 'flood')}",
                    hoverinfo='text'
                ))
            
            fig.update_layout(
                mapbox=dict(
                    style=mapbox_style,
                    center=dict(lat=6.0, lon=12.0),
                    zoom=5
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                title="Carte des Risques d'Inondation"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Légende
            st.markdown("**Légende :**")
            leg_col1, leg_col2, leg_col3, leg_col4 = st.columns(4)
            
            with leg_col1:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #28a745;"></div>Faible</div>', unsafe_allow_html=True)
            with leg_col2:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #ffc107;"></div>Modéré</div>', unsafe_allow_html=True)
            with leg_col3:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #fd7e14;"></div>Élevé</div>', unsafe_allow_html=True)
            with leg_col4:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #dc3545;"></div>Critique</div>', unsafe_allow_html=True)
        
        else:
            st.warning("⚠️ Aucune couche d'inondation à afficher avec les filtres actuels")
    
    elif map_type == 'Risque Sécheresse':
        drought_layers = [l for l in filtered_layers if hasattr(l, 'risk_type') and l.risk_type.value == 'drought']
        
        if drought_layers:
            fig = go.Figure()
            
            for layer in drought_layers:
                coords = layer.geometry['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                
                color_scale = get_risk_color_scale('drought')
                color = color_scale.get(layer.level, '#999999')
                
                fig.add_trace(go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    fill='toself',
                    fillcolor=color + '66',
                    line=dict(color=color, width=2),
                    name=layer.properties.get('zone_name', 'Zone'),
                    text=f"{layer.properties.get('zone_name')}<br>Sévérité: {get_risk_level_label(layer.level, 'drought')}",
                    hoverinfo='text'
                ))
            
            fig.update_layout(
                mapbox=dict(
                    style=mapbox_style,
                    center=dict(lat=6.0, lon=12.0),
                    zoom=5
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                title="Carte des Risques de Sécheresse"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Légende
            st.markdown("**Légende :**")
            leg_col1, leg_col2, leg_col3, leg_col4 = st.columns(4)
            
            with leg_col1:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #fef0d9;"></div>Faible</div>', unsafe_allow_html=True)
            with leg_col2:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #fdcc8a;"></div>Modéré</div>', unsafe_allow_html=True)
            with leg_col3:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #fc8d59;"></div>Élevé</div>', unsafe_allow_html=True)
            with leg_col4:
                st.markdown('<div class="legend-item"><div class="legend-color" style="background: #d7301f;"></div>Critique</div>', unsafe_allow_html=True)
        
        else:
            st.warning("⚠️ Aucune couche de sécheresse à afficher avec les filtres actuels")
    
    else:  # Multi-Risques
        if filtered_layers:
            fig = go.Figure()
            
            for layer in filtered_layers:
                coords = layer.geometry['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                
                risk_type = layer.risk_type.value if hasattr(layer.risk_type, 'value') else str(layer.risk_type)
                color_scale = get_risk_color_scale(risk_type)
                color = color_scale.get(layer.level, '#999999')
                
                risk_label = '🌊' if risk_type == 'flood' else '🌵' if risk_type == 'drought' else '⚠️'
                
                fig.add_trace(go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    fill='toself',
                    fillcolor=color + '44',
                    line=dict(color=color, width=2),
                    name=f"{risk_label} {layer.properties.get('zone_name', 'Zone')}",
                    text=f"{layer.properties.get('zone_name')}<br>Type: {risk_type}<br>Niveau: {layer.level}",
                    hoverinfo='text'
                ))
            
            fig.update_layout(
                mapbox=dict(
                    style=mapbox_style,
                    center=dict(lat=6.0, lon=12.0),
                    zoom=5
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                title="Carte Multi-Risques"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 **Astuce :** Cliquez sur la légende pour activer/désactiver des couches")
        
        else:
            st.warning("⚠️ Aucune couche à afficher avec les filtres actuels")

# ========================================
# TAB 2: ZONES CRITIQUES
# ========================================

with tab2:
    st.markdown("### 📋 Zones en Situation Critique")
    
    critical_zones_list = zone_provider.get_critical_zones()
    
    if critical_zones_list:
        st.warning(f"⚠️ **{len(critical_zones_list)} zone(s) en situation critique identifiée(s)**")
        
        for zone in critical_zones_list:
            risk_status = zone.get_risk_status()
            
            # Déterminer couleur de bordure
            border_color = '#dc3545' if risk_status['overall'] == 'critical' else '#fd7e14'
            
            st.markdown(f"""
                <div class="zone-card" style="border-left: 4px solid {border_color};">
                    <div class="zone-title">{zone.zone_name}</div>
                    <div class="zone-meta">
                        📍 {zone.zone_type.value.replace('_', ' ').title()} • 
                        👥 {zone.population:,} habitants • 
                        📏 {zone.area_km2:,.0f} km²
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Détails risques
            risk_col1, risk_col2, risk_col3 = st.columns(3)
            
            with risk_col1:
                flood_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(risk_status['flood'], '#6c757d')
                
                st.markdown(f"""
                    <div style="background: {flood_color}22; padding: 1rem; border-radius: 8px; border: 2px solid {flood_color};">
                        <div style="font-size: 0.85rem; color: #666;">Risque Inondation</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: {flood_color};">
                            {risk_status['flood'].upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with risk_col2:
                drought_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(risk_status['drought'], '#6c757d')
                
                st.markdown(f"""
                    <div style="background: {drought_color}22; padding: 1rem; border-radius: 8px; border: 2px solid {drought_color};">
                        <div style="font-size: 0.85rem; color: #666;">Risque Sécheresse</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: {drought_color};">
                            {risk_status['drought'].upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with risk_col3:
                overall_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(risk_status['overall'], '#6c757d')
                
                st.markdown(f"""
                    <div style="background: {overall_color}22; padding: 1rem; border-radius: 8px; border: 2px solid {overall_color};">
                        <div style="font-size: 0.85rem; color: #666;">Risque Global</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: {overall_color};">
                            {risk_status['overall'].upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            # Alertes actives
            active_alerts = [a for a in zone.active_alerts if a.is_active()]
            
            if active_alerts:
                st.markdown("**🔔 Alertes Actives :**")
                
                for alert in active_alerts:
                    alert_icon = '🌊' if alert.alert_type == 'flood' else '🌵' if alert.alert_type == 'drought' else '⚠️'
                    
                    alert_color = {
                        'yellow': '#ffc107',
                        'orange': '#fd7e14',
                        'red': '#dc3545',
                        'extreme': '#721c24'
                    }.get(alert.level, '#6c757d')
                    
                    st.markdown(f"""
                        <div style="background: {alert_color}22; padding: 0.8rem; border-radius: 6px; border-left: 3px solid {alert_color}; margin-bottom: 0.5rem;">
                            <div style="font-weight: 600; color: {alert_color};">
                                {alert_icon} {alert.description}
                            </div>
                            <div style="font-size: 0.85rem; color: #666; margin-top: 0.3rem;">
                                ⏱️ Expire dans {alert.time_remaining()}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            
            # Bouton voir détails
            if st.button(f"📄 Voir fiche détaillée", key=f"detail_{zone.zone_id}"):
                st.session_state['selected_zone_id'] = zone.zone_id
                st.rerun()
            
            st.markdown("---")
    
    else:
        st.success("✅ Aucune zone en situation critique actuellement")

# ========================================
# TAB 3: ANALYSES DÉTAILLÉES
# ========================================

with tab3:
    st.markdown("### 📊 Analyses Détaillées par Zone")
    
    # Sélection zone
    zone_names = {zone.zone_name: zone.zone_id for zone in zone_provider.zones.values()}
    
    selected_zone_name = st.selectbox(
        "Sélectionner une zone",
        options=list(zone_names.keys()),
        key="selected_zone_analysis"
    )
    
    if selected_zone_name:
        zone_id = zone_names[selected_zone_name]
        
        # Générer rapport
        report = zone_provider.generate_zone_report(zone_id)
        
        if report:
            st.markdown(f"#### 📍 {report['zone_info']['name']}")
            
            # Infos générales
            info_col1, info_col2, info_col3, info_col4 = st.columns(4)
            
            with info_col1:
                st.metric("Type", report['zone_info']['type'].replace('_', ' ').title())
            
            with info_col2:
                st.metric("Surface", f"{report['zone_info']['area_km2']:,.0f} km²")
            
            with info_col3:
                if report['zone_info']['population']:
                    st.metric("Population", f"{report['zone_info']['population']:,}")
                else:
                    st.metric("Population", "N/A")
            
            with info_col4:
                coords = report['zone_info']['coordinates']
                st.metric("Coordonnées", f"{coords['lat']:.2f}°, {coords['lon']:.2f}°")
            
            st.markdown("---")
            
            # Évaluation des risques
            st.markdown("##### 🎯 Évaluation des Risques")
            
            risk_status = report['risk_assessment']
            
            assess_col1, assess_col2, assess_col3 = st.columns(3)
            
            with assess_col1:
                flood_level = risk_status['flood']
                flood_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(flood_level, '#6c757d')
                
                st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 3px solid {flood_color}; text-align: center;">
                        <div style="font-size: 3rem;">🌊</div>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 0.5rem;">Inondation</div>
                        <div style="font-size: 1.8rem; font-weight: bold; color: {flood_color}; margin-top: 0.5rem;">
                            {flood_level.upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with assess_col2:
                drought_level = risk_status['drought']
                drought_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(drought_level, '#6c757d')
                
                st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 3px solid {drought_color}; text-align: center;">
                        <div style="font-size: 3rem;">🌵</div>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 0.5rem;">Sécheresse</div>
                        <div style="font-size: 1.8rem; font-weight: bold; color: {drought_color}; margin-top: 0.5rem;">
                            {drought_level.upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with assess_col3:
                overall_level = risk_status['overall']
                overall_color = {
                    'low': '#28a745',
                    'moderate': '#ffc107',
                    'high': '#fd7e14',
                    'critical': '#dc3545'
                }.get(overall_level, '#6c757d')
                
                st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 3px solid {overall_color}; text-align: center;">
                        <div style="font-size: 3rem;">⚠️</div>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 0.5rem;">Global</div>
                        <div style="font-size: 1.8rem; font-weight: bold; color: {overall_color}; margin-top: 0.5rem;">
                            {overall_level.upper()}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Indices climatiques
            if report['climate_indices']:
                st.markdown("##### 🌡️ Indices Climatiques")
                
                indices = report['climate_indices']
                
                ind_col1, ind_col2, ind_col3 = st.columns(3)
                
                with ind_col1:
                    if indices['spi'] is not None:
                        st.metric(
                            "SPI (Sécheresse)",
                            f"{indices['spi']:.2f}",
                            delta=None,
                            help="Standardized Precipitation Index"
                        )
                
                with ind_col2:
                    if indices['temp_anomaly'] is not None:
                        st.metric(
                            "Anomalie Température",
                            f"{indices['temp_anomaly']:+.1f}°C"
                        )
                
                with ind_col3:
                    if indices['precip_anomaly'] is not None:
                        st.metric(
                            "Anomalie Précipitations",
                            f"{indices['precip_anomaly']:+.1f}%"
                        )
                
                # Interprétation SPI
                if indices['spi'] is not None:
                    spi_value = indices['spi']
                    
                    if spi_value < -2.0:
                        st.error("🔴 **Sécheresse Extrême** (SPI < -2.0)")
                    elif spi_value < -1.5:
                        st.warning("🟠 **Sécheresse Sévère** (-2.0 ≤ SPI < -1.5)")
                    elif spi_value < -1.0:
                        st.warning("🟡 **Sécheresse Modérée** (-1.5 ≤ SPI < -1.0)")
                    elif spi_value < -0.5:
                        st.info("ℹ️ **Sécheresse Légère** (-1.0 ≤ SPI < -0.5)")
                    else:
                        st.success("✅ **Conditions Normales** (SPI ≥ -0.5)")
                
                st.markdown("---")
            
            # Alertes actives
            if report['active_alerts']:
                st.markdown("##### 🔔 Alertes Actives")
                
                for alert in report['active_alerts']:
                    alert_icon = '🌊' if alert['type'] == 'flood' else '🌵'
                    
                    alert_color = {
                        'yellow': '#ffc107',
                        'orange': '#fd7e14',
                        'red': '#dc3545'
                    }.get(alert['level'], '#6c757d')
                    
                    with st.expander(f"{alert_icon} {alert['description']} - Expire dans {alert['time_remaining']}"):
                        st.markdown(f"**Niveau :** {alert['level'].upper()}")
                        
                        st.markdown("**Recommandations :**")
                        for rec in alert['recommendations']:
                            st.markdown(f"- {rec}")
                
                st.markdown("---")
            
            # Événements récents
            if report['recent_events']:
                st.markdown("##### 📅 Événements Récents (30 jours)")
                
                for event in report['recent_events']:
                    event_icon = '🌊' if event['type'] == 'flood' else '🌵' if event['type'] == 'drought' else '⚠️'
                    
                    st.markdown(f"""
                        **{event_icon} {event['date']}** - {event['description']}  
                        *Sévérité :* {event['severity'].upper()} • *Impacts :* {event['impacts']}
                    """)
                
                st.markdown("---")
            
            # Résumé historique
            st.markdown("##### 📊 Résumé Historique")
            
            hist = report['historical_summary']
            
            hist_col1, hist_col2 = st.columns(2)
            
            with hist_col1:
                st.metric("Total Événements", hist['total_events'])
                st.metric("Événements (30j)", hist['recent_events_30d'])
            
            with hist_col2:
                st.markdown("**Répartition par type :**")
                
                for event_type, count in hist['events_by_type'].items():
                    st.markdown(f"- {event_type.title()} : **{count}**")

# ========================================
# TAB 4: STATISTIQUES & TENDANCES
# ========================================

with tab4:
    st.markdown("### 📈 Statistiques Globales et Tendances")
    
    # Statistiques générales
    st.markdown("#### 📊 Vue d'Ensemble")
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    
    with stat_col1:
        st.markdown("""
            **🗺️ Couverture Cartographique**
            
            - Zones totales : {zones}
            - Couches actives : {layers}
            - Surface couverte : {area}
        """.format(
            zones=len(zone_provider),
            layers=stats['total_layers'],
            area=stats['formatted_area']
        ))
    
    with stat_col2:
        st.markdown("""
            **⚠️ Alertes et Risques**
            
            - Alertes actives : {alerts}
            - Zones critiques : {critical}
            - Taux critique : {rate:.1f}%
        """.format(
            alerts=total_alerts,
            critical=len(zones_critiques),
            rate=(len(zones_critiques) / len(zone_provider) * 100) if len(zone_provider) > 0 else 0
        ))
    
    with stat_col3:
        total_pop = sum(
            zone.population or 0
            for zone in zone_provider.zones.values()
        )
        
        critical_pop = sum(
            zone.population or 0
            for zone in zones_critiques
        )
        
        st.markdown("""
            **👥 Impact Population**
            
            - Population totale : {total:,}
            - En zone critique : {critical:,}
            - % affecté : {pct:.1f}%
        """.format(
            total=total_pop,
            critical=critical_pop,
            pct=(critical_pop / total_pop * 100) if total_pop > 0 else 0
        ))
    
    st.markdown("---")
    
    # Répartition par type de risque
    st.markdown("#### 📊 Répartition des Risques")
    
    if stats['by_type']:
        # Graphique en barres
        risk_types_labels = list(stats['by_type'].keys())
        risk_counts = list(stats['by_type'].values())
        
        fig_risk_types = go.Figure(data=[
            go.Bar(
                x=risk_types_labels,
                y=risk_counts,
                marker_color=['#2196F3', '#ffc107', '#f44336', '#9c27b0', '#00bcd4'][:len(risk_types_labels)],
                text=risk_counts,
                textposition='auto'
            )
        ])
        
        fig_risk_types.update_layout(
            title="Nombre de Couches par Type de Risque",
            xaxis_title="Type de Risque",
            yaxis_title="Nombre de Couches",
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_risk_types, use_container_width=True)
    
    # Répartition par niveau
    st.markdown("#### 🎯 Répartition par Niveau de Risque")
    
    if stats['by_level']:
        level_labels = list(stats['by_level'].keys())
        level_counts = list(stats['by_level'].values())
        
        # Couleurs selon niveau
        level_colors = {
            'low': '#28a745',
            'moderate': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545',
            'extreme': '#721c24'
        }
        
        colors = [level_colors.get(level, '#6c757d') for level in level_labels]
        
        fig_levels = go.Figure(data=[
            go.Pie(
                labels=[l.upper() for l in level_labels],
                values=level_counts,
                marker=dict(colors=colors),
                hole=0.4
            )
        ])
        
        fig_levels.update_layout(
            title="Distribution des Niveaux de Risque",
            height=400
        )
        
        st.plotly_chart(fig_levels, use_container_width=True)

# ========================================
# FOOTER
# ========================================

st.markdown("---")
st.caption(f"""
Module 2 - Cartes de Risques et Catastrophes | ONACC v2.1 (Modernisé)  
📡 Données: Supabase + Open-Meteo | 🛰️ Imagerie: Satellite | 🌍 Géolocalisation: Automatique  
MàJ: {datetime.now().strftime('%d/%m/%Y %H:%M')}
""")