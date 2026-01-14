# pages/23_Dashboard_Module3.py
"""
Dashboard Module 3 : Alertes précoces climatiques et hydrométéo
==============================================================

Variante (avec client SEASONAL_API direct dans ce fichier, tout en gardant la priorité “core” quand dispo)

V1+ (Consolidé):
- Par défaut: récupération de la position utilisateur (si GeolocationService dispo)
- Sélection Région + Localité depuis mnocc_stations (avec filtre)
- Prévisions multi-horizons: 10j, 20j, 30j, 3m, 6m, 1an
  * Forecast API: /v1/forecast (limité à 16 jours)
  * Seasonal API: /v1/seasonal (direct ici) pour 20/30j/3m/6m (si core indisponible)
  * Climate API:  /v1/climate (direct ici ou via core_fetch_climate_daily si dispo) pour 1 an
- Graphiques dynamiques Plotly + table des données
- Détection et génération d’alertes (flood/drought) sur l’horizon sélectionné
- Diffusion (simulation outbox) + ACK (session_state si tables absentes)

Notes:
- Seasonal API n’est pas “1 an” (souvent ~7 mois max). Pour 1 an => Climate API.
- On garde une logique robuste: core > seasonal direct > climate direct > forecast direct (dernier recours).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.ui import approval_gate
from core.supabase_client import supabase_user

APP_TZ = "Africa/Douala"

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
SEASONAL_API = "https://seasonal-api.open-meteo.com/v1/seasonal"
CLIMATE_API = "https://climate-api.open-meteo.com/v1/climate"

DAILY_VARS = "precipitation_sum,temperature_2m_max,temperature_2m_min,wind_speed_10m_max"

# Optionnel: géolocalisation (Module 1)
try:
    from core.module1 import GeolocationService, format_coordinates  # type: ignore
except Exception:  # pragma: no cover
    GeolocationService = None  # type: ignore

    def format_coordinates(lat: float, lon: float) -> str:  # type: ignore
        return f"{lat:.4f}, {lon:.4f}"


# Optionnel: wrapper centralisé core.open_meteo
try:
    from core.open_meteo import fetch_daily_forecast  # type: ignore
except Exception:  # pragma: no cover
    fetch_daily_forecast = None  # type: ignore

# Optionnel: Climate wrapper si vous avez patché core/open_meteo.py
try:
    from core.open_meteo import fetch_climate_daily as core_fetch_climate_daily  # type: ignore
except Exception:  # pragma: no cover
    core_fetch_climate_daily = None  # type: ignore


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Module 3 - Alertes Précoces | ONACC",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styles (moderne)
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
        margin-bottom: 1.2rem;
        box-shadow: 0 12px 45px rgba(221, 36, 118, 0.30);
      }
      .module-title { font-size: 2.05rem; font-weight: 800; margin-bottom: .35rem; }
      .module-subtitle { font-size: 1.0rem; opacity: .95; }

      .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.05rem;
        border-radius: 14px;
        color: white;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
      }
      .metric-value { font-size: 2.0rem; font-weight: 800; margin: .30rem 0; }
      .metric-label { font-size: .9rem; opacity: .9; }

      .soft {
        background: #f8f9fa;
        border-radius: 14px;
        padding: 1rem;
        border: 1px solid #eee;
      }

      .hint {
        background: #eef6ff;
        border: 1px solid #d6e9ff;
        border-left: 4px solid #2196F3;
        padding: .85rem 1rem;
        border-radius: 12px;
      }

      .alert-card {
        background: white;
        border-radius: 14px;
        padding: 1.1rem;
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
        font-weight: 800;
        font-size: .85rem;
        border: 1px solid rgba(0,0,0,.08);
      }
      .pill.red { background: #f8d7da; color: #721c24; }
      .pill.orange { background: #ffe5d0; color: #7a3b00; }
      .pill.yellow { background: #fff3cd; color: #856404; }
      .pill.green { background: #d4edda; color: #155724; }
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
        Localisation • Prévisions multi-horizons • Détection • Niveaux d’alerte • Diffusion • ACK
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c_back, _ = st.columns([1, 8])
with c_back:
    if st.button("← Retour Dashboard Principal", use_container_width=True):
        st.switch_page("pages/10_Dashboard.py")

# -----------------------------
# Supabase helpers (tolérant)
# -----------------------------
def supa():
    return supabase_user(st.session_state["access_token"])


def safe_table_exists(table_name: str) -> bool:
    try:
        _ = supa().table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def safe_select(
    table: str, order: Optional[Tuple[str, bool]] = None, limit: int = 200
) -> List[Dict[str, Any]]:
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


# -----------------------------
# Structures
# -----------------------------
ALERT_LEVELS = ["green", "yellow", "orange", "red"]
LEVEL_LABEL = {"green": "VERT", "yellow": "JAUNE", "orange": "ORANGE", "red": "ROUGE"}
RISK_TYPES = ["flood", "drought"]
RISK_LABEL = {"flood": "Inondation", "drought": "Sécheresse"}

SEVERITY_FROM_LEVEL = {"green": 1, "yellow": 2, "orange": 3, "red": 4}
LEVEL_FROM_SEVERITY = {1: "green", 2: "yellow", 3: "orange", 4: "red"}


def now() -> datetime:
    return datetime.now()


def default_rules() -> Dict[str, Any]:
    return {
        "flood": {"yellow": 50.0, "orange": 80.0, "red": 120.0},
        "drought": {"yellow": 7, "orange": 10, "red": 14},
    }


# -----------------------------
# Localisation utilisateur
# -----------------------------
def get_user_location() -> Dict[str, Any]:
    if "user_location" in st.session_state and isinstance(st.session_state["user_location"], dict):
        return st.session_state["user_location"]

    if GeolocationService is not None:
        try:
            geo = GeolocationService()
            with st.spinner("🌍 Détection de votre position…"):
                loc = geo.get_user_location()
            if loc and loc.get("lat") is not None and loc.get("lon") is not None:
                st.session_state["user_location"] = loc
                return loc
        except Exception:
            pass

    loc = {"lat": 3.8480, "lon": 11.5021, "localite": "Yaoundé", "region": "Centre", "accuracy": None}
    st.session_state["user_location"] = loc
    return loc


@st.cache_data(ttl=300)
def get_stations() -> pd.DataFrame:
    try:
        res = supa().table("mnocc_stations").select("*").order("region").order("localite").execute()
        df = pd.DataFrame(res.data or [])
        if df.empty:
            return df
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        if "id" in df.columns:
            df["id"] = df["id"].astype(str)
        df = df.dropna(subset=["id", "localite", "latitude", "longitude"])
        return df
    except Exception:
        return pd.DataFrame()


stations_df = get_stations()
user_loc = get_user_location()

# -----------------------------
# Horizons
# -----------------------------
HORIZON_CHOICES: Dict[str, Dict[str, Any]] = {
    "10 jours": {"days": 10, "kind": "forecast"},
    "20 jours": {"days": 20, "kind": "seasonal"},
    "30 jours": {"days": 30, "kind": "seasonal"},
    "3 mois": {"days": 90, "kind": "seasonal"},
    "6 mois": {"days": 180, "kind": "seasonal"},
    "1 an": {"days": 365, "kind": "climate"},
}

# -----------------------------
# Clients Open-Meteo directs (Forecast / Seasonal / Climate)
# -----------------------------
@st.cache_data(ttl=900)
def fetch_forecast_daily(lat: float, lon: float, days: int) -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "forecast_days": min(int(days), 16),
        "timezone": APP_TZ,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }
    r = requests.get(FORECAST_API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=900)
def fetch_seasonal_daily(lat: float, lon: float, days: int) -> Dict[str, Any]:
    """
    Seasonal API direct:
    - Même convention "forecast_days" que le core actuel (ça fonctionne en pratique sur l’API seasonal).
    - On borne à days (20/30/90/180) demandé.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "forecast_days": int(days),
        "timezone": APP_TZ,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }
    r = requests.get(SEASONAL_API, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=900)
