"""
map.py
------
Stage 2 map building for StudentStay Colombo.

Improvements over Stage 1:
- Point layers use meaningful icons (bed, home, graduation cap, shield,
  plus, shopping cart, bus, train) instead of plain colored dots.
- Point layers are grouped with marker clustering, so busy layers
  (e.g. Bus Stops) don't overwhelm the map when zoomed out. Cluster
  bubbles are colored to match their own layer (not Leaflet's default
  generic green/orange/red scheme), and a legend + on-map tip explain
  what the numbered circles mean.
- A visible legend (matching the actual marker colors/icons) is added
  to the map, with a short tip about cluster circles.
- Popups show friendly, readable field labels instead of raw column
  names, and hide empty values.
- Polygon boundaries (Colombo District, Western Province) get clearer
  styling (dashed outline, subtle fill) and a JSON-safe popup.
- A fullscreen button lets users expand the map for easier browsing.

Stage 1's raw-attribute popups are still shown for now — the fully
polished accommodation information cards are still Stage 3's job.
"""

import re
import folium
import pandas as pd
from folium.plugins import MarkerCluster, Fullscreen

from modules.data_loader import LAYER_CONFIG
from modules.accommodation import ACCOMMODATION_LAYERS, build_accommodation_card_html

# Folium's built-in Icon marker only accepts this fixed set of colors.
VALID_ICON_COLORS = {
    "red", "blue", "green", "purple", "orange", "darkred", "lightred",
    "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "white",
    "pink", "lightblue", "lightgreen", "gray", "black", "lightgray",
}


def _safe_icon_color(color: str) -> str:
    """Fall back to 'blue' if a layer's configured color isn't a valid
    Folium Icon color (e.g. a hex code used for polygon fills)."""
    return color if color in VALID_ICON_COLORS else "blue"


def _friendly_field_name(col: str) -> str:
    """Turn a raw column name into a readable label for popups.
    e.g. 'monthly_rent' -> 'Monthly Rent', 'gender-pref' -> 'Gender Pref'
    """
    cleaned = re.sub(r"[_\-]+", " ", str(col)).strip()
    return cleaned.title() if cleaned else str(col)


def _json_safe_gdf(gdf):
    """
    Return a copy of the GeoDataFrame where every non-geometry column is
    safe to convert to JSON. Folium's GeoJson layer serializes attributes
    to JSON internally, and types like pandas Timestamp are not JSON
    serializable by default, so we convert them to plain strings here.
    """
    safe = gdf.copy()
    for col in safe.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_datetime64_any_dtype(safe[col]):
            safe[col] = safe[col].astype(str)
        elif safe[col].dtype == object:
            safe[col] = safe[col].apply(
                lambda v: v.isoformat() if isinstance(v, (pd.Timestamp,)) else v
            )
    return safe


def _cluster_icon_create_function(color: str) -> str:
    """
    Build a small JavaScript function (as a string) that draws a cluster
    bubble in the SAME color as this layer's markers, instead of Leaflet's
    default generic green/orange/red cluster-size coloring. This keeps the
    map consistent with the legend, so the numbered circles clearly belong
    to one layer.
    """
    return f"""
    function(cluster) {{
        var count = cluster.getChildCount();
        return L.divIcon({{
            html: '<div style="background-color:{color}; color:white; ' +
                  'border-radius:50%; width:34px; height:34px; line-height:34px; ' +
                  'text-align:center; font-weight:bold; font-size:12px; ' +
                  'border:2px solid white; box-shadow:0 0 3px rgba(0,0,0,0.4);">' +
                  count + '</div>',
            className: 'studentstay-cluster-icon',
            iconSize: L.point(34, 34)
        }});
    }}
    """


def _row_to_popup_html(row, exclude_cols=("geometry",)):
    """Build a readable HTML table of a row's attributes for the popup.
    Uses friendly field labels and skips empty/missing values."""
    lines = ["<div style='font-size:13px'><b>Feature Information</b>",
             "<table style='margin-top:4px'>"]
    for col, value in row.items():
        if col in exclude_cols:
            continue
        if pd.isna(value) or str(value).strip() == "":
            continue
        label = _friendly_field_name(col)
        lines.append(
            f"<tr><td style='padding-right:8px'><b>{label}</b></td><td>{value}</td></tr>"
        )
    lines.append("</table></div>")
    return "".join(lines)


