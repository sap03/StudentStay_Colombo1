# modules/compare.py
# Stage 14 - Compare up to 3 accommodations side by side.
# Reuses build_unified_table() from Stage 8 (search.py).

import pandas as pd
import streamlit as st

from modules.search import build_unified_table


def _find_column(df, candidates):
    """Return the first column matching one of the candidate names (case-insensitive)."""
    lowered = {col.lower(): col for col in df.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _find_distance_column(df, keywords):
    """Find a column that looks like a distance AND mentions one of the keywords.
    Example: 'dist_bus_m' or 'nearest_railway_km'."""
    for col in df.columns:
        name = col.lower()
        if "dist" in name or "nearest" in name:
            if any(word in name for word in keywords):
                return col
    return None


def _format_value(value, column_name=""):
    """Turn a raw value into readable text for the comparison table."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    text = str(value).strip()
    if text == "" or text.lower() in ("nan", "none"):
        return "-"

    # Add units to numeric distances based on the column name
    name = column_name.lower()
    try:
        number = float(value)
        if name.endswith("_km") or "_km_" in name:
            return f"{number:.2f} km"
        if name.endswith("_m") or "_m_" in name:
            return f"{number/1000:.2f} km" if number >= 1000 else f"{number:.0f} m"
    except (ValueError, TypeError):
        pass
    return text


def render_compare(layers):
    """Draw the Compare tab. `layers` is st.session_state.layers."""
    st.subheader("⚖️ Compare Accommodation")

    try:
        df = build_unified_table(layers)
    except Exception as e:
        st.error(f"Could not build the accommodation table. Details: {e}")
        return

    if df is None or len(df) == 0:
        st.info("No accommodation data loaded yet.")
        return

    # Plain pandas table (drop geometry so display works smoothly)
    df = pd.DataFrame(df)
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])
    df = df.reset_index(drop=True)

    # ---- Give every listing a readable, unique label ----
    name_col = _find_column(df, ["name", "title", "display_name", "label", "review_id"])
    if name_col:
        base_labels = df[name_col].fillna("Unnamed").astype(str)
    else:
        base_labels = pd.Series([f"Listing {i}" for i in range(len(df))])

    # Add a number if two listings share the same name
    df["_label"] = [f"{label}  (#{i})" for i, label in enumerate(base_labels)]

    # ---- Choose listings ----
    selected = st.multiselect(
        "Choose 2 or 3 accommodations to compare",
        options=df["_label"].tolist(),
        max_selections=3,
        placeholder="Start typing a name...",
    )

    if len(selected) < 2:
        st.info("Select at least 2 accommodations to see the comparison.")
        return

    chosen = df[df["_label"].isin(selected)].set_index("_label")
    chosen = chosen.loc[selected]  # keep the order the user picked them

    # ---- Which rows to show (display name, candidate column names / keywords) ----
    normal_fields = [
        ("Source", ["layer", "source", "source_layer"]),
        ("Type", ["type", "accommodation_type"]),
        ("Rent", ["rent_lkr", "rent", "rent_range", "monthly_rent", "rent_text"]),
        ("Gender", ["gender", "gender_preference"]),
        ("Availability", ["availability"]),
        ("Facilities", ["facilities"]),
    ]
    distance_fields = [
        ("Distance to university", ["univ", "institution", "hei"]),
        ("Distance to bus stop", ["bus"]),
        ("Distance to railway", ["rail", "train"]),
        ("Distance to supermarket", ["supermarket", "market"]),
        ("Distance to healthcare", ["health", "hospital"]),
        ("Distance to police", ["police"]),
    ]

    table = {}  # {row title: {listing label: text}}

    for title, candidates in normal_fields:
        col = _find_column(chosen, candidates)
        if col:
            table[title] = {label: _format_value(chosen.loc[label, col], col) for label in selected}
        else:
            table[title] = {label: "-" for label in selected}

    for title, keywords in distance_fields:
        col = _find_distance_column(chosen, keywords)
        if col:
            table[title] = {label: _format_value(chosen.loc[label, col], col) for label in selected}
        else:
            table[title] = {label: "-" for label in selected}

    # Rows = attributes, columns = listings
    compare_df = pd.DataFrame(table).T
    st.dataframe(compare_df, use_container_width=True)

    st.caption("A dash (-) means that information was not recorded for that listing.")

    # ---- Debug helper (delete once everything looks right) ----
    with st.expander("🛠 Debug: columns detected"):
        st.write("All columns:", list(df.columns))