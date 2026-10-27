from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import dcc, html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "kume_atamalari.csv"
BACKGROUND = "#F3F4F6"
BOUNDARY = "#D1D5DB"

CLUSTER_ORDER = [5, 4, 3, 2, 1]
CLUSTER_NAMES = {
    1: "Pre-transition",
    2: "Early transition",
    3: "Mid-transition",
    4: "Late transition",
    5: "Post-transition",
}
CLUSTER_COLORS = {
    1: "#2166AC",
    2: "#67A9CF",
    3: "#F7F7F7",
    4: "#EF8A62",
    5: "#B2182B",
}
REQUIRED_COLUMNS = {
    "iso3", "country", "year", "cluster", "region", "tfr", "lex", "median_age"
}


class DataValidationError(ValueError):
    pass


def load_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(
            f"Required input file not found: {DATA_FILE}\n"
            "G02 requires data/out/kume_atamalari.csv."
        )
    try:
        df = pd.read_csv(DATA_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read {DATA_FILE.name}: {exc}") from exc

    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(
            f"{DATA_FILE.name} is missing required columns: " + ", ".join(missing)
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["cluster"] = pd.to_numeric(df["cluster"], errors="coerce")
    df = df.dropna(subset=["iso3", "year", "cluster"]).copy()
    df["year"] = df["year"].astype(int)
    df["cluster"] = df["cluster"].astype(int)
    df = df[df["cluster"].isin(CLUSTER_ORDER)].copy()
    df = df[df["year"] % 5 == 0].copy()
    df = df[df["year"].between(1950, 2050)].copy()
    if df.empty:
        raise DataValidationError(
            "No rows remain after filtering to known clusters and 5-year intervals from 1950 to 2050."
        )

    df["cluster_label"] = df["cluster"].map(CLUSTER_NAMES)
    df["period_type"] = df["year"].apply(
        lambda year: "Projection" if year > 2023 else "UN estimate"
    )
    df["frame_label"] = df["year"].astype(str) + df["year"].apply(
        lambda year: " (Projection)" if year > 2023 else ""
    )
    return df


def build_map(df: pd.DataFrame):
    color_map = {CLUSTER_NAMES[c]: CLUSTER_COLORS[c] for c in CLUSTER_ORDER}
    category_order = [CLUSTER_NAMES[c] for c in CLUSTER_ORDER]
    frame_order = [
        f"{year}{' (Projection)' if year > 2023 else ''}"
        for year in sorted(df["year"].unique())
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
            "period_type": True,
        },
        animation_frame="frame_label",
        category_orders={"cluster_label": category_order, "frame_label": frame_order},
        color_discrete_map=color_map,
        labels={
            "cluster_label": "Demographic Transition Stage",
            "region": "Region",
            "period_type": "Data Status",
            "tfr": "Total Fertility Rate",
            "lex": "Life Expectancy",
            "median_age": "Median Age",
        },
        title="Global Demographic Transition, 1950–2050",
    )
    fig.update_geos(
        projection_type="natural earth",
        showframe=False,
        showcoastlines=True,
        coastlinecolor=BOUNDARY,
        showcountries=True,
        countrycolor=BOUNDARY,
        showland=True,
        landcolor=BACKGROUND,
        showocean=True,
        oceancolor=BACKGROUND,
        bgcolor=BACKGROUND,
    )
    fig.update_layout(
        title={"x": 0.5, "xanchor": "center"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "size": 13, "color": "#1F2937"},
        legend_title_text="Demographic Transition Stage",
        margin={"l": 10, "r": 10, "t": 70, "b": 10},
        height=690,
        autosize=True,
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "x": 0.02,
            "y": 0.02,
            "xanchor": "left",
            "yanchor": "bottom",
            "buttons": [
                {
                    "label": "Play",
                    "method": "animate",
                    "args": [None, {
                        "frame": {"duration": 700, "redraw": True},
                        "transition": {"duration": 250},
                        "fromcurrent": True,
                    }],
                },
                {
                    "label": "Pause",
                    "method": "animate",
                    "args": [[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0},
                    }],
                },
            ],
        }],
    )
    return fig


def build_layout(df: pd.DataFrame, show_back_link: bool = True):
    fig = build_map(df)
    years = sorted(df["year"].unique())
    countries = df["iso3"].nunique()
    clusters = df["cluster"].nunique()
    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g02-page-header", children=[
            html.Div("G02 / DEMOGRAPHIC TRANSITION", className="g02-eyebrow"),
            html.H1("Global Demographic Transition, 1950–2050"),
            html.P(
                "Explore how countries move through demographic transition stages over time. "
                "Use the animation controls to move between five-year intervals.",
                className="g02-intro",
            ),
        ]),
        html.Div(className="metrics", children=[
            make_metric_card("Countries represented", f"{countries:,}", "Unique ISO-3 country identifiers in the filtered data."),
            make_metric_card("Years available", f"{len(years):,}", f"Five-year intervals from {years[0]} to {years[-1]}.") ,
            make_metric_card("Transition stages", f"{clusters:,}", "Distinct demographic transition clusters shown on the map."),
        ]),
        html.Section(className="g02-panel", children=[
            dcc.Graph(
                id="g02-animated-map",
                figure=fig,
                config={"responsive": True, "displaylogo": False},
                style={"width": "100%"},
            ),
        ]),
        html.Section(className="g02-method-note", children=[
            html.Strong("Data note: "),
            "Years after 2023 are labeled as projections; years through 2023 are labeled as UN estimates. "
            "The map uses five-year intervals between 1950 and 2050.",
        ]),
    ])
    return html.Main(className="g02-dashboard", children=children)
