# core/vigilance_scores.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.supabase_client import supabase_service


# === Alignement enums ===
# Adaptez si votre enum risk utilise d'autres libellés (ex: "inondation"/"secheresse")
RISK_FLOOD = "flood"
RISK_DROUGHT = "drought"

SOURCE_HOURLY = "open-meteo-hourly"

# Indicator codes (standardisés)
IC_PRCP_24H = "PRCP_24H"
IC_PRCP_72H = "PRCP_72H"
IC_RX1H = "RX1H"  # max pluie horaire (proxy)
IC_HI_MAX_24H = "HEAT_INDEX_MAX_24H"
IC_TMAX_24H = "TMAX_24H"
IC_CDD = "CDD"
IC_FLOOD_SCORE = "FLOOD_SCORE"
IC_DROUGHT_SCORE = "DROUGHT_SCORE"


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


def flood_score(prcp_24h: float, prcp_72h: float, rx1h: Optional[float]) -> int:
    score = 0

    # 24h (0–40)
    if prcp_24h is not None:
        if prcp_24h >= 100: score += 40
        elif prcp_24h >= 50: score += 30
        elif prcp_24h >= 20: score += 15

    # 72h (0–40)
    if prcp_72h is not None:
        if prcp_72h >= 200: score += 40
        elif prcp_72h >= 120: score += 30
        elif prcp_72h >= 50: score += 15

    # max horaire (0–20)
    if rx1h is not None:
        if rx1h >= 40: score += 20
        elif rx1h >= 20: score += 10

    return int(max(0, min(100, score)))


def drought_score(cdd: Optional[float], hi_max_24h: Optional[float], tmax_24h: Optional[float]) -> int:
    score = 0

    # CDD (0–50)
    if cdd is not None:
        if cdd > 20: score += 50
        elif cdd > 10: score += 35
        elif cdd >= 5: score += 15

    # Stress thermique (0–25) - préférence Heat Index, sinon Tmax
    x = hi_max_24h if hi_max_24h is not None else tmax_24h
    if x is not None:
        if x > 38: score += 25
        elif x >= 35: score += 18
        elif x >= 32: score += 10

    return int(max(0, min(100, score)))


def _load_station_admin_map() -> Dict[str, str]:
    svc = supabase_service()
    res = svc.table("mnocc_stations").select("id,admin_code").execute()
    rows = res.data or []
    # admin_code doit être renseigné pour la choroplèthe
    return {r["id"]: r.get("admin_code") for r in rows if r.get("admin_code")}


def _load_hourly_obs(since_iso: str) -> pd.DataFrame:
    svc = supabase_service()
    res = (
        svc.table("meteo_observations_hourly")
        .select("station_id,observed_at,prcp_mm,temp_c,rh_pct")
        .gte("observed_at", since_iso)
        .execute()
    )
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, errors="coerce")
    return df


