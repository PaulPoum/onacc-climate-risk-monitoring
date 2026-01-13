# core/open_meteo.py
from __future__ import annotations

from dataclasses import dataclass
import requests

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
SEASONAL_API = "https://seasonal-api.open-meteo.com/v1/seasonal"

DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,pressure_msl"


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
        return HorizonPlan("D20", SEASONAL_API, 20, "open-meteo-seasonal-ec46")
    if h == "D30":
        return HorizonPlan("D30", SEASONAL_API, 30, "open-meteo-seasonal-ec46")
    if h == "M6":
        return HorizonPlan("M6", SEASONAL_API, 180, "open-meteo-seasonal-seas5")
    if h in ("Y1", "A1", "AN1", "1AN"):
        raise ValueError(
            "Horizon 1 an (Y1) non supporté nativement par Open-Meteo Seasonal (7 mois max)."
        )
    raise ValueError(f"Horizon inconnu: {h}")


def fetch_daily_forecast(lat: float, lon: float, days: int, seasonal: bool = False) -> dict:
    url = SEASONAL_API if seasonal else FORECAST_API

    # Forecast API: max 16 jours (doc) :contentReference[oaicite:4]{index=4}
    if not seasonal and days > 16:
        raise ValueError("Forecast API limitée à 16 jours. Utiliser seasonal=True pour >16 jours.")

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "forecast_days": int(days),
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=45)
    r.raise_for_status()
    return r.json()


def fetch_hourly_nowcast(lat: float, lon: float, past_days: int = 3, forecast_days: int = 1, timezone: str = "UTC") -> dict:
    """
    Veille quasi temps réel:
    - past_days: historique récent (archived forecasts)
    - forecast_days: court terme
    Forecast API supporte past_days + forecast_days (doc). :contentReference[oaicite:5]{index=5}
    """
    if forecast_days > 16:
        raise ValueError("forecast_days > 16 non supporté sur forecast API.")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY_VARS,
        "past_days": int(past_days),
        "forecast_days": int(forecast_days),
        "timezone": timezone,
    }
    r = requests.get(FORECAST_API, params=params, timeout=45)
    r.raise_for_status()
    return r.json()
