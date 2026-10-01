# modules/dashboard.py
# Stage 13 - Dashboard: summary statistics for all accommodation listings.
# Reuses build_unified_table() from Stage 8 (search.py).

import pandas as pd
import streamlit as st

from modules.search import build_unified_table


def _find_column(df, candidates):
    """Return the first column in df whose name matches one of the candidates
    (case-insensitive). Returns None if nothing matches."""
    lowered = {col.lower(): col for col in df.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def render_dashboard(layers):
    """Draw the dashboard. `layers` is st.session_state.layers."""
    st.subheader("📊 Accommodation Dashboard")

    # Build the same combined table used by Search & Filter
    try:
        df = build_unified_table(layers)
    except Exception as e:
        st.error(
            "The dashboard could not build the combined accommodation table. "
            f"Details: {e}"
        )
        return

    if df is None or len(df) == 0:
        st.info("No accommodation data loaded yet. Load your layers first.")
        return

    # Turn geometry into plain data so pandas can handle it easily
    df = pd.DataFrame(df)

    # Find the columns we need (adjust these lists if your names differ)
    rent_col = _find_column(df, ["rent_lkr", "rent_numeric", "rent_min", "rent", "monthly_rent"])
    type_col = _find_column(df, ["type", "accommodation_type"])
    avail_col = _find_column(df, ["availability"])
    source_col = _find_column(df, ["layer", "source", "source_layer"])

    # ---- 1. Key numbers ----
    total = len(df)

    # Available = "Available" or "Limited availability" (not "Currently full")
    available = 0
    if avail_col:
        text = df[avail_col].astype(str).str.lower()
        available = int(
            (text.str.contains("available") & ~text.str.contains("not|unavailable")).sum()
        )

    average_rent = None
    rent_count = 0
    if rent_col:
        rents = pd.to_numeric(df[rent_col], errors="coerce").dropna()
        rent_count = len(rents)
        if rent_count > 0:
            average_rent = rents.mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total accommodations", total)
    c2.metric("Available now", available)
    c3.metric(
        "Average rent",
        f"Rs. {average_rent:,.0f}" if average_rent is not None else "N/A",
    )

    if avail_col is None or available == 0:
        st.caption("Availability is only recorded for Add Boarding submissions, "
                   "so this number may be small.")
    if rent_count:
        st.caption(f"Average rent is based on {rent_count} of {total} listings "
                   "that have rent information.")

    st.divider()

    # ---- 2. Accommodation by type ----
    left, right = st.columns(2)

    with left:
        st.markdown("**Accommodation by type**")
        if type_col:
            type_counts = (
                df[type_col].fillna("Unknown").replace("", "Unknown")
                .astype(str).value_counts()
            )
            st.bar_chart(type_counts)
        else:
            st.info("No 'type' column found.")

    # ---- 3. Listings by source ----
    with right:
        st.markdown("**Listings by source**")
        if source_col:
            st.bar_chart(df[source_col].astype(str).value_counts())
        else:
            st.info("No source/layer column found.")

    # ---- Debug helper (delete once everything looks right) ----
    with st.expander("🛠 Debug: columns detected"):
        st.write("All columns:", list(df.columns))
        st.write({
            "rent": rent_col, "type": type_col,
            "availability": avail_col, "source": source_col,
        })