# core/open_meteo.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import requests

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
SEASONAL_API = "https://seasonal-api.open-meteo.com/v1/seasonal"
CLIMATE_API = "https://climate-api.open-meteo.com/v1/climate"

# Variables cohérentes avec la Climate API (et généralement compatibles forecast/seasonal)
DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,pressure_msl"

# Limites pratiques
FORECAST_MAX_DAYS = 16
SEASONAL_MAX_DAYS = 215  # ~7 mois (ordre de grandeur, selon produits Open-Meteo)


@dataclass(frozen=True)
class HorizonPlan:
    horizon: str
    api: str
    days: int
    source: str


def horizon_plan(h: str) -> HorizonPlan:
    h = h.upper().strip()
    if h == "D10":
        return HorizonPlan("D10", FORECAST_API, 10, "open-meteo-forecast")
    if h == "D20":
        return HorizonPlan("D20", SEASONAL_API, 20, "open-meteo-seasonal")
    if h == "D30":
        return HorizonPlan("D30", SEASONAL_API, 30, "open-meteo-seasonal")
    if h == "M3":
        return HorizonPlan("M3", SEASONAL_API, 90, "open-meteo-seasonal")
    if h == "M6":
        return HorizonPlan("M6", SEASONAL_API, 180, "open-meteo-seasonal")
    if h in ("Y1", "A1", "AN1", "1AN"):
        return HorizonPlan("Y1", CLIMATE_API, 365, "open-meteo-climate")
    raise ValueError(f"Horizon inconnu: {h}")


def _raise_http_error(r: requests.Response, context: str) -> None:
    """
    Donne un message exploitable dans Streamlit au lieu d'un HTTPError opaque.
    """
    try:
        body = (r.text or "")[:800]
    except Exception:
        body = "<unreadable body>"
    raise requests.HTTPError(
        f"{context} | HTTP {r.status_code} | url={r.url} | body={body}"
    )


def fetch_daily_forecast(lat: float, lon: float, days: int, seasonal: bool = False) -> dict:
    """
    Court/moyen terme:
    - Forecast API (<=16 jours)
    - Seasonal API (<=~7 mois) quand seasonal=True
    """
    days_i = int(days)

    if not seasonal:
        if days_i > FORECAST_MAX_DAYS:
            raise ValueError(
                f"Forecast API limitée à {FORECAST_MAX_DAYS} jours. "
                f"Demandé={days_i}. Utiliser seasonal=True ou Climate API."
            )
        url = FORECAST_API
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": DAILY_VARS,
            "forecast_days": days_i,
            "timezone": "auto",
        }
    else:
        if days_i > SEASONAL_MAX_DAYS:
            raise ValueError(
                f"Seasonal API ne couvre pas {days_i} jours (≈ max {SEASONAL_MAX_DAYS}). "
                f"Pour 1 an, utilisez Climate API (/v1/climate)."
            )
        url = SEASONAL_API
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": DAILY_VARS,
            "forecast_days": days_i,
            "timezone": "auto",
        }

    r = requests.get(url, params=params, timeout=45)
    if not r.ok:
        _raise_http_error(r, "Open-Meteo daily fetch failed")
    return r.json()


def fetch_climate_daily(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    model: str = "MRI_AGCM3_2_S",
    daily_vars: str = DAILY_VARS,
    timeformat: str = "iso8601",
    apikey: Optional[str] = None,
) -> dict:
    """
    Long terme (Climate API):
    /v1/climate nécessite start_date, end_date, models et daily. :contentReference[oaicite:1]{index=1}
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "models": model,
        "daily": daily_vars,
        "timeformat": timeformat,
    }
    if apikey:
        params["apikey"] = apikey

    r = requests.get(CLIMATE_API, params=params, timeout=60)
    if not r.ok:
        _raise_http_error(r, "Open-Meteo climate fetch failed")
    return r.json()


def fetch_hourly_nowcast(
    lat: float,
    lon: float,
    past_days: int = 3,
    forecast_days: int = 1,
    timezone: str = "UTC",
) -> dict:
    if int(forecast_days) > FORECAST_MAX_DAYS:
        raise ValueError(f"forecast_days > {FORECAST_MAX_DAYS} non supporté sur forecast API.")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY_VARS,
        "past_days": int(past_days),
        "forecast_days": int(forecast_days),
        "timezone": timezone,
    }
    r = requests.get(FORECAST_API, params=params, timeout=45)
    if not r.ok:
        _raise_http_error(r, "Open-Meteo hourly fetch failed")
    return r.json()
