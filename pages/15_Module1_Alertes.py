# pages/15_Module1_Alertes.py
"""
Module 1 - Gestion des Alertes
Configuration seuils et notifications (version simplifiée)
"""
from __future__ import annotations

import streamlit as st
from core.ui import approval_gate
from core.supabase_client import supabase_user

st.set_page_config(
    page_title="Alertes Automatiques | Module 1",
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
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(250, 112, 154, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="page-header">
        <h1 style="margin:0;">🚨 Alertes Automatiques</h1>
        <p style="margin:0.5rem 0 0 0;">Configuration et Gestion des Notifications</p>
    </div>
""", unsafe_allow_html=True)

st.info("🚧 **En développement** - Le système d'alertes automatiques sera disponible dans une prochaine version.")

st.markdown("### ⚙️ Fonctionnalités Prévues")

features = [
    ("📋 Règles d'Alerte", "Configuration seuils par indicateur et zone"),
    ("🎚️ Niveaux d'Alerte", "Vert / Jaune / Orange / Rouge"),
    ("📧 Notifications Email", "Via Resend API"),
    ("📱 Notifications SMS", "Via Twilio API"),
    ("🔗 Webhooks", "Intégration systèmes tiers"),
    ("📊 Historique", "Traçabilité complète"),
    ("✅ Acquittement", "Confirmation réception alertes"),
]

for title, desc in features:
    st.markdown(f"""
        <div style="background:white;padding:1.5rem;border-radius:12px;margin:1rem 0;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <strong style="font-size:1.1rem;">{title}</strong><br>
            <span style="color:#666;font-size:0.9rem;">{desc}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("### 📋 Exemple de Règle")

with st.expander("Voir exemple"):
    st.code("""
{
  "name": "Alerte Inondation Critique - Douala",
  "risk": "flood",
  "indicator_code": "FLOOD_SCORE",
  "operator": ">=",
  "threshold": 75.0,
  "level": "rouge",
  "geographic_scope": ["CM-LT"],
  "notification_channels": ["email", "sms", "webhook"],
  "active": true
}
    """, language="json")

if st.button("← Retour Hub Module 1", key="back"):
    st.switch_page("pages/11_Module1_Hub.py")