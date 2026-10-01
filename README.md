# StudentStay Colombo

**Find a place to stay. Find what you need around it.**

A web-based GIS application to help students find accommodation in and
around Colombo, Sri Lanka.

This README currently covers **Stage 1: Data upload and basic map** only.
Later stages (Supabase, submissions, search, admin, etc.) will be added
to this README as they are built.

---

## 1. Folder structure

```text
StudentStay_Colombo/
│
├── app.py                  ← Main Streamlit application
├── requirements.txt
├── .env.example
├── README.md
├── .gitignore
│
├── modules/
│   ├── data_loader.py      ← Layer identification, CSV/GeoJSON loading, validation
│   ├── map.py               ← Folium map building
│   └── utils.py              ← Small helper functions
│
└── data/
    └── development/          ← (Optional) place your 10 GIS files here for convenience.
                                 They are NOT read directly from disk — you still upload
                                 them through the app's file uploader.
```

---

## 2. Installation

Open a terminal in VS Code, inside the `StudentStay_Colombo` folder, and run:

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv

# 2. Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install the required packages
pip install -r requirements.txt
```

---

## 3. Running the application

```bash
streamlit run app.py
```

This will open the app in your browser, usually at `http://localhost:8501`.

---

## 4. How to test Stage 1

1. Make sure you have your 10 files ready, named exactly as described in
   the project brief (e.g. `Student-Reported Accommodation.csv`,
   `Bus Stops.geojson`, etc.). Small differences in capitalization,
   spaces, hyphens, or underscores are fine — the app normalizes them.

2. In the app, use the **Upload GIS Layers** section and select all
   10 files at once (you can drag-and-drop or use the file browser
   with Ctrl/Cmd held down to select multiple files).

3. Check that each file shows a ✅ with the correct layer name next
   to it. If any file shows a ⚠️, use the manual dropdown that appears
   below to assign it to the correct layer.

4. Click **LOAD ALL LAYERS**.

5. You should see:
   - A **Warnings and messages** section (only appears if there is
     something worth flagging, e.g. missing coordinates).
   - A **Loaded Layers** section showing each layer's feature count,
     geometry type, CRS, and status.
   - An **Interactive Map** with all layers, a layer control (top
     right of the map) to toggle layers on/off, and clickable
     features that show a popup with their attributes.

### What you should see if everything works

- All 10 layers listed under "Loaded Layers" with status "Loaded".
- Point layers (Student-Reported Accommodation, Existing Boarding
  Locations, Higher Education Institutions, Police Stations,
  Healthcare Facilities, Supermarkets, Bus Stops, Railway Stations)
  shown as small colored circles on the map.
- Polygon layers (Colombo District, Western Province) shown as
  outlined boundaries.
- Clicking any point or boundary opens a popup with its raw
  attributes (this is expected for Stage 1 — polished accommodation
  cards come in Stage 3).
- Accommodation points outside Colombo District (but inside Western
  Province) are still shown, not removed.

### If something goes wrong

- Read the message in the **Warnings and messages** section — each
  one explains what happened, which file/layer caused it, and how to
  fix it.
- If a file isn't recognized, double check its exact filename against
  the list in the project brief, or use the manual assignment
  dropdown.
- If latitude/longitude aren't detected in a CSV file, check that your
  column headers are close to: `latitude`/`lat`/`y` and
  `longitude`/`lon`/`lng`/`long`/`x`.

---

## 5. Notes on data storage (Stage 1)

- Nothing you upload in Stage 1 is permanently saved anywhere. It only
  exists in the app's memory (`st.session_state`) while the app is
  running, and is cleared when you close it or reload the page.
- Supabase is not used yet. It will be introduced starting from
  Stage 4 (Add Boarding workflow), and will be the **only** place
  where student-submitted information is stored — never on your
  laptop.

---

## 6. Next steps

Once you've confirmed Stage 1 works correctly with your real 10 files,
let me know and we will move on to **Stage 2 — Improve GIS map**.
