"""
proximity.py
--------------
Stage 6: calculates real geographic distance from each accommodation
point to the nearest bus stop, railway station, supermarket, police
station, healthcare facility, and university.

IMPORTANT: this does NOT subtract latitude/longitude values directly
(that would give a meaningless number, not a real distance). Instead,
both the accommodation points and the facility points are reprojected
into EPSG:32644 (UTM Zone 44N, the correct metric projection for Sri
Lanka), and distances are measured in that projected space, in meters.
"""

import geopandas as gpd

# UTM Zone 44N -- covers Sri Lanka, gives accurate distances in meters.
METRIC_CRS = "EPSG:32644"

# Maps: source layer name -> (output column name, friendly display label)
FACILITY_LAYER_CONFIG = {
    "Bus Stops": ("nearest_bus_stop_m", "Bus stop"),
    "Railway Stations": ("nearest_railway_m", "Railway station"),
    "Supermarkets": ("nearest_supermarket_m", "Supermarket"),
    "Police Stations": ("nearest_police_m", "Police station"),
    "Healthcare Facilities": ("nearest_healthcare_m", "Healthcare facility"),
    "Higher Education Institutions": ("nearest_university_m", "University"),
}


def compute_nearest_facilities(accommodation_gdf: gpd.GeoDataFrame, layers: dict) -> gpd.GeoDataFrame:
    """
    For every facility layer available in `layers`, add a column to
    `accommodation_gdf` holding the distance (in meters) from each
    accommodation point to the NEAREST feature in that facility layer.

    Layers that aren't loaded yet are simply skipped (no crash) -- the
    resulting column just won't exist, and the accommodation card
    already handles missing columns gracefully.
    """
    if accommodation_gdf is None or accommodation_gdf.empty:
        return accommodation_gdf

    result = accommodation_gdf.copy()

    # Reproject the accommodation points once, reuse for every facility layer.
    acc_projected = result.to_crs(METRIC_CRS)

    for layer_name, (col_name, _label) in FACILITY_LAYER_CONFIG.items():
        facility_gdf = layers.get(layer_name)

        if facility_gdf is None or facility_gdf.empty:
            continue  # layer not loaded -- skip, don't error

        facility_projected = facility_gdf.to_crs(METRIC_CRS)[["geometry"]]

        # sjoin_nearest finds, for each accommodation point, the closest
        # feature in the facility layer and returns the distance in the
        # same units as the projected CRS (meters, since UTM is metric).
        joined = gpd.sjoin_nearest(
            acc_projected[["geometry"]],
            facility_projected,
            distance_col="_dist_m",
            how="left",
        )

        # sjoin_nearest can occasionally produce duplicate matches if two
        # facility points are exactly equidistant -- keep just the closest
        # one per accommodation point.
        joined = joined[~joined.index.duplicated(keep="first")]

        result[col_name] = joined["_dist_m"].round(0)

    return result


def format_distance(meters) -> str:
    """Format a distance in meters as '350 m' or '1.2 km', matching the spec's example output."""
    if meters is None:
        return "Unknown"
    try:
        meters = float(meters)
    except (ValueError, TypeError):
        return "Unknown"

    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.1f} km"
