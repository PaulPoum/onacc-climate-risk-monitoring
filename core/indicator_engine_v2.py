# core/indicator_engine_v2.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.supabase_client import supabase_service

SOURCE = "open-meteo-dynamic-v2"


# Mapping : variables Open-Meteo -> colonnes DB (meteo_observations_hourly)
VAR_MAP = {
    "precipitation": "prcp_mm",
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "rh_pct",
    "wind_gusts_10m": "wind_gust_ms",
    "wind_speed_10m": "wind_ms",
    "pressure_msl": "pressure_hpa",
}

# Variables dérivées calculables localement (à partir de variables Open-Meteo stockées)
DERIVED = {"heat_index"}  # produira une colonne "heat_index_c"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _heat_index_c(temp_c: Optional[float], rh_pct: Optional[float]) -> Optional[float]:
    if temp_c is None or rh_pct is None:
        return None
    if temp_c < 27 or rh_pct < 40:
        return temp_c
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


def _load_defs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    svc = supabase_service()
    ind = svc.table("vigilance_indicator_defs").select("*").eq("enabled", True).execute().data or []
    sco = svc.table("vigilance_score_defs").select("*").eq("enabled", True).execute().data or []
    return pd.DataFrame(ind), pd.DataFrame(sco)


def _station_admin_map() -> Dict[str, str]:
    svc = supabase_service()
    rows = svc.table("mnocc_stations").select("id,admin_code").execute().data or []
    return {r["id"]: r["admin_code"] for r in rows if r.get("admin_code")}


def _load_hourly_obs(since: datetime, needed_cols: List[str]) -> pd.DataFrame:
    """
    Charge un minimum de colonnes depuis meteo_observations_hourly.
    """
    svc = supabase_service()

    # Colonnes physiques disponibles dans la table (fixes)
    base_cols = {"station_id", "observed_at", "prcp_mm", "temp_c", "rh_pct", "wind_gust_ms", "wind_ms", "pressure_hpa"}
    cols = ["station_id", "observed_at"] + [c for c in needed_cols if c in base_cols]

    res = (
        svc.table("meteo_observations_hourly")
        .select(",".join(cols))
        .gte("observed_at", since.isoformat())
        .execute()
    )
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True, errors="coerce")
    return df


def _percentile_rank(series: pd.Series, x: float) -> float:
    s = series.dropna().astype(float)
    if s.empty:
        return 0.0
    return float((s <= x).mean())


def _zscore(series: pd.Series, x: float) -> float:
    s = series.dropna().astype(float)
    if s.empty:
        return 0.0
    mu = float(s.mean())
    sd = float(s.std())
    if sd == 0.0 or np.isnan(sd):
        return 0.0
    return float((x - mu) / sd)


def _normalize_value(
    df_all: pd.DataFrame,
    admin_code: str,
    metric_series: pd.Series,
    x: float,
    norm: Dict[str, Any],
    now: datetime,
) -> float:
    """
    Retourne score01 (0..1) basé sur le lookback des données Open-Meteo stockées.
    """
    method = str(norm.get("method", "percentile")).lower()
    lookback_days = int(norm.get("lookback_days", 365))
    seasonal = norm.get("seasonal")  # ex: "month"

    hist = df_all[df_all["admin_code"] == admin_code].copy()
    hist = hist[hist["observed_at"] >= (now - timedelta(days=lookback_days))]

    if seasonal == "month":
        hist = hist[hist["observed_at"].dt.month == now.month]

    # La série historique utilisée doit correspondre à la métrique calculée
    # Ici on passe explicitement metric_series (pré-calculée) pour éviter de refaire des resamples lourds.
    s = metric_series.loc[metric_series.index.intersection(hist.index)] if hasattr(metric_series, "index") else metric_series

    if method == "zscore":
        z = _zscore(s, x)
        return float(1.0 / (1.0 + np.exp(-z)))  # sigmoid -> 0..1
    else:
        return _percentile_rank(s, x)


