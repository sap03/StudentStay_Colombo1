"""
data_loader.py
---------------
Stage 1 data loading logic for StudentStay Colombo.

Responsibilities:
- Know the 10 expected layer names and their type (csv / geojson).
- Match an uploaded filename to one of the 10 expected layers.
- Load CSV files (with latitude/longitude) into GeoDataFrames.
- Load GeoJSON files into GeoDataFrames.
- Validate the data and collect clear, friendly warnings/errors.

Nothing here touches Supabase. Stage 1 only works with files the
student uploads from their own computer, for development purposes.
"""

import io
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from modules.utils import normalize_name, make_warning

# ---------------------------------------------------------------------
# 1. The 10 expected layers (exact names required by the project brief)
# ---------------------------------------------------------------------

LAYER_CONFIG = {
    "Student-Reported Accommodation": {
        "source_type": "csv",
        "geometry_type": "Point",
        "color": "red",
        "icon": "bed",
    },
    "Existing Boarding Locations": {
        "source_type": "csv",
        "geometry_type": "Point",
        "color": "orange",
        "icon": "home",
    },
    "Higher Education Institutions": {
        "source_type": "csv",
        "geometry_type": "Point",
        "color": "blue",
        "icon": "graduation-cap",
    },
    "Police Stations": {
        "source_type": "csv",
        "geometry_type": "Point",
        "color": "darkblue",
        "icon": "shield",
    },
    "Healthcare Facilities": {
        "source_type": "csv",
        "geometry_type": "Point",
        "color": "green",
        "icon": "plus",
    },
    "Supermarkets": {
        "source_type": "geojson",
        "geometry_type": "Point",
        "color": "purple",
        "icon": "shopping-cart",
    },
    "Bus Stops": {
        "source_type": "geojson",
        "geometry_type": "Point",
        "color": "cadetblue",
        "icon": "bus",
    },
    "Railway Stations": {
        "source_type": "geojson",
        "geometry_type": "Point",
        "color": "gray",
        "icon": "train",
    },
    "Colombo District": {
        "source_type": "geojson",
        "geometry_type": "Polygon",
        "color": "#3186cc",
        "icon": None,
    },
    "Western Province": {
        "source_type": "geojson",
        "geometry_type": "Polygon",
        "color": "#808080",
        "icon": None,
    },
}

# Pre-compute normalized versions of the canonical layer names, once.
_NORMALIZED_LOOKUP = {normalize_name(name): name for name in LAYER_CONFIG}

# Field names we will search for (case-insensitive) inside CSV files.
LAT_FIELD_CANDIDATES = ["latitude", "lat", "y"]
LON_FIELD_CANDIDATES = ["longitude", "lon", "lng", "long", "x"]


# ---------------------------------------------------------------------
# 2. Filename -> layer identification
# ---------------------------------------------------------------------

def identify_layer(filename: str):
    """
    Try to match an uploaded filename to one of the 10 expected layers.

    Returns the canonical layer name (e.g. "Bus Stops") if a match is
    found, otherwise returns None so the app can fall back to manual
    assignment.
    """
    normalized = normalize_name(filename)
    return _NORMALIZED_LOOKUP.get(normalized)


