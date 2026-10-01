# modules/reports.py
# Stage 12 - Report a listing. Reports are stored in Supabase, never locally.

import pandas as pd
import streamlit as st

# ADJUST THIS LINE if your function in supabase_client.py has a different name
from modules.supabase_client import get_supabase_client as get_client
from modules.search import build_unified_table

REASONS = [
    "Incorrect information",
    "No longer available",
    "Fake listing",
    "Inappropriate content",
    "Other",
]


def _find_column(df, candidates):
    lowered = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def submit_report(listing_ref, listing_name, source_layer, reason, details):
    """Save one report to Supabase. Returns (True, "") or (False, error text)."""
    row = {
        "listing_ref": str(listing_ref) if listing_ref is not None else None,
        "listing_name": listing_name,
        "source_layer": source_layer,
        "reason": reason,
        "details": details.strip() or None,
        "status": "OPEN",
    }
    try:
        # "minimal" = don't ask Supabase to send the row back
        # (public visitors are not allowed to read the reports table)
        get_client().table("reports").insert(row, returning="minimal").execute()
        return True, ""
    except Exception as e:
        return False, str(e)


def get_reports(status="OPEN"):
    """ADMIN ONLY: fetch reports with the given status."""
    result = (
        get_client().table("reports").select("*")
        .eq("status", status).order("created_at", desc=True).execute()
    )
    return result.data or []


def set_report_status(report_id, new_status):
    """ADMIN ONLY: mark a report REVIEWED or DISMISSED."""
    get_client().table("reports").update({"status": new_status}).eq("id", report_id).execute()


def render_report_tab(layers):
    """Draw the Report Listing tab."""
    st.subheader("🚩 Report a Listing")
    st.caption("Spotted a problem? Tell us and an administrator will review it. "
               "Please do not include personal details in your message.")

    try:
        df = pd.DataFrame(build_unified_table(layers))
    except Exception as e:
        st.error(f"Could not load the listings. Details: {e}")
        return
    if df.empty:
        st.info("No listings loaded yet.")
        return
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])
    df = df.reset_index(drop=True)

    name_col = _find_column(df, ["name", "title", "display_name", "label", "review_id"])
    id_col = _find_column(df, ["id", "review_id", "accommodation_id"])
    source_col = _find_column(df, ["layer", "source", "source_layer"])

    names = df[name_col].fillna("Unnamed").astype(str) if name_col else \
        pd.Series([f"Listing {i}" for i in range(len(df))])
    labels = [f"{n}  (#{i})" for i, n in enumerate(names)]

    choice = st.selectbox("Which listing?", labels, index=None,
                          placeholder="Start typing a name...")
    reason = st.selectbox("What is the problem?", REASONS)
    details = st.text_area("More details (optional)", max_chars=500)

    if st.button("Submit report", type="primary"):
        if choice is None:
            st.warning("Please choose a listing first.")
            return
        i = labels.index(choice)
        row = df.iloc[i]
        ok, err = submit_report(
            listing_ref=row[id_col] if id_col else i,
            listing_name=str(names.iloc[i]),
            source_layer=str(row[source_col]) if source_col else None,
            reason=reason,
            details=details,
        )
        if ok:
            st.success("Thank you. Your report has been sent for review.")
        else:
            st.error("The report could not be saved. Check your internet connection "
                     "and Supabase setup.")
            with st.expander("Technical details"):
                st.code(err)