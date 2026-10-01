"""
StudentStay Colombo — main app
================================
Public-facing layout:
- GIS layers load automatically from data/development.
- Approved community submissions load automatically from Supabase.
- Manual upload remains available inside Developer tools.
- Explore Map, Find Near University, Search & Filter, and Add Boarding
  are separated into tabs.

Developer tools and Admin are hidden from normal visitors. To access
them, visit this app with ?dev=YOUR_SECRET appended to the URL, where
YOUR_SECRET matches DEV_ACCESS_KEY in secrets.toml.

Run with:
    streamlit run app.py
"""

import os
import streamlit as st
import folium
from streamlit_folium import st_folium

from modules import data_loader
from modules.map import build_map
from modules.utils import format_warning_markdown
from modules.submissions import submit_accommodation
from modules.photos import render_photo_uploader, upload_photos
from modules.duplicates import find_nearby_accommodation


st.set_page_config(
    page_title="StudentStay Colombo",
    layout="wide",
    page_icon="🏠"
)

DEV_FOLDER = "data/development"


# -----------------------------------------------------------------
# Session state setup
# -----------------------------------------------------------------
if "layers" not in st.session_state:
    st.session_state.layers = {}

if "layer_info" not in st.session_state:
    st.session_state.layer_info = {}

if "all_warnings" not in st.session_state:
    st.session_state.all_warnings = []

if "manual_assignments" not in st.session_state:
    st.session_state.manual_assignments = {}

if "manual_coord_fields" not in st.session_state:
    st.session_state.manual_coord_fields = {}

if "add_boarding_location" not in st.session_state:
    st.session_state.add_boarding_location = None

if "auto_load_attempted" not in st.session_state:
    st.session_state.auto_load_attempted = False


# -----------------------------------------------------------------
# Core loading logic
# -----------------------------------------------------------------
def load_files_from_paths(file_sources):
    """
    file_sources: list of (filename, file_like_object) tuples.
    Loads each into st.session_state.layers / layer_info / all_warnings.
    """

    st.session_state.layers = {}
    st.session_state.layer_info = {}
    st.session_state.all_warnings = []

    for filename, file_obj in file_sources:

        layer_name = (
            st.session_state.manual_assignments.get(filename)
            or data_loader.identify_layer(filename)
        )

        if not layer_name:

            st.session_state.all_warnings.append({
                "title": "File not assigned to a layer",
                "source": filename,
                "detail": (
                    "This file's name did not match any known layer."
                ),
                "fix_hint": (
                    "Rename the file to match one of the expected "
                    "layer names, or assign it manually in Developer tools."
                ),
            })

            continue

        manual_lat, manual_lon = (
            st.session_state.manual_coord_fields.get(
                filename,
                (None, None)
            )
        )

        result = data_loader.load_layer(
            file_obj,
            layer_name,
            manual_lat_field=manual_lat,
            manual_lon_field=manual_lon,
        )

        st.session_state.all_warnings.extend(
            [
                {
                    **w,
                    "source": f"{layer_name} ({filename})"
                }
                for w in result["warnings"]
            ]
        )

        if result["success"]:

            gdf = result["gdf"]

            st.session_state.layers[layer_name] = gdf

            st.session_state.layer_info[layer_name] = {
                "features": len(gdf),
                "geometry": (
                    gdf.geom_type.mode()[0]
                    if not gdf.empty
                    else "Unknown"
                ),
                "crs": str(gdf.crs),
                "status": "Loaded",
                "total_rows_in_file": result["total_rows"],
            }

        else:

            st.session_state.layer_info[layer_name] = {
                "features": 0,
                "geometry": "-",
                "crs": "-",
                "status": "Failed",
                "total_rows_in_file": result.get(
                    "total_rows",
                    0
                ),
            }

    # Calculate nearest facilities for accommodation layers
    from modules.proximity import compute_nearest_facilities

    for acc_layer in [
        "Student-Reported Accommodation",
        "Existing Boarding Locations",
    ]:

        if acc_layer in st.session_state.layers:

            st.session_state.layers[acc_layer] = (
                compute_nearest_facilities(
                    st.session_state.layers[acc_layer],
                    st.session_state.layers,
                )
            )


