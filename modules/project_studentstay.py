"""
accommodation.py
-----------------
Stage 3 logic for StudentStay Colombo: turning raw accommodation rows
(from the "Student-Reported Accommodation" and "Existing Boarding
Locations" CSV layers) into a clean, readable information card,
instead of showing raw GIS attribute tables.

IMPORTANT — matches real data, not a hypothetical schema:
Your actual CSV headers are full survey questions (e.g. "What type of
accommodation you live in?", "How safe do you feel in your boarding
place?"), not short field names like "gender" or "facilities" — those
don't exist in your files at all. So field detection here uses
SUBSTRING matching (does the column header contain a known phrase?)
rather than exact matching, and recognizes the specific
condition/cleanliness/ventilation/safety/issues/distance questions
your survey actually asks, showing them as a "Student Feedback"
section on the card.

If a future CSV DOES use simpler headers (gender, facilities, photo,
verified, etc.) those are still recognized too — this module supports
both styles at once.

Anything not recognized (and not a technical GIS/ID field) is still
shown, just tucked into a collapsible "Additional details" section —
nothing is ever silently deleted.

Photo uploads and Supabase storage are NOT part of this stage — that
is Stage 5. If a CSV happens to already contain a real photo URL, we
simply try to display it; nothing is uploaded or stored here.
"""

import re
import pandas as pd

from modules.utils import normalize_name

# The two layers that should use the accommodation card instead of the
# raw attribute popup.
ACCOMMODATION_LAYERS = {
    "Student-Reported Accommodation",
    "Existing Boarding Locations",
}

# Each canonical field maps to a list of substrings. A column matches a
# field if its normalized header CONTAINS any of these substrings
# (not an exact match) — because real survey headers are full
# questions, e.g. "What type of accommodation you live in?" contains
# the substring "type".
FIELD_ALIASES = {
    "name": ["name", "title"],
    "type": ["type of accommodation", "accommodation type", "room type", "type"],
    "rent": ["monthly rent", "rent range", "rent", "price"],
    "gender": ["gender"],
    "availability": ["availability", "current availability"],
    "description": ["description", "short description", "notes", "details"],
    "verification": ["verification status", "verified", "is verified"],
    "photo": ["photo url", "photo urls", "image url", "photo link", "picture", "photo"],
    "rooms": ["share your room", "share your house", "number of rooms", "occupants", "rooms"],
}

# Survey-style "quality / safety" questions that are genuinely useful
# to a student searching for accommodation. Shown as a "Student
# Feedback" section rather than as header badges, since they're
# ratings/comments rather than core listing facts.
QUALITY_FIELD_ALIASES = {
    "condition": ["physical condition", "physiscal condition", "condition of your boarding", "condition"],
    "cleanliness": ["cleanliness"],
    "ventilation": ["ventilation"],
    "safety": ["how safe do you feel", "safe do you feel", "safety"],
    "issues": ["experienced any issues", "issues"],
    "dist_university": ["from your university", "distance to university", "distance from university"],
    "dist_transit": ["bus stop or railway", "nearest bus stop", "distance to bus", "distance to railway"],
}

QUALITY_LABELS = {
    "condition": "Physical Condition",
    "cleanliness": "Cleanliness & Sanitation",
    "ventilation": "Ventilation & Lighting",
    "safety": "Safety Rating",
    "issues": "Reported Issues",
    "dist_university": "Distance to University (self-reported)",
    "dist_transit": "Distance to Bus/Rail (self-reported)",
}

# Individual facility columns that may exist as separate Yes/No fields
# in a future, simpler-schema CSV (not present in the current survey
# data, but supported in case a listing-style file is used instead).
FACILITY_KEYWORDS = {
    "wifi": "Wi-Fi",
    "wi fi": "Wi-Fi",
    "attached bathroom": "Attached Bathroom",
    "kitchen": "Kitchen",
    "parking": "Parking",
    "laundry": "Laundry",
    "furnished": "Furnished",
    "air conditioning": "Air Conditioning",
    "ac": "Air Conditioning",
}

# Purely technical / GIS / identifier fields that should never be shown
# to a normal user, even in "Additional details".
HIDDEN_FIELDS = {
    "fid", "objectid", "shape leng", "shape area", "index", "unnamed 0",
    "latitude", "lat", "longitude", "lon", "lng", "long", "x", "y", "geometry",
}


