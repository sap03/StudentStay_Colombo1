# modules/duplicates.py
# Stage 10 - Duplicate checking. Warns if a new submission is very close to
# an existing accommodation point. Never blocks the submission.

import math

import pandas as pd

# Distance under which we consider two points a possible duplicate
DUPLICATE_THRESHOLD_METERS = 50


def _haversine_meters(lat1, lon1, lat2, lon2):
    """Proper geographic distance between two points, in meters.
    (Not a simple subtraction of lat/lon — see Stage 25's requirement.)"""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _find_column(df, candidates):
    lowered = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def find_nearby_accommodation(new_lat, new_lon, layers, threshold=DUPLICATE_THRESHOLD_METERS):
    """
    Check the existing accommodation layers for any point within `threshold`
    meters of (new_lat, new_lon).

    `layers` is st.session_state.layers (a dict of {layer_name: GeoDataFrame}).

    Returns a list of matches, each a dict with:
        layer, name, distance_m
    Sorted closest-first. Empty list means no nearby listing was found.
    """
    accommodation_layers = [
        "Student-Reported Accommodation",
        "Existing Boarding Locations",
        "Community Submissions",
    ]

    matches = []

    for layer_name in accommodation_layers:
        gdf = layers.get(layer_name)
        if gdf is None or len(gdf) == 0:
            continue

        name_col = _find_column(gdf, ["name", "title", "display_name", "review_id"])

        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            # Point geometry: x = longitude, y = latitude
            existing_lat, existing_lon = geom.y, geom.x

            distance = _haversine_meters(new_lat, new_lon, existing_lat, existing_lon)
            if distance <= threshold:
                matches.append({
                    "layer": layer_name,
                    "name": str(row[name_col]) if name_col else "Unnamed listing",
                    "distance_m": round(distance, 1),
                })

    matches.sort(key=lambda m: m["distance_m"])
    return matches