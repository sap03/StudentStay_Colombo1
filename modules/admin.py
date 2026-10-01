"""
admin.py
---------
Stage 11: admin review workflow for accommodation submissions.

- get_submissions(status): fetch rows from Supabase by status
- approve_submission(id) / reject_submission(id): update status
- get_approved_as_gdf(): converts approved submissions into a
  GeoDataFrame so they can be merged onto the public map, alongside
  the static CSV-based accommodation layers.

Only approved listings are ever shown publicly -- pending and
rejected submissions never appear on the map, per the project's
privacy/security requirements.
"""

import geopandas as gpd
from shapely.geometry import Point

from modules.supabase_client import get_supabase_client

TABLE_NAME = "accommodation_submissions"


def get_submissions(status: str | None = None) -> list[dict]:
    """
    Fetch submissions from Supabase, optionally filtered by status
    ('PENDING', 'APPROVED', 'REJECTED'). Returns an empty list (not
    an error) if the table is empty or unreachable -- callers should
    check for that gracefully.
    """
    try:
        client = get_supabase_client()
        query = client.table(TABLE_NAME).select("*")
        if status:
            query = query.eq("status", status)
        response = query.order("submission_date", desc=True).execute()
        return response.data or []
    except Exception:
        return []


def approve_submission(submission_id: str) -> bool:
    """Set a submission's status to APPROVED. Returns True on success."""
    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).update({"status": "APPROVED"}).eq("id", submission_id).execute()
        return True
    except Exception:
        return False


def reject_submission(submission_id: str) -> bool:
    """Set a submission's status to REJECTED (kept in the database, just hidden). Returns True on success."""
    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).update({"status": "REJECTED"}).eq("id", submission_id).execute()
        return True
    except Exception:
        return False


def remove_submission(submission_id: str) -> bool:
    """Permanently delete a submission (e.g. an outdated listing). Returns True on success."""
    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).delete().eq("id", submission_id).execute()
        return True
    except Exception:
        return False


def get_approved_as_gdf() -> gpd.GeoDataFrame:
    """
    Fetch all APPROVED submissions and return them as a GeoDataFrame
    ready to merge onto the map, using the same column style as the
    rest of the app (a 'name' column, EPSG:4326 geometry).
    """
    rows = get_submissions(status="APPROVED")

    if not rows:
        return gpd.GeoDataFrame(columns=["name", "geometry"], geometry="geometry", crs="EPSG:4326")

    records = []
    for row in rows:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if lat is None or lon is None:
            continue
        records.append({
            "name": row.get("title", "Community Submission"),
            "type": row.get("type"),
            "rent_lkr": row.get("rent_lkr"),
            "gender": row.get("gender"),
            "availability": row.get("availability"),
            "facilities": row.get("facilities"),
            "rooms_occupants": row.get("rooms_occupants"),
            "description": row.get("description"),
            "submission_date": row.get("submission_date"),
            "geometry": Point(lon, lat),
        })

    if not records:
        return gpd.GeoDataFrame(columns=["name", "geometry"], geometry="geometry", crs="EPSG:4326")

    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