def _normalize_field(col: str) -> str:
    """Like utils.normalize_name, but also strips punctuation (question
    marks, parentheses, slashes) so full survey-question headers can be
    matched by substring, e.g. 'How safe do you feel in your boarding
    place?' -> 'how safe do you feel in your boarding place'."""
    base = normalize_name(col)
    base = re.sub(r"[^\w\s]", "", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def _is_technical_or_id_field(col: str) -> bool:
    """True for GIS/internal fields and any *_id-style identifier
    column (Place_ID, Review_ID, submission_id, Object ID, etc.)."""
    norm = _normalize_field(col)
    if norm in HIDDEN_FIELDS:
        return True
    return norm == "id" or norm.endswith(" id")


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return str(value).strip() == ""


def _is_truthy(value) -> bool:
    if _is_empty(value):
        return False
    return str(value).strip().lower() in {"yes", "y", "true", "1", "x", "available"}


def _find_field(row, aliases):
    """
    Search the row's columns for one whose normalized header CONTAINS
    any of the given alias substrings. Returns (column_name, value) or
    (None, None) if nothing matches (or every match is empty).
    """
    for col in row.index:
        norm = _normalize_field(col)
        if any(alias in norm for alias in aliases):
            if not _is_empty(row[col]):
                return col, row[col]
    return None, None


def _find_all_fields(row, aliases, used_cols):
    """Like _find_field, but returns every matching (col, value) pair
    with a non-empty value, and marks each as used."""
    matches = []
    for col in row.index:
        norm = _normalize_field(col)
        if any(alias in norm for alias in aliases) and not _is_empty(row[col]):
            matches.append((col, row[col]))
            used_cols.add(col)
    return matches


def _extract_facilities(row, used_cols: set):
    """Collect facility tags from either a combined column (e.g.
    'Facilities: Wi-Fi, Kitchen') or separate Yes/No columns. Not
    present in the current survey-style CSVs, but supported for a
    future listing-style file."""
    tags = []

    for col in row.index:
        norm = _normalize_field(col)
        if norm in ("facilities", "amenities"):
            value = row[col]
            if not _is_empty(value):
                parts = re.split(r"[;,/]", str(value))
                tags.extend(p.strip() for p in parts if p.strip())
            used_cols.add(col)

    for col in row.index:
        norm = _normalize_field(col)
        if norm in FACILITY_KEYWORDS and _is_truthy(row[col]):
            tags.append(FACILITY_KEYWORDS[norm])
            used_cols.add(col)

    seen = set()
    unique_tags = []
    for tag in tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            unique_tags.append(tag)
    return unique_tags


def _format_rent(value):
    """Try to format as currency; if it's a text range (e.g. 'Below
    10,000 LKR' or '20,000 – 30,000 LKR', as in the real survey data),
    just show it as-is."""
    try:
        amount = float(str(value).replace(",", "").replace("Rs.", "").strip())
        return f"Rs. {amount:,.0f}"
    except (ValueError, TypeError):
        return str(value).strip()


def _availability_badge(value):
    text = str(value).strip().lower()
    if "full" in text:
        return "Currently Full", "#777"
    if "limited" in text:
        return "Limited Availability", "#c77700"
    if "avail" in text:
        return "Available", "#2e8b57"
    return str(value).strip().title() or "Unknown", "#777"


def _pill(text, bg="#eee", fg="#333"):
    return (
        f"<span style='background:{bg};color:{fg};padding:2px 9px;"
        f"border-radius:10px;font-size:11px;margin-right:4px;"
        f"display:inline-block;margin-bottom:4px'>{text}</span>"
    )


def _friendly_field_name(col: str) -> str:
    cleaned = re.sub(r"[_\-]+", " ", str(col)).strip()
    return cleaned.title() if cleaned else str(col)


def build_accommodation_card_html(row, layer_name: str = "") -> str:
    """
    Build the clean accommodation information card HTML for a single
    row from an accommodation layer (Student-Reported Accommodation or
    Existing Boarding Locations).
    """
    used_cols = {"geometry"}
    html = ["<div style='font-size:13px; max-width:290px;'>"]

    # --- Name / title ---------------------------------------------------
    name_col, name_val = _find_field(row, FIELD_ALIASES["name"])
    if name_col:
        used_cols.add(name_col)

    if name_val and not _is_empty(name_val):
        title = str(name_val).strip()
    else:
        # No name column (e.g. the anonymous Student-Reported Accommodation
        # survey) — fall back to a friendly identifier using whatever
        # ID-like column exists, instead of a generic "Accommodation".
        id_col, id_val = None, None
        for col in row.index:
            if _normalize_field(col).endswith(" id") or _normalize_field(col) == "id":
                id_col, id_val = col, row[col]
                break
        if id_col and not _is_empty(id_val):
            used_cols.add(id_col)
            try:
                id_display = f"{int(float(id_val))}"
            except (ValueError, TypeError):
                id_display = str(id_val)
            title = f"Student-Reported Location #{id_display}"
        else:
            title = "Reported Accommodation"

    # --- Verification badge (shown next to the name, if present) -----
    verif_col, verif_val = _find_field(row, FIELD_ALIASES["verification"])
    verified_badge = ""
    if verif_col:
        used_cols.add(verif_col)
        if _is_truthy(verif_val):
            verified_badge = " " + _pill("✓ Verified", bg="#e6f4ea", fg="#2e8b57")

    html.append(
        f"<div style='font-size:15px;font-weight:bold;margin-bottom:6px'>{title}{verified_badge}</div>"
    )

    # --- Badges: type / gender / availability -------------------------
    badges = []

    type_col, type_val = _find_field(row, FIELD_ALIASES["type"])
    if type_col:
        used_cols.add(type_col)
        if not _is_empty(type_val):
            badges.append(_pill(str(type_val).strip().title()))

    gender_col, gender_val = _find_field(row, FIELD_ALIASES["gender"])
    if gender_col:
        used_cols.add(gender_col)
        if not _is_empty(gender_val):
            badges.append(_pill(str(gender_val).strip().title(), bg="#eef2ff", fg="#3b4cca"))

    avail_col, avail_val = _find_field(row, FIELD_ALIASES["availability"])
    if avail_col:
        used_cols.add(avail_col)
        if not _is_empty(avail_val):
            label, color = _availability_badge(avail_val)
            badges.append(_pill(label, bg="#f2f2f2", fg=color))

    if badges:
        html.append(f"<div style='margin-bottom:6px'>{''.join(badges)}</div>")

    # --- Rent -------------------------------------------------------------
    rent_col, rent_val = _find_field(row, FIELD_ALIASES["rent"])
    if rent_col:
        used_cols.add(rent_col)
        if not _is_empty(rent_val):
            html.append(
                f"<div style='margin-bottom:6px'><b>{_format_rent(rent_val)}</b> / month</div>"
            )

    # --- Rooms / occupants ------------------------------------------------
    rooms_col, rooms_val = _find_field(row, FIELD_ALIASES["rooms"])
    if rooms_col:
        used_cols.add(rooms_col)
        if not _is_empty(rooms_val):
            html.append(f"<div style='margin-bottom:6px;color:#444'>Sharing: {rooms_val}</div>")

    # --- Facilities (only present in listing-style CSVs) -------------
    facility_tags = _extract_facilities(row, used_cols)
    if facility_tags:
        tag_html = "".join(_pill(t, bg="#eaf4ff", fg="#1f5fa8") for t in facility_tags)
        html.append(f"<div style='margin-bottom:6px'>{tag_html}</div>")

    # --- Description --------------------------------------------------
    desc_col, desc_val = _find_field(row, FIELD_ALIASES["description"])
    if desc_col:
        used_cols.add(desc_col)
        if not _is_empty(desc_val):
            html.append(f"<div style='margin-bottom:6px;color:#444'>{desc_val}</div>")

    # --- Photo (only if a real URL already exists in the data) -------
    photo_col, photo_val = _find_field(row, FIELD_ALIASES["photo"])
    if photo_col:
        used_cols.add(photo_col)
        if not _is_empty(photo_val) and str(photo_val).strip().lower().startswith("http"):
            html.append(
                f"<img src='{photo_val}' style='width:100%;max-width:250px;"
                f"border-radius:6px;margin-bottom:6px;' "
                f"onerror=\"this.style.display='none'\">"
            )

    # --- Student Feedback: condition / cleanliness / ventilation / -----
    # safety / issues / self-reported distances. This is where your
    # real survey data actually lives, so it gets its own clearly
    # labeled section rather than being buried in "Additional details".
    feedback_rows = []
    for key, aliases in QUALITY_FIELD_ALIASES.items():
        col, val = _find_field(row, aliases)
        if col:
            used_cols.add(col)
            if not _is_empty(val):
                feedback_rows.append((QUALITY_LABELS[key], str(val).strip()))

    if feedback_rows:
        rows_html = "".join(
            f"<tr><td style='padding-right:8px;color:#555;white-space:nowrap'><b>{label}</b></td>"
            f"<td>{value}</td></tr>"
            for label, value in feedback_rows
        )
        html.append(
            "<div style='margin-top:4px;margin-bottom:6px;padding:6px 8px;"
            "background:#f7f7f7;border-radius:6px;'>"
            "<div style='font-weight:bold;color:#555;margin-bottom:3px;font-size:11px;"
            "text-transform:uppercase;letter-spacing:0.3px;'>Student Feedback</div>"
            f"<table style='font-size:12px'>{rows_html}</table></div>"
        )

    # --- Location (derived from the actual point geometry) -----------
    geom = row.geometry
    if geom is not None and not geom.is_empty:
        html.append(
            f"<div style='color:#777;font-size:11px;margin-bottom:6px'>"
            f"Location: {geom.y:.5f}, {geom.x:.5f}</div>"
        )

    # --- Anything left over: shown, not hidden, just tucked away ------
    leftover = [
        col for col in row.index
        if col not in used_cols and not _is_technical_or_id_field(col) and not _is_empty(row[col])
    ]
    if leftover:
        rows_html = "".join(
            f"<tr><td style='padding-right:8px;color:#555'><b>{_friendly_field_name(c)}</b></td>"
            f"<td>{row[c]}</td></tr>"
            for c in leftover
        )
        html.append(
            "<details style='margin-top:4px'><summary style='cursor:pointer;color:#555'>"
            "Additional details</summary>"
            f"<table style='margin-top:4px'>{rows_html}</table></details>"
        )

    html.append("</div>")
    return "".join(html)
