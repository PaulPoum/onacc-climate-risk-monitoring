# pages/02_Connexion.py
from __future__ import annotations

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Connexion - ONACC", layout="centered")

try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_ANON_KEY"]
    client = create_client(supabase_url, supabase_key)
except KeyError as e:
    st.error(f"❌ Secret manquant : {e}")
    st.error("Vérifiez que les secrets sont bien configurés dans Streamlit Cloud")
    st.stop()

def do_login(email: str, password: str) -> None:
    email = (email or "").strip().lower()
    password = (password or "").strip()

    if not email:
        raise ValueError("Veuillez renseigner votre email.")
    if not password:
        raise ValueError("Veuillez renseigner votre mot de passe.")

    # IMPORTANT: utiliser la réponse retournée
    res = client.auth.sign_in_with_password({"email": email, "password": password})

    # Selon versions supabase-py, la session est dans res.session
    session = getattr(res, "session", None) or client.auth.get_session()
    if not session:
        raise RuntimeError("Connexion échouée (session absente).")

    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token

    # Ne pas switch_page ici : on relance app.py (qui routera selon profile)
    st.rerun()


# Si déjà connecté -> rerun pour laisser app.py router (approved/pending/change pwd)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    st.info("Session active. Redirection…")
    st.rerun()

st.title("Connexion")

with st.form("login_form", clear_on_submit=False):
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Mot de passe", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        submit = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
    with col2:
        go_req = st.form_submit_button("Demander l’accès", use_container_width=True)

if go_req:
    st.switch_page("pages/03_Demande_acces.py")

if submit:
    try:
        do_login(email, password)
    except Exception as e:
        # Diagnostic utile sans exposer le mot de passe
        st.error(f"Erreur: {e}")
        st.caption(f"(Debug) email envoyé à Supabase: '{(email or '').strip().lower()}'")