# -----------------------------------------------------------------
# Auto-load from data/development on first run
# -----------------------------------------------------------------
if not st.session_state.auto_load_attempted:

    st.session_state.auto_load_attempted = True

    if os.path.isdir(DEV_FOLDER):

        local_paths = [
            os.path.join(DEV_FOLDER, fn)
            for fn in os.listdir(DEV_FOLDER)
            if fn.lower().endswith(
                (".csv", ".geojson", ".json")
            )
        ]

        if local_paths:

            sources = []

            for path in local_paths:

                filename = os.path.basename(path)

                sources.append(
                    (filename, open(path, "rb"))
                )

            load_files_from_paths(sources)

            for _, f in sources:
                f.close()


# -----------------------------------------------------------------
# Merge approved community submissions from Supabase
# -----------------------------------------------------------------
from modules.admin import get_approved_as_gdf

approved_gdf = get_approved_as_gdf()

if not approved_gdf.empty:

    st.session_state.layers[
        "Community Submissions"
    ] = approved_gdf


# -----------------------------------------------------------------
# Hero banner
# -----------------------------------------------------------------
total_locations = (
    st.session_state.layer_info.get(
        "Student-Reported Accommodation",
        {}
    ).get("features", 0)
    +
    st.session_state.layer_info.get(
        "Existing Boarding Locations",
        {}
    ).get("features", 0)
)

# Add approved community submissions to accommodation count
if not approved_gdf.empty:
    total_locations += len(approved_gdf)


universities = (
    st.session_state.layer_info.get(
        "Higher Education Institutions",
        {}
    ).get("features", 0)
)


loaded_count = sum(
    1
    for info in st.session_state.layer_info.values()
    if info.get("status") == "Loaded"
)


st.markdown(
"""
<div style="background: linear-gradient(135deg, #1a5276, #154360); padding: 28px 30px; border-radius: 12px; color: white; margin-bottom: 18px;">
<div style="font-size: 1.8rem; font-weight: 700;">🏠 StudentStay Colombo</div>
<div style="opacity: 0.9; margin-top: 4px;">Find a place to stay. Find what you need around it.</div>
</div>
""",
unsafe_allow_html=True,
)


col1, col2, col3 = st.columns(3)


col1.metric(
    "Accommodation locations",
    total_locations
)


col2.metric(
    "Universities mapped",
    universities
)


col3.metric(
    "Layers loaded",
    f"{loaded_count} / 10"
)


# -----------------------------------------------------------------
# Developer access check
# -----------------------------------------------------------------
# Normal visitors never see Developer tools, Admin, or raw data
# warnings. To reach them, open this app with ?dev=YOUR_SECRET in
# the URL, where YOUR_SECRET matches DEV_ACCESS_KEY in secrets.toml.
is_dev = st.query_params.get("dev") == st.secrets.get("DEV_ACCESS_KEY")


if not st.session_state.layers:

    if is_dev:
        st.warning(
            "No data is loaded yet. Open **Developer tools** in the "
            "sidebar and load your files from there."
        )
    else:
        st.info(
            "No accommodation data is currently available. "
            "Please check back soon."
        )


# -----------------------------------------------------------------
# Warnings (developer-only)
# -----------------------------------------------------------------
if is_dev and st.session_state.all_warnings:

    with st.expander(
        f"⚠️ Data warnings ({len(st.session_state.all_warnings)})",
        expanded=False
    ):

        for w in st.session_state.all_warnings:

            st.markdown(
                format_warning_markdown(w)
            )

            st.markdown("---")


# -----------------------------------------------------------------
# Main content: tabs
# -----------------------------------------------------------------
tab_explore, tab_uni, tab_search, tab_dash, tab_compare, tab_report, tab_add = st.tabs(
    [
        "🗺️ Explore Map",
        "🎓 Find Near University",
        "🔍 Search & Filter",
        "📊 Dashboard",
        "⚖️ Compare",
        "🚩 Report Listing",
        "➕ Add Boarding"
    ]
)


# -----------------------------------------------------------------
# Explore Map
# -----------------------------------------------------------------
with tab_explore:

    if st.session_state.layers:

        st.caption(
            "Click any point or boundary to see its details. "
            "Use the layer control to show/hide layers."
        )

        fmap = build_map(
            st.session_state.layers
        )

        st_folium(
            fmap,
            width=None,
            height=620,
            returned_objects=[]
        )

    else:

        st.info(
            "The map will appear here once data is loaded."
        )


