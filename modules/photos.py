# modules/photos.py
# Stage 5 - Photo upload for Add Boarding submissions.
# Photos go straight to Supabase Storage, never saved on the laptop.

import uuid

import streamlit as st

# Use the SAME import fix you applied in reports.py
from modules.supabase_client import get_supabase_client as get_client

BUCKET_NAME = "accommodation-photos"
ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]
MAX_PHOTOS = 5
MAX_SIZE_MB = 5


def render_photo_uploader():
    """
    Show a file uploader for accommodation photos.
    Returns the list of uploaded file objects (in-memory, not yet saved).
    Call upload_photos() with this list AFTER the listing itself is saved,
    so you have the accommodation ID to name the files with.
    """
    files = st.file_uploader(
        "Photos (optional)",
        type=ALLOWED_TYPES,
        accept_multiple_files=True,
        help=f"Up to {MAX_PHOTOS} photos, {MAX_SIZE_MB} MB each. "
             f"Accepted: {', '.join(ALLOWED_TYPES)}.",
    )

    if not files:
        return []

    if len(files) > MAX_PHOTOS:
        st.warning(f"Only the first {MAX_PHOTOS} photos will be uploaded.")
        files = files[:MAX_PHOTOS]

    valid_files = []
    for f in files:
        size_mb = f.size / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            st.warning(f"'{f.name}' is {size_mb:.1f} MB — skipped (max {MAX_SIZE_MB} MB).")
            continue
        valid_files.append(f)

    if valid_files:
        st.caption(f"{len(valid_files)} photo(s) ready to upload.")

    return valid_files


def upload_photos(accommodation_id, files):
    """
    Upload each file to Supabase Storage under a folder named after the
    accommodation ID, and return a list of public URLs.

    Call this AFTER the listing row is saved to Supabase, since it needs
    the accommodation_id to organize the files.
    """
    if not files:
        return []

    client = get_client()
    urls = []

    for f in files:
        extension = f.name.split(".")[-1].lower()
        storage_path = f"{accommodation_id}/{uuid.uuid4().hex}.{extension}"

        try:
            file_bytes = f.getvalue()
            client.storage.from_(BUCKET_NAME).upload(
                storage_path,
                file_bytes,
                {"content-type": f.type or f"image/{extension}"},
            )
            public_url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)
            urls.append(public_url)
        except Exception as e:
            st.warning(f"Could not upload '{f.name}': {e}")

    return urls