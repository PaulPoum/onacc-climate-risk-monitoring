# pages/22_Dashboard_Module2.py
"""
Dashboard Module 2 : Cartes de risques et catastrophes
"""
from __future__ import annotations

import streamlit as st
from datetime import date, datetime
from core.ui import approval_gate

st.set_page_config(
    page_title="Module 2 - Cartes | ONACC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
        
        .module-header {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(67, 233, 123, 0.3);
        }
        
        .module-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        
        .module-subtitle {
            font-size: 1rem;
            opacity: 0.9;
        }
        
        .feature-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease;
            height: 100%;
        }
        
        .feature-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
        }
        
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .feature-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #1a1a1a;
        }
        
        .feature-desc {
            font-size: 0.9rem;
            color: #666;
            line-height: 1.5;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: #fff3cd;
            color: #856404;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Guards
if not st.session_state.get("access_token"):
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

if not approval_gate():
    st.stop()

# Header
st.markdown("""
    <div class="module-header">
        <div class="module-title">🗺️ Module 2 : Cartes de risques et catastrophes</div>
        <div class="module-subtitle">Système d'information géographique avec cartographie multi-risques</div>
    </div>
""", unsafe_allow_html=True)

# Bouton retour
if st.button("← Retour au Dashboard Principal", key="back_main"):
    st.switch_page("pages/10_Dashboard.py")

# Badge statut
st.markdown('<div class="status-badge">🚧 Module en développement</div>', unsafe_allow_html=True)

st.markdown("---")

# Vue d'ensemble
st.markdown("### 📊 Vue d'Ensemble du Module")

st.info("""
ℹ️ **Module en construction**

Ce module est actuellement en développement. Les fonctionnalités seront progressivement 
ajoutées dans les prochaines versions de la plateforme.
""")

st.markdown("---")

# Fonctionnalités prévues
st.markdown("### 🛠️ Fonctionnalités Prévues")

features = [('🗺️', 'Cartographie Multi-Risques', 'Visualisation géospatiale des zones à risque'), ('📍', 'Zones Critiques', 'Identification et suivi des zones prioritaires'), ('📊', 'Analyse Spatiale', "Outils d'analyse géographique avancés"), ('🔍', 'Recherche Territoriale', 'Recherche et filtres géographiques')]

feat_cols = st.columns(2)

for i, (icon, title, desc) in enumerate(features):
    with feat_cols[i % 2]:
        st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
        """.format(icon=icon, title=title, desc=desc), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")

# Section roadmap
st.markdown("### 🗓️ Roadmap de Développement")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Phase 1 - Court terme (1-2 mois) :**
    - 🎯 Définition des spécifications
    - 📐 Conception des interfaces
    - 🔨 Développement des fonctionnalités de base
    """)

with col2:
    st.markdown("""
    **Phase 2 - Moyen terme (3-6 mois) :**
    - 🚀 Déploiement des fonctionnalités avancées
    - 🧪 Tests et optimisation
    - 📚 Documentation utilisateur
    """)

st.markdown("---")

# Footer
st.caption("Module 2 - Cartes de risques et catastrophes | ONACC v2.0")