def expected_source_type(filename: str) -> str:
    """Return 'csv' or 'geojson' based on the file extension."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".geojson") or lower.endswith(".json"):
        return "geojson"
    return "unknown"


# ---------------------------------------------------------------------
# 3. CSV loading (latitude/longitude -> Point geometry)
# ---------------------------------------------------------------------

def _find_coordinate_fields(columns):
    """
    Case-insensitively search the given column names for a latitude
    field and a longitude field. Returns (lat_field, lon_field) where
    either can be None if not found.
    """
    lower_map = {col.lower().strip(): col for col in columns}

    lat_field = None
    for candidate in LAT_FIELD_CANDIDATES:
        if candidate in lower_map:
            lat_field = lower_map[candidate]
            break

    lon_field = None
    for candidate in LON_FIELD_CANDIDATES:
        if candidate in lower_map:
            lon_field = lower_map[candidate]
            break

    return lat_field, lon_field


def load_csv_layer(file_obj, layer_name: str, manual_lat_field=None, manual_lon_field=None):
    """
    Load a CSV file into a GeoDataFrame of Point geometries.

    Returns a dict:
        {
            "gdf": GeoDataFrame or None,
            "warnings": [list of warning dicts],
            "success": bool,
            "total_rows": int,
            "valid_rows": int,
        }
    """
    warnings = []

    try:
        df = pd.read_csv(file_obj)
    except Exception as exc:
        warnings.append(make_warning(
            "Could not read CSV file",
            layer_name,
            f"The file could not be parsed as a CSV. Technical detail: {exc}",
            "Open the file and make sure it is a valid, comma-separated CSV file.",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": 0, "valid_rows": 0}

    if df.empty:
        warnings.append(make_warning(
            "Empty CSV file",
            layer_name,
            "The file was read successfully but contains no rows.",
            "Check that the correct file was uploaded and that it has data rows below the header.",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": 0, "valid_rows": 0}

    total_rows = len(df)

    # Detect latitude/longitude fields (or use manual override)
    if manual_lat_field and manual_lon_field:
        lat_field, lon_field = manual_lat_field, manual_lon_field
    else:
        lat_field, lon_field = _find_coordinate_fields(df.columns)

    if not lat_field or not lon_field:
        warnings.append(make_warning(
            "Latitude/Longitude fields not found",
            layer_name,
            f"Could not automatically detect coordinate columns. Available columns: {list(df.columns)}",
            "Use the manual field selection option to choose the correct latitude and longitude columns.",
        ))
        return {
            "gdf": None, "warnings": warnings, "success": False,
            "total_rows": total_rows, "valid_rows": 0,
            "needs_manual_fields": True, "available_columns": list(df.columns),
        }

    # Convert to numeric, keeping track of anything that fails
    df["_lat_numeric"] = pd.to_numeric(df[lat_field], errors="coerce")
    df["_lon_numeric"] = pd.to_numeric(df[lon_field], errors="coerce")

    missing_coords = df["_lat_numeric"].isna() | df["_lon_numeric"].isna()
    missing_count = int(missing_coords.sum())

    # Basic sanity range check for lat/lon (do not silently "fix" values,
    # just flag anything clearly out of range)
    out_of_range = (
        (df["_lat_numeric"] < -90) | (df["_lat_numeric"] > 90) |
        (df["_lon_numeric"] < -180) | (df["_lon_numeric"] > 180)
    )
    out_of_range_count = int((out_of_range & ~missing_coords).sum())

    invalid_mask = missing_coords | out_of_range
    valid_df = df[~invalid_mask].copy()
    valid_rows = len(valid_df)

    if missing_count > 0:
        warnings.append(make_warning(
            "Missing or non-numeric coordinates",
            layer_name,
            f"{missing_count} row(s) had a missing or non-numeric latitude/longitude value and were "
            f"excluded from the map. The original CSV data is not modified.",
            "Check those rows in your CSV and fill in valid numeric coordinates if you want them mapped.",
        ))

    if out_of_range_count > 0:
        warnings.append(make_warning(
            "Coordinates out of valid range",
            layer_name,
            f"{out_of_range_count} row(s) had latitude/longitude values outside the valid Earth range "
            f"(latitude -90 to 90, longitude -180 to 180) and were excluded from the map.",
            "Double-check these rows for swapped latitude/longitude columns or data entry mistakes.",
        ))

    # Duplicate detection (same rounded coordinates + same name column if present)
    dup_count = 0
    if valid_rows > 0:
        rounded = valid_df[["_lat_numeric", "_lon_numeric"]].round(6)
        dup_count = int(rounded.duplicated().sum())
        if dup_count > 0:
            warnings.append(make_warning(
                "Possible duplicate locations",
                layer_name,
                f"{dup_count} row(s) share the same coordinates as another row in this file.",
                "This is only a warning — duplicates are not removed automatically. Review them if needed.",
            ))

    if valid_rows == 0:
        warnings.append(make_warning(
            "No valid coordinates found",
            layer_name,
            "None of the rows had usable latitude/longitude values.",
            "Check the coordinate columns in the CSV file.",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": total_rows, "valid_rows": 0}

    geometry = [Point(xy) for xy in zip(valid_df["_lon_numeric"], valid_df["_lat_numeric"])]
    valid_df = valid_df.drop(columns=["_lat_numeric", "_lon_numeric"])
    gdf = gpd.GeoDataFrame(valid_df, geometry=geometry, crs="EPSG:4326")

    return {
        "gdf": gdf,
        "warnings": warnings,
        "success": True,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "lat_field": lat_field,
        "lon_field": lon_field,
    }


# ---------------------------------------------------------------------
# 4. GeoJSON loading
# ---------------------------------------------------------------------

def load_geojson_layer(file_obj, layer_name: str):
    """
    Load a GeoJSON file into a GeoDataFrame using GeoPandas.

    Returns the same shaped dict as load_csv_layer().
    """
    warnings = []

    try:
        raw_bytes = file_obj.read()
        gdf = gpd.read_file(io.BytesIO(raw_bytes))
    except Exception as exc:
        warnings.append(make_warning(
            "Could not read GeoJSON file",
            layer_name,
            f"The file could not be parsed as GeoJSON. Technical detail: {exc}",
            "Make sure the file is valid GeoJSON (you can check it by opening it in geojson.io).",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": 0, "valid_rows": 0}

    if gdf.empty:
        warnings.append(make_warning(
            "Empty GeoJSON file",
            layer_name,
            "The file was read successfully but contains no features.",
            "Check that the correct file was uploaded.",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": 0, "valid_rows": 0}

    total_rows = len(gdf)

    # CRS handling: warn instead of guessing
    if gdf.crs is None:
        warnings.append(make_warning(
            "Missing coordinate reference system (CRS)",
            layer_name,
            "This GeoJSON file does not specify a CRS. It is being treated as EPSG:4326 "
            "(the GeoJSON standard), but this was not confirmed from the file itself.",
            "If your data uses a different CRS, set it correctly in your GIS software before exporting.",
        ))
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    elif gdf.crs.to_string() != "EPSG:4326":
        warnings.append(make_warning(
            "Non-standard CRS detected",
            layer_name,
            f"This file uses {gdf.crs.to_string()}. It has been reprojected to EPSG:4326 for mapping.",
            "No action needed, this is just for your information.",
        ))
        gdf = gdf.to_crs("EPSG:4326")

    # Geometry validity check (warn, do not delete)
    invalid_mask = ~gdf.geometry.is_valid
    invalid_count = int(invalid_mask.sum())
    if invalid_count > 0:
        warnings.append(make_warning(
            "Invalid geometry detected",
            layer_name,
            f"{invalid_count} feature(s) have technically invalid geometry (e.g. self-intersecting polygons).",
            "These features are still loaded. Consider fixing them in QGIS if you see rendering issues.",
        ))

    missing_geom_mask = gdf.geometry.isna()
    missing_geom_count = int(missing_geom_mask.sum())
    valid_geom_gdf = gdf[~missing_geom_mask].copy()

    if missing_geom_count > 0:
        warnings.append(make_warning(
            "Missing geometry",
            layer_name,
            f"{missing_geom_count} feature(s) had no geometry and were excluded from the map.",
            "Check the original GeoJSON file for empty geometry entries.",
        ))

    valid_rows = len(valid_geom_gdf)
    if valid_rows == 0:
        warnings.append(make_warning(
            "No usable features found",
            layer_name,
            "None of the features in this file had usable geometry.",
            "Check the GeoJSON file's geometry.",
        ))
        return {"gdf": None, "warnings": warnings, "success": False, "total_rows": total_rows, "valid_rows": 0}

    return {
        "gdf": valid_geom_gdf,
        "warnings": warnings,
        "success": True,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
    }


# ---------------------------------------------------------------------
# 5. Generic dispatcher
# ---------------------------------------------------------------------

def load_layer(file_obj, layer_name: str, manual_lat_field=None, manual_lon_field=None):
    """
    Load a single uploaded file according to the source type defined
    for its identified layer.
    """
    config = LAYER_CONFIG.get(layer_name)
    if config is None:
        return {
            "gdf": None,
            "warnings": [make_warning(
                "Unknown layer",
                layer_name,
                "This layer name is not one of the 10 expected StudentStay Colombo layers.",
                "Use manual assignment to map this file to a valid layer, or check the filename.",
            )],
            "success": False,
            "total_rows": 0,
            "valid_rows": 0,
        }

    if config["source_type"] == "csv":
        return load_csv_layer(file_obj, layer_name, manual_lat_field, manual_lon_field)
    else:
        return load_geojson_layer(file_obj, layer_name)
