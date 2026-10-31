from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
COUNTRY_FILE = PROJECT_DIR / "data" / "out" / "g06_goc_kalkani.csv"
COUNT_FILE = PROJECT_DIR / "data" / "out" / "g06_goc_kalkani_sayim.csv"

BG = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
REGION_COLORS = {
    "Asia": "#D55E00",
    "Europe": "#0072B2",
    "Africa": "#E69F00",
    "North America": "#56B4E9",
    "South America": "#009E73",
    "Oceania": "#CC79A7",
    "Latin America and the Caribbean": "#009E73",
}
QUADRANT_LABELS = {
    "growth_inflow": "GROWTH + INFLOW",
    "growth_outflow": "GROWTH + OUTFLOW",
    "double_loss": "NATURAL DECLINE + OUTFLOW",
    "natural_decline": "NATURAL DECLINE",
    "shield": "MIGRATION SHIELD",
}
REQUIRED_COUNTRY_COLUMNS = {
    "country", "iso3", "region", "year", "nat_change_rate", "net_migration_rate",
    "pop_millions", "pop_change_positive", "quadrant", "is_projection", "note",
}
REQUIRED_COUNT_COLUMNS = {
    "year", "n_countries", "n_natural_decline", "n_shield", "n_shield_growing",
    "n_double_loss", "n_growth_inflow", "n_growth_outflow", "n_decline_and_growing",
    "is_projection", "decline_and_growing_share_pct",
}


class DataValidationError(ValueError):
    """Raised when G06 data files are missing or malformed."""


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y", "evet"}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    for path in (COUNTRY_FILE, COUNT_FILE):
        if not path.is_file():
            raise DataValidationError(
                f"Required input file not found: {path}\n"
                "Place both G06 CSV files in the project's data/out/ folder."
            )
    try:
        countries = pd.read_csv(COUNTRY_FILE, low_memory=False)
        counts = pd.read_csv(COUNT_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read G06 CSV files: {exc}") from exc
    countries.columns = countries.columns.astype(str).str.strip()
    counts.columns = counts.columns.astype(str).str.strip()
    missing_c = sorted(REQUIRED_COUNTRY_COLUMNS - set(countries.columns))
    missing_n = sorted(REQUIRED_COUNT_COLUMNS - set(counts.columns))
    if missing_c or missing_n:
        details = []
        if missing_c:
            details.append(f"{COUNTRY_FILE.name} missing: {', '.join(missing_c)}")
        if missing_n:
            details.append(f"{COUNT_FILE.name} missing: {', '.join(missing_n)}")
        raise DataValidationError("\n".join(details))

    countries = countries.copy()
    counts = counts.copy()
    for col in ("year", "nat_change_rate", "net_migration_rate", "pop_millions"):
        countries[col] = pd.to_numeric(countries[col], errors="coerce")
    for col in ("year", "n_countries", "n_natural_decline", "n_shield", "n_shield_growing",
                "n_double_loss", "n_growth_inflow", "n_growth_outflow", "n_decline_and_growing",
                "decline_and_growing_share_pct"):
        counts[col] = pd.to_numeric(counts[col], errors="coerce")
    countries = countries.dropna(subset=["country", "region", "year", "nat_change_rate", "net_migration_rate"])
    counts = counts.dropna(subset=["year", "n_countries"])
    countries["year"] = countries["year"].astype(int)
    counts["year"] = counts["year"].astype(int)
    countries["region"] = countries["region"].astype(str).str.strip()
    countries["country"] = countries["country"].astype(str).str.strip()
    countries["quadrant"] = countries["quadrant"].astype(str).str.strip()
    countries["is_projection"] = countries["is_projection"].map(parse_bool)
    counts["is_projection"] = counts["is_projection"].map(parse_bool)
    countries["pop_millions"] = countries["pop_millions"].fillna(1).clip(lower=0)
    countries["note"] = countries["note"].fillna("").astype(str)
    if countries.empty or counts.empty:
        raise DataValidationError("G06 CSV files contain no usable rows.")
    return countries.sort_values(["year", "country"]).reset_index(drop=True), counts.sort_values("year").reset_index(drop=True)


def _base_layout(fig: go.Figure, title: str, subtitle: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.99, xanchor="left", yanchor="top", font=dict(size=20, color=TEXT)),
        font=dict(family="Inter, Arial, sans-serif", color=TEXT, size=12),
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        margin=dict(l=64, r=30, t=150, b=60),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text="Region"),
        xaxis=dict(title="Natural population change (per 1,000 people)", gridcolor=GRID, zeroline=False,
                   showline=True, linecolor=BORDER),
        yaxis=dict(title="Net migration (per 1,000 people)", gridcolor=GRID, zeroline=False,
                   showline=True, linecolor=BORDER),
        annotations=list(fig.layout.annotations or ()) + [dict(
            text=subtitle, x=0, y=1.0, xref="paper", yref="paper", yshift=60,
            xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=12, color=MUTED)
        )],
    )
    return fig


