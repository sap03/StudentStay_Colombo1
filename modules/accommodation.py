
"""
accommodation.py

Stage 3 logic for StudentStay Colombo: turning raw accommodation rows
(from the "Student-Reported Accommodation", "Existing Boarding
Locations", and "Community Submissions" layers) into a clean,
readable information card instead of showing raw GIS attribute tables.
"""

import re

import pandas as pd

from modules.utils import normalize_name
from modules.proximity import FACILITY_LAYER_CONFIG, format_distance


# The accommodation layers that should use the accommodation card
# instead of the raw attribute popup.
ACCOMMODATION_LAYERS = {
    "Student-Reported Accommodation",
    "Existing Boarding Locations",
    "Community Submissions",
}


# Each canonical field maps to a list of substrings.
FIELD_ALIASES = {
    "name": ["name", "title"],
    "type": [
        "type of accommodation",
        "accommodation type",
        "room type",
        "type",
    ],
    "rent": ["monthly rent", "rent range", "rent", "price"],
    "gender": ["gender"],
    "availability": ["availability", "current availability"],
    "description": [
        "description",
        "short description",
        "notes",
        "details",
    ],
    "verification": [
        "verification status",
        "verified",
        "is verified",
    ],
    "photo": [
        "photo url",
        "photo urls",
        "image url",
        "photo link",
        "picture",
        "photo",
    ],
    "rooms": [
        "share your room",
        "share your house",
        "number of rooms",
        "occupants",
        "rooms",
    ],
}


