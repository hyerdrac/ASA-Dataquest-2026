import pandas as pd
import plotly.express as px

# --------------------------------------------------
# 1. Settings
# --------------------------------------------------

cluster_order = [5, 4, 3, 2, 1]

cluster_names = {
    1: "Pre-transition",
    2: "Early transition",
    3: "Mid-transition",
    4: "Late transition",
    5: "Post-transition"
}

# Paletinizdeki küme renkleri (Mevcut haliyle doğru)
cluster_colors = {
    1: "#2166AC",
    2: "#67A9CF",
    3: "#F7F7F7",
    4: "#EF8A62",
    5: "#B2182B",
}

# Yeni arka plan ve sınır renkleri
background_color = "#F3F4F6"
boundary_color = "#D1D5DB"

# --------------------------------------------------
# 2. Load data
# --------------------------------------------------

df = pd.read_csv("./data/out/kume_atamalari.csv")

# Convert columns to appropriate types
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["cluster"] = pd.to_numeric(df["cluster"], errors="coerce")

df = df.dropna(subset=["iso3", "year", "cluster"]).copy()

df["year"] = df["year"].astype(int)
df["cluster"] = df["cluster"].astype(int)

# Keep only clusters with defined colors
df = df[df["cluster"].isin(cluster_order)].copy()

# --------------------------------------------------
# 3. Select 5-year intervals
# --------------------------------------------------

df = df[df["year"] % 5 == 0].copy()

# Optional: restrict to 1950–2050
df = df[df["year"].between(1950, 2050)].copy()

# --------------------------------------------------
# 4. Add English cluster labels
# --------------------------------------------------

df["cluster_label"] = df["cluster"].map(cluster_names)

# Mark projections
df["period_type"] = df["year"].apply(
    lambda year: "Projection" if year > 2023 else "UN estimate"
)

# Add a label distinguishing projected years
df["frame_label"] = df["year"].astype(str) + df["year"].apply(
    lambda year: " (Projection)" if year > 2023 else ""
)

# Ensure chronological animation order
frame_order = [
    f"{year}{' (Projection)' if year > 2023 else ''}"
    for year in sorted(df["year"].unique())
]

# --------------------------------------------------
# 5. Create animated map
# --------------------------------------------------

color_map = {
    cluster_names[c]: cluster_colors[c]
    for c in cluster_order
}

category_order = [
    cluster_names[c]
    for c in cluster_order
]

fig = px.choropleth(
    df,
    locations="iso3",
    locationmode="ISO-3",
    color="cluster_label",
    hover_name="country",
    hover_data={
        "region": True,
        "year": True,
        "cluster_label": True,
        "tfr": ":.2f",
        "lex": ":.2f",
        "median_age": ":.1f",
        "iso3": False,
        "cluster": False,
        "frame_label": False,
        "period_type": True
    },
    animation_frame="frame_label",
    category_orders={
        "cluster_label": category_order,
        "frame_label": frame_order
    },
    color_discrete_map=color_map,
    labels={
        "cluster_label": "Demographic Transition Stage",
        "region": "Region",
        "period_type": "Data Status",
        "tfr": "Total Fertility Rate",
        "lex": "Life Expectancy",
        "median_age": "Median Age"
    },
    title="Global Demographic Transition, 1950–2050"
)

# --------------------------------------------------
# 6. Map styling
# --------------------------------------------------

fig.update_geos(
    projection_type="natural earth",
    showframe=False,
    showcoastlines=True,
    coastlinecolor=boundary_color,
    showcountries=True,
    countrycolor=boundary_color,
    showland=True,
    landcolor=background_color,
    showocean=True,
    oceancolor=background_color,
    bgcolor=background_color
)

fig.update_layout(
    title_x=0.5,
    paper_bgcolor=background_color,
    plot_bgcolor=background_color,
    legend_title_text="Demographic Transition Stage",
    margin=dict(l=10, r=10, t=70, b=10)
)

# --------------------------------------------------
# 7. Animation controls
# --------------------------------------------------

fig.update_layout(
    updatemenus=[
        {
            "type": "buttons",
            "showactive": False,
            "x": 0.05,
            "y": 0.05,
            "buttons": [
                {
                    "label": "Play",
                    "method": "animate",
                    "args": [
                        None,
                        {
                            "frame": {"duration": 700, "redraw": True},
                            "transition": {"duration": 250},
                            "fromcurrent": True
                        }
                    ]
                },
                {
                    "label": "Pause",
                    "method": "animate",
                    "args": [
                        [None],
                        {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0}
                        }
                    ]
                }
            ]
        }
    ]
)

# --------------------------------------------------
# 8. Save and display
# --------------------------------------------------

fig.write_html(
    "./charts/g02_animated_demographic_map.html",
    auto_play=False
)

fig.show()