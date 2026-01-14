# app.py
from __future__ import annotations

import os
import streamlit as st
from supabase import create_client
from postgrest.exceptions import APIError

APP_TITLE = "ONACC Climate Risk Monitoring"


@st.cache_resource(show_spinner=False)
def supa():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token") and st.session_state.get("refresh_token"))


def logout(reason: str | None = None) -> None:
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("profile", None)
    st.session_state.pop("user_email", None)
    st.session_state.pop("modules", None)
    if reason:
        st.warning(reason)
    st.rerun()


def attach_auth(client):
    token = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if not token or not refresh:
        return client

    try:
        client.auth.set_session(token, refresh)
    except Exception:
        logout("Session invalide. Veuillez vous reconnecter.")
        return client

    try:
        client.postgrest.auth(token)
    except Exception:
        pass

    return client


def current_user(client) -> tuple[str, str]:
    """Retourne (user_id, email) du user Auth."""
    try:
        u = client.auth.get_user()
        if hasattr(u, "user") and getattr(u.user, "id", None):
            uid = str(u.user.id)
            email = str(getattr(u.user, "email", "") or "").lower()
            return uid, email
        if isinstance(u, dict):
            user = u.get("user") or {}
            uid = str(user.get("id") or "")
            email = str(user.get("email") or "").lower()
            if uid:
                return uid, email
    except Exception:
        pass

    logout("Session invalide: utilisateur introuvable (get_user).")
    return "", ""