def build_scatter_figure(countries: pd.DataFrame, year: int) -> go.Figure:
    data = countries[countries["year"] == int(year)].copy()
    fig = go.Figure()
    if data.empty:
        fig.add_annotation(text=f"No country data available for {year}.", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        _base_layout(fig, "Migration shield", "Select a year to explore the natural-change / migration quadrants.")
        return fig

    data["_label_priority"] = data["net_migration_rate"].abs() + data["nat_change_rate"].abs() * 0.2
    # Label only the most informative extremes (8–10 countries), not all ~160 bubbles.
    label_rows = data.nlargest(9, "_label_priority").index.tolist()
    turkey_mask = data["country"].str.casefold().isin({"türkiye", "turkiye", "turkey"})
    turkey_indices = data.index[turkey_mask].tolist()
    for idx in turkey_indices:
        if idx not in label_rows:
            label_rows = (label_rows[:9] + [idx])[:10]
    data["_label"] = data.index.map(lambda idx: data.loc[idx, "country"] if idx in label_rows else "")

    for region, part in data.groupby("region", sort=False):
        color = REGION_COLORS.get(region, "#9CA3AF")
        fig.add_trace(go.Scatter(
            x=part["nat_change_rate"], y=part["net_migration_rate"], mode="markers+text",
            name=region, text=part["_label"], textposition="top center",
            textfont=dict(size=10, color=TEXT),
            marker=dict(size=(part["pop_millions"].clip(lower=0.5, upper=200) ** 0.38 * 5.5),
                        color=color, opacity=0.78, line=dict(width=0.7, color="#FFFFFF")),
            customdata=part[["country", "iso3", "region", "year", "quadrant", "pop_millions", "is_projection", "note"]].to_numpy(),
            hovertemplate=("<b>%{customdata[0]}</b> (%{customdata[1]})<br>Region: %{customdata[2]}"
                           "<br>Year: %{customdata[3]}<br>Natural change: %{x:.2f}‰"
                           "<br>Net migration: %{y:.2f}‰<br>Population: %{customdata[5]:.2f} million"
                           "<br>Group: %{customdata[4]}<br>Projection: %{customdata[6]}"
                           "<br>%{customdata[7]}<extra></extra>"),
        ))

    x_min, x_max = float(data["nat_change_rate"].min()), float(data["nat_change_rate"].max())
    y_min, y_max = float(data["net_migration_rate"].min()), float(data["net_migration_rate"].max())
    x_pad = max(5, (x_max - x_min) * 0.08)
    y_pad = max(5, (y_max - y_min) * 0.08)
    fig.add_hline(y=0, line=dict(color="#9CA3AF", width=1.2, dash="dot"))
    fig.add_vline(x=0, line=dict(color="#9CA3AF", width=1.2, dash="dot"))
    # Faint quadrant captions stay behind the country marks.
    fig.add_annotation(x=0.03, y=0.97, xref="paper", yref="paper", text="GROWTH + INFLOW",
                       showarrow=False, font=dict(size=11, color="#B7BEC8"), xanchor="left")
    fig.add_annotation(x=0.97, y=0.97, xref="paper", yref="paper", text="GROWTH + OUTFLOW",
                       showarrow=False, font=dict(size=11, color="#B7BEC8"), xanchor="right")
    fig.add_annotation(x=0.03, y=0.04, xref="paper", yref="paper", text="NATURAL DECLINE + INFLOW",
                       showarrow=False, font=dict(size=11, color="#B7BEC8"), xanchor="left")
    fig.add_annotation(x=0.97, y=0.04, xref="paper", yref="paper", text="DOUBLE LOSS",
                       showarrow=False, font=dict(size=11, color="#B7BEC8"), xanchor="right")
    projection = bool(data["is_projection"].mode().iloc[0])
    year_color = "#B45309" if projection else TEXT
    year_label = f"{year} · PROJECTION" if projection else f"{year} · OBSERVED / ESTIMATE"
    fig.add_annotation(x=1, y=1.0, xref="paper", yref="paper", yshift=100, text=year_label,
                       showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=13, color=year_color))
    _base_layout(fig, "Migration shield", "Each bubble is a country; bubble size represents population. Labels are limited to key extremes.")
    fig.update_xaxes(range=[min(x_min - x_pad, -2), max(x_max + x_pad, 2)])
    fig.update_yaxes(range=[min(y_min - y_pad, -2), max(y_max + y_pad, 2)])
    return fig


