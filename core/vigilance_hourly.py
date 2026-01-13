# core/vigilance_hourly.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional

import pandas as pd

from core.open_meteo import fetch_hourly_nowcast
from core.supabase_client import supabase_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _heat_index_c(temp_c: Optional[float], rh_pct: Optional[float]) -> Optional[float]:
    if temp_c is None or rh_pct is None:
        return None
    if temp_c < 27 or rh_pct < 40:
        return temp_c

    # Celsius -> Fahrenheit
    T = temp_c * 9 / 5 + 32
    R = rh_pct
    HI = (
        -42.379
        + 2.04901523 * T
        + 10.14333127 * R
        - 0.22475541 * T * R
        - 0.00683783 * T * T
        - 0.05481717 * R * R
        + 0.00122874 * T * T * R
        + 0.00085282 * T * R * R
        - 0.00000199 * T * T * R * R
    )
    return (HI - 32) * 5 / 9


def _chunks(items: List[Dict[str, Any]], size: int = 500) -> List[List[Dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def ingest_hourly_observations(limit_stations: int = 200, past_days: int = 3, forecast_days: int = 1) -> Dict[str, int]:
    """
    - Lit stations
    - Appelle Open-Meteo hourly
    - Upsert dans meteo_observations_hourly
    Retourne un résumé.
    """
    svc = supabase_service()

    st = svc.table("mnocc_stations").select("id,latitude,longitude,admin_code,region").limit(int(limit_stations)).execute()
    rows = st.data or []
    if not rows:
        return {"stations": 0, "observations": 0, "errors": 0}

    obs_rows: List[Dict[str, Any]] = []
    errors = 0

    for s in rows:
        try:
            data = fetch_hourly_nowcast(
                lat=float(s["latitude"]),
                lon=float(s["longitude"]),
                past_days=past_days,
                forecast_days=forecast_days,
                timezone="UTC",
            )
            hourly = data.get("hourly") or {}
            times = hourly.get("time") or []
            if not times:
                continue

            pr = hourly.get("precipitation") or [None] * len(times)
            tc = hourly.get("temperature_2m") or [None] * len(times)
            rh = hourly.get("relative_humidity_2m") or [None] * len(times)
            ws = hourly.get("wind_speed_10m") or [None] * len(times)
            wg = hourly.get("wind_gusts_10m") or [None] * len(times)
            pm = hourly.get("pressure_msl") or [None] * len(times)

            for i, t in enumerate(times):
                obs_rows.append(
                    {
                        "station_id": s["id"],
                        "observed_at": t,  # ISO string
                        "prcp_mm": pr[i],
                        "temp_c": tc[i],
                        "rh_pct": rh[i],
                        "wind_ms": ws[i],
                        "wind_gust_ms": wg[i],
                        "pressure_hpa": pm[i],
                        "source": "open-meteo",
                        "payload": {
                            "admin_code": s.get("admin_code"),
                            "region": s.get("region"),
                        },
                    }
                )
        except Exception:
            errors += 1

    # Upsert par blocs
    inserted = 0
    for part in _chunks(obs_rows, size=800):
        up = svc.table("meteo_observations_hourly").upsert(part, on_conflict="station_id,observed_at").execute()
        if getattr(up, "error", None):
            errors += 1
        else:
            inserted += len(part)

    return {"stations": len(rows), "observations": inserted, "errors": errors}


def compute_vigilance_indicators_today() -> pd.DataFrame:
    """
    Calcule des indicateurs “veille” à partir des observations stockées :
      - PRCP_24H_ADMIN (mm)
      - PRCP_72H_ADMIN (mm)
      - WIND_GUST_24H_ADMIN (m/s)
      - HEAT_INDEX_MAX_24H_ADMIN (°C)
    Agrégation par admin_code (si manquant, on bascule sur region).
    Retourne un DataFrame prêt à afficher.
    """
    svc = supabase_service()
    now = _utc_now()
    t24 = (now - timedelta(hours=24)).isoformat()
    t72 = (now - timedelta(hours=72)).isoformat()

    # Récupère les observations 72h (on calcule 24h et 72h à partir de là)
    res = (
        svc.table("meteo_observations_hourly")
        .select("station_id,observed_at,prcp_mm,temp_c,rh_pct,wind_gust_ms,payload")
        .gte("observed_at", t72)
        .execute()
    )
    data = res.data or []
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, errors="coerce")
    df["admin_code"] = df["payload"].apply(lambda x: (x or {}).get("admin_code"))
    df["region"] = df["payload"].apply(lambda x: (x or {}).get("region"))

    # clé d’agrégation: admin_code sinon region
    df["area_key"] = df["admin_code"].fillna(df["region"]).fillna("N/A")

    df24 = df[df["observed_at"] >= pd.to_datetime(t24, utc=True)]
    df["heat_index_c"] = df.apply(lambda r: _heat_index_c(r.get("temp_c"), r.get("rh_pct")), axis=1)
    df24["heat_index_c"] = df24.apply(lambda r: _heat_index_c(r.get("temp_c"), r.get("rh_pct")), axis=1)

    out = (
        df.groupby("area_key", as_index=False)
        .agg(
            prcp_72h_mm=("prcp_mm", "sum"),
        )
    )

    out24 = (
        df24.groupby("area_key", as_index=False)
        .agg(
            prcp_24h_mm=("prcp_mm", "sum"),
            wind_gust_24h_ms=("wind_gust_ms", "max"),
            heat_index_max_24h_c=("heat_index_c", "max"),
        )
    )

    out = out.merge(out24, on="area_key", how="left")
    out["date"] = date.today().isoformat()

    # Ordre “zones critiques”
    out = out.sort_values(["prcp_24h_mm", "heat_index_max_24h_c"], ascending=[False, False])
    return out