def fetch_climate_daily(lat: float, lon: float, start_date: str, end_date: str, model: str = "MRI_AGCM3_2_S") -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "models": model,
        "daily": DAILY_VARS,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timeformat": "iso8601",
    }
    r = requests.get(CLIMATE_API, params=params, timeout=40)
    r.raise_for_status()
    return r.json()


def _http_error_details(e: Exception) -> str:
    if isinstance(e, requests.HTTPError) and getattr(e, "response", None) is not None:
        resp = e.response
        body = ""
        try:
            body = (resp.text or "")[:500]
        except Exception:
            body = ""
        return f"HTTP {resp.status_code} | {resp.url} | {body}"
    return f"{type(e).__name__}: {e}"


def fetch_daily_any(lat: float, lon: float, days: int, kind: str) -> Tuple[Dict[str, Any], str]:
    """
    Priorité:
    - core (si dispo et compatible)
    - sinon direct: forecast / seasonal / climate selon kind
    Fallbacks:
    - seasonal -> climate -> forecast(16)
    - climate  -> forecast(16)
    """

    # 1) core prioritaire
    if kind == "forecast":
        if fetch_daily_forecast is not None:
            try:
                raw = fetch_daily_forecast(lat, lon, min(int(days), 16), seasonal=False)  # type: ignore
                return raw, "core.open_meteo (forecast)"
            except Exception as e:
                try:
                    raw = fetch_forecast_daily(lat, lon, min(int(days), 16))
                    return raw, f"forecast_fallback (core err: {_http_error_details(e)})"
                except Exception as e2:
                    return {}, f"forecast_failed ({_http_error_details(e2)})"
        raw = fetch_forecast_daily(lat, lon, min(int(days), 16))
        return raw, "forecast_direct"

    if kind == "seasonal":
        # core seasonal si dispo
        if fetch_daily_forecast is not None:
            try:
                raw = fetch_daily_forecast(lat, lon, int(days), seasonal=True)  # type: ignore
                return raw, "core.open_meteo (seasonal)"
            except Exception as e:
                # fallback direct seasonal
                try:
                    raw = fetch_seasonal_daily(lat, lon, int(days))
                    return raw, f"seasonal_direct (core err: {_http_error_details(e)})"
                except Exception as e2:
                    # fallback climate
                    try:
                        s = date.today()
                        e3 = s + timedelta(days=int(days))
                        if core_fetch_climate_daily is not None:
                            raw = core_fetch_climate_daily(lat, lon, s, e3, model="MRI_AGCM3_2_S")  # type: ignore
                            return raw, f"core.open_meteo (climate fallback, seasonal failed: {_http_error_details(e2)})"
                        raw = fetch_climate_daily(lat, lon, s.isoformat(), e3.isoformat(), "MRI_AGCM3_2_S")
                        return raw, f"climate_fallback (seasonal failed: {_http_error_details(e2)})"
                    except Exception as e3:
                        raw = fetch_forecast_daily(lat, lon, 16)
                        return raw, f"forecast_fallback (seasonal+climate failed: {_http_error_details(e3)})"

        # pas de core => direct seasonal
        try:
            raw = fetch_seasonal_daily(lat, lon, int(days))
            return raw, "seasonal_direct"
        except Exception as e2:
            # fallback climate
            try:
                s = date.today()
                e3 = s + timedelta(days=int(days))
                if core_fetch_climate_daily is not None:
                    raw = core_fetch_climate_daily(lat, lon, s, e3, model="MRI_AGCM3_2_S")  # type: ignore
                    return raw, f"core.open_meteo (climate fallback, seasonal failed: {_http_error_details(e2)})"
                raw = fetch_climate_daily(lat, lon, s.isoformat(), e3.isoformat(), "MRI_AGCM3_2_S")
                return raw, f"climate_fallback (seasonal failed: {_http_error_details(e2)})"
            except Exception as e3:
                raw = fetch_forecast_daily(lat, lon, 16)
                return raw, f"forecast_fallback (seasonal+climate failed: {_http_error_details(e3)})"

    # kind == "climate" (1 an)
    s = date.today()
    e2 = s + timedelta(days=int(days))

    if core_fetch_climate_daily is not None:
        try:
            raw = core_fetch_climate_daily(lat, lon, s, e2, model="MRI_AGCM3_2_S")  # type: ignore
            return raw, "core.open_meteo (climate)"
        except Exception as e:
            try:
                raw = fetch_climate_daily(lat, lon, s.isoformat(), e2.isoformat(), "MRI_AGCM3_2_S")
                return raw, f"climate_direct (core err: {_http_error_details(e)})"
            except Exception as e2:
                raw = fetch_forecast_daily(lat, lon, 16)
                return raw, f"forecast_fallback (climate failed: {_http_error_details(e2)})"

    try:
        raw = fetch_climate_daily(lat, lon, s.isoformat(), e2.isoformat(), "MRI_AGCM3_2_S")
        return raw, "climate_direct"
    except Exception as e:
        raw = fetch_forecast_daily(lat, lon, 16)
        return raw, f"forecast_fallback (climate failed: {_http_error_details(e)})"