def get_profile(client, uid: str) -> dict:
    """Récupère le profil, évite .single()"""
    res = (
        client.table("profiles")
        .select("*")
        .eq("user_id", uid)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        raise RuntimeError(f"Aucun profil trouvé pour user_id={uid}.")
    return res.data[0]


def get_modules(client) -> list[dict]:
    """Récupère les modules autorisés via RPC my_modules."""
    try:
        res = client.rpc("my_modules", {}).execute()
        return res.data or []
    except Exception:
        return []


def is_super_admin(email: str) -> bool:
    """Vérifie si l'email est super-admin"""
    SUPER_ADMINS = set((st.secrets.get("SUPER_ADMIN_EMAILS") or []))
    return email.lower() in {x.lower() for x in SUPER_ADMINS}


def page_exists(filepath: str) -> bool:
    """Vérifie si un fichier de page existe"""
    return os.path.isfile(filepath)


# ---------- UI ----------
st.set_page_config(page_title=APP_TITLE, layout="wide")

PUBLIC_PAGES = [
    st.Page("pages/01_Splash.py", title="Accueil", icon="🏠"),
    st.Page("pages/02_Connexion.py", title="Connexion", icon="🔐"),
    st.Page("pages/03_Demande_acces.py", title="Demande d'accès", icon="📝"),
]

# Si non connecté -> menu public
if not is_logged_in():
    st.navigation(PUBLIC_PAGES).run()
    raise SystemExit

# Client user attaché
client = attach_auth(supa())

# UID + email
uid, email = current_user(client)
st.session_state["user_email"] = email

# Profil utilisateur
try:
    profile = get_profile(client, uid)
except APIError as e:
    logout(f"Impossible de charger le profil (API): {e}")
    raise SystemExit
except Exception as e:
    st.error(str(e))
    st.stop()

st.session_state["profile"] = profile

# Super-admin check
user_is_super_admin = is_super_admin(email)

# Sidebar: session controls
with st.sidebar:
    st.markdown(f"### {APP_TITLE}")
    st.caption(f"Connecté: {email or profile.get('email','')}")

    if user_is_super_admin:
        st.success("🔑 **SUPER-ADMIN**")
        st.caption("Accès complet à tous les modules")

    if st.button("Déconnexion", use_container_width=True):
        logout()

# 1) Force change password (super-admin bypass)
must_change = bool(profile.get("must_change_password", True))
if must_change and not user_is_super_admin:
    st.navigation([st.Page("pages/04_Changer_mdp.py", title="Changer mot de passe", icon="🔑")]).run()
    raise SystemExit

# 2) Pending -> waiting (super-admin bypass)
if not user_is_super_admin and str(profile.get("access_status")) != "approved":
    st.navigation([st.Page("pages/05_En_attente.py", title="En attente", icon="⏳")]).run()
    raise SystemExit

# 3) Modules - Super-admin obtient TOUS les modules
if user_is_super_admin:
    # Important : inclure MODULE1..MODULE9 pour cohérence UI (dashboard + contrôles)
    modules = [
        {"code": "DASHBOARD", "title": "Dashboard"},
        {"code": "MODULE1", "title": "Module 1 - Veille"},
        {"code": "MODULE2", "title": "Module 2 - Cartes"},
        {"code": "MODULE3", "title": "Module 3 - Alertes"},
        {"code": "MODULE4", "title": "Module 4 - Analyse"},
        {"code": "MODULE5", "title": "Module 5 - Événements"},
        {"code": "MODULE6", "title": "Module 6 - Territoires"},
        {"code": "MODULE7", "title": "Module 7 - Utilisateurs"},
        {"code": "MODULE8", "title": "Module 8 - Paramétrage"},
        {"code": "MODULE9", "title": "Module 9 - Audit"},

        # Pages fonctionnelles
        {"code": "CARTE", "title": "Cartes SIG"},
        {"code": "INGESTION_OPENMETEO", "title": "Ingestion"},
        {"code": "VEILLE_HOURLY", "title": "Veille Hourly"},
        {"code": "VEILLE_SCORES", "title": "Scores V2"},
        {"code": "PIPELINE_V2", "title": "Pipeline"},
        {"code": "ADMIN_APPROVALS", "title": "Admin"},
    ]
else:
    modules = get_modules(client)

st.session_state["modules"] = modules

# Mapping complet des pages
module_to_page = {
    "DASHBOARD": st.Page("pages/10_Dashboard.py", title="Dashboard", icon="📊"),

    "CARTE": st.Page("pages/20_Carte.py", title="Cartes SIG", icon="🗺️"),
    "INGESTION_OPENMETEO": st.Page("pages/80_Ingestion_OpenMeteo.py", title="Ingestion Open-Meteo", icon="📥"),
    "VEILLE_HOURLY": st.Page("pages/81_Veille_Hourly_OpenMeteo.py", title="Veille Hourly", icon="⏱️"),
    "VEILLE_SCORES": st.Page("pages/82_Veille_Scores_V2.py", title="Scores V2", icon="🧮"),
    "PIPELINE_V2": st.Page("pages/83_Pipeline_Veille_V2.py", title="Pipeline", icon="⚙️"),
    "ADMIN_APPROVALS": st.Page("pages/90_Admin_Approvals.py", title="Admin", icon="✅"),
}

# Ajouter les dashboards des modules SEULEMENT s'ils existent
module_dashboards = [
    ("MODULE1", "pages/21_Dashboard_Module1.py", "Module 1 - Veille Météo", "🌦️"),
    ("MODULE2", "pages/22_Dashboard_Module2.py", "Module 2 - Cartes", "🗺️"),
    ("MODULE3", "pages/23_Dashboard_Module3.py", "Module 3 - Alertes", "🚨"),
    ("MODULE4", "pages/24_Dashboard_Module4.py", "Module 4 - Analyse", "📈"),
    ("MODULE5", "pages/25_Dashboard_Module5.py", "Module 5 - Événements", "🌪️"),
    ("MODULE6", "pages/26_Dashboard_Module6.py", "Module 6 - Territoires", "🎯"),
    ("MODULE7", "pages/27_Dashboard_Module7.py", "Module 7 - Utilisateurs", "👥"),
    ("MODULE8", "pages/28_Dashboard_Module8.py", "Module 8 - Paramétrage", "⚙️"),
    ("MODULE9", "pages/29_Dashboard_Module9.py", "Module 9 - Audit", "📝"),
]

for code, filepath, title, icon in module_dashboards:
    if page_exists(filepath):
        module_to_page[code] = st.Page(filepath, title=title, icon=icon)

pages: list[st.Page] = []
pages.append(module_to_page["DASHBOARD"])

if user_is_super_admin:
    for code, page in module_to_page.items():
        if code != "DASHBOARD" and page not in pages:
            pages.append(page)
else:
    allowed_codes = [m.get("code") for m in modules if m.get("code")]

    for code in allowed_codes:
        if code == "DASHBOARD":
            continue
        if code == "ADMIN_APPROVALS":
            continue
        if code in module_to_page and module_to_page[code] not in pages:
            pages.append(module_to_page[code])

st.navigation(pages).run()
