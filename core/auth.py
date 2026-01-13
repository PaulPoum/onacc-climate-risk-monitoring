# core/auth.py
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

import requests
import streamlit as st
from supabase import create_client

from .supabase_client import supa_service


# -----------------------
# Utils temps
# -----------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------
# Session / login helpers (AJOUTS)
# -----------------------
def is_logged_in() -> bool:
    """
    Vrai si la session Streamlit contient access_token + refresh_token.
    """
    return bool(st.session_state.get("access_token") and st.session_state.get("refresh_token"))


def _user_client():
    """
    Client Supabase en contexte utilisateur (RLS) à partir des tokens Streamlit.
    """
    c = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    token = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if token and refresh:
        c.auth.set_session(token, refresh)
        try:
            c.postgrest.auth(token)
        except Exception:
            pass
    return c


def fetch_profile() -> dict:
    """
    Récupère le profile du user courant via son user_id (auth.uid()).
    Évite `.single()` sans filtre (qui peut renvoyer plusieurs lignes).
    """
    c = _user_client()

    u = c.auth.get_user()
    user_id = None

    # supabase-py versions: objet ou dict
    if hasattr(u, "user") and getattr(u.user, "id", None):
        user_id = str(u.user.id)
    elif isinstance(u, dict):
        user_id = str((u.get("user") or {}).get("id") or "")

    if not user_id:
        return {}

    res = (
        c.table("profiles")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else {}


def load_modules() -> List[Dict[str, Any]]:
    """
    Charge les modules autorisés via RPC `my_modules`.
    Met en cache dans st.session_state["modules"].
    """
    c = _user_client()
    try:
        res = c.rpc("my_modules", {}).execute()
        mods = res.data or []
    except Exception:
        mods = []

    st.session_state["modules"] = mods
    return mods


# -----------------------
# Password + provisioning
# -----------------------
def generate_temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*?"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _extract_user_id(created: Any) -> str:
    if hasattr(created, "user") and getattr(created.user, "id", None):
        return str(created.user.id)
    if isinstance(created, dict):
        user = created.get("user") or created.get("data", {}).get("user")
        if isinstance(user, dict) and user.get("id"):
            return str(user["id"])
    raise RuntimeError(f"Impossible d’extraire user_id du retour create_user: {created}")


def send_credentials_email(email: str, temp_password: str, fullname: Optional[str] = None) -> None:
    api_key = st.secrets.get("RESEND_API_KEY", "")
    mail_from = st.secrets.get("MAIL_FROM", "")
    app_url = st.secrets.get("APP_URL", "")

    if not api_key or not mail_from:
        raise RuntimeError("Secrets manquants: RESEND_API_KEY ou MAIL_FROM")

    subject = "ONACC Climate Risk — Identifiants d’accès (temporaire)"
    html = f"""
      <p>Bonjour{(' ' + fullname) if fullname else ''},</p>
      <p>Votre demande d’accès a été approuvée. Un compte a été créé.</p>
      <p><b>Email :</b> {email}<br/>
         <b>Mot de passe temporaire :</b> {temp_password}</p>
      <p><b>Connexion :</b> {app_url}</p>
      <p>Important : changez votre mot de passe après la première connexion.</p>
    """

    # Timeout court pour éviter “ça tourne”
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"from": mail_from, "to": [email], "subject": subject, "html": html},
        timeout=8,
    )
    if not (200 <= r.status_code < 300):
        raise RuntimeError(f"Resend HTTP {r.status_code}: {r.text[:800]}")


def provision_user_for_access_request(
    request_id: str,
    email: str,
    fullname: Optional[str],
    org: Optional[str],
    phone: Optional[str],
) -> str:
    """
    Provisioning déclenché côté admin:
    - crée Auth user
    - upsert profile en approved + must_change_password
    - trace dans access_requests
    - envoie email
    Retourne user_id.
    """
    svc = supa_service()
    temp_pwd = generate_temp_password()

    # 1) Create Auth user (Admin)
    try:
        created = svc.auth.admin.create_user(
            {
                "email": email,
                "password": temp_pwd,
                "email_confirm": True,
                "user_metadata": {"fullname": fullname, "org": org},
            }
        )
        user_id = _extract_user_id(created)
    except Exception as e:
        svc.table("access_requests").update(
            {"last_error": str(e), "last_error_at": _now(), "provision_error": str(e)}
        ).eq("id", request_id).execute()
        raise

    # 2) Upsert profile -> APPROVED
    svc.table("profiles").upsert(
        {
            "user_id": user_id,
            "email": email,
            "fullname": fullname,
            "org": org,
            "phone": phone,
            "access_status": "approved",
            "must_change_password": True,
            "updated_at": _now(),
        }
    ).execute()

    # 3) Bookkeeping access_requests
    svc.table("access_requests").update(
        {
            "provisioned_user_id": user_id,
            "provisioned_at": _now(),
            "invited_user_id": user_id,
            "invited_at": _now(),
            "last_error": None,
            "last_error_at": None,
            "provision_error": None,
        }
    ).eq("id", request_id).execute()

    # 4) Email
    try:
        send_credentials_email(email=email, temp_password=temp_pwd, fullname=fullname)
        svc.table("access_requests").update({"temp_password_sent_at": _now()}).eq("id", request_id).execute()
    except Exception as e:
        svc.table("access_requests").update(
            {
                "last_error": f"email failed: {e}",
                "last_error_at": _now(),
                "provision_error": f"email failed: {e}",
            }
        ).eq("id", request_id).execute()
        raise

    return user_id

def reset_password_and_resend(
    user_id: str,
    email: str,
    fullname: Optional[str],
    request_id: Optional[str] = None,
) -> None:
    svc = supa_service()
    temp_pwd = generate_temp_password()

    # Admin: reset password
    svc.auth.admin.update_user_by_id(user_id, {"password": temp_pwd, "email_confirm": True})

    # Email
    send_credentials_email(email=email, temp_password=temp_pwd, fullname=fullname)

    # (Optionnel) trace côté access_requests
    if request_id:
        try:
            svc.table("access_requests").update(
                {"temp_password_sent_at": _now(), "last_error": None, "provision_error": None}
            ).eq("id", request_id).execute()
        except Exception:
            pass