def _pad_list(x: Any, n: int) -> List[Any]:
    if x is None:
        x = []
    if not isinstance(x, list):
        try:
            x = list(x)
        except Exception:
            x = []
    if len(x) >= n:
        return x[:n]
    return x + [None] * (n - len(x))


def daily_to_df(raw: Dict[str, Any]) -> pd.DataFrame:
    d = (raw or {}).get("daily", {}) or {}
    time = d.get("time", []) or []
    n = len(time)
    if n == 0:
        return pd.DataFrame()

    precip = _pad_list(d.get("precipitation_sum", []), n)
    tmax = _pad_list(d.get("temperature_2m_max", []), n)
    tmin = _pad_list(d.get("temperature_2m_min", []), n)

    wind = d.get("wind_speed_10m_max", None)
    if wind is None:
        wind = d.get("windspeed_10m_max", None)
    wind = _pad_list(wind or [], n)

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(time, errors="coerce"),
            "precip_mm": pd.to_numeric(precip, errors="coerce"),
            "tmax_c": pd.to_numeric(tmax, errors="coerce"),
            "tmin_c": pd.to_numeric(tmin, errors="coerce"),
            "wind_kmh": pd.to_numeric(wind, errors="coerce"),
        }
    )
    df = df.dropna(subset=["date"])
    if df.empty:
        return df
    df["tmean_c"] = (df["tmax_c"] + df["tmin_c"]) / 2.0
    return df.sort_values("date")


def plot_forecast(df: pd.DataFrame, title: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "🌧️ Précipitations (mm/j)",
            "🌡️ Températures (°C)",
            "💨 Vent max (km/h)",
            "📦 Distribution (Tmax)",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.10,
    )

    fig.add_trace(go.Bar(x=df["date"], y=df["precip_mm"], name="Précip.", showlegend=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["date"], y=df["tmax_c"], name="Tmax", mode="lines", showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=df["date"], y=df["tmin_c"], name="Tmin", mode="lines", fill="tonexty", showlegend=False), row=1, col=2)

    fig.add_trace(go.Scatter(x=df["date"], y=df["wind_kmh"], name="Vent", mode="lines", fill="tozeroy", showlegend=False), row=2, col=1)

    fig.add_trace(go.Box(y=df["tmax_c"], name="Tmax", showlegend=False), row=2, col=2)

    fig.update_xaxes(rangeslider=dict(visible=True), row=1, col=1)
    fig.update_xaxes(rangeslider=dict(visible=True), row=1, col=2)

    fig.update_layout(
        title=title,
        height=720,
        hovermode="x unified",
        template="plotly_white",
        margin=dict(t=80, b=30, l=25, r=25),
    )
    return fig