def _build_legend_html(active_layers: dict) -> str:
    """Build a small fixed-position HTML legend listing every layer that
    is actually loaded, with a symbol matching what's on the map."""
    rows = []
    for layer_name in active_layers:
        config = LAYER_CONFIG.get(layer_name, {})
        color = config.get("color", "#3186cc")
        icon = config.get("icon")

        if icon:
            # Point layer -> show a small circular color swatch with the
            # Font Awesome icon inside it (same icon used on the map).
            symbol = (
                f"<span style='display:inline-block;width:16px;height:16px;"
                f"border-radius:50%;background:{color};text-align:center;"
                f"line-height:16px;margin-right:6px;'>"
                f"<i class='fa fa-{icon}' style='font-size:9px;color:white'></i></span>"
            )
        else:
            # Polygon/boundary layer -> show an outlined square swatch.
            symbol = (
                f"<span style='display:inline-block;width:14px;height:14px;"
                f"border:2px solid {color};background:transparent;"
                f"margin-right:6px;'></span>"
            )

        rows.append(
            f"<div style='margin-bottom:4px'>{symbol}<span>{layer_name}</span></div>"
        )

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 9999;
        background: white;
        padding: 10px 14px;
        border: 1px solid #999;
        border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
    ">
        <div style="font-weight:bold; margin-bottom:6px;">Legend</div>
        {''.join(rows)}
        <div style="margin-top:8px; padding-top:6px; border-top:1px solid #ddd; color:#555; max-width:230px;">
            <b>Tip:</b> numbered circles are groups of nearby points, colored
            to match their layer. Zoom in or click a circle to reveal the
            individual markers underneath it.
        </div>
    </div>
    """
    return legend_html


def build_map(layers: dict):
    """
    layers: dict of {layer_name: GeoDataFrame}
    Returns a folium.Map object with all layers, icons, clustering,
    a legend, and improved polygon styling.
    """
    # Compute a combined bounding box across all layers so we can
    # automatically zoom to the data/study area.
    all_bounds = []
    for gdf in layers.values():
        if gdf is not None and not gdf.empty:
            all_bounds.append(gdf.total_bounds)  # [minx, miny, maxx, maxy]

    if all_bounds:
        minx = min(b[0] for b in all_bounds)
        miny = min(b[1] for b in all_bounds)
        maxx = max(b[2] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)
        center = [(miny + maxy) / 2, (minx + maxx) / 2]
    else:
        # Fallback: rough center of Colombo District
        center = [6.9271, 79.8612]

    fmap = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    for layer_name, gdf in layers.items():
        if gdf is None or gdf.empty:
            continue

        config = LAYER_CONFIG.get(layer_name, {})
        color = config.get("color", "blue")
        geometry_type = config.get("geometry_type", "Point")
        icon_name = config.get("icon")

        if geometry_type == "Point":
            # Group markers in a cluster so busy layers (e.g. Bus Stops)
            # stay readable when zoomed out, and collapse into a single
            # number until the user zooms in.
            cluster = MarkerCluster(
                name=layer_name,
                icon_create_function=_cluster_icon_create_function(_safe_icon_color(color)),
            )

            for _, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue

                # Accommodation layers get the clean Stage 3 info card;
                # every other layer (facilities, transport, etc.) keeps
                # the Stage 1/2 raw-attribute popup.
                if layer_name in ACCOMMODATION_LAYERS:
                    popup_html = build_accommodation_card_html(row, layer_name=layer_name)
                    popup_width = 300
                else:
                    popup_html = _row_to_popup_html(row)
                    popup_width = 300

                folium.Marker(
                    location=[geom.y, geom.x],
                    popup=folium.Popup(popup_html, max_width=popup_width),
                    tooltip=layer_name,
                    icon=folium.Icon(
                        color=_safe_icon_color(color),
                        icon=icon_name or "map-marker",
                        prefix="fa",
                    ),
                ).add_to(cluster)

            cluster.add_to(fmap)

        else:  # Polygon / boundary layers
            def style_function(feature, color=color):
                return {
                    "fillColor": color,
                    "color": color,
                    "weight": 2,
                    "fillOpacity": 0.08,
                    "dashArray": "6, 4",
                }

            def highlight_function(feature, color=color):
                return {
                    "fillOpacity": 0.2,
                    "weight": 3,
                }

            safe_gdf = _json_safe_gdf(gdf)
            attribute_fields = [c for c in safe_gdf.columns if c != "geometry"]
            tooltip_fields = attribute_fields[:3]

            folium.GeoJson(
                safe_gdf,
                name=layer_name,
                style_function=style_function,
                highlight_function=highlight_function,
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields) if tooltip_fields else None,
                popup=folium.GeoJsonPopup(fields=attribute_fields) if attribute_fields else None,
            ).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)

    # Fullscreen button, top-left of the map, for a bigger working view.
    Fullscreen(position="topleft").add_to(fmap)

    # Add the legend last so it sits on top of the map.
    fmap.get_root().html.add_child(folium.Element(_build_legend_html(layers)))

    if all_bounds:
        fmap.fit_bounds([[miny, minx], [maxy, maxx]])

    return fmap


def build_university_search_map(
    university_lat,
    university_lon,
    university_label,
    radius_m,
    filtered_accommodation_layers: dict
):
    import folium
    from folium.plugins import MarkerCluster
    from modules.accommodation import build_accommodation_card_html

    fmap = folium.Map(
        location=[university_lat, university_lon],
        zoom_start=14,
        tiles="OpenStreetMap"
    )

    folium.Marker(
        location=[university_lat, university_lon],
        popup=folium.Popup(
            f"<b>{university_label}</b>",
            max_width=200
        ),
        tooltip=university_label,
        icon=folium.Icon(
            color="darkblue",
            icon="graduation-cap",
            prefix="fa"
        ),
    ).add_to(fmap)

    folium.Circle(
        location=[university_lat, university_lon],
        radius=radius_m,
        color="#378ADD",
        weight=2,
        fill=True,
        fill_opacity=0.07,
    ).add_to(fmap)

    total_found = 0

    for layer_name, gdf in filtered_accommodation_layers.items():

        if gdf is None or gdf.empty:
            continue

        cluster = MarkerCluster(name=layer_name)

        for _, row in gdf.iterrows():

            geom = row.geometry

            if geom is None or geom.is_empty:
                continue

            popup_html = build_accommodation_card_html(
                row,
                layer_name=layer_name
            )

            folium.Marker(
                location=[geom.y, geom.x],
                popup=folium.Popup(
                    popup_html,
                    max_width=300
                ),
                tooltip=layer_name,
                icon=folium.Icon(
                    color="red",
                    icon="home",
                    prefix="fa"
                ),
            ).add_to(cluster)

            total_found += 1

        cluster.add_to(fmap)

        folium.LayerControl(
        collapsed=False
    ).add_to(fmap)

    return fmap, total_found

