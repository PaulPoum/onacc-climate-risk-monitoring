# pages/10_Dashboard.py
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.ui import approval_gate
from core.supabase_client import supabase_user
from core.open_meteo import fetch_daily_forecast

st.set_page_config(
    page_title="Dashboard - ONACC Climate Risk Monitoring", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styles CSS modernisés ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Header personnalisé */
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }
        
        .dashboard-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        
        .dashboard-subtitle {
            font-size: 1.1rem;
            opacity: 0.95;
            font-weight: 400;
        }
        
        /* Cards KPI */
        .kpi-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
        }
        
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
            border-color: #667eea;
        }
        
        .kpi-icon {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .kpi-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: #667eea;
            margin: 0.5rem 0;
        }
        
        .kpi-label {
            font-size: 0.95rem;
            color: #666;
            font-weight: 500;
        }
        
        /* Forecast section */
        .forecast-section {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 2rem;
            border-radius: 16px;
            margin: 2rem 0;
            box-shadow: 0 4px 20px rgba(33, 150, 243, 0.2);
        }
        
        .forecast-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1565c0;
            margin-bottom: 0.5rem;
        }
        
        .forecast-subtitle {
            font-size: 1rem;
            color: #1976d2;
            margin-bottom: 1.5rem;
        }
        
        /* Alert cards compactes */
        .alert-mini {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 0.8rem;
            border-left: 4px solid;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .alert-icon-mini {
            font-size: 2rem;
            flex-shrink: 0;
        }
        
        .alert-content-mini {
            flex: 1;
        }
        
        .alert-title-mini {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        
        .alert-desc-mini {
            font-size: 0.85rem;
            color: #666;
        }
        
        .alert-secheresse { border-left-color: #ff9800; }
        .alert-pluie { border-left-color: #2196F3; }
        .alert-chaleur { border-left-color: #f44336; }
        .alert-vent { border-left-color: #009688; }
        
        /* Stats box */
        .stats-box {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        }
        
        /* Module cards */
        .module-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 2px solid transparent;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
            position: relative;
            overflow: hidden;
        }
        
        .module-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }
        
        .module-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
            border-color: #667eea;
        }
        
        .module-card:hover::before {
            transform: scaleX(1);
        }
        
        .module-number {
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            text-align: center;
            line-height: 40px;
            font-weight: 800;
            font-size: 1.2rem;
            margin-bottom: 1rem;
        }
        
        .module-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }
        
        .module-desc {
            font-size: 0.95rem;
            color: #666;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .status-partiel {
            background: #fff3cd;
            color: #856404;
        }
        
        .status-ok {
            background: #d4edda;
            color: #155724;
        }
        
        .status-dev {
            background: #e2e3e5;
            color: #383d41;
        }
        
        /* Quick access section */
        .quick-access {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
        }
        
        .quick-access-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 1.5rem;
        }
        
        /* Info boxes */
        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        /* Custom divider */
        .custom-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, #667eea, transparent);
            margin: 2rem 0;
            border: none;
        }
        
        /* Animation d'entrée */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .animate-in {
            animation: fadeInUp 0.6s ease-out;
        }
    </style>
""", unsafe_allow_html=True)

APP_TITLE = "ONACC Climate Risk Monitoring"

# -----------------------------
# Session helpers
# -----------------------------
def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token") and st.session_state.get("refresh_token"))

def get_user_email() -> str:
    em = (st.session_state.get("user_email") or "").strip().lower()
    if em:
        return em
    prof = st.session_state.get("profile") or {}
    return str(prof.get("email") or "").strip().lower()

SUPER_ADMINS = {str(x).strip().lower() for x in (st.secrets.get("SUPER_ADMIN_EMAILS") or [])}

# -----------------------------
# Guards
# -----------------------------
st.markdown("""
    <div class="dashboard-header animate-in">
        <div class="dashboard-title">🌍 Dashboard ONACC Climate Risk</div>
        <div class="dashboard-subtitle">
            Plateforme de surveillance et d'analyse des risques climatiques au Cameroun
        </div>
    </div>