def compute_flood_level(df: pd.DataFrame, rules: Dict[str, Any]) -> Tuple[str, str]:
    if df.empty or "precip_mm" not in df.columns:
        return "green", "Aucune donnée précipitation disponible."

    max_1d = float(df["precip_mm"].max(skipna=True) or 0.0)
    day = "N/A"
    if df["precip_mm"].notna().any():
        row = df.loc[df["precip_mm"].idxmax()]
        if pd.notna(row["date"]):
            day = str(pd.to_datetime(row["date"]).date())

    thr = rules["flood"]
    if max_1d >= thr["red"]:
        level = "red"
    elif max_1d >= thr["orange"]:
        level = "orange"
    elif max_1d >= thr["yellow"]:
        level = "yellow"
    else:
        level = "green"

    return level, f"Max précipitations prévues: {max_1d:.1f} mm/j (jour: {day})."


def compute_drought_level(df: pd.DataFrame, rules: Dict[str, Any]) -> Tuple[str, str]:
    if df.empty or "precip_mm" not in df.columns:
        return "green", "Aucune donnée précipitation disponible."

    pr = df["precip_mm"].fillna(0.0).tolist()
    dates = df["date"].tolist()

    max_streak = 0
    cur = 0
    start_best: Optional[datetime] = None
    start_cur: Optional[datetime] = None

    for i, p in enumerate(pr):
        if float(p) < 1.0:
            if cur == 0:
                start_cur = pd.to_datetime(dates[i]).to_pydatetime() if pd.notna(dates[i]) else None
            cur += 1
            if cur > max_streak:
                max_streak = cur
                start_best = start_cur
        else:
            cur = 0
            start_cur = None

    thr = rules["drought"]
    if max_streak >= thr["red"]:
        level = "red"
    elif max_streak >= thr["orange"]:
        level = "orange"
    elif max_streak >= thr["yellow"]:
        level = "yellow"
    else:
        level = "green"

    avg_tmax = float(df["tmax_c"].mean(skipna=True) or 0.0)
    start_txt = start_best.date().isoformat() if start_best else "N/A"
    return level, f"Série sèche prévue: {max_streak} jour(s) (début: {start_txt}), Tmax moyenne: {avg_tmax:.1f}°C."


DB_RISK_ALERTS = safe_table_exists("risk_alerts")
DB_RECIP = safe_table_exists("alert_recipients")
DB_ACK = safe_table_exists("alert_ack")
DB_OUTBOX = safe_table_exists("notification_outbox")


def ensure_session_state():
    st.session_state.setdefault("m3_rules", default_rules())
    st.session_state.setdefault("m3_alerts", [])
    st.session_state.setdefault("m3_recipients", [])
    st.session_state.setdefault("m3_ack", [])
    st.session_state.setdefault("m3_outbox", [])
    st.session_state.setdefault("m3_horizon", "10 jours")
    st.session_state.setdefault("m3_region", "Toutes")
    st.session_state.setdefault("m3_localite", "me")


ensure_session_state()


def load_alerts_demo() -> List[Dict[str, Any]]:
    return st.session_state["m3_alerts"]


def save_alert_demo(a: Dict[str, Any]) -> None:
    st.session_state["m3_alerts"].insert(0, a)


def try_save_risk_alerts(a: Dict[str, Any]) -> bool:
    if not DB_RISK_ALERTS:
        return False

    payload = {
        "risk": a.get("risk_type"),
        "severity": int(SEVERITY_FROM_LEVEL.get(a.get("level", "green"), 1)),
        "title": a.get("title", ""),
        "message": a.get("message", ""),
        "admin_code": a.get("admin_code"),
        "sector_code": a.get("sector_code"),
        "project_code": a.get("project_code"),
        "start_at": a.get("issued_at"),
        "end_at": a.get("expires_at"),
        "status": "active",
    }
    return safe_insert("risk_alerts", payload)


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


def load_recipients() -> List[Dict[str, Any]]:
    if DB_RECIP:
        return safe_select("alert_recipients", order=("created_at", True), limit=1000)
    return st.session_state["m3_recipients"]


def save_recipient(r: Dict[str, Any]) -> None:
    if DB_RECIP and safe_insert("alert_recipients", r):
        return
    st.session_state["m3_recipients"].insert(0, r)


def load_ack() -> List[Dict[str, Any]]:
    if DB_ACK:
        return safe_select("alert_ack", order=("acked_at", True), limit=2000)
    return st.session_state["m3_ack"]


def add_ack(ack: Dict[str, Any]) -> None:
    if DB_ACK and safe_insert("alert_ack", ack):
        return
    st.session_state["m3_ack"].insert(0, ack)


def push_outbox(item: Dict[str, Any]) -> None:
    if DB_OUTBOX and safe_insert("notification_outbox", item):
        return
    st.session_state["m3_outbox"].insert(0, item)


