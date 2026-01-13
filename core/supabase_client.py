# core/supabase_client.py
from __future__ import annotations

from typing import Optional, Callable

import streamlit as st
from supabase import Client, create_client


def _read_secret(*keys: str) -> Optional[str]:
    """
    Lit la config Supabase depuis:
    - st.secrets["supabase"][...]
    - ou st.secrets[...]
    """
    if "supabase" in st.secrets:
        for k in keys:
            if k in st.secrets["supabase"]:
                return str(st.secrets["supabase"][k])

    for k in keys:
        if k in st.secrets:
            return str(st.secrets[k])

    return None


def _get_supabase_url() -> str:
    url = _read_secret("url", "SUPABASE_URL")
    if not url:
        raise ValueError(
            "Supabase URL introuvable. Ajoutez st.secrets['supabase']['url'] "
            "ou st.secrets['SUPABASE_URL'] dans .streamlit/secrets.toml"
        )
    return url


def _get_anon_key() -> str:
    key = _read_secret("anon_key", "SUPABASE_ANON_KEY", "anon")
    if not key:
        raise ValueError(
            "Supabase ANON key introuvable. Ajoutez st.secrets['supabase']['anon_key'] "
            "ou st.secrets['SUPABASE_ANON_KEY'] dans .streamlit/secrets.toml"
        )
    return key


def _get_service_key() -> str:
    key = _read_secret("service_role_key", "SUPABASE_SERVICE_ROLE_KEY", "service_role")
    if not key:
        raise ValueError(
            "Supabase SERVICE ROLE key introuvable. Ajoutez st.secrets['supabase']['service_role_key'] "
            "ou st.secrets['SUPABASE_SERVICE_ROLE_KEY'] dans .streamlit/secrets.toml"
        )
    return key


@st.cache_resource(show_spinner=False)
def _client(url: str, key: str) -> Client:
    # Cache par (url, key)
    return create_client(url, key)


def supa_anon() -> Client:
    """Client ANON (RLS active côté DB)."""
    return _client(_get_supabase_url(), _get_anon_key())


def supa_service() -> Client:
    """Client SERVICE ROLE (bypass RLS) — à utiliser UNIQUEMENT côté serveur Streamlit."""
    return _client(_get_supabase_url(), _get_service_key())


def supabase_user(access_token: str) -> Client:
    """
    Client en contexte utilisateur (RLS) :
    - on crée un client anon
    - puis on injecte le JWT access_token dans PostgREST
    (les signatures varient selon supabase-py, on gère plusieurs cas)
    """
    c = supa_anon()

    # Compat supabase-py: postgrest.auth(<token>) ou postgrest.auth(token=<token>)
    try:
        c.postgrest.auth(access_token)  # type: ignore[arg-type]
        return c
    except Exception:
        pass

    try:
        c.postgrest.auth(token=access_token)  # type: ignore[call-arg]
        return c
    except Exception:
        pass

    # Fallback: pas de support dans la version actuelle
    return c


def supabase_service() -> Client:
    """Alias explicite (service role) pour écritures système côté Streamlit."""
    return supa_service()


class _LazyClient:
    """
    Proxy pour conserver la rétro-compat:
    `from core.supabase_client import supabase`
    sans initialiser le client au moment de l'import.
    """

    def __init__(self, factory: Callable[[], Client]) -> None:
        self._factory = factory
        self._instance: Optional[Client] = None

    def _get(self) -> Client:
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def __getattr__(self, name: str):
        return getattr(self._get(), name)


# Rétro-compat:
# - `supabase` se comporte comme un Client, mais est lazy
supabase = _LazyClient(supa_anon)

# Optionnel si tu veux aussi un alias lazy service
supabase_admin = _LazyClient(supa_service)
