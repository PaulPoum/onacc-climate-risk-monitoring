# pages/13_Module1_Vue_Regionale.py
"""
Module 1 - Vue Régionale
Analyse détaillée par région/commune avec séries temporelles
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta

from core.ui import approval_gate
from core.supabase_client import supabase_user
from core.open_meteo import fetch_daily_forecast

st.set_page_config(
    page_title="Vue Régionale | Module 1",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vérifications
if not st.session_state.get("access_token"):
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;500;600;700;800&display=swap');
        
        * { font-family: 'Inter', sans-serif; }
        
        .page-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }
        
        .info-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
        }
        
        .metric-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: #1565c0;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }
        
        .alert-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #ff9800;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="page-header">
        <h1 style="margin:0;">📍 Vue Régionale Détaillée</h1>
        <p style="margin:0.5rem 0 0 0; opacity:0.95;">Analyse approfondie par région ou commune</p>
    </div>
""", unsafe_allow_html=True)

# Client
uclient = supabase_user(st.session_state["access_token"])

# Sélection région/commune
st.markdown("### 🎯 Sélection de la Zone")

col1, col2 = st.columns([2, 1])

with col1:
    # Charger les codes admin disponibles
    try:
        admin_res = uclient.table("risk_indicators").select("admin_code").execute()
        admin_codes = sorted(list(set([r['admin_code'] for r in (admin_res.data or [])])))
        
        if not admin_codes:
            st.warning("Aucune zone administrative avec des données disponibles.")
            st.stop()
        
        selected_admin = st.selectbox(
            "Zone administrative",
            options=admin_codes,
            index=0 if admin_codes else None
        )
    except Exception as e:
        st.error(f"Erreur chargement zones: {e}")
        st.stop()

with col2:
    period = st.selectbox(
        "Période d'analyse",
        options=["7 derniers jours", "30 derniers jours", "90 derniers jours"],
        index=1
    )
    
    days_map = {
        "7 derniers jours": 7,
        "30 derniers jours": 30,
        "90 derniers jours": 90
    }
    nb_days = days_map[period]

# Infos zone sélectionnée
st.markdown(f"""
    <div class="info-card">
        <strong style="font-size:1.2rem;">📍 {selected_admin}</strong><br>
        <span style="color:#666;">Période: {period}</span>
    </div>
""", unsafe_allow_html=True)

# ----- SECTION 1: INDICATEURS ACTUELS -----
st.markdown("### 📊 Situation Actuelle")

