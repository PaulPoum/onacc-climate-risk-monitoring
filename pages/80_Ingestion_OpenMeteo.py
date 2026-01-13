# pages/80_Ingestion_OpenMeteo.py
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from core.auth import is_logged_in
from core.supabase_client import supabase_user, supabase_service
from core.ui import approval_gate
from core.open_meteo import fetch_daily_forecast, horizon_plan

st.title("Ingestion Open-Meteo → climate_forecasts")

if not is_logged_in():
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

st.caption("Cette page écrit dans la base. Réservez-la aux profils techniques (INGENIEUR_ONACC / ADMIN_NATIONAL).")

horizon = st.selectbox("Horizon", ["D10", "D20", "D30", "M6", "Y1"])
limit = st.number_input("Nombre de stations à ingérer (pour test)", min_value=1, max_value=5000, value=50, step=10)

run_btn = st.button("Lancer ingestion")

if run_btn:
    # Y1: non supporté nativement par Open-Meteo Seasonal (7 mois). :contentReference[oaicite:12]{index=12}
    try:
        plan = horizon_plan(horizon)
    except Exception as e:
        st.error(str(e))
        st.info("Solution recommandée: pour Y1, basculer sur votre modèle ONACC (SARIMA-LSTM) ou un autre provider long-range.")
        st.stop()

    uclient = supabase_user(st.session_state["access_token"])
    stations = uclient.table("mnocc_stations").select("id,localite,latitude,longitude,region").limit(int(limit)).execute()
    if getattr(stations, "error", None):
        st.error(stations.error.message)
        st.stop()

    rows = stations.data or []
    if not rows:
        st.warning("Aucune station trouvée.")
        st.stop()

    run_at = datetime.now(timezone.utc).isoformat()
    svc = supabase_service()

    inserted_total = 0
    errors = 0

    prog = st.progress(0.0)
    for i, s in enumerate(rows, start=1):
        try:
            seasonal = (plan.api != "https://api.open-meteo.com/v1/forecast")
            data = fetch_daily_forecast(s["latitude"], s["longitude"], days=plan.days, seasonal=seasonal)

            daily = data.get("daily", {})
            times = daily.get("time", [])
            if not times:
                prog.progress(i / len(rows))
                continue

            payload_rows = []
            tmax = daily.get("temperature_2m_max", [None] * len(times))
            tmin = daily.get("temperature_2m_min", [None] * len(times))
            pr   = daily.get("precipitation_sum", [None] * len(times))
            wmx  = daily.get("wind_speed_10m_max", [None] * len(times))

            for idx, t in enumerate(times):
                payload_rows.append({
                    "station_id": s["id"],
                    "horizon": plan.horizon,
                    "source": plan.source,
                    "run_at": run_at,
                    "valid_date": t,
                    "payload": {
                        "temperature_2m_max": tmax[idx],
                        "temperature_2m_min": tmin[idx],
                        "precipitation_sum": pr[idx],
                        "wind_speed_10m_max": wmx[idx],
                    }
                })

            # Upsert par blocs (évite doublons)
            chunk = 300
            for j in range(0, len(payload_rows), chunk):
                part = payload_rows[j:j+chunk]
                up = (
                    svc.table("climate_forecasts")
                    .upsert(part, on_conflict="station_id,horizon,source,valid_date")
                    .execute()
                )
                if getattr(up, "error", None):
                    errors += 1

            inserted_total += len(payload_rows)

        except Exception:
            errors += 1

        prog.progress(i / len(rows))

    st.success(f"Ingestion terminée. Lignes upsertées (approx.): {inserted_total}. Erreurs: {errors}.")

    df = pd.DataFrame(rows)
    st.subheader("Stations traitées (échantillon)")
    st.dataframe(df.head(20), use_container_width=True)
