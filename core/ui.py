# core/ui.py
import streamlit as st

def topbar():
    app_name = st.secrets.get("APP_NAME", "ONACC Climate Risk")
    st.sidebar.markdown(f"### {app_name}")

def approval_gate():
    """
    Affiche un message si non approuvé.
    """
    prof = st.session_state.get("profile") or {}
    status = str(prof.get("access_status", "pending"))
    if status != "approved":
        st.warning(
            "Votre compte n’est pas encore approuvé.\n\n"
            f"Statut actuel : **{status}**.\n\n"
            "Contactez l’administrateur ONACC ou soumettez une demande d’accès si nécessaire."
        )
        return False
    return True

def role_badge():
    prof = st.session_state.get("profile") or {}
    st.sidebar.caption(f"Connecté: {prof.get('email', st.session_state.get('user_email',''))}")
