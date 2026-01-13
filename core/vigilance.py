# core/vigilance.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.supabase_client import get_supabase
from core.open_meteo import OpenMeteoClient


@dataclass
class Station:
    id: str
    localite: str
    latitude: float
    longitude: float
    admin_code: Optional[str]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_stations() -> List[Station]:
    sb = get_supabase()
    res = sb.table("mnocc_stations").select("id,localite,latitude,longitude,admin_code").execute()
    rows = res.data or []
    return [
        Station(
            id=r["id"],
            localite=r["localite"],
            latitude=float(r["latitude"]),
            longitude=float(r["longitude"]),
            admin_code=r.get("admin_code"),
        )
        for r in rows
    ]


def heat_index_c(temp_c: float, rh_pct: float) -> float:
    """
    Heat Index approximation (NOAA-like) in Celsius.
    Valid mainly for T>=27C and RH>=40; otherwise returns temp.
    """
    if temp_c is None or rh_pct is None:
        return None
    if temp_c < 27 or rh_pct < 40:
        return temp_c
    # convert to Fahrenheit
    T = temp_c * 9/5 + 32
    R = rh_pct
    HI = (
        -42.379 + 2.04901523*T + 10.14333127*R
        - 0.22475541*T*R - 0.00683783*T*T
        - 0.05481717*R*R + 0.00122874*T*T*R
        + 0.00085282*T*R*R - 0.00000199*T*T*R*R
    )
    # back to Celsius
    return (HI - 32) * 5/9


def flood_score(prcp_24h: float, prcp_72h: float, rx1day: Optional[float]) -> int:
    score = 0

    # 24h
    if prcp_24h is not None:
        if prcp_24h >= 100: score += 40
        elif prcp_24h >= 50: score += 30
        elif prcp_24h >= 20: score += 15

    # 72h
    if prcp_72h is not None:
        if prcp_72h >= 200: score += 40
        elif prcp_72h >= 120: score += 30
        elif prcp_72h >= 50: score += 15

    # rx1day / max hourly proxy
    if rx1day is not None:
        if rx1day >= 40: score += 20
        elif rx1day >= 20: score += 10

    return int(max(0, min(100, score)))


def drought_score(cdd: float, prcp30_ratio: Optional[float], tmax_3d: Optional[float], hi_max: Optional[float]) -> int:
    score = 0

    # CDD
    if cdd is not None:
        if cdd > 20: score += 50
        elif cdd > 10: score += 35
        elif cdd >= 5: score += 15

    # 30d ratio (current / median proxy)
    if prcp30_ratio is not None:
        if prcp30_ratio < 0.5: score += 25
        elif prcp30_ratio < 0.7: score += 18
        elif prcp30_ratio < 0.9: score += 10

    # Heat / Tmax
    x = hi_max if hi_max is not None else tmax_3d
    if x is not None:
        if x > 38: score += 25
        elif x >= 35: score += 18
        elif x >= 32: score += 10

    return int(max(0, min(100, score)))


def upsert_observations(obs_rows: List[Dict[str, Any]]) -> None:
    """
    Insert rows into meteo_observations (idempotent via unique index).
    In Supabase python client, upsert requires specifying 'on_conflict' keys.
    """
    if not obs_rows:
        return
    sb = get_supabase()
    sb.table("meteo_observations").upsert(obs_rows, on_conflict="station_id,observed_at").execute()