def build_count_figure(counts: pd.DataFrame, selected_year: int) -> go.Figure:
    fig = go.Figure()
    series = [
        ("n_natural_decline", "Natural decline", "#D55E00"),
        ("n_shield", "Migration shield", "#0072B2"),
        ("n_double_loss", "Double loss", "#B2182B"),
        ("n_growth_inflow", "Growth + inflow", "#009E73"),
        ("n_growth_outflow", "Growth + outflow", "#6B7280"),
    ]
    for col, name, color in series:
        if col in counts:
            fig.add_trace(go.Scatter(x=counts["year"], y=counts[col], mode="lines", name=name,
                                     line=dict(color=color, width=2)))
    if selected_year in set(counts["year"]):
        fig.add_vline(x=selected_year, line=dict(color="#111827", width=1.5, dash="dash"))
    fig.update_layout(
        title=dict(text="Country counts by demographic–migration group", x=0.02, font=dict(size=19, color=TEXT)),
        paper_bgcolor=BG, plot_bgcolor=PANEL, font=dict(family="Inter, Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=58, r=25, t=70, b=50), legend=dict(orientation="h", y=1.02, x=0),
        xaxis=dict(title="Year", gridcolor=GRID, showline=True, linecolor=BORDER),
        yaxis=dict(title="Number of countries", gridcolor=GRID, rangemode="tozero", showline=True, linecolor=BORDER),
    )
    return fig


def build_layout(countries: pd.DataFrame, counts: pd.DataFrame, show_back_link: bool = True):
    years = sorted(countries["year"].unique().tolist())
    default_year = 2023 if 2023 in years else years[-1]
    selected_counts = counts[counts["year"] == default_year]
    count_value = int(selected_counts["n_countries"].iloc[0]) if not selected_counts.empty else int(countries[countries["year"] == default_year]["country"].nunique())
    shield_value = int(selected_counts["n_shield"].iloc[0]) if not selected_counts.empty and pd.notna(selected_counts["n_shield"].iloc[0]) else 0
    projection_count = int(countries[countries["year"] == default_year]["is_projection"].sum())
    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g06-header", children=[
            html.Div("G06 · MIGRATION SHIELD", className="g06-eyebrow"),
            html.H1("The migration shield"),
            html.P("Explore how natural population change and net migration combine across countries. "
                   "Move through time to compare observed estimates and projections.", className="g06-intro"),
        ]),
        html.Section(className="metrics g06-metrics", children=[
            html.Div([html.Div("Countries in selected year", className="metric-label"),
                      html.Div(f"{count_value:,}", id="g06-kpi-countries", className="metric-value"),
                      html.Div(f"Year: {default_year}", id="g06-kpi-year", className="metric-description")], className="metric-card"),
            html.Div([html.Div("Migration shield", className="metric-label"),
                      html.Div(f"{shield_value:,}", id="g06-kpi-shield", className="metric-value"),
                      html.Div("Countries classified in the shield group", className="metric-description")], className="metric-card"),
            html.Div([html.Div("Projection observations", className="metric-label"),
                      html.Div(f"{projection_count:,}", id="g06-kpi-projection", className="metric-value"),
                      html.Div("Rows marked as projections in selected year", className="metric-description")], className="metric-card"),
        ]),
        html.Section(className="g06-panel", children=[
            html.Div(className="g06-controls", children=[
                html.Div([html.Label("Year", htmlFor="g06-year-slider", className="g06-label"),
                          dcc.Slider(id="g06-year-slider", min=min(years), max=max(years), value=default_year,
                                     marks={y: str(y) for y in years if y == min(years) or y == max(years) or y % 10 == 0},
                                     step=1, updatemode="mouseup")], className="g06-slider-wrap"),
                html.Div(id="g06-year-status", className="g06-year-status"),
            ]),
        ]),
        html.Section(className="g06-panel", children=[
            html.H2("Country migration quadrants", className="g06-section-heading"),
            dcc.Graph(id="g06-scatter-graph", figure=build_scatter_figure(countries, default_year),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "620px", "minHeight": "620px", "width": "100%"}),
        ]),
        html.Section(className="g06-panel", children=[
            html.H2("How the country groups change over time", className="g06-section-heading"),
            dcc.Graph(id="g06-count-graph", figure=build_count_figure(counts, default_year),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "430px", "minHeight": "430px", "width": "100%"}),
        ]),
        html.Div(className="g06-method-note", children=[
            html.Strong("How to read this view. "),
            "The vertical axis is net migration rate and the horizontal axis is natural population change rate; "
            "bubble size indicates population. Country labels are limited to the most extreme observations and Türkiye when present. "
            "Projection years use an amber year label. The supplied country counts are shown separately below.",
        ]),
    ])
    return html.Main(className="g06-dashboard", children=children)


