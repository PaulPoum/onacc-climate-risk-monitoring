# pages/04_Changer_mdp.py
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Changer mot de passe - ONACC", layout="centered")
st.title("Changer votre mot de passe")

client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

def attach_session():
    token = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if token and refresh:
        client.auth.set_session(token, refresh)
        try:
            client.postgrest.auth(token)
        except Exception:
            pass

if not (st.session_state.get("access_token") and st.session_state.get("refresh_token")):
    st.warning("Veuillez vous connecter.")
    st.stop()

attach_session()

new_pwd = st.text_input("Nouveau mot de passe", type="password")
new_pwd2 = st.text_input("Confirmer le mot de passe", type="password")

if st.button("Valider", type="primary", use_container_width=True):
    if not new_pwd or len(new_pwd) < 8:
        st.error("Mot de passe trop court (min 8 caractères).")
        st.stop()
    if new_pwd != new_pwd2:
        st.error("Les mots de passe ne correspondent pas.")
        st.stop()

    try:
        client.auth.update_user({"password": new_pwd})
    except Exception as e:
        st.error(f"Impossible de changer le mot de passe: {e}")
        st.stop()

    # Marquer must_change_password=false côté DB (si RLS autorise l’update du profil courant)
    try:
        client.table("profiles").update({"must_change_password": False}).execute()
    except Exception:
        pass

    st.success("Mot de passe mis à jour. Redirection…")
    # IMPORTANT: ne pas switch_page (menu courant = uniquement cette page)
    st.rerun()