def _compute_cdd_from_hourly(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    CDD approximatif:
      - on agrège par jour (UTC) la pluie (sum)
      - dry day si sum < 1mm
      - streak depuis aujourd'hui vers le passé
    """
    if df_hourly.empty:
        return pd.DataFrame(columns=["admin_code", "cdd"])

    df = df_hourly.copy()
    df["date"] = df["observed_at"].dt.date
    daily = (
        df.groupby(["admin_code", "date"], as_index=False)
        .agg(prcp_day=("prcp_mm", "sum"))
        .sort_values(["admin_code", "date"])
    )

    out = []
    for admin_code, g in daily.groupby("admin_code"):
        g = g.sort_values("date")
        # streak à partir de la dernière date disponible (idéalement today)
        streak = 0
        for _, row in g.iterrows():
            if (row["prcp_day"] or 0) < 1.0:
                streak += 1
            else:
                streak = 0
        out.append({"admin_code": admin_code, "cdd": float(streak)})

    return pd.DataFrame(out)


def compute_admin_metrics() -> pd.DataFrame:
    """
    Retourne un DF par admin_code avec:
      prcp_24h, prcp_72h, rx1h, hi_max_24h, tmax_24h, cdd
    """
    now = _utc_now()
    t24 = now - timedelta(hours=24)
    t72 = now - timedelta(hours=72)
    t30d = now - timedelta(days=30)

    station_admin = _load_station_admin_map()
    if not station_admin:
        return pd.DataFrame()

    # Charger 72h pour pluie/HI/Tmax
    df72 = _load_hourly_obs(t72.isoformat())
    if df72.empty:
        return pd.DataFrame()

    df72["admin_code"] = df72["station_id"].map(station_admin)
    df72 = df72.dropna(subset=["admin_code"])

    # Charger 30j pour CDD
    df30 = _load_hourly_obs(t30d.isoformat())
    if not df30.empty:
        df30["admin_code"] = df30["station_id"].map(station_admin)
        df30 = df30.dropna(subset=["admin_code"])

    df24 = df72[df72["observed_at"] >= t24].copy()

    # Heat index + Tmax 24h
    df24["heat_index_c"] = df24.apply(lambda r: _heat_index_c(r.get("temp_c"), r.get("rh_pct")), axis=1)

    # Agrégations 24h/72h par admin_code
    pr24 = df24.groupby("admin_code", as_index=False).agg(
        prcp_24h=("prcp_mm", "sum"),
        rx1h=("prcp_mm", "max"),
        hi_max_24h=("heat_index_c", "max"),
        tmax_24h=("temp_c", "max"),
    )
    pr72 = df72.groupby("admin_code", as_index=False).agg(
        prcp_72h=("prcp_mm", "sum"),
    )

    out = pr72.merge(pr24, on="admin_code", how="left")

    # CDD
    if not df30.empty:
        cdd = _compute_cdd_from_hourly(df30[["admin_code", "observed_at", "prcp_mm"]])
        out = out.merge(cdd, on="admin_code", how="left")
    else:
        out["cdd"] = None

    # Nettoyage
    for c in ["prcp_24h", "prcp_72h", "rx1h", "hi_max_24h", "tmax_24h", "cdd"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def build_indicator_rows(df_admin: pd.DataFrame, valid_date: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for _, r in df_admin.iterrows():
        admin = r["admin_code"]

        pr24 = None if pd.isna(r.get("prcp_24h")) else float(r["prcp_24h"])
        pr72 = None if pd.isna(r.get("prcp_72h")) else float(r["prcp_72h"])
        rx1h = None if pd.isna(r.get("rx1h")) else float(r["rx1h"])
        hi = None if pd.isna(r.get("hi_max_24h")) else float(r["hi_max_24h"])
        tmax = None if pd.isna(r.get("tmax_24h")) else float(r["tmax_24h"])
        cdd = None if pd.isna(r.get("cdd")) else float(r["cdd"])

        fscore = flood_score(pr24, pr72, rx1h)
        dscore = drought_score(cdd, hi, tmax)

        payload_common = {
            "prcp_24h": pr24,
            "prcp_72h": pr72,
            "rx1h": rx1h,
            "heat_index_max_24h": hi,
            "tmax_24h": tmax,
            "cdd": cdd,
        }

        # Flood indicators
        rows.append({
            "admin_code": admin,
            "risk": RISK_FLOOD,
            "indicator_code": IC_PRCP_24H,
            "valid_date": valid_date,
            "value": pr24,
            "unit": "mm",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_FLOOD,
            "indicator_code": IC_PRCP_72H,
            "valid_date": valid_date,
            "value": pr72,
            "unit": "mm",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_FLOOD,
            "indicator_code": IC_RX1H,
            "valid_date": valid_date,
            "value": rx1h,
            "unit": "mm",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_FLOOD,
            "indicator_code": IC_FLOOD_SCORE,
            "valid_date": valid_date,
            "value": float(fscore),
            "unit": "score",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })

        # Drought indicators
        rows.append({
            "admin_code": admin,
            "risk": RISK_DROUGHT,
            "indicator_code": IC_CDD,
            "valid_date": valid_date,
            "value": cdd,
            "unit": "days",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_DROUGHT,
            "indicator_code": IC_HI_MAX_24H,
            "valid_date": valid_date,
            "value": hi,
            "unit": "C",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_DROUGHT,
            "indicator_code": IC_TMAX_24H,
            "valid_date": valid_date,
            "value": tmax,
            "unit": "C",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })
        rows.append({
            "admin_code": admin,
            "risk": RISK_DROUGHT,
            "indicator_code": IC_DROUGHT_SCORE,
            "valid_date": valid_date,
            "value": float(dscore),
            "unit": "score",
            "horizon": None,
            "source": SOURCE_HOURLY,
            "payload": payload_common,
        })

    return rows


def persist_risk_indicators(rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert via ux_risk_indicators_natural.
    Retourne (upserted_approx, errors).
    """
    if not rows:
        return (0, 0)

    svc = supabase_service()
    errors = 0
    upserted = 0

    # Batch upsert
    chunk = 800
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        up = (
            svc.table("risk_indicators")
            .upsert(
                part,
                on_conflict="admin_code,risk,indicator_code,valid_date,horizon,source"
            )
            .execute()
        )
        if getattr(up, "error", None):
            errors += 1
        else:
            upserted += len(part)

    return (upserted, errors)


def run_scores_pipeline(valid_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Pipeline V2:
      - calcule agrégats admin
      - calcule scores Flood/Drought
      - persiste dans risk_indicators
    """
    if valid_date is None:
        valid_date = date.today().isoformat()

    df_admin = compute_admin_metrics()
    if df_admin.empty:
        return {"admin_units": 0, "rows": 0, "upserted": 0, "errors": 0}

    rows = build_indicator_rows(df_admin, valid_date=valid_date)
    upserted, errors = persist_risk_indicators(rows)

    return {
        "admin_units": int(df_admin.shape[0]),
        "rows": int(len(rows)),
        "upserted": int(upserted),
        "errors": int(errors),
        "valid_date": valid_date,
    }
