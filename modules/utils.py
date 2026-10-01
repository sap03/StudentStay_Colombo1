"""
utils.py
--------
Small helper functions used across the StudentStay Colombo app.

Stage 1 responsibilities:
- Normalize filenames so that small differences (capitalization,
  spaces vs hyphens vs underscores, file extension) do not stop the
  app from recognizing a layer.
- Provide a consistent way to build friendly warning/error messages.
"""

import os
import re


def normalize_name(raw_name: str) -> str:
    """
    Turn a filename (or layer name) into a simple, comparable form.

    Examples:
        "Student-Reported Accommodation.csv" -> "student reported accommodation"
        "existing_boarding_locations.CSV"    -> "existing boarding locations"
        "Higher   Education Institutions"    -> "higher education institutions"

    Steps:
        1. Remove the file extension (if any).
        2. Lowercase everything.
        3. Replace hyphens and underscores with spaces.
        4. Collapse multiple spaces into a single space.
        5. Strip leading/trailing spaces.
    """
    # Remove extension, e.g. "file.csv" -> "file"
    name_without_ext = os.path.splitext(raw_name)[0]

    # Lowercase
    name = name_without_ext.lower()

    # Replace hyphens and underscores with a normal space
    name = name.replace("-", " ").replace("_", " ")

    # Collapse multiple spaces into one, and trim
    name = re.sub(r"\s+", " ", name).strip()

    return name


def make_warning(title: str, layer_or_file: str, detail: str, fix_hint: str) -> dict:
    """
    Build a consistent warning/error dictionary that the UI can display
    in a friendly way (what happened, where, and how to fix it).
    """
    return {
        "title": title,
        "source": layer_or_file,
        "detail": detail,
        "fix_hint": fix_hint,
    }


def format_warning_markdown(warning: dict) -> str:
    """Turn a warning dict into a readable Markdown block for Streamlit."""
    return (
        f"**{warning['title']}** — `{warning['source']}`\n\n"
        f"- What happened: {warning['detail']}\n"
        f"- How to fix it: {warning['fix_hint']}"
    )
