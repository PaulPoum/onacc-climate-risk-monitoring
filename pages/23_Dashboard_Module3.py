# pages/23_Dashboard_Module3.py
"""
Dashboard Module 3 : Alertes précoces climatiques et hydrométéo
==============================================================

Objectif:
- Transformer des signaux (indices / prévisions / règles) en alertes opérationnelles multi-risques
- Appliquer des niveaux d'alerte (vert/jaune/orange/rouge)
- Diffuser multi-canaux (SMS/Email/Web/API) -> ici: simulation + outbox si tables existent
- Suivre alertes, destinataires et accusés de réception (ACK)

NB:
- Cette page fonctionne même si les tables Supabase ne sont pas encore créées (mode démo).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pandas as pd
import requests
import streamlit as st

from core.ui import approval_gate
from core.supabase_client import supabase_user

# -----------------------------
# Config page
# -----------------------------
st.set_page_config(
    page_title="Module 3 - Alertes Précoces | ONACC",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styles
# -----------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
      * { font-family: 'Inter', sans-serif; }

      .module-header {
        background: linear-gradient(135deg, #ff512f 0%, #dd2476 100%);
        padding: 2rem;
        border-radius: 18px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 12px 45px rgba(221, 36, 118, 0.30);
      }
      .module-title { font-size: 2.2rem; font-weight: 800; margin-bottom: .4rem; }
      .module-subtitle { font-size: 1.05rem; opacity: .95; }

      .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 14px;
        color: white;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
      }
      .metric-value { font-size: 2.1rem; font-weight: 800; margin: .35rem 0; }
      .metric-label { font-size: .9rem; opacity: .9; }

      .alert-card {
        background: white;
        border-radius: 14px;
        padding: 1.2rem;
        border-left: 6px solid #ddd;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        margin-bottom: .9rem;
      }
      .alert-card.red { border-left-color: #dc3545; }
      .alert-card.orange { border-left-color: #fd7e14; }
      .alert-card.yellow { border-left-color: #ffc107; }
      .alert-card.green { border-left-color: #28a745; }

      .pill {
        display: inline-block;
        padding: .25rem .7rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: .85rem;
        border: 1px solid rgba(0,0,0,.08);
      }
      .pill.red { background: #f8d7da; color: #721c24; }
      .pill.orange { background: #ffe5d0; color: #7a3b00; }
      .pill.yellow { background: #fff3cd; color: #856404; }
      .pill.green { background: #d4edda; color: #155724; }

      .soft {
        background: #f8f9fa;
        border-radius: 14px;
        padding: 1rem;
        border: 1px solid #eee;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Guards
# -----------------------------
if not st.session_state.get("access_token"):
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="module-header">
      <div class="module-title">🚨 Module 3 : Alertes précoces climatiques et hydrométéo</div>
      <div class="module-subtitle">
        Détection automatique • Niveaux d’alerte • Diffusion multi-canaux • Suivi des destinataires & ACK
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_back, _ = st.columns([1, 7])
with col_back:
    if st.button("← Retour Dashboard Principal", use_container_width=True):
        st.switch_page("pages/10_Dashboard.py")

# -----------------------------
# Helpers Supabase (tolérant)
# -----------------------------
def supa():
    return supabase_user(st.session_state["access_token"])

def safe_table_exists(table_name: str) -> bool:
    """
    On ne peut pas introspecter proprement Postgres via supabase-py en client anon.
    Donc on teste un select minimal.
    """
    try:
        _ = supa().table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False

def safe_select(table: str, order: Optional[Tuple[str, bool]] = None, limit: int = 200) -> List[Dict[str, Any]]:
    try:
        q = supa().table(table).select("*")
        if order:
            col, desc = order
            q = q.order(col, desc=desc)
        res = q.limit(limit).execute()
        return res.data or []
    except Exception:
        return []

def safe_insert(table: str, payload: Dict[str, Any]) -> bool:
    try:
        _ = supa().table(table).insert(payload).execute()
        return True
    except Exception:
        return False

def safe_update(table: str, match: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    try:
        q = supa().table(table).update(payload)
        for k, v in match.items():
            q = q.eq(k, v)
        _ = q.execute()
        return True
    except Exception:
        return False

# -----------------------------
# Data structures
# -----------------------------
ALERT_LEVELS = ["green", "yellow", "orange", "red"]
LEVEL_LABEL = {"green": "VERT", "yellow": "JAUNE", "orange": "ORANGE", "red": "ROUGE"}
RISK_TYPES = ["flood", "drought"]
RISK_LABEL = {"flood": "Inondation", "drought": "Sécheresse"}

@dataclass
class Alert:
    alert_id: str
    risk_type: str
    level: str
    zone_name: str
    region: str
    station_id: Optional[int]
    lat: float
    lon: float
    signal_summary: str
    issued_at: datetime
    expires_at: datetime
    status: str  # active|expired|cancelled
    channels: List[str]
    recipients_count: int = 0
    ack_count: int = 0

def now() -> datetime:
    return datetime.now()

def default_rules() -> Dict[str, Any]:
    """
    Règles simples V1 (adaptables ensuite via Module 8):
    - Flood (mm/24h): yellow>=50, orange>=80, red>=120
    - Drought (jours secs consécutifs): yellow>=7, orange>=10, red>=14
    """
    return {
        "flood": {"yellow": 50.0, "orange": 80.0, "red": 120.0},
        "drought": {"yellow": 7, "orange": 10, "red": 14},
    }

# -----------------------------
# Open-Meteo (prévisions) pour détection V1
# -----------------------------
@st.cache_data(ttl=900)
def fetch_open_meteo_daily(lat: float, lon: float, forecast_days: int = 10) -> Dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,windspeed_10m_max",
        "forecast_days": min(int(forecast_days), 16),
        "timezone": "Africa/Douala",
    }
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()

def compute_flood_level(daily: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[str, str]:
    d = daily.get("daily", {})
    pr = d.get("precipitation_sum", []) or []
    dates = d.get("time", []) or []
    if not pr:
        return "green", "Aucune donnée précipitation disponible."

    max_1d = max(pr)
    idx = pr.index(max_1d)
    day = dates[idx] if idx < len(dates) else "N/A"

    # Niveau
    thr = rules["flood"]
    if max_1d >= thr["red"]:
        level = "red"
    elif max_1d >= thr["orange"]:
        level = "orange"
    elif max_1d >= thr["yellow"]:
        level = "yellow"
    else:
        level = "green"

    summary = f"Max précipitations prévues: {max_1d:.1f} mm/24h (jour: {day})."
    return level, summary

def compute_drought_level(daily: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[str, str]:
    d = daily.get("daily", {})
    pr = d.get("precipitation_sum", []) or []
    tmax = d.get("temperature_2m_max", []) or []
    dates = d.get("time", []) or []
    if not pr:
        return "green", "Aucune donnée précipitation disponible."

    # streak de jours secs prévus (< 1mm)
    max_streak = 0
    cur = 0
    start_best = None
    start_cur = None

    for i, p in enumerate(pr):
        if p < 1.0:
            if cur == 0:
                start_cur = dates[i] if i < len(dates) else None
            cur += 1
            if cur > max_streak:
                max_streak = cur
                start_best = start_cur
        else:
            cur = 0
            start_cur = None

    # Niveau
    thr = rules["drought"]
    if max_streak >= thr["red"]:
        level = "red"
    elif max_streak >= thr["orange"]:
        level = "orange"
    elif max_streak >= thr["yellow"]:
        level = "yellow"
    else:
        level = "green"

    avg_tmax = (sum(tmax) / len(tmax)) if tmax else 0.0
    summary = f"Série sèche prévue: {max_streak} jour(s) (début: {start_best or 'N/A'}), Tmax moyenne: {avg_tmax:.1f}°C."
    return level, summary

# -----------------------------
# Stations (Supabase)
# -----------------------------
@st.cache_data(ttl=300)
def get_stations() -> pd.DataFrame:
    try:
        res = supa().table("mnocc_stations").select("*").order("localite").execute()
        df = pd.DataFrame(res.data or [])
        if df.empty:
            return df
        # normalisation
        for c in ["latitude", "longitude"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["id", "localite", "latitude", "longitude"])
        return df
    except Exception:
        return pd.DataFrame()

stations_df = get_stations()

# -----------------------------
# Storage (DB ou session)
# Tables attendues (optionnelles) :
# - risk_alerts
# - alert_recipients
# - alert_ack
# - notification_outbox
# -----------------------------
DB_ALERTS = safe_table_exists("risk_alerts")
DB_RECIP = safe_table_exists("alert_recipients")
DB_ACK = safe_table_exists("alert_ack")
DB_OUTBOX = safe_table_exists("notification_outbox")

def ensure_session_state():
    if "m3_rules" not in st.session_state:
        st.session_state["m3_rules"] = default_rules()
    if "m3_alerts" not in st.session_state:
        st.session_state["m3_alerts"] = []  # List[dict]
    if "m3_recipients" not in st.session_state:
        st.session_state["m3_recipients"] = []  # List[dict]
    if "m3_ack" not in st.session_state:
        st.session_state["m3_ack"] = []  # List[dict]
    if "m3_outbox" not in st.session_state:
        st.session_state["m3_outbox"] = []  # List[dict]

ensure_session_state()

def load_alerts() -> List[Dict[str, Any]]:
    if DB_ALERTS:
        rows = safe_select("risk_alerts", order=("issued_at", True), limit=500)
        return rows
    return st.session_state["m3_alerts"]

def save_alert(a: Dict[str, Any]) -> None:
    if DB_ALERTS:
        ok = safe_insert("risk_alerts", a)
        if not ok:
            st.warning("Échec écriture Supabase (risk_alerts). Bascule en session.")
            st.session_state["m3_alerts"].insert(0, a)
    else:
        st.session_state["m3_alerts"].insert(0, a)

def load_recipients() -> List[Dict[str, Any]]:
    if DB_RECIP:
        return safe_select("alert_recipients", order=("created_at", True), limit=1000)
    return st.session_state["m3_recipients"]

def save_recipient(r: Dict[str, Any]) -> None:
    if DB_RECIP:
        ok = safe_insert("alert_recipients", r)
        if not ok:
            st.warning("Échec écriture Supabase (alert_recipients). Bascule en session.")
            st.session_state["m3_recipients"].insert(0, r)
    else:
        st.session_state["m3_recipients"].insert(0, r)

def load_ack() -> List[Dict[str, Any]]:
    if DB_ACK:
        return safe_select("alert_ack", order=("acked_at", True), limit=2000)
    return st.session_state["m3_ack"]

def add_ack(ack: Dict[str, Any]) -> None:
    if DB_ACK:
        ok = safe_insert("alert_ack", ack)
        if not ok:
            st.warning("Échec écriture Supabase (alert_ack). Bascule en session.")
            st.session_state["m3_ack"].insert(0, ack)
    else:
        st.session_state["m3_ack"].insert(0, ack)

def push_outbox(item: Dict[str, Any]) -> None:
    if DB_OUTBOX:
        ok = safe_insert("notification_outbox", item)
        if not ok:
            st.warning("Échec écriture Supabase (notification_outbox). Bascule en session.")
            st.session_state["m3_outbox"].insert(0, item)
    else:
        st.session_state["m3_outbox"].insert(0, item)

# -----------------------------
# Sidebar filters
# -----------------------------
with st.sidebar:
    st.markdown("### Filtres & Paramètres")
    risk_filter = st.multiselect(
        "Types de risque",
        options=RISK_TYPES,
        default=["flood", "drought"],
        format_func=lambda x: f"{'🌊' if x=='flood' else '🌵'} {RISK_LABEL[x]}",
    )
    level_filter = st.multiselect(
        "Niveaux",
        options=ALERT_LEVELS,
        default=["yellow", "orange", "red"],
        format_func=lambda x: f"{'🟢' if x=='green' else '🟡' if x=='yellow' else '🟠' if x=='orange' else '🔴'} {LEVEL_LABEL[x]}",
    )
    status_filter = st.multiselect(
        "Statut",
        options=["active", "expired", "cancelled"],
        default=["active"],
    )
    horizon_days = st.select_slider("Horizon analyse (jours)", options=[7, 10, 14, 16], value=10)

# -----------------------------
# Compute KPIs
# -----------------------------
alerts = load_alerts()
recipients = load_recipients()
acks = load_ack()

def is_active(a: Dict[str, Any]) -> bool:
    try:
        if a.get("status") != "active":
            return False
        exp = a.get("expires_at")
        if isinstance(exp, str):
            exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
        elif isinstance(exp, datetime):
            exp_dt = exp
        else:
            return True
        return exp_dt >= now()
    except Exception:
        return a.get("status") == "active"

active_alerts = [a for a in alerts if is_active(a)]
critical_active = [a for a in active_alerts if a.get("level") == "red"]

# Ack rate
ack_df = pd.DataFrame(acks) if acks else pd.DataFrame(columns=["alert_id"])
ack_rate = 0.0
if active_alerts:
    # nombre d'alertes actives avec >=1 ack
    acked_ids = set(ack_df["alert_id"].astype(str).tolist()) if not ack_df.empty else set()
    acked_alerts = sum(1 for a in active_alerts if str(a.get("alert_id")) in acked_ids)
    ack_rate = (acked_alerts / len(active_alerts)) * 100.0

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(
        f"""
        <div class="metric-box">
          <div class="metric-value">{len(active_alerts)}</div>
          <div class="metric-label">Alertes actives</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
          <div class="metric-value">{len(critical_active)}</div>
          <div class="metric-label">Actives critiques</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
          <div class="metric-value">{len(recipients)}</div>
          <div class="metric-label">Destinataires</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
          <div class="metric-value">{len(acks)}</div>
          <div class="metric-label">ACK cumulés</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        f"""
        <div class="metric-box" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color:#333;">
          <div class="metric-value">{ack_rate:.0f}%</div>
          <div class="metric-label">Taux ACK (alertes actives)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")

# -----------------------------
# Tabs
# -----------------------------
tab_detect, tab_active, tab_diff, tab_ack, tab_rules = st.tabs(
    [
        "🧠 Détection & Génération",
        "🚨 Alertes (actives & historique)",
        "📣 Diffusion & Destinataires",
        "✅ Accusés de réception (ACK)",
        "⚙️ Règles & Seuils",
    ]
)

# =========================================================
# TAB 1: Detection & generation
# =========================================================
with tab_detect:
    st.markdown("#### Générer des alertes à partir des stations (Open-Meteo)")
    if stations_df.empty:
        st.error("❌ Aucune station trouvée dans mnocc_stations.")
        st.stop()

    left, right = st.columns([2, 1])
    with left:
        station_options = [
            f"{row['localite']} — {row.get('region','N/A')}"
            for _, row in stations_df.iterrows()
        ]
        selected_label = st.selectbox("Station", options=station_options, key="m3_station")
        idx = station_options.index(selected_label)
        st_row = stations_df.iloc[idx]
        st.info(
            f"📍 **{st_row['localite']}** | Région: **{st_row.get('region','N/A')}** | "
            f"Coord.: {float(st_row['latitude']):.4f}, {float(st_row['longitude']):.4f}"
        )

    with right:
        st.markdown('<div class="soft">', unsafe_allow_html=True)
        st.caption("Actions")
        gen_flood = st.button("🌊 Détecter (Inondation)", use_container_width=True)
        gen_drought = st.button("🌵 Détecter (Sécheresse)", use_container_width=True)
        gen_both = st.button("⚡ Détecter (les deux)", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Detection
    if gen_flood or gen_drought or gen_both:
        with st.spinner("🔄 Analyse Open-Meteo…"):
            try:
                fc = fetch_open_meteo_daily(float(st_row["latitude"]), float(st_row["longitude"]), horizon_days)
            except Exception as e:
                st.error(f"Erreur Open-Meteo: {e}")
                fc = {}

        rules = st.session_state["m3_rules"]

        def create_alert(risk_type: str) -> Optional[Dict[str, Any]]:
            if not fc:
                return None

            if risk_type == "flood":
                level, summary = compute_flood_level(fc, rules)
                icon = "🌊"
                validity = timedelta(days=2)
            else:
                level, summary = compute_drought_level(fc, rules)
                icon = "🌵"
                validity = timedelta(days=7)

            # On ne crée pas d'alerte si niveau vert (sauf si utilisateur force)
            create_even_green = st.checkbox("Créer aussi les alertes VERTES (debug)", value=False, key=f"m3_green_{risk_type}")
            if level == "green" and not create_even_green:
                st.success(f"✅ Aucun dépassement de seuil ({icon} {RISK_LABEL[risk_type]}).")
                return None

            issued = now()
            exp = issued + validity

            alert = {
                "alert_id": str(uuid.uuid4()),
                "risk_type": risk_type,
                "level": level,
                "zone_name": str(st_row["localite"]),
                "region": str(st_row.get("region", "")),
                "station_id": int(st_row["id"]),
                "lat": float(st_row["latitude"]),
                "lon": float(st_row["longitude"]),
                "signal_summary": summary,
                "issued_at": issued.isoformat(),
                "expires_at": exp.isoformat(),
                "status": "active",
                "channels": ["web"],  # par défaut
                "created_by": st.session_state.get("user_email", ""),
            }
            return alert

        created: List[Dict[str, Any]] = []
        if gen_flood or gen_both:
            a = create_alert("flood")
            if a:
                save_alert(a)
                created.append(a)
        if gen_drought or gen_both:
            a = create_alert("drought")
            if a:
                save_alert(a)
                created.append(a)

        if created:
            st.success(f"✅ {len(created)} alerte(s) créée(s).")
            st.rerun()

    st.markdown("---")
    st.markdown("#### Dernière analyse (aperçu prévisions)")
    try:
        with st.spinner("🔄 Chargement aperçu Open-Meteo…"):
            fc_preview = fetch_open_meteo_daily(
                float(stations_df.iloc[0]["latitude"]),
                float(stations_df.iloc[0]["longitude"]),
                7,
            )
        d = fc_preview.get("daily", {})
        df_prev = pd.DataFrame(
            {
                "date": pd.to_datetime(d.get("time", [])),
                "precip_mm": d.get("precipitation_sum", []),
                "tmax_c": d.get("temperature_2m_max", []),
                "tmin_c": d.get("temperature_2m_min", []),
            }
        )
        st.dataframe(df_prev, use_container_width=True, hide_index=True)
    except Exception:
        st.caption("Aperçu indisponible (réseau ou API).")

# =========================================================
# TAB 2: Alerts (active + history)
# =========================================================
with tab_active:
    st.markdown("#### Alertes filtrées")

    df_alerts = pd.DataFrame(alerts) if alerts else pd.DataFrame(
        columns=["alert_id","risk_type","level","zone_name","region","issued_at","expires_at","status"]
    )

    # Apply filters
    if not df_alerts.empty:
        df_alerts["risk_type"] = df_alerts["risk_type"].astype(str)
        df_alerts["level"] = df_alerts["level"].astype(str)
        df_alerts["status"] = df_alerts["status"].astype(str)

        df_f = df_alerts[
            df_alerts["risk_type"].isin(risk_filter)
            & df_alerts["level"].isin(level_filter + ["green"])  # pour éviter blocage
            & df_alerts["status"].isin(status_filter)
        ].copy()

        # Sort by issued_at desc
        if "issued_at" in df_f.columns:
            df_f["issued_at_dt"] = pd.to_datetime(df_f["issued_at"], errors="coerce")
            df_f = df_f.sort_values("issued_at_dt", ascending=False)

        # Render cards
        if df_f.empty:
            st.info("Aucune alerte pour les filtres sélectionnés.")
        else:
            for _, a in df_f.head(80).iterrows():
                risk = a.get("risk_type", "")
                level = a.get("level", "green")
                zone = a.get("zone_name", "")
                region = a.get("region", "")
                issued_at = str(a.get("issued_at", ""))
                expires_at = str(a.get("expires_at", ""))
                summary = str(a.get("signal_summary", ""))

                icon = "🌊" if risk == "flood" else "🌵" if risk == "drought" else "⚠️"
                level_lbl = LEVEL_LABEL.get(level, level).upper()

                st.markdown(
                    f"""
                    <div class="alert-card {level}">
                      <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                        <div>
                          <div style="font-weight:800; font-size:1.1rem;">{icon} {RISK_LABEL.get(risk, risk)} — {zone}</div>
                          <div style="opacity:.8; margin-top:.2rem;">Région: <b>{region}</b></div>
                        </div>
                        <div class="pill {level}">{level_lbl}</div>
                      </div>
                      <div style="margin-top:.7rem; line-height:1.6;">
                        <div><b>Signal :</b> {summary}</div>
                        <div><b>Émise :</b> {issued_at} • <b>Expire :</b> {expires_at}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Export
            with st.expander("📤 Export", expanded=False):
                st.download_button(
                    "Télécharger CSV (alertes filtrées)",
                    data=df_f.drop(columns=[c for c in ["issued_at_dt"] if c in df_f.columns]).to_csv(index=False).encode("utf-8"),
                    file_name="module3_alertes.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
    else:
        st.info("Aucune alerte disponible (créez-en depuis l’onglet Détection).")

# =========================================================
# TAB 3: Diffusion & recipients
# =========================================================
with tab_diff:
    st.markdown("#### Destinataires (ministères, autorités, services techniques, partenaires)")
    st.caption("Vous pouvez gérer une liste de diffusion et simuler l’envoi multi-canaux. L’intégration SMS/Email/API sera branchée ensuite sur un service dédié.")

    # Add recipient
    with st.expander("➕ Ajouter un destinataire", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_name = st.text_input("Nom complet", key="m3_r_name")
            r_org = st.text_input("Institution / Structure", key="m3_r_org")
        with c2:
            r_role = st.text_input("Rôle (ex: Gouverneur, Maire…)", key="m3_r_role")
            r_zone = st.text_input("Zone / Région (champ libre)", key="m3_r_zone")
        with c3:
            r_email = st.text_input("Email (optionnel)", key="m3_r_email")
            r_phone = st.text_input("Téléphone (optionnel)", key="m3_r_phone")
            r_channels = st.multiselect(
                "Canaux",
                options=["email", "sms", "web", "api"],
                default=["web"],
                key="m3_r_channels",
            )

        if st.button("Enregistrer destinataire", type="primary", use_container_width=True):
            if not r_name.strip() or not r_org.strip():
                st.warning("Veuillez renseigner au minimum Nom complet + Institution.")
            else:
                payload = {
                    "recipient_id": str(uuid.uuid4()),
                    "name": r_name.strip(),
                    "organization": r_org.strip(),
                    "role": r_role.strip(),
                    "zone": r_zone.strip(),
                    "email": r_email.strip(),
                    "phone": r_phone.strip(),
                    "channels": r_channels,
                    "created_at": now().isoformat(),
                }
                save_recipient(payload)
                st.success("✅ Destinataire enregistré.")
                st.rerun()

    recipients = load_recipients()
    df_r = pd.DataFrame(recipients) if recipients else pd.DataFrame(columns=["name","organization","role","zone","channels"])

    st.markdown("---")
    st.markdown("#### Liste de diffusion")
    st.dataframe(df_r, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Diffuser une alerte (simulation / outbox)")
    active_alerts = [a for a in load_alerts() if is_active(a)]

    if not active_alerts:
        st.info("Aucune alerte active à diffuser. Créez une alerte depuis l’onglet Détection.")
    else:
        alert_labels = []
        for a in active_alerts:
            icon = "🌊" if a.get("risk_type") == "flood" else "🌵"
            alert_labels.append(f"{icon} {RISK_LABEL.get(a.get('risk_type',''), a.get('risk_type',''))} — {a.get('zone_name','')} — {LEVEL_LABEL.get(a.get('level','green'))}")

        selected = st.selectbox("Alerte active", options=list(range(len(active_alerts))), format_func=lambda i: alert_labels[i], key="m3_alert_to_send")
        a = active_alerts[int(selected)]

        send_channels = st.multiselect(
            "Canaux de diffusion",
            options=["web", "email", "sms", "api"],
            default=["web"],
            key="m3_send_channels",
        )
        scope = st.selectbox("Cible", options=["Tous", "Filtrer par zone/région"], key="m3_scope")

        zone_key = ""
        if scope == "Filtrer par zone/région":
            zone_key = st.text_input("Mot-clé zone/région (ex: Nord, Extrême-Nord…)", key="m3_scope_key")

        # Resolve recipients
        selected_recipients = recipients
        if scope == "Filtrer par zone/région" and zone_key.strip():
            kz = zone_key.strip().lower()
            selected_recipients = [
                r for r in recipients
                if kz in str(r.get("zone","")).lower() or kz in str(r.get("organization","")).lower()
            ]

        st.caption(f"Destinataires ciblés: {len(selected_recipients)}")

        if st.button("📣 Lancer diffusion (simulation)", type="primary", use_container_width=True):
            if not selected_recipients:
                st.warning("Aucun destinataire ciblé.")
            else:
                # Outbox items
                for r in selected_recipients:
                    item = {
                        "outbox_id": str(uuid.uuid4()),
                        "alert_id": str(a.get("alert_id")),
                        "recipient_id": str(r.get("recipient_id","")),
                        "channels": send_channels,
                        "status": "queued",
                        "created_at": now().isoformat(),
                        "payload": {
                            "title": f"ONACC Alerte {LEVEL_LABEL.get(a.get('level','green'))} — {RISK_LABEL.get(a.get('risk_type',''), a.get('risk_type',''))}",
                            "zone": a.get("zone_name"),
                            "region": a.get("region"),
                            "summary": a.get("signal_summary"),
                            "issued_at": a.get("issued_at"),
                            "expires_at": a.get("expires_at"),
                        },
                    }
                    push_outbox(item)

                st.success("✅ Diffusion enregistrée (outbox).")
                st.rerun()

    # Outbox display (session only)
    if "m3_outbox" in st.session_state and st.session_state["m3_outbox"]:
        with st.expander("📦 Outbox (simulation)", expanded=False):
            st.dataframe(pd.DataFrame(st.session_state["m3_outbox"]), use_container_width=True, hide_index=True)

# =========================================================
# TAB 4: ACK
# =========================================================
with tab_ack:
    st.markdown("#### Accusés de réception (ACK) — suivi opérationnel")
    st.caption("Permet de confirmer que l’information a été reçue par les acteurs (ministères, gouverneurs, préfets, maires, services techniques…).")

    alerts_all = load_alerts()
    if not alerts_all:
        st.info("Aucune alerte disponible.")
    else:
        # choose alert
        labels = []
        for a in alerts_all[:300]:
            icon = "🌊" if a.get("risk_type") == "flood" else "🌵"
            labels.append(f"{icon} {a.get('zone_name','')} — {LEVEL_LABEL.get(a.get('level','green'))} — {a.get('issued_at','')}")
        selected_idx = st.selectbox("Sélectionner une alerte", options=list(range(min(len(alerts_all), 300))), format_func=lambda i: labels[i], key="m3_ack_alert")
        alert_sel = alerts_all[int(selected_idx)]

        recipients = load_recipients()
        if not recipients:
            st.warning("Aucun destinataire enregistré (onglet Diffusion & Destinataires).")
        else:
            rec_labels = [f"{r.get('name','')} — {r.get('organization','')}" for r in recipients]
            ridx = st.selectbox("Destinataire", options=list(range(len(recipients))), format_func=lambda i: rec_labels[i], key="m3_ack_rec")
            rec = recipients[int(ridx)]

            ack_status = st.selectbox("Statut ACK", options=["received", "read", "actioned"], index=0, key="m3_ack_status")
            ack_note = st.text_area("Note (optionnel)", key="m3_ack_note")

            if st.button("✅ Enregistrer ACK", type="primary", use_container_width=True):
                payload = {
                    "ack_id": str(uuid.uuid4()),
                    "alert_id": str(alert_sel.get("alert_id")),
                    "recipient_id": str(rec.get("recipient_id")),
                    "status": ack_status,
                    "note": ack_note.strip(),
                    "acked_at": now().isoformat(),
                }
                add_ack(payload)
                st.success("✅ ACK enregistré.")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Journal des ACK")
    acks = load_ack()
    if not acks:
        st.info("Aucun ACK enregistré.")
    else:
        df_ack = pd.DataFrame(acks)
        st.dataframe(df_ack, use_container_width=True, hide_index=True)

# =========================================================
# TAB 5: Rules & thresholds
# =========================================================
with tab_rules:
    st.markdown("#### Règles & Seuils (V1) — configurables")
    st.caption("En V1, on applique des seuils simples. L’intégration complète des référentiels et seuils avancés sera consolidée dans le Module 8.")

    rules = st.session_state["m3_rules"]

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("##### 🌊 Inondation — seuils mm/24h")
        y = st.number_input("JAUNE (≥)", min_value=0.0, value=float(rules["flood"]["yellow"]), step=5.0, key="m3_f_y")
        o = st.number_input("ORANGE (≥)", min_value=0.0, value=float(rules["flood"]["orange"]), step=5.0, key="m3_f_o")
        r = st.number_input("ROUGE (≥)", min_value=0.0, value=float(rules["flood"]["red"]), step=5.0, key="m3_f_r")
        st.caption("Référence: précipitations journalières (Open-Meteo daily precipitation_sum).")

    with r2:
        st.markdown("##### 🌵 Sécheresse — série de jours secs (< 1 mm)")
        y2 = st.number_input("JAUNE (≥ jours)", min_value=0, value=int(rules["drought"]["yellow"]), step=1, key="m3_d_y")
        o2 = st.number_input("ORANGE (≥ jours)", min_value=0, value=int(rules["drought"]["orange"]), step=1, key="m3_d_o")
        r2v = st.number_input("ROUGE (≥ jours)", min_value=0, value=int(rules["drought"]["red"]), step=1, key="m3_d_r")
        st.caption("Référence: séquence de jours secs prévus (p < 1 mm).")

    c_save, c_reset = st.columns([1, 1])
    with c_save:
        if st.button("💾 Enregistrer règles", type="primary", use_container_width=True):
            if not (y <= o <= r and y2 <= o2 <= r2v):
                st.error("Les seuils doivent être croissants (JAUNE ≤ ORANGE ≤ ROUGE).")
            else:
                st.session_state["m3_rules"] = {
                    "flood": {"yellow": float(y), "orange": float(o), "red": float(r)},
                    "drought": {"yellow": int(y2), "orange": int(o2), "red": int(r2v)},
                }
                st.success("✅ Règles mises à jour.")
                st.rerun()

    with c_reset:
        if st.button("↩️ Réinitialiser (défaut)", use_container_width=True):
            st.session_state["m3_rules"] = default_rules()
            st.success("✅ Règles réinitialisées.")
            st.rerun()

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption(
    f"Module 3 — Alertes précoces | ONACC v1 (Streamlit) | "
    f"MàJ: {now().strftime('%d/%m/%Y %H:%M')} | "
    f"DB hooks: alerts={DB_ALERTS}, recipients={DB_RECIP}, ack={DB_ACK}, outbox={DB_OUTBOX}"
)
