# pages/14_Module1_Indicateurs.py
"""
Module 1 - Indicateurs Avancés
Calcul SPI, SPEI, anomalies (version simplifiée - à étoffer)
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from core.ui import approval_gate
from core.supabase_client import supabase_user

st.set_page_config(
    page_title="Indicateurs Avancés | Module 1",
    layout="wide"
)

if not st.session_state.get("access_token"):
    st.warning("Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .page-header {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(67, 233, 123, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="page-header">
        <h1 style="margin:0;">📈 Indicateurs Avancés</h1>
        <p style="margin:0.5rem 0 0 0;">Calculs SPI, SPEI, Anomalies Spatiales</p>
    </div>
""", unsafe_allow_html=True)

st.info("🚧 **En développement** - Les indicateurs avancés (SPI, SPEI) seront disponibles dans une prochaine version.")

st.markdown("### 📊 Fonctionnalités Prévues")

features = [
    ("📐 SPI (Standardized Precipitation Index)", "Échelles 1, 3, 6, 12, 24 mois"),
    ("💧 SPEI (Standard Precip-Evapotranspiration Index)", "Avec calcul PET Thornthwaite"),
    ("🗺️ Anomalies Spatiales", "Cartes d'écarts à la normale"),
    ("📊 Percentiles Historiques", "Classement par rapport à la climatologie"),
    ("📈 Décomposition Saisonnière", "Tendance, saisonnalité, résidus"),
]

for title, desc in features:
    st.markdown(f"""
        <div style="background:white;padding:1.5rem;border-radius:12px;margin:1rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <strong style="font-size:1.1rem;">{title}</strong><br>
            <span style="color:#666;font-size:0.9rem;">{desc}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("### 📚 Références")
st.markdown("""
- **SPI** : McKee et al. (1993) - Échelles temporelles multiples
- **SPEI** : Vicente-Serrano et al. (2010) - Intègre l'évapotranspiration
- **Librairie Python** : `climate-indices` (pip install climate-indices)
""")

if st.button("← Retour Hub Module 1", key="back"):
    st.switch_page("pages/11_Module1_Hub.py")