# -----------------------------
# Sidebar: Région + Localité + Horizon + Filtres
# -----------------------------
with st.sidebar:
    st.markdown("### 📍 Localisation & Prévisions")

    regions: List[str] = ["Toutes"]
    if not stations_df.empty and "region" in stations_df.columns:
        uniq = sorted({str(x) for x in stations_df["region"].dropna().tolist() if str(x).strip()})
        regions += uniq

    region_sel = st.selectbox("Région", options=regions, key="m3_region")

    loc_ids: List[str] = ["me"]
    loc_labels: Dict[str, str] = {"me": f"📍 Ma position — {user_loc.get('region','') or ''}".strip()}
    loc_map: Dict[str, Dict[str, Any]] = {
        "me": {
            "id": None,
            "station_id": None,
            "lat": user_loc["lat"],
            "lon": user_loc["lon"],
            "localite": user_loc.get("localite", "Ma position"),
            "region": user_loc.get("region", ""),
            "admin_code": None,
            "accuracy": user_loc.get("accuracy"),
        }
    }

    if not stations_df.empty:
        df_f = stations_df.copy()
        if region_sel != "Toutes" and "region" in df_f.columns:
            df_f = df_f[df_f["region"].astype(str) == str(region_sel)]
        df_f = df_f.sort_values(["localite"])

        for _, r in df_f.iterrows():
            sid = str(r["id"])
            label = f"🏷️ {r['localite']} — {r.get('region','') or '—'}"
            loc_ids.append(sid)
            loc_labels[sid] = label
            loc_map[sid] = {
                "id": sid,
                "station_id": sid,
                "lat": float(r["latitude"]),
                "lon": float(r["longitude"]),
                "localite": str(r["localite"]),
                "region": str(r.get("region", "")),
                "admin_code": (str(r.get("admin_code")) if r.get("admin_code") else None),
                "accuracy": None,
            }

    if st.session_state.get("m3_localite") not in loc_ids:
        st.session_state["m3_localite"] = "me"

    loc_sel = st.selectbox(
        "Localité",
        options=loc_ids,
        format_func=lambda k: loc_labels.get(k, k),
        key="m3_localite",
    )
    selected_loc = loc_map[loc_sel]

    horizon_label = st.selectbox("Échelle de prévision", options=list(HORIZON_CHOICES.keys()), key="m3_horizon")

    st.markdown("---")
    st.markdown("### Filtres alertes")
    risk_filter = st.multiselect(
        "Types de risque",
        options=RISK_TYPES,
        default=["flood", "drought"],
        format_func=lambda x: f"{'🌊' if x=='flood' else '🌵'} {RISK_LABEL[x]}",
    )
    level_filter = st.multiselect(
        "Niveaux",
        options=["green", "yellow", "orange", "red"],
        default=["yellow", "orange", "red"],
        format_func=lambda x: f"{'🟢' if x=='green' else '🟡' if x=='yellow' else '🟠' if x=='orange' else '🔴'} {LEVEL_LABEL[x]}",
    )
    status_filter = st.multiselect("Statut", options=["active", "expired", "cancelled"], default=["active"])


# -----------------------------
# Chargement prévisions
# -----------------------------
hconf = HORIZON_CHOICES[horizon_label]
H_DAYS = int(hconf["days"])
KIND = str(hconf["kind"])

with st.spinner("📡 Chargement des prévisions (Open-Meteo)…"):
    raw_fc, fc_source = fetch_daily_any(float(selected_loc["lat"]), float(selected_loc["lon"]), H_DAYS, KIND)

df_fc = daily_to_df(raw_fc)

with st.expander("🧪 Debug payload Open-Meteo", expanded=False):
    st.caption("Utile si vous voyez des séries de tailles différentes.")
    d = (raw_fc or {}).get("daily", {}) or {}
    st.write({k: (len(v) if isinstance(v, list) else type(v).__name__) for k, v in d.items()})
    if st.checkbox("Afficher JSON complet", value=False):
        st.json(raw_fc)

if df_fc.empty:
    st.error("❌ Impossible de charger les prévisions pour cette localisation.")
    st.stop()

if KIND == "forecast" and H_DAYS > 16:
    st.markdown(
        f"""
        <div class="hint">
          <b>Limitation:</b> horizon demandé <b>{H_DAYS} jours</b>, mais la source utilisée est <b>Forecast</b> (max <b>16 jours</b>).
          Pour 20/30 jours, 3/6 mois, utilisez <b>Seasonal API</b>. Pour 1 an, utilisez <b>Climate API</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# KPIs
# -----------------------------
alerts = load_alerts_demo()
recipients = load_recipients()
acks = load_ack()

active_alerts = [a for a in alerts if is_active(a)]
critical_active = [a for a in active_alerts if a.get("level") == "red"]

ack_df = pd.DataFrame(acks) if acks else pd.DataFrame(columns=["alert_id"])
ack_rate = 0.0
if active_alerts:
    acked_ids = set(ack_df["alert_id"].astype(str).tolist()) if not ack_df.empty else set()
    acked_alerts = sum(1 for a in active_alerts if str(a.get("alert_id")) in acked_ids)
    ack_rate = (acked_alerts / len(active_alerts)) * 100.0

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""<div class="metric-box"><div class="metric-value">{len(active_alerts)}</div><div class="metric-label">Alertes actives</div></div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="metric-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);"><div class="metric-value">{len(critical_active)}</div><div class="metric-label">Actives critiques</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="metric-box" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);"><div class="metric-value">{len(recipients)}</div><div class="metric-label">Destinataires</div></div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="metric-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);"><div class="metric-value">{len(acks)}</div><div class="metric-label">ACK cumulés</div></div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="metric-box" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color:#333;"><div class="metric-value">{ack_rate:.0f}%</div><div class="metric-label">Taux ACK (actives)</div></div>""", unsafe_allow_html=True)

