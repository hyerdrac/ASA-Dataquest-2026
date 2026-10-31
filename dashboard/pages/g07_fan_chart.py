from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "g07_fan_chart.csv"

BG = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
FAN_COLOR = "#0072B2"

REQUIRED_COLUMNS = {
    "LocID", "LocTypeName", "Location", "Time",
    "alt95_bin", "alt95_milyon", "alt80_bin", "alt80_milyon",
    "medyan_bin", "medyan_milyon", "ust80_bin", "ust80_milyon",
    "ust95_bin", "ust95_milyon",
}
VALUE_COLUMNS = ["alt95_milyon", "alt80_milyon", "medyan_milyon", "ust80_milyon", "ust95_milyon"]
LABELS = {
    "alt95_milyon": "Low · 95% interval",
    "alt80_milyon": "Lower · 80% interval",
    "medyan_milyon": "Median projection",
    "ust80_milyon": "Upper · 80% interval",
    "ust95_milyon": "High · 95% interval",
}


class DataValidationError(ValueError):
    """Raised when the G07 CSV is missing or malformed."""


def load_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(
            f"Required input file not found: {DATA_FILE}\n"
            "Place g07_fan_chart.csv in the project's data/out/ folder."
        )
    try:
        df = pd.read_csv(DATA_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read G07 CSV: {exc}") from exc
    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(f"{DATA_FILE.name} missing columns: {', '.join(missing)}")
    df = df.copy()
    df["Location"] = df["Location"].astype(str).str.strip()
    df["LocTypeName"] = df["LocTypeName"].astype(str).str.strip()
    df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
    for col in VALUE_COLUMNS + ["alt95_bin", "alt80_bin", "medyan_bin", "ust80_bin", "ust95_bin"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Location", "Time", "medyan_milyon"])
    df["Time"] = df["Time"].astype(int)
    df = df.sort_values(["Location", "Time"]).reset_index(drop=True)
    if df.empty:
        raise DataValidationError("G07 CSV contains no usable rows after numeric conversion.")
    return df


def _endpoint_row(data: pd.DataFrame) -> pd.Series:
    endpoint = data[data["Time"] == 2100]
    if endpoint.empty:
        endpoint = data[data["Time"] == data["Time"].max()]
    return endpoint.iloc[-1]


def build_figure(df: pd.DataFrame, location: str) -> go.Figure:
    data = df[df["Location"] == location].sort_values("Time").copy()
    fig = go.Figure()
    if data.empty:
        fig.add_annotation(text=f"No observations available for {location}.", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        fig.update_layout(paper_bgcolor=BG, plot_bgcolor=PANEL)
        return fig

    x = data["Time"]
    # Outer 95% band: one hue at low opacity. The boundary lines are thin dashed gray.
    fig.add_trace(go.Scatter(
        x=x, y=data["alt95_milyon"], mode="lines", name="Low · 95%",
        line=dict(color="#9CA3AF", width=1, dash="dash"),
        hovertemplate="Year %{x}<br>Low 95%: %{y:.3f} million<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=data["ust95_milyon"], mode="lines", name="High · 95%",
        line=dict(color="#9CA3AF", width=1, dash="dash"), fill="tonexty",
        fillcolor="rgba(0,114,178,0.12)",
        hovertemplate="Year %{x}<br>High 95%: %{y:.3f} million<extra></extra>",
    ))
    # Inner 80% band: same hue, stronger opacity.
    fig.add_trace(go.Scatter(
        x=x, y=data["alt80_milyon"], mode="lines", name="Low · 80%",
        line=dict(color="rgba(0,114,178,0.0)", width=0),
        hovertemplate="Year %{x}<br>Low 80%: %{y:.3f} million<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=data["ust80_milyon"], mode="lines", name="High · 80%",
        line=dict(color="rgba(0,114,178,0.0)", width=0), fill="tonexty",
        fillcolor="rgba(0,114,178,0.25)",
        hovertemplate="Year %{x}<br>High 80%: %{y:.3f} million<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=data["medyan_milyon"], mode="lines", name="Median",
        line=dict(color=FAN_COLOR, width=3),
        hovertemplate="Year %{x}<br>Median: %{y:.3f} million<extra></extra>",
    ))

    endpoint = _endpoint_row(data)
    endpoint_year = int(endpoint["Time"])
    # Label the 95% and 80% interval edges plus median at the right edge.
    endpoint_labels = [
        ("alt95_milyon", "Low 95%", "#6B7280", -8),
        ("alt80_milyon", "Low 80%", FAN_COLOR, 0),
        ("medyan_milyon", "Median", FAN_COLOR, 0),
        ("ust80_milyon", "High 80%", FAN_COLOR, 0),
        ("ust95_milyon", "High 95%", "#6B7280", 8),
    ]
    for col, label, color, yshift in endpoint_labels:
        val = endpoint[col]
        if pd.notna(val):
            fig.add_annotation(
                x=endpoint_year, y=float(val), xref="x", yref="y",
                text=f"{label}: {float(val):,.1f}M", showarrow=False,
                xanchor="left", xshift=8, yshift=yshift,
                font=dict(size=10, color=color), bgcolor="rgba(255,255,255,0.82)",
            )

    fig.update_layout(
        title=dict(text=f"Population projection fan chart · {location}", x=0.02, xanchor="left",
                   font=dict(size=21, color=TEXT)),
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        font=dict(family="Inter, Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=70, r=170, t=95, b=62),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        xaxis=dict(title="Year", gridcolor=GRID, showline=True, linecolor=BORDER,
                   range=[int(data["Time"].min()), max(endpoint_year, int(data["Time"].max()))]),
        yaxis=dict(title="Population (millions)", gridcolor=GRID, showline=True, linecolor=BORDER,
                   rangemode="tozero"),
    )
    fig.add_annotation(
        x=1, y=1.12, xref="paper", yref="paper",
        text=f"Endpoint labels: {endpoint_year}", showarrow=False, xanchor="right",
        font=dict(size=12, color=MUTED),
    )
    return fig


def _default_location(df: pd.DataFrame) -> str:
    locations = set(df["Location"].unique())
    for candidate in ("Türkiye", "Turkey"):
        if candidate in locations:
            return candidate
    for candidate in ("World", "WORLD", "世界"):
        if candidate in locations:
            return candidate
    # Prefer aggregate rows if clearly identified; otherwise use the location with the most years.
    aggregates = df[df["LocTypeName"].str.casefold().str.contains("world|region|continent|group|aggregate", regex=True)]
    if not aggregates.empty:
        counts = aggregates.groupby("Location")["Time"].nunique().sort_values(ascending=False)
        return str(counts.index[0])
    counts = df.groupby("Location")["Time"].nunique().sort_values(ascending=False)
    return str(counts.index[0])


def build_layout(df: pd.DataFrame, show_back_link: bool = True):
    locations = sorted(df["Location"].dropna().unique().tolist())
    default_location = _default_location(df)
    selected = df[df["Location"] == default_location]
    endpoint = _endpoint_row(selected)
    median_value = float(endpoint["medyan_milyon"])
    range95 = float(endpoint["ust95_milyon"] - endpoint["alt95_milyon"])
    endpoint_year = int(endpoint["Time"])
    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g07-header", children=[
            html.Div("G07 · FAN CHART", className="g07-eyebrow"),
            html.H1("Population projection uncertainty"),
            html.P("Explore the median population projection and its 80% and 95% uncertainty intervals. "
                   "All bands use the same blue hue at two opacities; the outer High/Low bounds are dashed gray.",
                   className="g07-intro"),
        ]),
        html.Section(className="metrics g07-metrics", children=[
            html.Div([html.Div(f"Median · {endpoint_year}", className="metric-label"),
                      html.Div(f"{median_value:,.1f}M", id="g07-metric-median", className="metric-value"),
                      html.Div(f"{default_location} · population", className="metric-description")], className="metric-card"),
            html.Div([html.Div("95% interval width", className="metric-label"),
                      html.Div(f"{range95:,.1f}M", id="g07-metric-range", className="metric-value"),
                      html.Div(f"High–Low range in {endpoint_year}", className="metric-description")], className="metric-card"),
            html.Div([html.Div("Projection years", className="metric-label"),
                      html.Div(str(int(selected["Time"].nunique())), id="g07-metric-years", className="metric-value"),
                      html.Div(f"Available years for {default_location}", className="metric-description")], className="metric-card"),
        ]),
        html.Section(className="g07-panel", children=[
            html.Div(className="g07-controls", children=[
                html.Div([html.Label("Location", htmlFor="g07-location", className="g07-label"),
                          dcc.Dropdown(id="g07-location", options=[{"label": v, "value": v} for v in locations],
                                       value=default_location, clearable=False, searchable=True)],
                         className="g07-control"),
                html.P("Right-edge labels show the interval values at 2100 when available; otherwise they show the last year in the file.",
                       className="g07-note"),
            ]),
        ]),
        html.Section(className="g07-panel g07-chart-panel", children=[
            dcc.Graph(id="g07-fan-graph", figure=build_figure(df, default_location),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "680px", "minHeight": "680px", "width": "100%"}),
        ]),
        html.Div(className="g07-method-note", children=[
            html.Strong("How to read this chart. "),
            "The median is the central projection. The darker inner band represents the 80% interval and the lighter outer band the 95% interval. "
            "The dashed gray lines mark the outer Low/High bounds. Values are shown in millions; no values are interpolated.",
        ]),
    ])
    return html.Main(className="g07-dashboard", children=children)


def register_callbacks(app, df: pd.DataFrame) -> None:
    @app.callback(
        Output("g07-fan-graph", "figure"),
        Output("g07-metric-median", "children"),
        Output("g07-metric-range", "children"),
        Output("g07-metric-years", "children"),
        Input("g07-location", "value"),
    )
    def update_g07(location):
        location = location if location in set(df["Location"].unique()) else _default_location(df)
        selected = df[df["Location"] == location]
        endpoint = _endpoint_row(selected)
        year = int(endpoint["Time"])
        median = float(endpoint["medyan_milyon"])
        range95 = float(endpoint["ust95_milyon"] - endpoint["alt95_milyon"])
        return (
            build_figure(df, location),
            f"{median:,.1f}M",
            f"{range95:,.1f}M",
            f"{int(selected['Time'].nunique()):,}",
        )