def _compute_metric(
    df_window: pd.DataFrame,
    agg: Dict[str, Any],
) -> pd.DataFrame:
    """
    Calcule une métrique par admin_code à partir d'une fenêtre df_window.
    Règles:
      - agg = { "<variable>": "sum|max|mean|min" } pour variables mappées
      - agg = { "heat_index": "max" } pour variable dérivée
    Retour: DataFrame(admin_code, value)
    """
    # Support multi-agg: si plusieurs clés, on calcule d'abord chaque composante et on SUM (par défaut)
    # (extensible via params['combine'])
    parts = []

    for var, method in (agg or {}).items():
        method = str(method).lower().strip()

        if var in DERIVED:
            # heat_index -> heat_index_c
            col = "heat_index_c"
        else:
            # variable Open-Meteo -> colonne DB
            col = VAR_MAP.get(var)
            if not col:
                continue

        if col not in df_window.columns:
            continue

        g = df_window.groupby("admin_code")[col]

        if method == "sum":
            s = g.sum()
        elif method == "max":
            s = g.max()
        elif method == "min":
            s = g.min()
        elif method == "mean":
            s = g.mean()
        else:
            # fallback
            s = g.mean()

        parts.append(s.rename(var))

    if not parts:
        return pd.DataFrame(columns=["admin_code", "value"])

    tmp = pd.concat(parts, axis=1).reset_index()

    # Combine rule: default sum if multiple parts
    if len(parts) == 1:
        tmp["value"] = tmp.iloc[:, 1].astype(float)
    else:
        tmp["value"] = tmp.iloc[:, 1:].sum(axis=1).astype(float)

    return tmp[["admin_code", "value"]]


def compute_indicators(valid_date: str) -> pd.DataFrame:
    ind_defs, _ = _load_defs()
    if ind_defs.empty:
        return pd.DataFrame()

    station_admin = _station_admin_map()
    if not station_admin:
        return pd.DataFrame()

    now = _utcnow()

    # Fenêtre max demandée (heures) + lookback max (jours) pour normalisation
    max_hours = 0
    max_lookback_days = 0
    needed_vars = set()

    for _, d in ind_defs.iterrows():
        w = d.get("window_spec") or {}
        max_hours = max(max_hours, int(w.get("hours", 0)))
        n = d.get("normalization") or {}
        max_lookback_days = max(max_lookback_days, int(n.get("lookback_days", 365)))
        for v in (d.get("variables") or []):
            needed_vars.add(v)

    needed_cols = set()
    for v in needed_vars:
        if v in DERIVED:
            continue
        col = VAR_MAP.get(v)
        if col:
            needed_cols.add(col)

    # Charger un bloc large: lookback + fenêtre
    since = now - timedelta(days=max_lookback_days + 2)
    df = _load_hourly_obs(since=since, needed_cols=sorted(list(needed_cols)))
    if df.empty:
        return pd.DataFrame()

    df["admin_code"] = df["station_id"].map(station_admin)
    df = df.dropna(subset=["admin_code"]).copy()

    # Dérivées
    if ("temperature_2m" in needed_vars) and ("relative_humidity_2m" in needed_vars):
        if "temp_c" in df.columns and "rh_pct" in df.columns:
            df["heat_index_c"] = df.apply(
                lambda r: _heat_index_c(
                    float(r["temp_c"]) if pd.notna(r.get("temp_c")) else None,
                    float(r["rh_pct"]) if pd.notna(r.get("rh_pct")) else None,
                ),
                axis=1,
            )

    outputs: List[Dict[str, Any]] = []

    for _, d in ind_defs.iterrows():
        code = d["code"]
        risk = d["risk"]  # risk_type (inondation/secheresse)
        unit = d.get("unit")
        resolution = d["resolution"]
        window_spec = d.get("window_spec") or {}
        agg = d.get("aggregation") or {}
        norm = d.get("normalization") or {}

        if resolution != "hourly":
            # V2 actuelle: hourly (vos defs actuelles)
            # daily/seasonal peuvent être ajoutés ensuite
            continue

        hours = int(window_spec.get("hours", 24))
        dfw = df[df["observed_at"] >= (now - timedelta(hours=hours))].copy()
        if dfw.empty:
            continue

        metric = _compute_metric(dfw, agg)
        if metric.empty:
            continue

        # Pour normalisation: on construit une série "historique" de la même métrique
        # Approche rapide:
        # - si sum 24h / 72h => resample daily sur prcp_mm puis rolling
        # - si max horaire => série brute prcp_mm
        # - si heat index max => série brute heat_index_c
        # On déduit le "type" de la métrique à partir de agg
        metric_series_by_admin: Dict[str, pd.Series] = {}

        # Détection type
        keys = list(agg.keys())
        k0 = keys[0] if keys else None
        m0 = str(agg.get(k0, "mean")).lower() if k0 else "mean"

        for admin in metric["admin_code"].unique():
            sub = df[df["admin_code"] == admin].set_index("observed_at").sort_index()

            if k0 == "precipitation" and m0 == "sum":
                # cumuls journaliers -> rolling window en jours approx
                daily = sub["prcp_mm"].resample("D").sum()
                # window hours -> convert to days (ceil)
                win_days = int(np.ceil(hours / 24))
                hist_metric = daily.rolling(win_days, min_periods=1).sum()
            elif k0 == "precipitation" and m0 == "max":
                hist_metric = sub["prcp_mm"]
            elif k0 == "heat_index" and m0 == "max":
                if "heat_index_c" in sub.columns:
                    hist_metric = sub["heat_index_c"]
                else:
                    hist_metric = pd.Series([], dtype=float)
            elif k0 == "wind_gusts_10m" and m0 == "max":
                if "wind_gust_ms" in sub.columns:
                    hist_metric = sub["wind_gust_ms"]
                else:
                    hist_metric = pd.Series([], dtype=float)
            else:
                # fallback: série brute si possible
                col = VAR_MAP.get(k0, "")
                hist_metric = sub[col] if col and col in sub.columns else pd.Series([], dtype=float)

            metric_series_by_admin[admin] = hist_metric

        for _, row in metric.iterrows():
            admin = row["admin_code"]
            val = row["value"]
            if pd.isna(val):
                continue

            hist_metric = metric_series_by_admin.get(admin, pd.Series([], dtype=float))
            score01 = _normalize_value(df_all=df, admin_code=admin, metric_series=hist_metric, x=float(val), norm=norm, now=now)

            outputs.append({
                "admin_code": admin,
                "risk": risk,
                "indicator_code": code,
                "valid_date": valid_date,
                "value": float(val),
                "unit": unit,
                "horizon": None,
                "source": SOURCE,
                "payload": {
                    "title": d.get("title"),
                    "variables": d.get("variables"),
                    "window_spec": window_spec,
                    "aggregation": agg,
                    "normalization": norm,
                    "score01": float(score01),
                },
            })

    return pd.DataFrame(outputs)