st.markdown("")

# -----------------------------
# Tabs
# -----------------------------
tab_loc, tab_detect, tab_alerts, tab_diff, tab_ack, tab_rules = st.tabs(
    [
        "📍 Localisation & Prévisions",
        "🧠 Détection & Génération",
        "🚨 Alertes (actives & historique)",
        "📣 Diffusion & Destinataires",
        "✅ Accusés de réception (ACK)",
        "⚙️ Règles & Seuils",
    ]
)

# =========================================================
# TAB 0
# =========================================================
with tab_loc:
    st.markdown("#### Localisation sélectionnée")
    cA, cB, cC = st.columns([2.0, 2.0, 4.0])
    with cA:
        st.metric("📍 Localité", str(selected_loc.get("localite", "Ma position")))
    with cB:
        st.metric("🗺️ Région", str(selected_loc.get("region", "")) or "—")
    with cC:
        st.metric("🧭 Coordonnées", format_coordinates(float(selected_loc["lat"]), float(selected_loc["lon"])))
        if selected_loc.get("accuracy"):
            st.caption(f"Précision : ±{float(selected_loc['accuracy']):.0f} m")

    st.markdown("---")
    st.markdown(f"#### Prévisions — {horizon_label} (source: {fc_source})")
    fig = plot_forecast(df_fc, f"Prévisions {horizon_label} — {selected_loc.get('localite','Localité')}")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 Données (table)", expanded=False):
        st.dataframe(
            df_fc[["date", "precip_mm", "tmax_c", "tmin_c", "tmean_c", "wind_kmh"]].copy(),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Max pluie (mm/j)", f"{float(df_fc['precip_mm'].max(skipna=True) or 0):.1f}")
    with s2:
        st.metric("Max Tmax (°C)", f"{float(df_fc['tmax_c'].max(skipna=True) or 0):.1f}")
    with s3:
        st.metric("Min Tmin (°C)", f"{float(df_fc['tmin_c'].min(skipna=True) or 0):.1f}")
    with s4:
        st.metric("Max vent (km/h)", f"{float(df_fc['wind_kmh'].max(skipna=True) or 0):.1f}")

# =========================================================
# TAB 1
# =========================================================
with tab_detect:
    st.markdown("#### Détection automatique (sur l’horizon sélectionné)")
    st.caption("V1: seuils simples (pluie journalière et séries de jours secs). Ajustez les seuils dans l’onglet Règles & Seuils.")

    rules = st.session_state["m3_rules"]
    flood_level, flood_summary = compute_flood_level(df_fc, rules)
    drought_level, drought_summary = compute_drought_level(df_fc, rules)

    d1, d2 = st.columns(2)
    with d1:
        st.markdown(
            f"""
            <div class="alert-card {flood_level}">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                <div>
                  <div style="font-weight:800; font-size:1.1rem;">🌊 Inondation — {selected_loc.get('localite','')}</div>
                  <div style="opacity:.8;">Région: <b>{selected_loc.get('region','')}</b> • Horizon: <b>{horizon_label}</b></div>
                </div>
                <div class="pill {flood_level}">{LEVEL_LABEL.get(flood_level, flood_level)}</div>
              </div>
              <div style="margin-top:.65rem; line-height:1.6;">
                <div><b>Signal :</b> {flood_summary}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d2:
        st.markdown(
            f"""
            <div class="alert-card {drought_level}">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                <div>
                  <div style="font-weight:800; font-size:1.1rem;">🌵 Sécheresse — {selected_loc.get('localite','')}</div>
                  <div style="opacity:.8;">Région: <b>{selected_loc.get('region','')}</b> • Horizon: <b>{horizon_label}</b></div>
                </div>
                <div class="pill {drought_level}">{LEVEL_LABEL.get(drought_level, drought_level)}</div>
              </div>
              <div style="margin-top:.65rem; line-height:1.6;">
                <div><b>Signal :</b> {drought_summary}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    left, right = st.columns([2, 1])
    with left:
        st.markdown(
            f"""
            <div class="soft">
              <b>Localité:</b> {selected_loc.get('localite','Ma position')} •
              <b>Coord:</b> {format_coordinates(float(selected_loc["lat"]), float(selected_loc["lon"]))} •
              <b>Horizon:</b> {horizon_label} •
              <b>Source:</b> {fc_source}
              <br><span style="opacity:.75;">Changez Région/Localité/Horizon dans la barre latérale.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.caption("Actions")
        create_even_green = st.checkbox("Créer aussi VERT (debug)", value=False, key="m3_create_green_debug")
        gen_flood = st.button("🌊 Générer alerte Inondation", use_container_width=True)
        gen_drought = st.button("🌵 Générer alerte Sécheresse", use_container_width=True)
        gen_both = st.button("⚡ Générer les deux", type="primary", use_container_width=True)

    def build_demo_alert(risk_type: str, level: str, summary: str) -> Optional[Dict[str, Any]]:
        if level == "green" and not create_even_green:
            return None

        issued = now()
        validity = timedelta(days=2) if risk_type == "flood" else timedelta(days=7)
        exp = issued + validity

        zone = str(selected_loc.get("localite", "Ma position"))
        reg = str(selected_loc.get("region", ""))

        title = f"Alerte {RISK_LABEL.get(risk_type, risk_type)} {LEVEL_LABEL.get(level, level)} — {zone}"
        message = f"{summary}\nLocalité: {zone} | Région: {reg} | Horizon: {horizon_label} | Source: {fc_source}"

        a = {
            "alert_id": str(uuid.uuid4()),
            "risk_type": risk_type,
            "level": level,
            "zone_name": zone,
            "region": reg,
            "station_id": selected_loc.get("station_id"),
            "admin_code": selected_loc.get("admin_code"),
            "lat": float(selected_loc["lat"]),
            "lon": float(selected_loc["lon"]),
            "signal_summary": summary,
            "issued_at": issued.isoformat(),
            "expires_at": exp.isoformat(),
            "status": "active",
            "channels": ["web"],
            "created_by": st.session_state.get("user_email", ""),
            "context": {"horizon_label": horizon_label, "source": fc_source},
            "title": title,
            "message": message,
            "sector_code": None,
            "project_code": None,
        }
        return a

    if gen_flood or gen_drought or gen_both:
        created: List[Dict[str, Any]] = []

        if gen_flood or gen_both:
            a = build_demo_alert("flood", flood_level, flood_summary)
            if a:
                if not try_save_risk_alerts(a):
                    save_alert_demo(a)
                created.append(a)

        if gen_drought or gen_both:
            a = build_demo_alert("drought", drought_level, drought_summary)
            if a:
                if not try_save_risk_alerts(a):
                    save_alert_demo(a)
                created.append(a)

        if created:
            st.success(f"✅ {len(created)} alerte(s) créée(s).")
            st.rerun()
        else:
            st.info("Aucune alerte générée (niveaux VERTS, non créés par défaut).")

# =========================================================
# TAB 2
# =========================================================
with tab_alerts:
    st.markdown("#### Alertes filtrées (actives & historique)")
    alerts = load_alerts_demo()

    df_alerts = pd.DataFrame(alerts) if alerts else pd.DataFrame(
        columns=["alert_id", "risk_type", "level", "zone_name", "region", "issued_at", "expires_at", "status"]
    )

    if df_alerts.empty:
        st.info("Aucune alerte (utilisez l’onglet Détection & Génération).")
    else:
        df_alerts["risk_type"] = df_alerts["risk_type"].astype(str)
        df_alerts["level"] = df_alerts["level"].astype(str)
        df_alerts["status"] = df_alerts["status"].astype(str)

        df_f = df_alerts[
            df_alerts["risk_type"].isin(risk_filter)
            & df_alerts["level"].isin(level_filter + ["green"])
            & df_alerts["status"].isin(status_filter)
        ].copy()

        df_f["issued_at_dt"] = pd.to_datetime(df_f["issued_at"], errors="coerce")
        df_f = df_f.sort_values("issued_at_dt", ascending=False)

        if df_f.empty:
            st.info("Aucune alerte pour les filtres sélectionnés.")
        else:
            for _, a in df_f.head(120).iterrows():
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

            with st.expander("📤 Export", expanded=False):
                st.download_button(
                    "Télécharger CSV (alertes filtrées)",
                    data=df_f.drop(columns=["issued_at_dt"]).to_csv(index=False).encode("utf-8"),
                    file_name="module3_alertes.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

# =========================================================
# TAB 3
# =========================================================
with tab_diff:
    st.markdown("#### Destinataires & diffusion (simulation / outbox)")
    st.caption("L’intégration SMS/Email/API sera branchée ensuite sur un service dédié. En attendant: outbox en session_state.")

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
            r_channels = st.multiselect("Canaux", options=["email", "sms", "web", "api"], default=["web"], key="m3_r_channels")

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
    df_r = pd.DataFrame(recipients) if recipients else pd.DataFrame(columns=["name", "organization", "role", "zone", "channels"])
    st.markdown("---")
    st.markdown("#### Liste de diffusion")
    st.dataframe(df_r, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Diffuser une alerte (simulation / outbox)")
    active_alerts = [a for a in load_alerts_demo() if is_active(a)]
    if not active_alerts:
        st.info("Aucune alerte active à diffuser. Créez une alerte depuis l’onglet Détection & Génération.")
    else:
        alert_labels = []
        for a in active_alerts:
            icon = "🌊" if a.get("risk_type") == "flood" else "🌵"
            alert_labels.append(f"{icon} {a.get('zone_name','')} — {LEVEL_LABEL.get(a.get('level','green'))}")

        selected = st.selectbox("Alerte active", options=list(range(len(active_alerts))), format_func=lambda i: alert_labels[i], key="m3_alert_to_send")
        a = active_alerts[int(selected)]

        send_channels = st.multiselect("Canaux de diffusion", options=["web", "email", "sms", "api"], default=["web"], key="m3_send_channels")
        scope = st.selectbox("Cible", options=["Tous", "Filtrer par zone/région"], key="m3_scope")

        zone_key = ""
        if scope == "Filtrer par zone/région":
            zone_key = st.text_input("Mot-clé zone/région (ex: Nord, Extrême-Nord…)", key="m3_scope_key")

        selected_recipients = recipients
        if scope == "Filtrer par zone/région" and zone_key.strip():
            kz = zone_key.strip().lower()
            selected_recipients = [
                r for r in recipients
                if kz in str(r.get("zone", "")).lower() or kz in str(r.get("organization", "")).lower()
            ]

        st.caption(f"Destinataires ciblés: {len(selected_recipients)}")

        if st.button("📣 Lancer diffusion (simulation)", type="primary", use_container_width=True):
            if not selected_recipients:
                st.warning("Aucun destinataire ciblé.")
            else:
                for r in selected_recipients:
                    item = {
                        "outbox_id": str(uuid.uuid4()),
                        "alert_id": str(a.get("alert_id")),
                        "recipient_id": str(r.get("recipient_id", "")),
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

    if st.session_state.get("m3_outbox"):
        with st.expander("📦 Outbox (simulation)", expanded=False):
            st.dataframe(pd.DataFrame(st.session_state["m3_outbox"]), use_container_width=True, hide_index=True)

# =========================================================
# TAB 4
# =========================================================
with tab_ack:
    st.markdown("#### Accusés de réception (ACK) — suivi opérationnel")
    st.caption("Confirme que l’information a été reçue/lue/traitée (simulation).")

    alerts_all = load_alerts_demo()
    if not alerts_all:
        st.info("Aucune alerte disponible.")
    else:
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
        st.dataframe(pd.DataFrame(acks), use_container_width=True, hide_index=True)

# =========================================================
# TAB 5
# =========================================================
with tab_rules:
    st.markdown("#### Règles & Seuils (V1) — configurables")
    st.caption("Seuils simples. Les seuils avancés (SPI/SPEI, percentiles, multi-indicateurs) iront dans Module 8.")

    rules = st.session_state["m3_rules"]

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("##### 🌊 Inondation — seuils mm/j")
        y = st.number_input("JAUNE (≥)", min_value=0.0, value=float(rules["flood"]["yellow"]), step=5.0, key="m3_f_y")
        o = st.number_input("ORANGE (≥)", min_value=0.0, value=float(rules["flood"]["orange"]), step=5.0, key="m3_f_o")
        rv = st.number_input("ROUGE (≥)", min_value=0.0, value=float(rules["flood"]["red"]), step=5.0, key="m3_f_r")
        st.caption("Référence: precipitation_sum (mm/j).")

    with r2:
        st.markdown("##### 🌵 Sécheresse — série de jours secs (< 1 mm)")
        y2 = st.number_input("JAUNE (≥ jours)", min_value=0, value=int(rules["drought"]["yellow"]), step=1, key="m3_d_y")
        o2 = st.number_input("ORANGE (≥ jours)", min_value=0, value=int(rules["drought"]["orange"]), step=1, key="m3_d_o")
        r2v = st.number_input("ROUGE (≥ jours)", min_value=0, value=int(rules["drought"]["red"]), step=1, key="m3_d_r")
        st.caption("Référence: séquence de jours secs (precip < 1 mm).")

    c_save, c_reset = st.columns([1, 1])
    with c_save:
        if st.button("💾 Enregistrer règles", type="primary", use_container_width=True):
            if not (y <= o <= rv and y2 <= o2 <= r2v):
                st.error("Les seuils doivent être croissants (JAUNE ≤ ORANGE ≤ ROUGE).")
            else:
                st.session_state["m3_rules"] = {
                    "flood": {"yellow": float(y), "orange": float(o), "red": float(rv)},
                    "drought": {"yellow": int(y2), "orange": int(o2), "red": int(r2v)},
                }
                st.success("✅ Règles mises à jour.")
                st.rerun()

    with c_reset:
        if st.button("↩️ Réinitialiser (défaut)", use_container_width=True):
            st.session_state["m3_rules"] = default_rules()
            st.success("✅ Règles réinitialisées.")
            st.rerun()

st.markdown("---")
st.caption(
    f"Module 3 — Alertes précoces | ONACC (Streamlit) | "
    f"MàJ: {now().strftime('%d/%m/%Y %H:%M')} | "
    f"Tables: risk_alerts={DB_RISK_ALERTS}, recipients={DB_RECIP}, ack={DB_ACK}, outbox={DB_OUTBOX} | "
    f"Région={st.session_state.get('m3_region')} | Localité={st.session_state.get('m3_localite')} | "
    f"Horizon={horizon_label} ({H_DAYS}j) | Source={fc_source}"
)
