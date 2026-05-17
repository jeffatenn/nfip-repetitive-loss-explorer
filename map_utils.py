import folium
import pandas as pd
from folium.plugins import MarkerCluster


def build_map(df: pd.DataFrame) -> folium.Map:
    # Drop rows with missing coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    if df.empty:
        return folium.Map(location=[39, -95], zoom_start=4)

    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()

    # Zoom out more when viewing a full state vs a single county
    n = len(df)
    zoom = 10 if n < 500 else 7 if n < 5_000 else 5

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    # Cluster markers so the map doesn't get overwhelmed at state level
    cluster = MarkerCluster(
        options={"maxClusterRadius": 40, "disableClusteringAtZoom": 13}
    ).add_to(m)

    # Add a simple legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 10px 14px; border-radius: 6px;
                border: 1px solid #ccc; font-size: 13px; line-height: 1.8;">
        <b>Legend</b><br>
        <span style="color:red;">●</span> Severe Repetitive Loss<br>
        <span style="color:orange;">●</span> Repetitive Loss<br>
        <span style="color:green;">●</span> Mitigated
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Build markers without iterrows — iterate over records (faster)
    for row in df.to_dict(orient='records'):
        if row.get('nfipSrl'):
            color = 'red'
        elif row.get('mitigatedIndicator'):
            color = 'green'
        else:
            color = 'orange'

        tooltip = (
            f"City: {row.get('reportedCity', 'N/A')}<br>"
            f"Flood Zone: {row.get('floodZone', 'N/A')}<br>"
            f"Occupancy: {row.get('occupancyType', 'N/A')}<br>"
            f"Total Losses: {row.get('totalLosses', 'N/A')}<br>"
            f"SRL: {row.get('nfipSrl', False)} | "
            f"Mitigated: {row.get('mitigatedIndicator', False)}"
        )

        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            tooltip=folium.Tooltip(tooltip, sticky=True)
        ).add_to(cluster)

    return m