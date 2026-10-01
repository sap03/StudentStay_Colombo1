"""
university_search.py
----------------------
Stage 7: lets a user pick a university and a search radius, then
filters accommodation layers down to only points within that radius.

Uses the same proper metric projection (UTM Zone 44N) as proximity.py
-- distances/buffers are real geographic distances, not naive
lat/long subtraction.
"""

import geopandas as gpd
from modules.proximity import METRIC_CRS

DISTANCE_OPTIONS_M = {
    "500 m": 500,
    "1 km": 1000,
    "2 km": 2000,
    "5 km": 5000,
}


def get_university_options(layers: dict) -> list[tuple[str, float, float]]:
    """
    Returns a list of (display_label, latitude, longitude) for every
    university in the Higher Education Institutions layer, for use in
    a selectbox. Falls back gracefully if the layer isn't loaded or
    has no obvious name column.
    """
    gdf = layers.get("Higher Education Institutions")
    if gdf is None or gdf.empty:
        return []

    # Find a name-like column (case-insensitive), fall back to a
    # generic numbered label if nothing obvious exists.
    name_col = None
    for col in gdf.columns:
        if col.lower().strip() in ("name", "institution", "university", "title"):
            name_col = col
            break

    options = []
    for i, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        label = str(row[name_col]).strip() if name_col and not gdf[name_col].isna().loc[i] else f"University #{i + 1}"
        options.append((label, geom.y, geom.x))

    return options


def find_accommodation_within_radius(
    university_lat: float, university_lon: float, radius_m: float, accommodation_layers: dict
) -> dict:
    """
    accommodation_layers: dict like {"Student-Reported Accommodation": gdf, "Existing Boarding Locations": gdf}

    Returns a dict of the same shape, but each GeoDataFrame is filtered
    to only points within `radius_m` meters of the university, with an
    added 'distance_to_university_m' column (real projected distance,
    not lat/long subtraction).
    """
    uni_point = gpd.GeoSeries(
        gpd.points_from_xy([university_lon], [university_lat]), crs="EPSG:4326"
    ).to_crs(METRIC_CRS).iloc[0]

    filtered = {}
    for layer_name, gdf in accommodation_layers.items():
        if gdf is None or gdf.empty:
            filtered[layer_name] = gdf
            continue

        projected = gdf.to_crs(METRIC_CRS)
        distances = projected.geometry.distance(uni_point)

        within = gdf.copy()
        within["distance_to_university_m"] = distances.round(0)
        within = within[distances <= radius_m]

        filtered[layer_name] = within

    return filtered