""", unsafe_allow_html=True)

if not is_logged_in():
    st.warning("⚠️ Veuillez vous connecter pour accéder au dashboard.")
    if st.button("🔐 Se connecter", type="primary"):
        st.switch_page("pages/02_Connexion.py")
    st.stop()

if not approval_gate():
    st.stop()

email = get_user_email()
is_super_admin = email in SUPER_ADMINS

u = supabase_user(st.session_state["access_token"])

# -----------------------------
# Modules & Navigation
# -----------------------------
def fetch_allowed_module_codes() -> set[str]:
    try:
        res = u.rpc("my_modules", {}).execute()
        data = res.data or []
        codes = {str(m.get("code")).strip() for m in data if m.get("code")}
        return {c for c in codes if c}
    except Exception:
        return set()

allowed_codes = fetch_allowed_module_codes()
allowed_codes.add("DASHBOARD")

if is_super_admin:
    allowed_codes.add("ADMIN_APPROVALS")

CODE_TO_PAGE = {
    "DASHBOARD": "pages/10_Dashboard.py",
    "CARTE": "pages/20_Carte.py",
    "INGESTION_OPENMETEO": "pages/80_Ingestion_OpenMeteo.py",
    "VEILLE_HOURLY": "pages/81_Veille_Hourly_OpenMeteo.py",
    "VEILLE_SCORES": "pages/82_Veille_Scores_V2.py",
    "PIPELINE_V2": "pages/83_Pipeline_Veille_V2.py",
    "ADMIN_APPROVALS": "pages/90_Admin_Approvals.py",
}

def can_navigate_to(code: str) -> bool:
    if code not in CODE_TO_PAGE:
        return False
    if code == "ADMIN_APPROVALS" and not is_super_admin:
        return False
    return code in allowed_codes

def navigate_to(code: str) -> None:
    if not can_navigate_to(code):
        st.warning("❌ Accès non autorisé pour votre profil.")
        return
    st.switch_page(CODE_TO_PAGE[code])


def navigate_to_module(module_id: int) -> None:
    """Navigation vers le dashboard d'un module"""
    module_pages = {
        1: "pages/21_Dashboard_Module1.py",
        2: "pages/22_Dashboard_Module2.py",
        3: "pages/23_Dashboard_Module3.py",
        4: "pages/24_Dashboard_Module4.py",
        5: "pages/25_Dashboard_Module5.py",
        6: "pages/26_Dashboard_Module6.py",
        7: "pages/27_Dashboard_Module7.py",
        8: "pages/28_Dashboard_Module8.py",
        9: "pages/29_Dashboard_Module9.py",
    }
    
    if module_id in module_pages:
        st.switch_page(module_pages[module_id])



# -----------------------------
# Obtenir la localisation de l'utilisateur
# -----------------------------
def get_user_location_from_session():
    """Récupère la localisation depuis la session Streamlit (si disponible via le navigateur)"""
    # Streamlit stocke la localisation dans query_params si fournie
    # Format attendu: ?lat=3.8480&lon=11.5021
    try:
        query_params = st.query_params
        if 'lat' in query_params and 'lon' in query_params:
            return {
                'lat': float(query_params['lat']),
                'lon': float(query_params['lon']),
                'localite': 'Ma Position',
                'region': 'Position actuelle'
            }
    except:
        pass
    
    # Sinon, utiliser Yaoundé par défaut (capitale du Cameroun)
    return {
        'lat': 3.8480,
        'lon': 11.5021,
        'localite': 'Yaoundé',
        'region': 'Centre'
    }

def charger_previsions_auto(station_info, horizon_label="10 jours", horizon_days=10, is_seasonal=False):
    """Charge automatiquement les prévisions pour une station"""
    try:
        raw = fetch_daily_forecast(station_info['lat'], station_info['lon'], horizon_days, is_seasonal)
        daily = raw.get('daily', {})
        
        if daily:
            df_prev = pd.DataFrame({
                'date': pd.to_datetime(daily['time']),
                'temperature_2m_max': daily.get('temperature_2m_max', []),
                'temperature_2m_min': daily.get('temperature_2m_min', []),
                'precipitation_sum': daily.get('precipitation_sum', []),
                'wind_speed_10m_max': daily.get('wind_speed_10m_max', [])
            })
            
            st.session_state['forecast_data'] = {
                'df': df_prev,
                'station': station_info,
                'horizon': horizon_label,
                'timestamp': datetime.now()
            }
            return True
    except Exception as e:
        st.error(f"❌ Erreur de chargement : {str(e)}")
    
    return False

