# core/nav.py
from __future__ import annotations

import streamlit as st
from core.supabase_client import supabase_user

# 1) Toutes les pages déclarées ici
CODE_TO_PAGE: dict[str, str] = {
    # Core
    "DASHBOARD": "pages/10_Dashboard.py",
    "CARTE": "pages/20_Carte.py",

    # Module 1 (Hub + sous-pages)
    "MODULE1_HUB": "pages/11_Module1_Hub.py",
    "MODULE1_SYNTH_NAT": "pages/12_Module1_Synthese_Nationale.py",
    "MODULE1_VUE_REGIONALE": "pages/13_Module1_Vue_Regionale.py",
    "MODULE1_INDICATEURS": "pages/14_Module1_Indicateurs.py",
    "MODULE1_ALERTES": "pages/15_Module1_Alertes.py",
    "MODULE1_RAPPORTS": "pages/16_Module1_Rapports.py",

    # Veille / Ingestion (tech)
    "INGESTION_OPENMETEO": "pages/80_Ingestion_OpenMeteo.py",
    "VEILLE_HOURLY": "pages/81_Veille_Hourly_OpenMeteo.py",
    "VEILLE_SCORES": "pages/82_Veille_Scores_V2.py",
    "PIPELINE_V2": "pages/83_Pipeline_Veille_V2.py",

    # Admin
    "ADMIN_APPROVALS": "pages/90_Admin_Approvals.py",
}

# 2) Expansion "module -> pages"
MODULE_EXPANSION: dict[str, set[str]] = {
    "MODULE1": {
        "MODULE1_HUB",
        "MODULE1_SYNTH_NAT",
        "MODULE1_VUE_REGIONALE",
        "MODULE1_INDICATEURS",
        "MODULE1_ALERTES",
        "MODULE1_RAPPORTS",
        "INGESTION_OPENMETEO",
        "VEILLE_HOURLY",
        "VEILLE_SCORES",
        "PIPELINE_V2",
    }
}

def get_user_email() -> str:
    em = (st.session_state.get("user_email") or "").strip().lower()
    if em:
        return em
    prof = st.session_state.get("profile") or {}
    return str(prof.get("email") or "").strip().lower()

def is_super_admin() -> bool:
    email = get_user_email()
    super_admins = {str(x).strip().lower() for x in (st.secrets.get("SUPER_ADMIN_EMAILS") or [])}
    return email in super_admins

def fetch_allowed_codes_from_rpc() -> set[str]:
    """
    Renvoie des codes 'modules' (ex: MODULE1, CARTE, etc.) ou des codes pages
    selon ce que ton RPC 'my_modules' renvoie.
    """
    try:
        u = supabase_user(st.session_state["access_token"])
        res = u.rpc("my_modules", {}).execute()
        data = res.data or []
        return {str(m.get("code")).strip() for m in data if m.get("code")}
    except Exception:
        return set()

def compute_allowed_pages() -> set[str]:
    """
    - Super admin: toutes les pages
    - Autres: expansion des modules autorisés
    """
    if is_super_admin():
        return set(CODE_TO_PAGE.keys())

    base = fetch_allowed_codes_from_rpc()
    pages: set[str] = set()

    # Toujours autoriser le dashboard
    pages.add("DASHBOARD")

    # Si le RPC renvoie directement des pages, on les conserve
    for code in base:
        if code in CODE_TO_PAGE:
            pages.add(code)

    # Expansion module -> pages
    for mod, expanded in MODULE_EXPANSION.items():
        if mod in base:
            pages |= expanded

    # ADMIN_APPROVALS toujours réservé super admin
    pages.discard("ADMIN_APPROVALS")

    return pages

def can_navigate(code: str, allowed_pages: set[str]) -> bool:
    return code in CODE_TO_PAGE and code in allowed_pages

def go(code: str, allowed_pages: set[str]) -> None:
    if not can_navigate(code, allowed_pages):
        st.warning("❌ Accès non autorisé pour votre profil.")
        return
    st.switch_page(CODE_TO_PAGE[code])
