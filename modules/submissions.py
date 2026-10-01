"""
submissions.py
----------------
Stage 4: handles submitting a new "Add Boarding" entry to Supabase.

This module does NOT touch the local filesystem at all -- every new
accommodation submission goes straight to the Supabase table
'accommodation_submissions', with status always starting as PENDING.

Photos are intentionally not handled here -- that's Stage 5.
"""

from modules.supabase_client import get_supabase_client

REQUIRED_FIELDS = ["title", "type", "rent_lkr", "gender", "availability", "latitude", "longitude"]


def submit_accommodation(data: dict) -> dict:
    """
    Insert a new accommodation submission into Supabase.

    `data` should contain:
        title, type, rent_lkr, gender, availability,   (required)
        facilities, rooms_occupants, description,       (optional)
        latitude, longitude                              (auto-captured from map click)

    status and submission_date are set automatically by the database
    itself (see the table's default values) -- we don't set them here.

    Returns a dict: {"success": bool, "message": str, "row": <inserted row or None>}
    """
    missing = [f for f in REQUIRED_FIELDS if not data.get(f) and data.get(f) != 0]
    if missing:
        return {
            "success": False,
            "message": f"Missing required field(s): {', '.join(missing)}. "
                       f"Please fill these in before submitting.",
            "row": None,
        }

    # Only send the columns that actually exist in the table --
    # anything else in `data` is ignored rather than causing an error.
    payload = {
        "title": data["title"],
        "type": data["type"],
        "rent_lkr": data["rent_lkr"],
        "gender": data["gender"],
        "availability": data["availability"],
        "facilities": data.get("facilities") or None,
        "rooms_occupants": data.get("rooms_occupants") or None,
        "description": data.get("description") or None,
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        # status and submission_date are left out on purpose --
        # the database sets them automatically (PENDING / now()).
    }

    try:
        client = get_supabase_client()
        response = client.table("accommodation_submissions").insert(payload).execute()

        if response.data:
            return {
                "success": True,
                "message": "Your accommodation was submitted and is now pending review.",
                "row": response.data[0],
            }
        else:
            return {
                "success": False,
                "message": "Submission did not return confirmation -- please check your Supabase table directly.",
                "row": None,
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Could not submit to the database. Details: {e}",
            "row": None,
        }