# -----------------------------
# Helpers sûrs
# -----------------------------
def safe_count(table: str, eq: tuple[str, str] | None = None) -> int:
    try:
        q = u.table(table).select("id", count="exact")
        if eq:
            q = q.eq(eq[0], eq[1])
        res = q.execute()
        return int(getattr(res, "count", 0) or 0)
    except Exception:
        return 0

def safe_select(table: str, cols: str, limit: int = 50, order_col: str | None = None, desc: bool = True):
    try:
        q = u.table(table).select(cols).limit(limit)
        if order_col:
            q = q.order(order_col, desc=desc)
        return (q.execute().data) or []
    except Exception:
        return []

# -----------------------------
# Analyse aléas (version compacte)
# -----------------------------
def analyser_aleas_compact(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    
    aleas = {}
    
    # Sécheresse
    jours_sans_pluie = 0
    max_secheresse = 0
    for _, row in df.iterrows():
        if row.get('precipitation_sum', 0) < 1:
            jours_sans_pluie += 1
            max_secheresse = max(max_secheresse, jours_sans_pluie)
        else:
            jours_sans_pluie = 0
    
    if max_secheresse >= 5:
        aleas['secheresse'] = {
            'duree': max_secheresse,
            'severite': 'Élevée' if max_secheresse >= 10 else 'Modérée'
        }
    
    # Pluies intenses
    pluies = df[df['precipitation_sum'] > 50]
    if len(pluies) > 0:
        aleas['pluies'] = {
            'count': len(pluies),
            'max': pluies['precipitation_sum'].max(),
            'dates': pluies.head(3)['date'].tolist()
        }
    
    # Chaleur extrême
    chaleur = df[df['temperature_2m_max'] > 35]
    if len(chaleur) > 0:
        aleas['chaleur'] = {
            'count': len(chaleur),
            'max': chaleur['temperature_2m_max'].max()
        }
    
    # Vents forts
    vents = df[df['wind_speed_10m_max'] > 60]
    if len(vents) > 0:
        aleas['vents'] = {
            'count': len(vents),
            'max': vents['wind_speed_10m_max'].max()
        }
    
    return aleas

def creer_graphique_compact(df: pd.DataFrame, titre: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('🌡️ Températures', '🌧️ Précipitations', '💨 Vent', '📊 Distribution'),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # Températures
    fig.add_trace(go.Scatter(x=df['date'], y=df['temperature_2m_max'],
                            name='Max', line=dict(color='#f44336', width=2),
                            showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['temperature_2m_min'],
                            name='Min', line=dict(color='#2196F3', width=2),
                            fill='tonexty', showlegend=False), row=1, col=1)
    
    # Précipitations
    fig.add_trace(go.Bar(x=df['date'], y=df['precipitation_sum'],
                        marker_color='#2196F3', showlegend=False), row=1, col=2)
    
    # Vent
    fig.add_trace(go.Scatter(x=df['date'], y=df['wind_speed_10m_max'],
                            line=dict(color='#009688', width=2),
                            fill='tozeroy', showlegend=False), row=2, col=1)
    
    # Distribution températures
    fig.add_trace(go.Box(y=df['temperature_2m_max'], name='Temp',
                        marker_color='#f44336', showlegend=False), row=2, col=2)
    
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="mm", row=1, col=2)
    fig.update_yaxes(title_text="km/h", row=2, col=1)
    fig.update_yaxes(title_text="°C", row=2, col=2)
    
    fig.update_layout(
        title=titre,
        height=600,
        showlegend=False,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(t=60, b=40, l=40, r=40)
    )
    
    return fig

# -----------------------------
# KPIs
# -----------------------------
st.markdown("### 📊 Indicateurs Clés de la Plateforme")

n_stations = safe_count("mnocc_stations")
n_alerts_active = safe_count("risk_alerts", eq=("status", "active"))
n_events = safe_count("events_impacts")
n_audit = safe_count("audit_logs")

today = date.today().isoformat()
try:
    n_forecasts_today = int(
        getattr(
            u.table("climate_forecasts").select("id", count="exact").eq("valid_date", today).execute(),
            "count", 0
        ) or 0
    )
except Exception:
    n_forecasts_today = 0

kpi_cols = st.columns(5)

kpis = [
    ("🌡️", n_stations, "Stations Météo"),
    ("⚠️", n_alerts_active, "Alertes Actives"),
    ("📅", n_forecasts_today, "Prévisions J0"),
    ("🌪️", n_events, "Événements"),
    ("📝", n_audit, "Logs d'Audit"),
]

for idx, (icon, value, label) in enumerate(kpis):
    with kpi_cols[idx]:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-value">{value:,}</div>
                <div class="kpi-label">{label}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# -----------------------------
# SECTION PRÉVISIONS MÉTÉOROLOGIQUES
# -----------------------------
with st.container():
    st.markdown("""
        <div class="forecast-section animate-in">
            <div class="forecast-title">🌦️ Prévisions Météorologiques</div>
            <div class="forecast-subtitle">Analyse intelligente avec détection automatique des aléas climatiques</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Récupérer stations
    stations_data = safe_select(
        "mnocc_stations",
        cols="id,localite,region,latitude,longitude",
        limit=1000,
        order_col="localite"
    )
    
    if not stations_data:
        st.warning("⚠️ Aucune station météo disponible dans la base de données.")
    else:
        # Ajouter la position de l'utilisateur au début
        user_location = get_user_location_from_session()
        
        # Composant JavaScript pour obtenir la géolocalisation (optionnel)
        st.components.v1.html("""
            <script>
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        
                        // Stocker dans sessionStorage
                        sessionStorage.setItem('user_lat', lat);
                        sessionStorage.setItem('user_lon', lon);
                        
                        // Envoyer à Streamlit via query params (optionnel)
                        // window.parent.postMessage({type: 'location', lat: lat, lon: lon}, '*');
                    },
                    function(error) {
                        console.log('Géolocalisation refusée ou non disponible');
                    },
                    {
                        enableHighAccuracy: false,
                        timeout: 5000,
                        maximumAge: 300000  // Cache 5 minutes
                    }
                );
            }
            </script>
        """, height=0)
        
        stations_dict = {
            f"📍 {user_location['localite']} ({user_location['region']})": user_location
        }
        
        # Ajouter toutes les autres stations
        for s in stations_data:
            stations_dict[f"{s['localite']} ({s['region']})"] = {
                'id': s.get('id'),
                'lat': s['latitude'],
                'lon': s['longitude'],
                'localite': s['localite'],
                'region': s['region']
            }
        
        # Charger automatiquement les prévisions au premier chargement
        if 'forecast_data' not in st.session_state:
            with st.spinner("⏳ Chargement des prévisions pour votre localisation..."):
                charger_previsions_auto(user_location, "10 jours", 10, False)
        
        # Interface sélection (2 colonnes + bouton)
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            # Sélectionner par défaut la localisation de l'utilisateur
            default_key = list(stations_dict.keys())[0]
            
            station_sel = st.selectbox(
                "📍 Sélectionner une localité",
                options=list(stations_dict.keys()),
                index=0,
                key="forecast_station_select"
            )
        
        with col2:
            horizon_options = {
                "10 jours": ("D10", 10, False),
                "20 jours": ("D20", 20, True),
                "30 jours": ("D30", 30, True),
                "6 mois": ("M6", 180, True),
            }
            
            horizon_lbl = st.selectbox(
                "📅 Échéance de prévision",
                options=list(horizon_options.keys()),
                index=0,
                key="forecast_horizon_select"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            load_btn = st.button("🔄 Charger", type="primary", use_container_width=True)
        
        if load_btn:
            station = stations_dict[station_sel]
            _, days, seasonal = horizon_options[horizon_lbl]
            
            with st.spinner(f"⏳ Chargement des prévisions..."):
                if charger_previsions_auto(station, horizon_lbl, days, seasonal):
                    st.success(f"✅ Prévisions chargées pour {station['localite']}")
                    st.rerun()
        
        # Afficher prévisions
        if 'forecast_data' in st.session_state:
            data = st.session_state['forecast_data']
            df = data['df']
            station = data['station']
            
            st.markdown(f"""
                <div class="stats-box">
                    <strong style="font-size: 1.2rem;">📍 {station['localite']} ({station['region']})</strong><br>
                    <span style="color: #666;">
                        {data['horizon']} • MàJ: {data['timestamp'].strftime('%d/%m/%Y %H:%M')}
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Aléas détectés
            aleas = analyser_aleas_compact(df)
            
            if aleas:
                st.markdown("**⚠️ Aléas Climatiques Détectés**")
                
                cols = st.columns(2)
                
                idx = 0
                if 'secheresse' in aleas:
                    with cols[idx % 2]:
                        a = aleas['secheresse']
                        st.markdown(f"""
                            <div class="alert-mini alert-secheresse">
                                <div class="alert-icon-mini">🌵</div>
                                <div class="alert-content-mini">
                                    <div class="alert-title-mini">Sécheresse</div>
                                    <div class="alert-desc-mini">{a['duree']} jours • {a['severite']}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    idx += 1
                
                if 'pluies' in aleas:
                    with cols[idx % 2]:
                        a = aleas['pluies']
                        dates_str = ", ".join([d.strftime('%d/%m') for d in a['dates']])
                        st.markdown(f"""
                            <div class="alert-mini alert-pluie">
                                <div class="alert-icon-mini">🌊</div>
                                <div class="alert-content-mini">
                                    <div class="alert-title-mini">Pluies intenses</div>
                                    <div class="alert-desc-mini">{a['count']}j • Max: {a['max']:.1f}mm ({dates_str})</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    idx += 1
                
                if 'chaleur' in aleas:
                    with cols[idx % 2]:
                        a = aleas['chaleur']
                        st.markdown(f"""
                            <div class="alert-mini alert-chaleur">
                                <div class="alert-icon-mini">🔥</div>
                                <div class="alert-content-mini">
                                    <div class="alert-title-mini">Chaleur extrême</div>
                                    <div class="alert-desc-mini">{a['count']}j • Max: {a['max']:.1f}°C</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    idx += 1
                
                if 'vents' in aleas:
                    with cols[idx % 2]:
                        a = aleas['vents']
                        st.markdown(f"""
                            <div class="alert-mini alert-vent">
                                <div class="alert-icon-mini">💨</div>
                                <div class="alert-content-mini">
                                    <div class="alert-title-mini">Vents forts</div>
                                    <div class="alert-desc-mini">{a['count']}j • Max: {a['max']:.1f}km/h</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("✅ Aucun aléa majeur détecté")
            
            # Stats résumées
            st.markdown("**📈 Statistiques**")
            stats_cols = st.columns(4)
            
            with stats_cols[0]:
                st.metric("🌡️ Temp. Max Moy", f"{df['temperature_2m_max'].mean():.1f}°C")
            with stats_cols[1]:
                st.metric("🌧️ Cumul", f"{df['precipitation_sum'].sum():.0f}mm")
            with stats_cols[2]:
                st.metric("🌵 Jours secs", f"{len(df[df['precipitation_sum'] < 1])}")
            with stats_cols[3]:
                st.metric("💨 Vent Max", f"{df['wind_speed_10m_max'].max():.0f}km/h")
            
            # Graphique
            with st.expander("📊 Visualisations détaillées", expanded=False):
                fig = creer_graphique_compact(
                    df,
                    f"Prévisions - {station['localite']} ({data['horizon']})"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Données brutes
                with st.expander("📋 Données brutes"):
                    st.dataframe(
                        df.style.format({
                            'temperature_2m_max': '{:.1f}°C',
                            'temperature_2m_min': '{:.1f}°C',
                            'precipitation_sum': '{:.1f}mm',
                            'wind_speed_10m_max': '{:.1f}km/h'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# -----------------------------
# Accès rapide
# -----------------------------
st.markdown("""
    <div class="quick-access">
        <div class="quick-access-title">⚡ Accès Rapide aux Modules</div>
    </div>
""", unsafe_allow_html=True)

quick_cols = st.columns(5)

quick_actions = [
    ("CARTE", "🗺️", "Cartes SIG"),
    ("INGESTION_OPENMETEO", "🌦️", "Open-Meteo"),
    ("VEILLE_HOURLY", "⏱️", "Veille Hourly"),
    ("VEILLE_SCORES", "🧮", "Scores V2"),
    ("ADMIN_APPROVALS", "✅", "Approbations"),
]

for idx, (code, icon, label) in enumerate(quick_actions):
    with quick_cols[idx]:
        enabled = can_navigate_to(code)
        if st.button(f"{icon} {label}", use_container_width=True,
                    disabled=not enabled, key=f"quick_{code}"):
            if enabled:
                navigate_to(code)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# -----------------------------
# Modules
# -----------------------------
st.markdown("### 📦 Modules de la Plateforme")
st.caption("Les modules disponibles dépendent de vos droits d'accès.")

MODULES = [
    {
        "id": 1,
        "title": "Veille hydrométéorologique et climatique",
        "desc": "Surveillance temps réel, prévisions et tableaux de bord opérationnels.",
        "pages": [
            ("INGESTION_OPENMETEO", "📥 Ingestion Open-Meteo"),
            ("VEILLE_HOURLY", "⏰ Veille Horaire"),
            ("VEILLE_SCORES", "📊 Scores V2"),
        ],
        "status": "partiel",
        "icon": "🌦️"
    },
    {
        "id": 2,
        "title": "Cartes de risques et catastrophes",
        "desc": "SIG avec cartographie multi-risques et zones critiques.",
        "pages": [("CARTE", "🗺️ Cartographie")],
        "status": "partiel",
        "icon": "🗺️"
    },
    {
        "id": 3,
        "title": "Alertes précoces climatiques",
        "desc": "Système de notifications et escalade des risques.",
        "pages": [],
        "status": "à développer",
        "icon": "🚨"
    },
    {
        "id": 4,
        "title": "Analyse & rapports",
        "desc": "Diagnostics climatiques et rapports automatisés.",
        "pages": [],
        "status": "à développer",
        "icon": "📈"
    },
    {
        "id": 5,
        "title": "Événements & impacts",
        "desc": "Documentation des catastrophes et évaluation impacts.",
        "pages": [],
        "status": "à développer",
        "icon": "🌪️"
    },
    {
        "id": 6,
        "title": "Secteurs & territoires",
        "desc": "Priorisation zones à risque et vulnérabilités.",
        "pages": [],
        "status": "à développer",
        "icon": "🎯"
    },
    {
        "id": 7,
        "title": "Utilisateurs & accès",
        "desc": "Gestion des rôles et permissions.",
        "pages": [("ADMIN_APPROVALS", "✅ Approbations")],
        "status": "partiel",
        "icon": "👥"
    },
    {
        "id": 8,
        "title": "Paramétrage",
        "desc": "Configuration seuils et référentiels.",
        "pages": [],
        "status": "à développer",
        "icon": "⚙️"
    },
    {
        "id": 9,
        "title": "Audit & historique",
        "desc": "Traçabilité complète des actions.",
        "pages": [],
        "status": "à développer",
        "icon": "📝"
    },
]

STATUS_CONFIG = {
    "partiel": ("status-partiel", "🟡 En développement"),
    "ok": ("status-ok", "🟢 Opérationnel"),
    "à développer": ("status-dev", "⚪ Planifié"),
}

module_cols = st.columns(3)

for i, m in enumerate(MODULES):
    with module_cols[i % 3]:
        status_class, status_text = STATUS_CONFIG.get(m["status"], ("status-dev", "⚪"))
        
        st.markdown(f"""
            <div class="module-card animate-in" style="animation-delay: {i * 0.1}s">
                <div class="module-number">{m['id']}</div>
                <div class="module-title">{m['icon']} {m['title']}</div>
                <div class="module-desc">{m['desc']}</div>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Bouton principal "Accéder au Module"
        if st.button(
            f"{m['icon']} Accéder au Module {m['id']}",
            key=f"access_mod_{m['id']}",
            use_container_width=True,
            type="primary"
        ):
            navigate_to_module(m['id'])
        
        st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
        
        # Sous-pages individuelles (optionnel, replié)
        if m.get("pages"):
            with st.expander("📋 Fonctionnalités détaillées", expanded=False):
                for code, label in m.get("pages", []):
                    if can_navigate_to(code):
                        if st.button(label, key=f"mod_{m['id']}_{code}",
                                   use_container_width=True, type="secondary"):
                            navigate_to(code)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# -----------------------------
# Focus opérationnel J0
# -----------------------------
st.markdown("### 🌍 Situation Opérationnelle du Jour")

data = safe_select(
    "climate_forecasts",
    cols="station_id,valid_date,payload,horizon,source",
    limit=800,
    order_col="valid_date",
    desc=True
)

j0 = [r for r in (data or []) 
      if str(r.get("valid_date")) == today and str(r.get("horizon")) == "D10"]

if not j0:
    st.markdown("""
        <div class="info-box">
            ℹ️ <strong>Aucune donnée disponible</strong><br>
            Lancez l'ingestion Open-Meteo pour charger les dernières prévisions.
        </div>
    """, unsafe_allow_html=True)
    
    if can_navigate_to("INGESTION_OPENMETEO"):
        if st.button("🌦️ Lancer l'ingestion", type="primary"):
            navigate_to("INGESTION_OPENMETEO")
else:
    stn = safe_select("mnocc_stations", cols="id,region,localite", limit=3000)
    stn_map = {x.get("id"): x for x in (stn or [])}

    rows = []
    for r in j0:
        stinfo = stn_map.get(r.get("station_id"), {}) or {}
        p = r.get("payload") or {}
        rows.append({
            "Région": stinfo.get("region") or "N/A",
            "Station": stinfo.get("localite") or r.get("station_id"),
            "Pluie (mm)": p.get("precipitation_sum"),
            "Tmax (°C)": p.get("temperature_2m_max"),
            "Vent (km/h)": p.get("wind_speed_10m_max"),
        })

    df = pd.DataFrame(rows)

    metrics_cols = st.columns(4)
    
    with metrics_cols[0]:
        st.metric("📍 Stations", len(df))
    with metrics_cols[1]:
        st.metric("🌧️ Pluie moy", f"{df['Pluie (mm)'].mean():.1f}mm")
    with metrics_cols[2]:
        st.metric("🌡️ Temp moy", f"{df['Tmax (°C)'].mean():.1f}°C")
    with metrics_cols[3]:
        st.metric("💨 Vent moy", f"{df['Vent (km/h)'].mean():.1f}km/h")

    c1, c2 = st.columns(2)
    
    with c1:
        st.caption("🌧️ Plus arrosées")
        by_region = df.groupby("Région", as_index=False).agg({
            "Pluie (mm)": "mean"
        }).sort_values("Pluie (mm)", ascending=False)
        st.dataframe(by_region.head(5), use_container_width=True, hide_index=True)
    
    with c2:
        st.caption("🌡️ Plus chaudes")
        by_temp = df.groupby("Région", as_index=False).agg({
            "Tmax (°C)": "mean"
        }).sort_values("Tmax (°C)", ascending=False)
        st.dataframe(by_temp.head(5), use_container_width=True, hide_index=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# -----------------------------
# Diagnostic
# -----------------------------
with st.expander("🔧 Administration & Diagnostic"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**👤 Utilisateur**")
        st.write("📧", email)
        st.write("👑 Admin:", "✅" if is_super_admin else "❌")
        st.write("🔑 Modules:", len(allowed_codes))
        
    with col2:
        st.markdown("**📦 Codes**")
        st.write(", ".join(sorted(list(allowed_codes))))
    
    if st.button("🔄 Recharger"):
        st.rerun()