def insert_risk_indicators(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    sb = get_supabase()
    sb.table("risk_indicators").insert(rows).execute()


def aggregate_admin_daily(df_obs: pd.DataFrame) -> pd.DataFrame:
    """
    Expect df_obs columns: admin_code, observed_at, prcp_mm, temp_c, rh_pct, wind_ms
    Build daily admin aggregates.
    """
    if df_obs.empty:
        return df_obs

    df = df_obs.copy()
    df["date"] = pd.to_datetime(df["observed_at"], utc=True).dt.date
    # daily sums/means
    g = df.groupby(["admin_code", "date"], dropna=False)
    out = g.agg(
        prcp_sum=("prcp_mm", "sum"),
        temp_mean=("temp_c", "mean"),
        temp_max=("temp_c", "max"),
        rh_mean=("rh_pct", "mean"),
        wind_mean=("wind_ms", "mean"),
        rx1day=("prcp_mm", "max"),  # proxy if hourly prcp exists
    ).reset_index()

    return out


def compute_cdd_from_daily(admin_daily: pd.DataFrame, dry_threshold_mm: float = 1.0) -> pd.DataFrame:
    """
    Compute consecutive dry days per admin_code from daily prcp_sum.
    """
    if admin_daily.empty:
        return admin_daily

    df = admin_daily.sort_values(["admin_code", "date"]).copy()
    df["is_dry"] = (df["prcp_sum"].fillna(0) < dry_threshold_mm).astype(int)

    cdd_list = []
    for admin_code, g in df.groupby("admin_code"):
        streak = 0
        for _, row in g.iterrows():
            if row["is_dry"] == 1:
                streak += 1
            else:
                streak = 0
        # last streak at end
        last_date = g["date"].max()
        cdd_list.append({"admin_code": admin_code, "date": last_date, "cdd": streak})

    return pd.DataFrame(cdd_list)


def run_vigilance_ingestion(hours_back: int = 72) -> Tuple[int, int]:
    """
    Fetch Open-Meteo hourly data for stations, store in meteo_observations,
    compute daily aggregates and push today's indicators into risk_indicators.
    Returns (n_obs_inserted, n_indicators_inserted).
    """
    stations = [s for s in load_stations() if s.admin_code]
    if not stations:
        return (0, 0)

    client = OpenMeteoClient()
    end = _utc_now()
    start = end - timedelta(hours=hours_back)

    # Fetch hourly data per station (simple loop MVP; can be optimized batch later)
    obs_rows: List[Dict[str, Any]] = []
    for s in stations:
        data = client.fetch_hourly(
            lat=s.latitude,
            lon=s.longitude,
            start=start,
            end=end,
            variables=["precipitation", "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_gusts_10m", "pressure_msl"],
        )
        # data expected as list of dicts with "time" + vars
        for r in data:
            obs_rows.append({
                "station_id": s.id,
                "observed_at": r["time"],
                "prcp_mm": r.get("precipitation"),
                "temp_c": r.get("temperature_2m"),
                "rh_pct": r.get("relative_humidity_2m"),
                "wind_ms": r.get("wind_speed_10m"),
                "wind_gust_ms": r.get("wind_gusts_10m"),
                "pressure_hpa": r.get("pressure_msl"),
                "payload": r,
                "source": "open-meteo",
            })

    upsert_observations(obs_rows)

    # Build aggregates for indicator calculations
    df_obs = pd.DataFrame([
        {
            "station_id": r["station_id"],
            "observed_at": r["observed_at"],
            "prcp_mm": r["prcp_mm"],
            "temp_c": r["temp_c"],
            "rh_pct": r["rh_pct"],
            "wind_ms": r["wind_ms"],
        }
        for r in obs_rows
    ])

    # Map station->admin_code
    st_admin = {s.id: s.admin_code for s in stations}
    df_obs["admin_code"] = df_obs["station_id"].map(st_admin)

    admin_daily = aggregate_admin_daily(df_obs)

    # Compute rolling windows for today
    today = date.today()
    last_1d = admin_daily[admin_daily["date"] == today].copy()

    # 24h and 72h from hourly: approximate by summing prcp over last 24/72 hours per admin
    df_obs["observed_at_dt"] = pd.to_datetime(df_obs["observed_at"], utc=True)
    last24 = df_obs[df_obs["observed_at_dt"] >= (end - timedelta(hours=24))].groupby("admin_code")["prcp_mm"].sum().reset_index(name="prcp_24h")
    last72 = df_obs[df_obs["observed_at_dt"] >= (end - timedelta(hours=72))].groupby("admin_code")["prcp_mm"].sum().reset_index(name="prcp_72h")
    rx1 = df_obs[df_obs["observed_at_dt"] >= (end - timedelta(hours=24))].groupby("admin_code")["prcp_mm"].max().reset_index(name="rx1day")

    # CDD from daily sums (use last 30 days window if available)
    # For MVP we compute streak from what we fetched (limited), later extend via stored history.
    cdd_df = compute_cdd_from_daily(admin_daily)

    # Heat index max last 24h
    tmp = df_obs[df_obs["observed_at_dt"] >= (end - timedelta(hours=24))].copy()
    tmp["hi_c"] = tmp.apply(lambda x: heat_index_c(x["temp_c"], x["rh_pct"]), axis=1)
    hi_max = tmp.groupby("admin_code")["hi_c"].max().reset_index(name="hi_max")

    # tmax_3d from daily temp_max last 3 days
    last3 = admin_daily[admin_daily["date"] >= (today - timedelta(days=2))]
    tmax_3d = last3.groupby("admin_code")["temp_max"].max().reset_index(name="tmax_3d")

    # 30d precip ratio proxy: current 30d / median(30d) not possible without long history.
    # MVP: compute ratio current 7d / median(7d) within fetched window (proxy).
    last7 = admin_daily[admin_daily["date"] >= (today - timedelta(days=6))]
    prcp7 = last7.groupby("admin_code")["prcp_sum"].sum().reset_index(name="prcp7")
    # proxy median baseline = median across admins today is not climatology; keep None for now.
    prcp7["prcp30_ratio"] = None

    # Merge all admin metrics
    df = last24.merge(last72, on="admin_code", how="outer").merge(rx1, on="admin_code", how="outer")
    df = df.merge(cdd_df[["admin_code", "cdd"]], on="admin_code", how="left")
    df = df.merge(hi_max, on="admin_code", how="left").merge(tmax_3d, on="admin_code", how="left").merge(prcp7[["admin_code", "prcp30_ratio"]], on="admin_code", how="left")

    # Build indicator rows
    rows = []
    for _, r in df.iterrows():
        admin_code = r["admin_code"]
        pr24 = None if pd.isna(r.get("prcp_24h")) else float(r["prcp_24h"])
        pr72 = None if pd.isna(r.get("prcp_72h")) else float(r["prcp_72h"])
        rx1v = None if pd.isna(r.get("rx1day")) else float(r["rx1day"])
        cdd = None if pd.isna(r.get("cdd")) else float(r["cdd"])
        hi = None if pd.isna(r.get("hi_max")) else float(r["hi_max"])
        t3 = None if pd.isna(r.get("tmax_3d")) else float(r["tmax_3d"])
        ratio = r.get("prcp30_ratio")

        fscore = flood_score(pr24, pr72, rx1v)
        dscore = drought_score(cdd, ratio, t3, hi)

        def add(code: str, val: Any, unit: str, risk: str):
            rows.append({
                "admin_code": admin_code,
                "risk": risk,
                "indicator_code": code,
                "valid_date": today.isoformat(),
                "value": val,
                "unit": unit,
                "horizon": None,
                "source": "open-meteo",
                "payload": {
                    "prcp_24h": pr24,
                    "prcp_72h": pr72,
                    "rx1day": rx1v,
                    "cdd": cdd,
                    "hi_max": hi,
                    "tmax_3d": t3,
                }
            })

        add("PRCP_24H", pr24, "mm", "flood")
        add("PRCP_72H", pr72, "mm", "flood")
        add("RX1DAY", rx1v, "mm", "flood")
        add("FLOOD_SCORE", fscore, "score", "flood")

        add("CDD", cdd, "days", "drought")
        add("HEAT_INDEX_MAX", hi, "C", "drought")
        add("TMAX_3D", t3, "C", "drought")
        add("DROUGHT_SCORE", dscore, "score", "drought")

    insert_risk_indicators(rows)

    return (len(obs_rows), len(rows))