def register_callbacks(app, countries: pd.DataFrame, counts: pd.DataFrame) -> None:
    @app.callback(
        Output("g06-scatter-graph", "figure"),
        Output("g06-count-graph", "figure"),
        Output("g06-year-status", "children"),
        Output("g06-year-status", "className"),
        Output("g06-kpi-countries", "children"),
        Output("g06-kpi-year", "children"),
        Output("g06-kpi-shield", "children"),
        Output("g06-kpi-projection", "children"),
        Input("g06-year-slider", "value"),
    )
    def update_g06(year):
        selected_year = int(year)
        year_data = countries[countries["year"] == selected_year]
        is_projection = bool(year_data["is_projection"].mode().iloc[0]) if not year_data.empty else False
        status = f"{selected_year} · {'PROJECTION' if is_projection else 'OBSERVED / ESTIMATE'}"
        status_class = "g06-year-status projection" if is_projection else "g06-year-status observed"
        selected_counts = counts[counts["year"] == selected_year]
        n_countries = int(selected_counts["n_countries"].iloc[0]) if not selected_counts.empty and pd.notna(selected_counts["n_countries"].iloc[0]) else int(year_data["country"].nunique())
        n_shield = int(selected_counts["n_shield"].iloc[0]) if not selected_counts.empty and pd.notna(selected_counts["n_shield"].iloc[0]) else 0
        n_projection = int(year_data["is_projection"].sum())
        return (
            build_scatter_figure(countries, selected_year),
            build_count_figure(counts, selected_year),
            status,
            status_class,
            f"{n_countries:,}",
            f"Year: {selected_year}",
            f"{n_shield:,}",
            f"{n_projection:,}",
        )
