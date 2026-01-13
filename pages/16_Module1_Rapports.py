# pages/16_Module1_Rapports.py
"""
Module 1 - Rapports & Bulletins
Génération automatique PDF/Excel (version simplifiée)
"""
from __future__ import annotations

import streamlit as st
from core.ui import approval_gate

st.set_page_config(
    page_title="Rapports & Bulletins | Module 1",
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
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            padding: 2rem;
            border-radius: 16px;
            color: #333;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(168, 237, 234, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="page-header">
        <h1 style="margin:0;">📄 Rapports & Bulletins</h1>
        <p style="margin:0.5rem 0 0 0;">Génération Automatique de Documents</p>
    </div>
""", unsafe_allow_html=True)

st.info("🚧 **En développement** - La génération automatique de rapports sera disponible dans une prochaine version.")

st.markdown("### 📑 Types de Rapports")

reports = [
    ("📅 Bulletin Hebdomadaire", "Synthèse 7 derniers jours"),
    ("📆 Bulletin Mensuel", "Bilan mensuel détaillé"),
    ("🌍 Rapport Saisonnier", "Analyse climatique saisonnière"),
    ("🚨 Rapport d'Événement", "Post-mortem catastrophe"),
    ("📊 Statistiques Annuelles", "Bilan annuel complet"),
]

for title, desc in reports:
    st.markdown(f"""
        <div style="background:white;padding:1.5rem;border-radius:12px;margin:1rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <strong style="font-size:1.1rem;">{title}</strong><br>
            <span style="color:#666;font-size:0.9rem;">{desc}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("### 🛠️ Technologies")
st.markdown("""
- **PDF** : ReportLab, WeasyPrint
- **Excel** : openpyxl, xlsxwriter
- **Templates** : Jinja2
- **Graphiques** : Plotly (export PNG)
""")

if st.button("← Retour Hub Module 1", key="back"):
    st.switch_page("pages/11_Module1_Hub.py")