"""
search.py
----------
Stage 8/9: normalizes all three accommodation-style layers
(Student-Reported Accommodation, Existing Boarding Locations,
Community Submissions) into ONE flat table with consistent columns,
so they can be filtered and shown as results cards together --
even though their underlying schemas are genuinely different
(survey-question text vs. structured Add Boarding fields).

This reuses the same field-detection logic already built in
accommodation.py, rather than duplicating it.
"""

import re
import pandas as pd

from modules.accommodation import (
    ACCOMMODATION_LAYERS, FIELD_ALIASES, QUALITY_FIELD_ALIASES,
    _find_field, _is_empty, _extract_facilities,
)
from modules.proximity import FACILITY_LAYER_CONFIG


def _parse_rent_numeric(rent_value):
    """
    Best-effort extraction of a single comparable rent number, used
    only for filtering (the original text is still shown to the user
    untouched). Handles:
      - plain numbers (from Community Submissions: rent_lkr)
      - ranges like '20,000 - 30,000 LKR' -> average
      - 'Below 10,000 LKR' -> 10,000 (upper bound, so 'max rent'
        filtering still correctly excludes/includes it)
    Returns None if nothing parseable is found.
    """
    if _is_empty(rent_value):
        return None

    if isinstance(rent_value, (int, float)):
        return float(rent_value)

    text = str(rent_value).replace(",", "")

    # Range: "20000 - 30000", "20000-30000", or using an en-dash/em-dash
    # ("20000 – 30000") which is what the real survey data actually uses.
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)", text)
    if range_match:
        low, high = float(range_match.group(1)), float(range_match.group(2))
        return (low + high) / 2

    # "Below 10000" / "Under 10000" -> use the number as the ceiling
    below_match = re.search(r"(?:below|under|less than)\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if below_match:
        return float(below_match.group(1))

    # "Above 30000" / "Over 30000" -> use the number as a rough estimate
    above_match = re.search(r"(?:above|over|more than)\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if above_match:
        return float(above_match.group(1))

    # Just a plain number somewhere in the text
    plain_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if plain_match:
        return float(plain_match.group(1))

    return None


def build_unified_table(layers: dict) -> pd.DataFrame:
    """
    Combines every loaded accommodation-type layer into one flat
    DataFrame. Each row also carries 'source_layer' and 'row_index'
    so a selected result can be traced back to its original
    GeoDataFrame row for map display.
    """
    records = []

    for layer_name in ACCOMMODATION_LAYERS:
        gdf = layers.get(layer_name)
        if gdf is None or gdf.empty:
            continue

        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            name_col, name_val = _find_field(row, FIELD_ALIASES["name"])
            type_col, type_val = _find_field(row, FIELD_ALIASES["type"])
            rent_col, rent_val = _find_field(row, FIELD_ALIASES["rent"])
            gender_col, gender_val = _find_field(row, FIELD_ALIASES["gender"])
            avail_col, avail_val = _find_field(row, FIELD_ALIASES["availability"])
            safety_col, safety_val = _find_field(row, QUALITY_FIELD_ALIASES["safety"])

            used_cols = set()
            facilities = _extract_facilities(row, used_cols)

            record = {
                "source_layer": layer_name,
                "row_index": idx,
                "name": str(name_val).strip() if name_val and not _is_empty(name_val) else "Unnamed listing",
                "type": str(type_val).strip() if type_val and not _is_empty(type_val) else None,
                "rent_text": str(rent_val).strip() if rent_val and not _is_empty(rent_val) else None,
                "rent_numeric": _parse_rent_numeric(rent_val),
                "gender": str(gender_val).strip() if gender_val and not _is_empty(gender_val) else None,
                "availability": str(avail_val).strip() if avail_val and not _is_empty(avail_val) else None,
                "safety": str(safety_val).strip() if safety_val and not _is_empty(safety_val) else None,
                "facilities": facilities,
                "latitude": geom.y,
                "longitude": geom.x,
            }

            for col_name, (dist_col, label) in FACILITY_LAYER_CONFIG.items():
                record[dist_col] = row[dist_col] if dist_col in row.index and not _is_empty(row.get(dist_col)) else None

            records.append(record)

    if not records:
        return pd.DataFrame(columns=[
            "source_layer", "row_index", "name", "type", "rent_text", "rent_numeric",
            "gender", "availability", "safety", "facilities", "latitude", "longitude",
        ])

    return pd.DataFrame(records)


def filter_table(
    df: pd.DataFrame,
    max_rent=None,
    types=None,
    genders=None,
    availabilities=None,
    max_dist_bus_km=None,
    max_dist_rail_km=None,
) -> pd.DataFrame:
    """
    Applies filters. A filter is skipped entirely if left as None/empty,
    so an unset filter never accidentally excludes rows with missing data.
    Rows with genuinely missing data for an ACTIVE filter are excluded
    from that filter's results (can't confirm they match).
    """
    result = df.copy()

    if max_rent is not None:
        result = result[result["rent_numeric"].notna() & (result["rent_numeric"] <= max_rent)]

    if types:
        result = result[result["type"].isin(types)]

    if genders:
        result = result[result["gender"].isin(genders) | result["gender"].isna()]

    if availabilities:
        result = result[result["availability"].isin(availabilities)]

    if max_dist_bus_km is not None:
        result = result[result["nearest_bus_stop_m"].notna() & (result["nearest_bus_stop_m"] / 1000 <= max_dist_bus_km)]

    if max_dist_rail_km is not None:
        result = result[result["nearest_railway_m"].notna() & (result["nearest_railway_m"] / 1000 <= max_dist_rail_km)]

    return result