def compute_scores(indicators_df: pd.DataFrame) -> pd.DataFrame:
    _, score_defs = _load_defs()
    if indicators_df.empty or score_defs.empty:
        return pd.DataFrame()

    df = indicators_df.copy()

    def get_score01(p):
        try:
            return float((p or {}).get("score01", 0.0))
        except Exception:
            return 0.0

    df["score01"] = df["payload"].apply(get_score01)

    out: List[Dict[str, Any]] = []
    for _, sd in score_defs.iterrows():
        score_code = sd["code"]               # SCORE_INONDATION / SCORE_SECHERESSE
        risk = sd["risk"]                     # inondation / secheresse
        weights = sd["indicator_weights"] or {}
        mapping = sd["mapping"] or {}
        clip = mapping.get("clip", [0, 100])
        lo, hi = float(clip[0]), float(clip[1])

        sub = df[df["risk"] == risk]
        if sub.empty:
            continue

        for admin, g in sub.groupby("admin_code"):
            total = 0.0
            wsum = 0.0
            comp = {}

            for ic, w in weights.items():
                w = float(w)
                v = g[g["indicator_code"] == ic]["score01"]
                if v.empty:
                    continue
                sval = float(v.iloc[0])
                comp[ic] = sval
                total += w * sval
                wsum += w

            if wsum == 0.0:
                continue

            score01 = total / wsum
            score = max(lo, min(hi, 100.0 * score01))

            out.append({
                "admin_code": admin,
                "risk": risk,
                "indicator_code": score_code,
                "valid_date": g["valid_date"].iloc[0],
                "value": float(score),
                "unit": "score",
                "horizon": None,
                "source": SOURCE,
                "payload": {
                    "weights": weights,
                    "components": comp,
                    "method": mapping.get("method", "weighted_sum"),
                },
            })

    return pd.DataFrame(out)


def upsert_risk_indicators(rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    if not rows:
        return (0, 0)

    svc = supabase_service()
    upserted = 0
    errors = 0
    chunk = 800

    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        res = (
            svc.table("risk_indicators")
            .upsert(part, on_conflict="admin_code,risk,indicator_code,valid_date,horizon,source")
            .execute()
        )
        if getattr(res, "error", None):
            errors += 1
        else:
            upserted += len(part)

    return upserted, errors


def run_pipeline_v2(valid_date: Optional[str] = None) -> Dict[str, Any]:
    if valid_date is None:
        valid_date = date.today().isoformat()

    ind_df = compute_indicators(valid_date=valid_date)
    score_df = compute_scores(indicators_df=ind_df)

    rows = []
    if not ind_df.empty:
        rows += ind_df.to_dict(orient="records")
    if not score_df.empty:
        rows += score_df.to_dict(orient="records")

    up, err = upsert_risk_indicators(rows)
    return {"valid_date": valid_date, "rows": len(rows), "upserted": up, "errors": err}