# -----------------------------------------------------------------
# Find Near University
# -----------------------------------------------------------------
with tab_uni:

    from modules.university_search import (
        get_university_options,
        find_accommodation_within_radius,
        DISTANCE_OPTIONS_M
    )

    from modules.map import build_university_search_map

    uni_options = get_university_options(
        st.session_state.layers
    )

    if not uni_options:

        st.info(
            "Universities layer isn't loaded yet."
        )

    else:

        labels = [
            f"{name}"
            for name, lat, lon in uni_options
        ]

        selected_label = st.selectbox(
            "Choose your university",
            labels
        )

        selected_distance_label = st.selectbox(
            "Search radius",
            list(DISTANCE_OPTIONS_M.keys()),
            index=2
        )

        if st.button(
            "Search",
            type="primary",
            key="university_search_button"
        ):

            selected = next(
                u
                for u in uni_options
                if u[0] == selected_label
            )

            _, uni_lat, uni_lon = selected

            radius_m = DISTANCE_OPTIONS_M[
                selected_distance_label
            ]

            accommodation_layers = {
                k: v
                for k, v in st.session_state.layers.items()
                if k in (
                    "Student-Reported Accommodation",
                    "Existing Boarding Locations",
                    "Community Submissions"
                )
            }

            filtered = find_accommodation_within_radius(
                uni_lat,
                uni_lon,
                radius_m,
                accommodation_layers
            )

            fmap, count = build_university_search_map(
                uni_lat,
                uni_lon,
                selected_label,
                radius_m,
                filtered
            )

            st.success(
                f"Found {count} accommodation option(s) "
                f"within {selected_distance_label} "
                f"of {selected_label}"
            )

            st_folium(
                fmap,
                width=None,
                height=600,
                returned_objects=[]
            )