# Survey-style quality / safety questions.
QUALITY_FIELD_ALIASES = {
    "condition": [
        "physical condition",
        "physiscal condition",
        "condition of your boarding",
        "condition",
    ],
    "cleanliness": ["cleanliness"],
    "ventilation": ["ventilation"],
    "safety": [
        "how safe do you feel",
        "safe do you feel",
        "safety",
    ],
    "issues": [
        "experienced any issues",
        "issues",
    ],
    "dist_university": [
        "from your university",
        "distance to university",
        "distance from university",
    ],
    "dist_transit": [
        "bus stop or railway",
        "nearest bus stop",
        "distance to bus",
        "distance to railway",
    ],
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


# Individual facility columns that may exist as separate Yes/No fields.
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
# to a normal user.
HIDDEN_FIELDS = {
    "fid",
    "objectid",
    "shape leng",
    "shape area",
    "index",
    "unnamed 0",
    "latitude",
    "lat",
    "longitude",
    "lon",
    "lng",
    "long",
    "x",
    "y",
    "geometry",
}


def _normalize_field(col: str) -> str:
    """Normalize a field name so full survey-question headers can be matched."""

    base = normalize_name(col)
    base = re.sub(r"[^\w\s]", "", base)
    base = re.sub(r"\s+", " ", base).strip()

    return base


def _is_technical_or_id_field(col: str) -> bool:
    """True for GIS/internal fields and ID-style identifier columns."""

    norm = _normalize_field(col)

    if norm in HIDDEN_FIELDS:
        return True

    return norm == "id" or norm.endswith(" id")


def _is_empty(value) -> bool:
    """Return True when a value is None, NaN, or an empty string."""

    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def _is_truthy(value) -> bool:
    """Return True for common Yes/True/Available values."""

    if _is_empty(value):
        return False

    return str(value).strip().lower() in {
        "yes",
        "y",
        "true",
        "1",
        "x",
        "available",
    }


def _find_field(row, aliases):
    """
    Search the row's columns for one whose normalized header contains
    any of the given alias substrings.
    """

    for col in row.index:
        norm = _normalize_field(col)

        if any(alias in norm for alias in aliases):
            if not _is_empty(row[col]):
                return col, row[col]

    return None, None


def _find_all_fields(row, aliases, used_cols):
    """Return every matching non-empty field."""

    matches = []

    for col in row.index:
        norm = _normalize_field(col)

        if (
            any(alias in norm for alias in aliases)
            and not _is_empty(row[col])
        ):
            matches.append((col, row[col]))
            used_cols.add(col)

    return matches


def _extract_facilities(row, used_cols: set):
    """Collect facility tags from combined or separate facility columns."""

    tags = []

    # Combined facilities / amenities column.
    for col in row.index:
        norm = _normalize_field(col)

        if norm in ("facilities", "amenities"):
            value = row[col]

            if not _is_empty(value):
                parts = re.split(r"[;,/]", str(value))

                tags.extend(
                    p.strip()
                    for p in parts
                    if p.strip()
                )

            used_cols.add(col)

    # Separate Yes/No facility columns.
    for col in row.index:
        norm = _normalize_field(col)

        if norm in FACILITY_KEYWORDS and _is_truthy(row[col]):
            tags.append(FACILITY_KEYWORDS[norm])
            used_cols.add(col)

    # Remove duplicates while preserving order.
    seen = set()
    unique_tags = []

    for tag in tags:
        key = tag.lower()

        if key not in seen:
            seen.add(key)
            unique_tags.append(tag)

    return unique_tags


def _format_rent(value):
    """Try to format numeric rent values as currency."""

    try:
        amount = float(
            str(value)
            .replace(",", "")
            .replace("Rs.", "")
            .strip()
        )

        return f"Rs. {amount:,.0f}"

    except (ValueError, TypeError):
        return str(value).strip()


def _availability_badge(value):
    """Return availability label and display color."""

    text = str(value).strip().lower()

    if "full" in text:
        return "Currently Full", "#777"

    if "limited" in text:
        return "Limited Availability", "#c77700"

    if "avail" in text:
        return "Available", "#2e8b57"

    return str(value).strip().title() or "Unknown", "#777"


def _pill(text, bg="#eee", fg="#333"):
    """Create a small HTML pill."""

    return (
        f"<span style='background:{bg};color:{fg};"
        f"padding:2px 9px;border-radius:10px;font-size:11px;"
        f"margin-right:4px;display:inline-block;"
        f"margin-bottom:4px'>{text}</span>"
    )


def _friendly_field_name(col: str) -> str:
    """Convert raw field names into readable labels."""

    cleaned = re.sub(r"[_\-]+", " ", str(col)).strip()

    return cleaned.title() if cleaned else str(col)


def build_accommodation_card_html(
    row,
    layer_name: str = "",
) -> str:
    """
    Build the clean accommodation information card HTML for a single row.
    """

    used_cols = {"geometry"}

    html = [
        "<div style='font-size:13px; max-width:290px;'>"
    ]

    # ------------------------------------------------------------------
    # Name / title
    # ------------------------------------------------------------------

    name_col, name_val = _find_field(
        row,
        FIELD_ALIASES["name"],
    )

    if name_col:
        used_cols.add(name_col)

    if name_val and not _is_empty(name_val):
        title = str(name_val).strip()

    else:
        # Fall back to an ID-like field.
        id_col, id_val = None, None

        for col in row.index:
            norm = _normalize_field(col)

            if norm.endswith(" id") or norm == "id":
                id_col = col
                id_val = row[col]
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

    # ------------------------------------------------------------------
    # Verification badge
    # ------------------------------------------------------------------

    verif_col, verif_val = _find_field(
        row,
        FIELD_ALIASES["verification"],
    )

    verified_badge = ""

    if verif_col:
        used_cols.add(verif_col)

        if _is_truthy(verif_val):
            verified_badge = " " + _pill(
                "✓ Verified",
                bg="#e6f4ea",
                fg="#2e8b57",
            )

    html.append(
        f"<div style='font-size:15px;font-weight:bold;"
        f"margin-bottom:6px'>{title}{verified_badge}</div>"
    )

    # ------------------------------------------------------------------
    # Badges: type / gender / availability
    # ------------------------------------------------------------------

    badges = []

    type_col, type_val = _find_field(
        row,
        FIELD_ALIASES["type"],
    )

    if type_col:
        used_cols.add(type_col)

        if not _is_empty(type_val):
            badges.append(
                _pill(
                    str(type_val).strip().title()
                )
            )

    gender_col, gender_val = _find_field(
        row,
        FIELD_ALIASES["gender"],
    )

    if gender_col:
        used_cols.add(gender_col)

        if not _is_empty(gender_val):
            badges.append(
                _pill(
                    str(gender_val).strip().title(),
                    bg="#eef2ff",
                    fg="#3b4cca",
                )
            )

    avail_col, avail_val = _find_field(
        row,
        FIELD_ALIASES["availability"],
    )

    if avail_col:
        used_cols.add(avail_col)

        if not _is_empty(avail_val):
            label, color = _availability_badge(
                avail_val
            )

            badges.append(
                _pill(
                    label,
                    bg="#f2f2f2",
                    fg=color,
                )
            )

    if badges:
        html.append(
            f"<div style='margin-bottom:6px'>"
            f"{''.join(badges)}</div>"
        )

    # ------------------------------------------------------------------
    # Rent
    # ------------------------------------------------------------------

    rent_col, rent_val = _find_field(
        row,
        FIELD_ALIASES["rent"],
    )

    if rent_col:
        used_cols.add(rent_col)

        if not _is_empty(rent_val):
            html.append(
                f"<div style='margin-bottom:6px'>"
                f"<b>{_format_rent(rent_val)}</b> / month"
                f"</div>"
            )

    # ------------------------------------------------------------------
    # Rooms / occupants
    # ------------------------------------------------------------------

    rooms_col, rooms_val = _find_field(
        row,
        FIELD_ALIASES["rooms"],
    )

    if rooms_col:
        used_cols.add(rooms_col)

        if not _is_empty(rooms_val):
            html.append(
                f"<div style='margin-bottom:6px;color:#444'>"
                f"Sharing: {rooms_val}</div>"
            )

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    facility_tags = _extract_facilities(
        row,
        used_cols,
    )

    if facility_tags:

        tag_html = "".join(
            _pill(
                t,
                bg="#eaf4ff",
                fg="#1f5fa8",
            )
            for t in facility_tags
        )

        html.append(
            f"<div style='margin-bottom:6px'>{tag_html}</div>"
        )

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    desc_col, desc_val = _find_field(
        row,
        FIELD_ALIASES["description"],
    )

    if desc_col:
        used_cols.add(desc_col)

        if not _is_empty(desc_val):
            html.append(
                f"<div style='margin-bottom:6px;color:#444'>"
                f"{desc_val}</div>"
            )

    # ------------------------------------------------------------------
    # Photo
    # ------------------------------------------------------------------

    photo_col, photo_val = _find_field(
        row,
        FIELD_ALIASES["photo"],
    )

    if photo_col:
        used_cols.add(photo_col)

        if (
            not _is_empty(photo_val)
            and str(photo_val).strip().lower().startswith("http")
        ):
            html.append(
                f"<img src='{photo_val}' "
                f"style='width:100%;max-width:250px;"
                f"border-radius:6px;margin-bottom:6px;' "
                f"onerror=\"this.style.display='none'\">"
            )

    # ------------------------------------------------------------------
    # Student Feedback
    # ------------------------------------------------------------------

    feedback_rows = []

    for key, aliases in QUALITY_FIELD_ALIASES.items():

        col, val = _find_field(
            row,
            aliases,
        )

        if col:
            used_cols.add(col)

            if not _is_empty(val):
                feedback_rows.append(
                    (
                        QUALITY_LABELS[key],
                        str(val).strip(),
                    )
                )

    if feedback_rows:

        rows_html = "".join(
            f"<tr>"
            f"<td style='padding-right:8px;color:#555;"
            f"white-space:nowrap'>"
            f"<b>{label}</b>"
            f"</td>"
            f"<td>{value}</td>"
            f"</tr>"
            for label, value in feedback_rows
        )

        html.append(
            "<div style='margin-top:4px;margin-bottom:6px;"
            "padding:6px 8px;background:#f7f7f7;"
            "border-radius:6px;'>"
            "<div style='font-weight:bold;color:#555;"
            "margin-bottom:3px;font-size:11px;"
            "text-transform:uppercase;letter-spacing:0.3px;'>"
            "Student Feedback</div>"
            f"<table style='font-size:12px'>{rows_html}</table>"
            "</div>"
        )

    # ------------------------------------------------------------------
    # Nearest Facilities
    # ------------------------------------------------------------------

    facility_rows = []

    for layer_name, (col_name, label) in FACILITY_LAYER_CONFIG.items():

        if (
            col_name in row.index
            and not _is_empty(row[col_name])
        ):

            used_cols.add(col_name)

            facility_rows.append(
                (
                    label,
                    format_distance(row[col_name]),
                )
            )

    if facility_rows:

        rows_html = "".join(
            f"<tr>"
            f"<td style='padding-right:8px;color:#555;"
            f"white-space:nowrap'>{label}</td>"
            f"<td style='text-align:right;font-weight:500'>"
            f"{dist}</td>"
            f"</tr>"
            for label, dist in facility_rows
        )

        html.append(
            "<div style='margin-top:4px;margin-bottom:6px;"
            "padding:6px 8px;background:#eaf4ff;"
            "border-radius:6px;'>"
            "<div style='font-weight:bold;color:#1f5fa8;"
            "margin-bottom:3px;font-size:11px;"
            "text-transform:uppercase;letter-spacing:0.3px;'>"
            "Nearest Facilities</div>"
            f"<table style='font-size:12px;width:100%'>"
            f"{rows_html}</table>"
            "</div>"
        )

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    geom = row.geometry

    if geom is not None and not geom.is_empty:

        html.append(
            f"<div style='color:#777;font-size:11px;"
            f"margin-bottom:6px'>"
            f"Location: {geom.y:.5f}, {geom.x:.5f}"
            f"</div>"
        )

    # ------------------------------------------------------------------
    # Additional details
    # ------------------------------------------------------------------

    leftover = [
        col
        for col in row.index
        if (
            col not in used_cols
            and not _is_technical_or_id_field(col)
            and not _is_empty(row[col])
        )
    ]

    if leftover:

        rows_html = "".join(
            f"<tr>"
            f"<td style='padding-right:8px;color:#555'>"
            f"<b>{_friendly_field_name(c)}</b>"
            f"</td>"
            f"<td>{row[c]}</td>"
            f"</tr>"
            for c in leftover
        )

        html.append(
            "<details style='margin-top:4px'>"
            "<summary style='cursor:pointer;color:#555'>"
            "Additional details"
            "</summary>"
            f"<table style='margin-top:4px'>{rows_html}</table>"
            "</details>"
        )

    html.append("</div>")

    return "".join(html)
