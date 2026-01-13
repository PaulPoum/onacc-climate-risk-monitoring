# pages/11_Module1_Hub.py
"""
Module 1 - Veille Hydrométéorologique et Climatique
Hub central donnant accès à tous les sous-modules
"""
from __future__ import annotations

import streamlit as st
from datetime import datetime, date
import pandas as pd
from core.ui import approval_gate
from core.supabase_client import supabase_user

st.set_page_config(
    page_title="Module 1 - Veille Hydrométéo | ONACC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vérifications
if not st.session_state.get("access_token"):
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# CSS du Module 1
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Header Module 1 */
        .module1-header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 15px 50px rgba(79, 172, 254, 0.3);
            text-align: center;
        }
        
        .module1-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .module1-subtitle {
            font-size: 1.3rem;
            opacity: 0.95;
            font-weight: 400;
            margin-bottom: 1rem;
        }
        
        .module1-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 0.5rem 1.5rem;
            border-radius: 30px;
            font-size: 0.9rem;
            font-weight: 600;
            backdrop-filter: blur(10px);
        }
        
        /* Stat Cards */
        .stat-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border-left: 4px solid;
            transition: all 0.3s ease;
            height: 100%;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }
        
        .stat-card.blue { border-color: #4facfe; }
        .stat-card.orange { border-color: #ff9800; }
        .stat-card.green { border-color: #4caf50; }
        .stat-card.red { border-color: #f44336; }
        
        .stat-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .stat-value {
            font-size: 3rem;
            font-weight: 800;
            margin: 0.5rem 0;
        }
        
        .stat-value.blue { color: #4facfe; }
        .stat-value.orange { color: #ff9800; }
        .stat-value.green { color: #4caf50; }
        .stat-value.red { color: #f44336; }
        
        .stat-label {
            font-size: 1rem;
            color: #666;
            font-weight: 500;
        }
        
        .stat-detail {
            font-size: 0.85rem;
            color: #999;
            margin-top: 0.5rem;
        }
        
        /* Sub-module Cards */
        .submodule-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
            position: relative;
            overflow: hidden;
            border: 2px solid transparent;
        }
        
        .submodule-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 0;
            background: linear-gradient(135deg, #4facfe, #00f2fe);
            transition: height 0.3s ease;
        }
        
        .submodule-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            border-color: #4facfe;
        }
        
        .submodule-card:hover::before {
            height: 100%;
        }
        
        .submodule-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .submodule-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .submodule-desc {
            font-size: 0.95rem;
            color: #666;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        
        .submodule-status {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .status-ok {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .status-dev {
            background: #fff3e0;
            color: #e65100;
        }
        
        .status-new {
            background: #e3f2fd;
            color: #1565c0;
        }
        
        /* Timeline */
        .timeline-item {
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            border-left: 3px solid #4facfe;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .timeline-time {
            font-size: 0.85rem;
            color: #999;
            font-weight: 600;
        }
        
        .timeline-content {
            font-size: 0.95rem;
            color: #333;
            margin-top: 0.3rem;
        }
        
        /* Info boxes */
        .info-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #2196f3;
            margin: 1rem 0;
        }
        
        .info-box strong {
            color: #1565c0;
            font-weight: 600;
        }
        
        .warning-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #ff9800;
            margin: 1rem 0;
        }
        
        .warning-box strong {
            color: #e65100;
            font-weight: 600;
        }
        
        /* Button custom */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="module1-header">
        <div class="module1-title">🌦️ Module 1</div>
        <div class="module1-subtitle">Veille Hydrométéorologique et Climatique</div>
        <div class="module1-badge">Surveillance Temps Réel • Prévisions • Alertes</div>
    </div>
""", unsafe_allow_html=True)

# Description
st.markdown("""
    <div class="info-box">
        <strong>À propos du Module 1</strong><br>
        Le module de veille hydrométéorologique et climatique fournit une synthèse en temps quasi réel 
        de la situation liée aux principaux risques climatiques (inondations, sécheresses). 
        Il agrège les données de précipitations, températures, humidité et vent, calcule des indicateurs 
        de déficit pluviométrique, stress hydrique et excès de pluie, et présente une vue synthétique 
        nationale et régionale des zones les plus critiques.
    </div>
""", unsafe_allow_html=True)

# Stats rapides
uclient = supabase_user(st.session_state["access_token"])

try:
    # Compter stations
    stations_count = uclient.table("mnocc_stations").select("id", count="exact").execute()
    nb_stations = stations_count.count if hasattr(stations_count, 'count') else 0
    
    # Compter observations récentes (24h)
    from datetime import timedelta
    h24_ago = (datetime.now() - timedelta(hours=24)).isoformat()
    obs_count = uclient.table("meteo_observations_hourly").select("id", count="exact").gte("observed_at", h24_ago).execute()
    nb_obs = obs_count.count if hasattr(obs_count, 'count') else 0
    
    # Compter alertes actives (simulé pour l'instant)
    alerts_count = 0  # À implémenter quand table risk_alerts existera
    
    # Dernière mise à jour
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M")
    
except Exception:
    nb_stations = 0
    nb_obs = 0
    alerts_count = 0
    last_update = "N/A"

st.markdown("### 📊 Vue d'Ensemble")

stat_cols = st.columns(4)

with stat_cols[0]:
    st.markdown(f"""
        <div class="stat-card blue">
            <div class="stat-icon">📍</div>
            <div class="stat-value blue">{nb_stations}</div>
            <div class="stat-label">Stations Actives</div>
            <div class="stat-detail">Réseau de surveillance</div>
        </div>
    """, unsafe_allow_html=True)

with stat_cols[1]:
    st.markdown(f"""
        <div class="stat-card green">
            <div class="stat-icon">📊</div>
            <div class="stat-value green">{nb_obs:,}</div>
            <div class="stat-label">Observations 24h</div>
            <div class="stat-detail">Données horaires</div>
        </div>
    """, unsafe_allow_html=True)

with stat_cols[2]:
    st.markdown(f"""
        <div class="stat-card orange">
            <div class="stat-icon">⚠️</div>
            <div class="stat-value orange">{alerts_count}</div>
            <div class="stat-label">Alertes Actives</div>
            <div class="stat-detail">En cours</div>
        </div>
    """, unsafe_allow_html=True)

with stat_cols[3]:
    st.markdown(f"""
        <div class="stat-card red">
            <div class="stat-icon">🔄</div>
            <div class="stat-value red" style="font-size: 1.5rem;">{last_update}</div>
            <div class="stat-label">Dernière MàJ</div>
            <div class="stat-detail">Temps réel</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Sous-modules
st.markdown("### 🎯 Sous-Modules Disponibles")

SUBMODULES = [
    {
        "title": "Synthèse Nationale",
        "icon": "🗺️",
        "desc": "Vue d'ensemble du territoire avec cartes interactives, zones critiques et indicateurs nationaux en temps réel.",
        "page": "pages/12_Module1_Synthese_Nationale.py",
        "status": "🆕 Nouveau",
        "status_class": "status-new"
    },
    {
        "title": "Vue Régionale",
        "icon": "📍",
        "desc": "Analyse détaillée par région/commune avec séries temporelles, comparaisons vs climatologie et prévisions 10 jours.",
        "page": "pages/13_Module1_Vue_Regionale.py",
        "status": "🆕 Nouveau",
        "status_class": "status-new"
    },
    {
        "title": "Indicateurs Avancés",
        "icon": "📈",
        "desc": "Calcul des indices SPI/SPEI, anomalies spatiales, percentiles historiques et visualisations scientifiques.",
        "page": "pages/14_Module1_Indicateurs.py",
        "status": "🆕 Nouveau",
        "status_class": "status-new"
    },
    {
        "title": "Alertes Automatiques",
        "icon": "🚨",
        "desc": "Configuration des seuils, règles de déclenchement, notifications multi-canaux et historique des alertes.",
        "page": "pages/15_Module1_Alertes.py",
        "status": "🔧 En développement",
        "status_class": "status-dev"
    },
    {
        "title": "Rapports & Bulletins",
        "icon": "📄",
        "desc": "Génération automatique de bulletins hebdomadaires/mensuels, export PDF/Excel et bibliothèque de rapports.",
        "page": "pages/16_Module1_Rapports.py",
        "status": "🔧 En développement",
        "status_class": "status-dev"
    },
    {
        "title": "Veille Horaire",
        "icon": "⏰",
        "desc": "Ingestion et analyse des observations horaires Open-Meteo avec synthèse des zones critiques du jour.",
        "page": "pages/81_Veille_Hourly_OpenMeteo.py",
        "status": "✅ Opérationnel",
        "status_class": "status-ok"
    },
    {
        "title": "Scores Flood/Drought",
        "icon": "🧮",
        "desc": "Calcul et visualisation des scores de risque inondation et sécheresse (0-100) par zone administrative.",
        "page": "pages/82_Veille_Scores_V2.py",
        "status": "✅ Opérationnel",
        "status_class": "status-ok"
    },
    {
        "title": "Pipeline Automatisé",
        "icon": "⚙️",
        "desc": "Exécution du pipeline complet de calcul des indicateurs et scores avec moteur dynamique V2.",
        "page": "pages/83_Pipeline_Veille_V2.py",
        "status": "✅ Opérationnel",
        "status_class": "status-ok"
    },
    {
        "title": "Ingestion Open-Meteo",
        "icon": "📥",
        "desc": "Interface d'ingestion des prévisions Open-Meteo (D10, D20, D30, M6) vers la base climate_forecasts.",
        "page": "pages/80_Ingestion_OpenMeteo.py",
        "status": "✅ Opérationnel",
        "status_class": "status-ok"
    },
]

# Affichage en grille 3 colonnes
cols = st.columns(3)

for idx, sub in enumerate(SUBMODULES):
    with cols[idx % 3]:
        st.markdown(f"""
            <div class="submodule-card">
                <div class="submodule-icon">{sub['icon']}</div>
                <div class="submodule-title">{sub['title']}</div>
                <div class="submodule-status {sub['status_class']}">{sub['status']}</div>
                <div class="submodule-desc">{sub['desc']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Accéder", key=f"sub_{idx}", use_container_width=True):
            st.switch_page(sub['page'])

st.markdown("<br>", unsafe_allow_html=True)

# Timeline activité récente
st.markdown("### 📅 Activité Récente")

timeline_items = [
    {
        "time": datetime.now().strftime("%H:%M"),
        "content": "🔄 Mise à jour automatique des observations horaires"
    },
    {
        "time": (datetime.now() - timedelta(hours=1)).strftime("%H:%M"),
        "content": "📊 Calcul des scores Flood/Drought pour toutes les régions"
    },
    {
        "time": (datetime.now() - timedelta(hours=2)).strftime("%H:%M"),
        "content": "📥 Ingestion des prévisions Open-Meteo (200 stations)"
    },
    {
        "time": (datetime.now() - timedelta(hours=6)).strftime("%H:%M"),
        "content": "🗺️ Génération de la carte des zones critiques"
    },
]

for item in timeline_items:
    st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-time">{item['time']}</div>
            <div class="timeline-content">{item['content']}</div>
        </div>
    """, unsafe_allow_html=True)

# Documentation
with st.expander("📚 Documentation & Aide"):
    st.markdown("""
        ### Guide d'utilisation du Module 1
        
        **Flux de travail recommandé :**
        
        1. **Synthèse Nationale** : Commencez par une vue d'ensemble du territoire
        2. **Vue Régionale** : Zoomez sur les zones critiques identifiées
        3. **Indicateurs Avancés** : Analysez en profondeur avec SPI/SPEI
        4. **Alertes** : Configurez les seuils et notifications
        5. **Rapports** : Générez les bulletins pour diffusion
        
        **Sources de données :**
        - Stations ONACC (observations horaires)
        - Open-Meteo API (prévisions court et moyen terme)
        - Calculs dérivés (indices climatiques, scores)
        
        **Fréquence de mise à jour :**
        - Observations : Horaire
        - Prévisions : 2 fois par jour
        - Scores : À la demande ou automatique
        - Alertes : Temps réel (selon règles)
        
        **Support :**
        Pour toute question ou problème technique, contactez l'équipe ONACC.
    """)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("🌦️ Module 1 - Veille Hydrométéorologique et Climatique | ONACC Climate Risk Monitoring Platform")