# -----------------------------------------------------------------
# Search & Filter
# -----------------------------------------------------------------
with tab_search:

    st.subheader(
        "🔍 Search & Filter"
    )

    st.caption(
        "Search accommodation by name, type, gender, "
        "availability, rent, and facilities."
    )

    # -------------------------------------------------------------
    # Collect accommodation layers
    # -------------------------------------------------------------
    accommodation_layers = {
        k: v
        for k, v in st.session_state.layers.items()
        if k in (
            "Student-Reported Accommodation",
            "Existing Boarding Locations",
            "Community Submissions"
        )
        and v is not None
        and not v.empty
    }

    if not accommodation_layers:

        st.info(
            "No accommodation data is currently loaded."
        )

    else:

        # ---------------------------------------------------------
        # Search text
        # ---------------------------------------------------------
        search_text = st.text_input(
            "Search by accommodation name",
            placeholder="e.g. boarding, room, annex..."
        )

        # ---------------------------------------------------------
        # Helper to find a field from possible names
        # ---------------------------------------------------------
        def find_column(gdf, possible_names):

            columns_lower = {
                str(col).lower().strip(): col
                for col in gdf.columns
            }

            for name in possible_names:

                if name.lower() in columns_lower:
                    return columns_lower[name.lower()]

            return None

        # ---------------------------------------------------------
        # Get available filter values
        # ---------------------------------------------------------
        all_types = set()
        all_genders = set()
        all_availability = set()

        for gdf in accommodation_layers.values():

            type_col = find_column(
                gdf,
                [
                    "type",
                    "accommodation_type",
                    "acc_type"
                ]
            )

            gender_col = find_column(
                gdf,
                [
                    "gender",
                    "gender_preference",
                    "preferred_gender"
                ]
            )

            availability_col = find_column(
                gdf,
                [
                    "availability",
                    "status"
                ]
            )

            if type_col:
                for value in gdf[type_col].dropna():
                    value = str(value).strip()
                    if value:
                        all_types.add(value)

            if gender_col:
                for value in gdf[gender_col].dropna():
                    value = str(value).strip()
                    if value:
                        all_genders.add(value)

            if availability_col:
                for value in gdf[availability_col].dropna():
                    value = str(value).strip()
                    if value:
                        all_availability.add(value)

        # ---------------------------------------------------------
        # Filter controls
        # ---------------------------------------------------------
        col1, col2, col3 = st.columns(3)

        with col1:

            selected_type = st.selectbox(
                "Accommodation type",
                ["All"] + sorted(all_types)
            )

        with col2:

            selected_gender = st.selectbox(
                "Gender preference",
                ["All"] + sorted(all_genders)
            )

        with col3:

            selected_availability = st.selectbox(
                "Availability",
                ["All"] + sorted(all_availability)
            )

        col4, col5 = st.columns(2)

        with col4:

            min_rent = st.number_input(
                "Minimum monthly rent (LKR)",
                min_value=0,
                value=0,
                step=500
            )

        with col5:

            max_rent = st.number_input(
                "Maximum monthly rent (LKR)",
                min_value=0,
                value=100000,
                step=500
            )

        selected_facilities = st.multiselect(
            "Facilities",
            [
                "Wi-Fi",
                "Attached bathroom",
                "Kitchen",
                "Parking",
                "Laundry",
                "Furnished",
                "Air conditioning"
            ]
        )

        # ---------------------------------------------------------
        # Search button
        # ---------------------------------------------------------
        if st.button(
            "Search accommodation",
            type="primary",
            key="accommodation_search_button"
        ):

            filtered_layers = {}

            total_results = 0

            # -----------------------------------------------------
            # Apply filters to every accommodation layer
            # -----------------------------------------------------
            for layer_name, gdf in accommodation_layers.items():

                filtered = gdf.copy()

                # -------------------------------------------------
                # Search by name/title
                # -------------------------------------------------
                if search_text.strip():

                    name_col = find_column(
                        filtered,
                        [
                            "title",
                            "name",
                            "accommodation_name",
                            "boarding_name"
                        ]
                    )

                    if name_col:

                        search_value = (
                            search_text
                            .strip()
                            .lower()
                        )

                        mask = (
                            filtered[name_col]
                            .fillna("")
                            .astype(str)
                            .str.lower()
                            .str.contains(
                                search_value,
                                na=False
                            )
                        )

                        filtered = filtered[mask]

                # -------------------------------------------------
                # Accommodation type
                # -------------------------------------------------
                if selected_type != "All":

                    type_col = find_column(
                        filtered,
                        [
                            "type",
                            "accommodation_type",
                            "acc_type"
                        ]
                    )

                    if type_col:

                        filtered = filtered[
                            filtered[type_col]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            ==
                            selected_type.lower()
                        ]

                # -------------------------------------------------
                # Gender
                # -------------------------------------------------
                if selected_gender != "All":

                    gender_col = find_column(
                        filtered,
                        [
                            "gender",
                            "gender_preference",
                            "preferred_gender"
                        ]
                    )

                    if gender_col:

                        filtered = filtered[
                            filtered[gender_col]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            ==
                            selected_gender.lower()
                        ]

                # -------------------------------------------------
                # Availability
                # -------------------------------------------------
                if selected_availability != "All":

                    availability_col = find_column(
                        filtered,
                        [
                            "availability",
                            "status"
                        ]
                    )

                    if availability_col:

                        filtered = filtered[
                            filtered[availability_col]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            ==
                            selected_availability.lower()
                        ]

                # -------------------------------------------------
                # Rent
                # -------------------------------------------------
                rent_col = find_column(
                    filtered,
                    [
                        "rent_lkr",
                        "rent",
                        "monthly_rent",
                        "monthly_rent_lkr"
                    ]
                )

                if rent_col:

                    rent_values = (
                        filtered[rent_col]
                        .astype(str)
                        .str.replace(
                            ",",
                            "",
                            regex=False
                        )
                        .str.replace(
                            "Rs.",
                            "",
                            regex=False
                        )
                        .str.replace(
                            "Rs",
                            "",
                            regex=False
                        )
                        .str.strip()
                    )

                    rent_numeric = (
                        __import__("pandas")
                        .to_numeric(
                            rent_values,
                            errors="coerce"
                        )
                    )

                    filtered = filtered[
                        rent_numeric.between(
                            min_rent,
                            max_rent,
                            inclusive="both"
                        )
                    ]

                # -------------------------------------------------
                # Facilities
                # -------------------------------------------------
                if selected_facilities:

                    facility_col = find_column(
                        filtered,
                        [
                            "facilities",
                            "facility",
                            "amenities"
                        ]
                    )

                    if facility_col:

                        facility_series = (
                            filtered[facility_col]
                            .fillna("")
                            .astype(str)
                            .str.lower()
                        )

                        for facility in selected_facilities:

                            facility_search = (
                                facility.lower()
                            )

                            filtered = filtered[
                                facility_series.str.contains(
                                    facility_search,
                                    na=False
                                )
                            ]

                            facility_series = (
                                filtered[facility_col]
                                .fillna("")
                                .astype(str)
                                .str.lower()
                            )

                if not filtered.empty:

                    filtered_layers[layer_name] = filtered

                    total_results += len(filtered)

            # -----------------------------------------------------
            # Display result
            # -----------------------------------------------------
            if total_results == 0:

                st.warning(
                    "No accommodation options matched "
                    "your selected filters."
                )

            else:

                st.success(
                    f"Found {total_results} "
                    f"accommodation option(s)."
                )

                for layer_name, gdf in filtered_layers.items():

                    st.markdown(
                        f"### {layer_name}"
                    )

                    st.caption(
                        f"{len(gdf)} result(s)"
                    )

                    # -------------------------------------------------
                    # Display accommodation cards
                    # -------------------------------------------------
                    from modules.accommodation import (
                        build_accommodation_card_html
                    )

                    for _, row in gdf.iterrows():

                        html = (
                            build_accommodation_card_html(
                                row,
                                layer_name=layer_name
                            )
                        )

                        st.markdown(
                            html,
                            unsafe_allow_html=True
                        )


