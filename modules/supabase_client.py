"""
supabase_client.py
--------------------
Connects to Supabase using credentials from Streamlit secrets
(.streamlit/secrets.toml) -- never hardcoded in this file, per the
project's security requirements.

Other modules should import get_supabase_client() rather than
creating their own connection, so we only connect once per session.
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client, reused across reruns in the same
    session (st.cache_resource keeps it alive without reconnecting
    every time the script reruns).
    """
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase credentials are missing. Make sure "
            ".streamlit/secrets.toml exists and contains both "
            "SUPABASE_URL and SUPABASE_KEY. See the Stage 4 setup "
            "steps for how to get these from your Supabase project."
        )

    return create_client(url, key)