try:
    valid_date = date.today().isoformat()
    
    # Récupérer tous les indicateurs de la zone
    indicators_res = uclient.table("risk_indicators").select(
        "indicator_code,value,unit,risk"
    ).eq("admin_code", selected_admin).eq("valid_date", valid_date).execute()
    
    indicators = {r['indicator_code']: r for r in (indicators_res.data or [])}
    
    metric_cols = st.columns(4)
    
    # PRCP_24H
    with metric_cols[0]:
        prcp_24h = indicators.get('PRCP_24H', {}).get('value', 0)
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{float(prcp_24h):.1f}</div>
                <div class="metric-label">Pluie 24h (mm)</div>
            </div>
        """, unsafe_allow_html=True)
    
    # CDD
    with metric_cols[1]:
        cdd = indicators.get('CDD', {}).get('value', 0)
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{float(cdd):.0f}</div>
                <div class="metric-label">Jours Secs Consécutifs</div>
            </div>
        """, unsafe_allow_html=True)
    
    # FLOOD_SCORE
    with metric_cols[2]:
        flood_score = indicators.get('FLOOD_SCORE', {}).get('value', 0)
        color = "#f44336" if float(flood_score) >= 75 else "#ff9800" if float(flood_score) >= 50 else "#4caf50"
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value" style="color:{color};">{float(flood_score):.0f}</div>
                <div class="metric-label">Score Inondation (/100)</div>
            </div>
        """, unsafe_allow_html=True)
    
    # DROUGHT_SCORE
    with metric_cols[3]:
        drought_score = indicators.get('DROUGHT_SCORE', {}).get('value', 0)
        color = "#f44336" if float(drought_score) >= 75 else "#ff9800" if float(drought_score) >= 50 else "#4caf50"
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value" style="color:{color};">{float(drought_score):.0f}</div>
                <div class="metric-label">Score Sécheresse (/100)</div>
            </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erreur chargement indicateurs: {e}")

# ----- SECTION 2: SÉRIES TEMPORELLES -----
st.markdown(f"### 📈 Évolution Temporelle ({period})")

try:
    date_start = (datetime.now() - timedelta(days=nb_days)).date().isoformat()
    
    # Charger historique des indicateurs
    hist_res = uclient.table("risk_indicators").select(
        "valid_date,indicator_code,value"
    ).eq("admin_code", selected_admin).gte("valid_date", date_start).order("valid_date").execute()
    
    df_hist = pd.DataFrame(hist_res.data or [])
    
    if not df_hist.empty:
        df_hist['value'] = pd.to_numeric(df_hist['value'], errors='coerce')
        df_hist['valid_date'] = pd.to_datetime(df_hist['valid_date'])
        
        # Créer subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Précipitations 24h (mm)",
                "Jours Secs Consécutifs",
                "Score Inondation (0-100)",
                "Score Sécheresse (0-100)"
            ),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # PRCP_24H
        df_prcp = df_hist[df_hist['indicator_code'] == 'PRCP_24H']
        if not df_prcp.empty:
            fig.add_trace(
                go.Bar(
                    x=df_prcp['valid_date'],
                    y=df_prcp['value'],
                    name='PRCP_24H',
                    marker_color='#2196f3'
                ),
                row=1, col=1
            )
        
        # CDD
        df_cdd = df_hist[df_hist['indicator_code'] == 'CDD']
        if not df_cdd.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_cdd['valid_date'],
                    y=df_cdd['value'],
                    mode='lines+markers',
                    name='CDD',
                    line=dict(color='#ff9800', width=2)
                ),
                row=1, col=2
            )
        
        # FLOOD_SCORE
        df_flood = df_hist[df_hist['indicator_code'] == 'FLOOD_SCORE']
        if not df_flood.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_flood['valid_date'],
                    y=df_flood['value'],
                    mode='lines+markers',
                    name='Flood',
                    line=dict(color='#2196f3', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.1)'
                ),
                row=2, col=1
            )
            
            # Seuils
            fig.add_hline(y=75, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
            fig.add_hline(y=50, line_dash="dash", line_color="orange", opacity=0.5, row=2, col=1)
        
        # DROUGHT_SCORE
        df_drought = df_hist[df_hist['indicator_code'] == 'DROUGHT_SCORE']
        if not df_drought.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_drought['valid_date'],
                    y=df_drought['value'],
                    mode='lines+markers',
                    name='Drought',
                    line=dict(color='#ff9800', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(255, 152, 0, 0.1)'
                ),
                row=2, col=2
            )
            
            # Seuils
            fig.add_hline(y=75, line_dash="dash", line_color="red", opacity=0.5, row=2, col=2)
            fig.add_hline(y=50, line_dash="dash", line_color="orange", opacity=0.5, row=2, col=2)
        
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Valeur")
        
        fig.update_layout(
            height=600,
            showlegend=False,
            template='plotly_white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée historique disponible pour cette zone.")
        
except Exception as e:
    st.warning(f"Erreur chargement historique: {e}")

# ----- SECTION 3: ALERTES ACTIVES -----
st.markdown("### 🚨 Alertes Actives")

# Simulé pour l'instant
if float(flood_score) >= 50 or float(drought_score) >= 50:
    alerts = []
    
    if float(flood_score) >= 75:
        alerts.append(("🔴 ALERTE ROUGE - Risque Inondation Critique", f"Score: {float(flood_score):.0f}/100"))
    elif float(flood_score) >= 50:
        alerts.append(("🟠 ALERTE ORANGE - Risque Inondation Élevé", f"Score: {float(flood_score):.0f}/100"))
    
    if float(drought_score) >= 75:
        alerts.append(("🔴 ALERTE ROUGE - Sécheresse Sévère", f"Score: {float(drought_score):.0f}/100"))
    elif float(drought_score) >= 50:
        alerts.append(("🟠 ALERTE ORANGE - Sécheresse Modérée", f"Score: {float(drought_score):.0f}/100"))
    
    for title, desc in alerts:
        st.markdown(f"""
            <div class="alert-box">
                <strong>{title}</strong><br>
                <span style="color:#666;">{desc}</span>
            </div>
        """, unsafe_allow_html=True)
else:
    st.success("✅ Aucune alerte active pour cette zone")

# ----- SECTION 4: PRÉVISIONS 10 JOURS -----
st.markdown("### 🔮 Prévisions 10 Jours")

try:
    # Récupérer station de la zone (première station trouvée)
    stations_res = uclient.table("mnocc_stations").select(
        "id,localite,latitude,longitude"
    ).eq("admin_code", selected_admin).limit(1).execute()
    
    if stations_res.data:
        station = stations_res.data[0]
        
        with st.spinner("Chargement prévisions..."):
            forecast_data = fetch_daily_forecast(
                station['latitude'],
                station['longitude'],
                days=10,
                seasonal=False
            )
            
            daily = forecast_data.get('daily', {})
            
            if daily:
                df_forecast = pd.DataFrame({
                    'date': pd.to_datetime(daily['time']),
                    'temp_max': daily.get('temperature_2m_max', []),
                    'temp_min': daily.get('temperature_2m_min', []),
                    'precip': daily.get('precipitation_sum', []),
                    'wind': daily.get('wind_speed_10m_max', [])
                })
                
                # Graphique prévisions
                fig_forecast = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=("Températures", "Précipitations"),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                # Températures
                fig_forecast.add_trace(
                    go.Scatter(
                        x=df_forecast['date'],
                        y=df_forecast['temp_max'],
                        mode='lines+markers',
                        name='Tmax',
                        line=dict(color='#f44336', width=2)
                    ),
                    row=1, col=1
                )
                
                fig_forecast.add_trace(
                    go.Scatter(
                        x=df_forecast['date'],
                        y=df_forecast['temp_min'],
                        mode='lines+markers',
                        name='Tmin',
                        line=dict(color='#2196f3', width=2)
                    ),
                    row=1, col=1
                )
                
                # Précipitations
                fig_forecast.add_trace(
                    go.Bar(
                        x=df_forecast['date'],
                        y=df_forecast['precip'],
                        name='Pluie',
                        marker_color='#2196f3'
                    ),
                    row=1, col=2
                )
                
                fig_forecast.update_xaxes(title_text="Date")
                fig_forecast.update_yaxes(title_text="°C", row=1, col=1)
                fig_forecast.update_yaxes(title_text="mm", row=1, col=2)
                
                fig_forecast.update_layout(
                    height=400,
                    showlegend=True,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                # Probabilité alerte (estimation simple)
                prob_flood = len(df_forecast[df_forecast['precip'] > 50]) / len(df_forecast) * 100
                prob_drought = len(df_forecast[df_forecast['precip'] < 1]) / len(df_forecast) * 100
                
                prob_cols = st.columns(2)
                with prob_cols[0]:
                    st.metric("📊 Probabilité Inondation", f"{prob_flood:.0f}%")
                with prob_cols[1]:
                    st.metric("📊 Probabilité Sécheresse", f"{prob_drought:.0f}%")
            else:
                st.warning("Données prévisions non disponibles")
    else:
        st.info("Aucune station associée à cette zone")
        
except Exception as e:
    st.warning(f"Erreur prévisions: {e}")

# Actions
st.markdown("### ⚡ Actions")

action_cols = st.columns(3)

with action_cols[0]:
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()

with action_cols[1]:
    if st.button("📈 Indicateurs Avancés", use_container_width=True):
        st.switch_page("pages/14_Module1_Indicateurs.py")

with action_cols[2]:
    if st.button("📄 Générer Rapport Zone", use_container_width=True):
        st.info("Fonctionnalité en développement")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.caption("📍 Vue Régionale - Module 1 | ONACC Climate Risk Monitoring")
with col2:
    if st.button("← Retour Hub", key="back_hub"):
        st.switch_page("pages/11_Module1_Hub.py")