# -----------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------
with tab_dash:
    from modules.dashboard import render_dashboard
    render_dashboard(st.session_state.layers)


# -----------------------------------------------------------------
# Compare
# -----------------------------------------------------------------
with tab_compare:
    from modules.compare import render_compare
    render_compare(st.session_state.layers)


# -----------------------------------------------------------------
# Report Listing
# -----------------------------------------------------------------
with tab_report:
    from modules.reports import render_report_tab
    render_report_tab(st.session_state.layers)


# -----------------------------------------------------------------
# Add Boarding
# -----------------------------------------------------------------
with tab_add:

    st.write(
        "Click a location on the map below, then fill in the form. "
        "Your submission goes directly to our database for review — "
        "nothing is stored on this computer."
    )

    pick_map = folium.Map(
        location=[6.9271, 79.8612],
        zoom_start=12
    )

    folium.TileLayer(
        "OpenStreetMap"
    ).add_to(pick_map)

    if st.session_state.add_boarding_location:

        folium.Marker(
            location=st.session_state.add_boarding_location,
            icon=folium.Icon(
                color="red",
                icon="map-pin",
                prefix="fa"
            ),
        ).add_to(pick_map)

    click_result = st_folium(
        pick_map,
        width=None,
        height=400,
        key="add_boarding_map",
        returned_objects=["last_clicked"]
    )

    if click_result and click_result.get("last_clicked"):

        st.session_state.add_boarding_location = [
            click_result["last_clicked"]["lat"],
            click_result["last_clicked"]["lng"],
        ]

    if st.session_state.add_boarding_location:

        lat, lon = (
            st.session_state.add_boarding_location
        )

        st.success(
            f"Location selected: {lat:.5f}, {lon:.5f}"
        )

    else:

        st.info(
            "Click anywhere on the map above to set "
            "the accommodation's location."
        )

    with st.form(
        "add_boarding_form",
        clear_on_submit=True
    ):

        st.subheader(
            "Accommodation details"
        )

        title = st.text_input(
            "Accommodation title / name *"
        )

        acc_type = st.selectbox(
            "Type *",
            [
                "Room",
                "Annex",
                "Boarding house",
                "Shared accommodation",
                "Other"
            ]
        )

        rent = st.number_input(
            "Monthly rent (LKR) *",
            min_value=0,
            step=500
        )

        gender = st.selectbox(
            "Gender preference *",
            [
                "Female",
                "Male",
                "Any"
            ]
        )

        availability = st.selectbox(
            "Availability *",
            [
                "Available",
                "Limited availability",
                "Currently full"
            ]
        )

        facilities = st.multiselect(
            "Facilities (optional)",
            [
                "Wi-Fi",
                "Attached bathroom",
                "Kitchen",
                "Parking",
                "Laundry",
                "Furnished",
                "Air conditioning",
                "Other"
            ],
        )

        rooms_occupants = st.text_input(
            "Number of rooms / occupants (optional)"
        )

        description = st.text_area(
            "Short description (optional)"
        )

        uploaded_photos = render_photo_uploader()

        submitted = st.form_submit_button(
            "Submit accommodation"
        )

        if submitted:

            if not st.session_state.add_boarding_location:

                st.error(
                    "Please click a location on the map above "
                    "before submitting."
                )

            elif not title.strip():

                st.error(
                    "Please enter an accommodation title/name."
                )

            else:

                lat, lon = (
                    st.session_state.add_boarding_location
                )

                nearby = find_nearby_accommodation(
                    lat,
                    lon,
                    st.session_state.layers
                )

                if nearby:
                    st.warning(
                        "⚠️ This location is very close to an existing accommodation. "
                        "Please check whether this listing already exists."
                    )
                    with st.expander(
                        f"Show {len(nearby)} nearby listing(s)"
                    ):
                        for m in nearby:
                            st.write(
                                f"- **{m['name']}** ({m['layer']}) — "
                                f"{m['distance_m']} m away"
                            )

                result = submit_accommodation({
                    "title": title.strip(),
                    "type": acc_type,
                    "rent_lkr": rent,
                    "gender": gender,
                    "availability": availability,
                    "facilities": (
                        ", ".join(facilities)
                        if facilities
                        else None
                    ),
                    "rooms_occupants": (
                        rooms_occupants.strip()
                        or None
                    ),
                    "description": (
                        description.strip()
                        or None
                    ),
                    "latitude": lat,
                    "longitude": lon,
                })

                if result["success"]:

                    st.success(
                        result["message"]
                    )

                    new_submission_id = (
                        result.get("data", {}).get("id")
                        if isinstance(result.get("data"), dict)
                        else result.get("id")
                    )

                    if uploaded_photos and new_submission_id:
                        photo_urls = upload_photos(
                            new_submission_id,
                            uploaded_photos
                        )
                        if photo_urls:
                            from modules.supabase_client import get_client

                            get_client().table("submissions").update(
                                {"photo_urls": photo_urls}
                            ).eq(
                                "id",
                                new_submission_id
                            ).execute()

                    st.session_state.add_boarding_location = None

                else:

                    st.error(
                        result["message"]
                    )


