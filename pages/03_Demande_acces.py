# pages/03_Demande_acces.py
from __future__ import annotations

import re
import streamlit as st
from core.supabase_client import supa_anon, supa_service

st.set_page_config(page_title="Demande d’accès - ONACC", layout="centered")
st.title("Demande d’accès")

anon = supa_anon()
svc = supa_service()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

with st.form("req", clear_on_submit=True):
    fullname = st.text_input("Nom complet *").strip()
    org = st.text_input("Organisation / Structure").strip()
    email = st.text_input("Email *").strip().lower()
    phone = st.text_input("Téléphone").strip()

    requested_role = st.selectbox(
        "Profil demandé *",
        [
            "LECTURE_SEULE",
            "FOCAL_COMMUNE",
            "FOCAL_REGION",
            "FOCAL_MINISTERE",
            "PROTECTION_CIVILE",
            "INGENIEUR_ONACC",
            "CHERCHEUR_ACADEMIQUE",
            "PARTENAIRE",
            "MEDIA_JOURNALISTE_CLIMAT",
        ],
    )
    justification = st.text_area("Justification").strip()
    ok = st.form_submit_button("Envoyer")

if ok:
    # Validations rapides
    if not fullname:
        st.error("Veuillez renseigner votre nom complet.")
        st.stop()

    if not email or not EMAIL_RE.match(email):
        st.error("Veuillez renseigner un email valide.")
        st.stop()

    # 1) Vérifier si une demande pending existe déjà (lecture via service role)
    #    (optionnel mais utile pour UX + debug)
    try:
        last_req = (
            svc.table("access_requests")
            .select(
                "id,status,created_at,reviewed_at,invited_at,temp_password_sent_at,last_error,provision_error"
            )
            .eq("email", email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if last_req and last_req[0].get("status") == "pending":
            r = last_req[0]
            st.warning(
                "Une demande est déjà enregistrée et est en cours de traitement.\n\n"
                "Vous recevrez un email après validation par l’administrateur."
            )
            st.caption(
                f"Demande ID: {r.get('id')} | "
                f"Créée: {r.get('created_at')} | "
                f"Validée: {r.get('reviewed_at') or 'non'} | "
                f"Invitation: {r.get('invited_at') or 'non'} | "
                f"Email identifiants: {r.get('temp_password_sent_at') or 'non'} | "
                f"Dernière erreur: {(r.get('provision_error') or r.get('last_error') or 'aucune')}"
            )
            st.stop()
    except Exception as e:
        st.caption(f"(Debug) Vérification statut impossible: {e}")

    # 2) Soumission via RPC (SECURITY DEFINER) => plus de blocage RLS sur INSERT
    #    IMPORTANT: la fonction doit exister côté Supabase:
    #    public.submit_access_request(p_fullname, p_email, p_requested_role, p_org, p_phone, p_justification) returns uuid
    try:
        res = anon.rpc(
            "submit_access_request",
            {
                "p_fullname": fullname,
                "p_email": email,
                "p_requested_role": requested_role,
                "p_org": org or None,
                "p_phone": phone or None,
                "p_justification": justification or None,
            },
        ).execute()

        # supabase-py renvoie souvent directement la valeur (uuid) dans res.data
        req_id = getattr(res, "data", None)

        # Si votre SQL renvoie un objet JSON au lieu d'un uuid brut, on tente d'extraire "id"
        if isinstance(req_id, dict) and "id" in req_id:
            req_id = req_id["id"]
        if isinstance(req_id, list) and len(req_id) == 1 and isinstance(req_id[0], dict) and "id" in req_id[0]:
            req_id = req_id[0]["id"]

        st.success("Demande envoyée. Elle sera validée par l’administrateur.")
        st.info("Vous recevrez un email dès que votre compte sera activé.")
        if req_id:
            st.caption(f"Référence demande: {req_id}")

    except Exception as e:
        msg = str(e)

        # Messages plus explicites selon les causes courantes
        if "Could not find the function" in msg or "PGRST202" in msg:
            st.error(
                "RPC introuvable: la fonction public.submit_access_request n’est pas déployée "
                "ou n’est pas exposée à PostgREST."
            )
            st.caption(f"(Debug) {e}")
        elif "42501" in msg or "row-level security" in msg:
            st.error(
                "Erreur de permissions/RLS lors de l’appel RPC. "
                "Vérifiez que la fonction est SECURITY DEFINER et que EXECUTE est accordé à anon/authenticated."
            )
            st.caption(f"(Debug) {e}")
        else:
            st.error(f"Impossible d’enregistrer la demande: {e}")