# -----------------------------------------------------------------
# Sidebar: Developer tools (hidden unless ?dev=YOUR_SECRET is in the URL)
# -----------------------------------------------------------------
if is_dev:
    with st.sidebar:

        with st.expander(
            "🛠️ Developer tools",
            expanded=False
        ):

            st.caption(
                "For loading/refreshing the underlying GIS data. "
                "Normal visitors don't need this."
            )

            uploaded_files = st.file_uploader(
                "Upload 10 GIS files (5 CSV + 5 GeoJSON)",
                type=[
                    "csv",
                    "geojson",
                    "json"
                ],
                accept_multiple_files=True,
            )

            identified = {}
            unidentified_files = []

            if uploaded_files:

                for f in uploaded_files:

                    layer_name = (
                        st.session_state.manual_assignments.get(
                            f.name
                        )
                        or data_loader.identify_layer(
                            f.name
                        )
                    )

                    if layer_name:

                        identified[f.name] = layer_name

                        st.markdown(
                            f"✅ `{f.name}` → **{layer_name}**"
                        )

                    else:

                        unidentified_files.append(f)

                        st.markdown(
                            f"⚠️ `{f.name}` → not recognized"
                        )

                if unidentified_files:

                    for f in unidentified_files:

                        options = [
                            "-- Select a layer --"
                        ] + list(
                            data_loader.LAYER_CONFIG.keys()
                        )

                        choice = st.selectbox(
                            f"Assign layer for {f.name}",
                            options,
                            key=f"manual_assign_{f.name}"
                        )

                        if choice != "-- Select a layer --":

                            st.session_state.manual_assignments[
                                f.name
                            ] = choice

                            identified[f.name] = choice

                if st.button(
                    "Load uploaded files",
                    type="primary"
                ):

                    for f in uploaded_files:
                        f.seek(0)

                    sources = [
                        (f.name, f)
                        for f in uploaded_files
                    ]

                    load_files_from_paths(
                        sources
                    )

                    st.success(
                        "Loaded. Switch to the Explore Map tab to see it."
                    )

            st.markdown("---")

            if st.button(
                "Reload from data/development folder"
            ):

                if os.path.isdir(DEV_FOLDER):

                    local_paths = [
                        os.path.join(
                            DEV_FOLDER,
                            fn
                        )
                        for fn in os.listdir(
                            DEV_FOLDER
                        )
                        if fn.lower().endswith(
                            (
                                ".csv",
                                ".geojson",
                                ".json"
                            )
                        )
                    ]

                    sources = [
                        (
                            os.path.basename(p),
                            open(p, "rb")
                        )
                        for p in local_paths
                    ]

                    load_files_from_paths(
                        sources
                    )

                    for _, f in sources:
                        f.close()

                    st.success(
                        "Reloaded from data/development."
                    )

                else:

                    st.warning(
                        "data/development folder not found."
                    )

            if st.session_state.layer_info:

                st.markdown("---")

                st.caption(
                    "Loaded layers:"
                )

                for name, info in (
                    st.session_state.layer_info.items()
                ):

                    icon = (
                        "✅"
                        if info["status"] == "Loaded"
                        else "❌"
                    )

                    st.caption(
                        f"{icon} {name}: "
                        f"{info['features']} features"
                    )


# -----------------------------------------------------------------
# Sidebar: Admin (hidden unless ?dev=YOUR_SECRET is in the URL)
# -----------------------------------------------------------------
if is_dev:
    with st.sidebar:

        with st.expander(
            "🔐 Admin",
            expanded=False
        ):

            pw = st.text_input(
                "Admin password",
                type="password",
                key="admin_pw"
            )

            if pw == st.secrets.get("ADMIN_PASSWORD"):

                from modules.admin import (
                    get_submissions,
                    approve_submission,
                    reject_submission,
                    remove_submission
                )

                pending = get_submissions(
                    status="PENDING"
                )

                st.caption(
                    f"{len(pending)} pending submission(s)"
                )

                for sub in pending:

                    with st.container(
                        border=True
                    ):

                        st.write(
                            f"**{sub.get('title')}**"
                        )

                        st.caption(
                            f"{sub.get('type')} — "
                            f"Rs. {sub.get('rent_lkr')} — "
                            f"{sub.get('gender')} — "
                            f"{sub.get('availability')}"
                        )

                        st.caption(
                            f"Location: "
                            f"{sub.get('latitude'):.5f}, "
                            f"{sub.get('longitude'):.5f}"
                        )

                        c1, c2 = st.columns(2)

                        if c1.button(
                            "Approve",
                            key=f"approve_{sub['id']}"
                        ):

                            approve_submission(
                                sub["id"]
                            )

                            st.rerun()

                        if c2.button(
                            "Reject",
                            key=f"reject_{sub['id']}"
                        ):

                            reject_submission(
                                sub["id"]
                            )

                            st.rerun()

                st.divider()
                from modules.reports import get_reports, set_report_status
                open_reports = get_reports(status="OPEN")
                st.caption(f"{len(open_reports)} open report(s)")
                for rep in open_reports:
                    with st.container(border=True):
                        st.write(f"**{rep.get('listing_name')}**")
                        st.caption(f"{rep.get('reason')} | {rep.get('source_layer')}")
                        if rep.get("details"):
                            st.write(rep["details"])
                        r1, r2 = st.columns(2)
                        if r1.button("Reviewed", key=f"rev_{rep['id']}"):
                            set_report_status(rep["id"], "REVIEWED")
                            st.rerun()
                        if r2.button("Dismiss", key=f"dis_{rep['id']}"):
                            set_report_status(rep["id"], "DISMISSED")
                            st.rerun()

            elif pw:

                st.error(
                    "Incorrect password."
                )
