from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "g05_sagkalim.csv"

REQUIRED_COLUMNS = {"country", "year", "sex", "age", "survivors_per_1000"}
BACKGROUND = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
TURKIYE = "#0072B2"
YEAR_COLORS = {1950: "#9ECAE1", 1990: "#4292C6", 2023: "#084594"}


class DataValidationError(ValueError):
    """Raised when the G05 input data is missing or invalid."""


def load_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(
            f"Required input file not found: {DATA_FILE}\n"
            "Place g05_sagkalim.csv in the project's data/out/ folder."
        )
    try:
        df = pd.read_csv(DATA_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read {DATA_FILE.name}: {exc}") from exc
    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(
            f"{DATA_FILE.name} is missing columns: {', '.join(missing)}"
        )
    df = df.copy()
    df["country"] = df["country"].astype(str).str.strip()
    df["sex"] = df["sex"].astype(str).str.strip().str.lower()
    for col in ("year", "age", "survivors_per_1000"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["country", "year", "age", "survivors_per_1000", "sex"])
    df["year"] = df["year"].astype(int)
    df["age"] = df["age"].astype(int)
    df = df[df["survivors_per_1000"].between(0, 1000)]
    if df.empty:
        raise DataValidationError("G05 input contains no usable survival observations.")
    if not set(df["sex"].unique()).issubset({"both", "female", "male"}):
        # Keep unexpected labels visible rather than silently remapping them.
        pass
    return df.sort_values(["country", "year", "sex", "age"]).reset_index(drop=True)


def _base_layout(fig: go.Figure, title: str, subtitle: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.02, y=0.99, xanchor="left", yanchor="top", font=dict(size=20, color=TEXT)),
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=PANEL,
        margin=dict(l=58, r=28, t=150, b=58),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0,
            xanchor="left", x=0, title_text=""
        ),
        xaxis=dict(
            title="Age (years)", gridcolor=GRID, zeroline=False,
            showline=True, linecolor=BORDER, dtick=10
        ),
        yaxis=dict(
            title="Survivors per 1,000 at birth", gridcolor=GRID,
            zeroline=False, range=[0, 1025], showline=True, linecolor=BORDER
        ),
        annotations=[
            dict(
                text=subtitle, x=0, y=1.0, xref="paper", yref="paper", yshift=60,
                xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=12, color=MUTED)
            )
        ],
    )
    return fig


def build_history_figure(df: pd.DataFrame, sex: str = "both") -> go.Figure:
    data = df[(df["country"] == "Türkiye") & (df["sex"] == sex) & (df["year"].isin([1950, 1990, 2023]))]
    fig = go.Figure()
    for year in [1950, 1990, 2023]:
        part = data[data["year"] == year].sort_values("age")
        if part.empty:
            continue
        # Markers only: the source has observations at selected ages, not a continuous life table.
        fig.add_trace(go.Scatter(
            x=part["age"], y=part["survivors_per_1000"],
            mode="markers+text" if year == 2023 else "markers",
            name=str(year), legendgroup=str(year),
            marker=dict(size=11 if year == 2023 else 9, color=YEAR_COLORS[year],
                        line=dict(width=1.3, color="#FFFFFF")),
            text=[f"{v:.1f}" for v in part["survivors_per_1000"]] if year == 2023 else None,
            textposition="top center", textfont=dict(size=10, color=YEAR_COLORS[year]),
            customdata=part[["country", "year", "sex", "age"]].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Year: %{customdata[1]}"
                "<br>Sex: %{customdata[2]}<br>Age: %{customdata[3]}"
                "<br>Survivors: %{y:.1f} per 1,000<extra></extra>"
            ),
        ))
    _base_layout(
        fig,
        "Türkiye: survival revolution",
        "Observed ages only — markers are intentionally not connected; color shades distinguish years.",
    )
    fig.update_xaxes(range=[-2, 67], tickvals=[0, 1, 5, 10, 20, 30, 40, 50, 60])
    return fig


def build_comparison_figure(df: pd.DataFrame, sex: str = "both") -> go.Figure:
    data = df[(df["year"] == 2023) & (df["sex"] == sex)]
    fig = go.Figure()
    peers = data[data["country"] != "Türkiye"]
    if not peers.empty:
        fig.add_trace(go.Scatter(
            x=peers["age"], y=peers["survivors_per_1000"],
            mode="markers", name="Other countries",
            marker=dict(size=8, color="#A7AFBA", opacity=0.8, line=dict(width=0.5, color="#FFFFFF")),
            customdata=peers[["country", "age"]].to_numpy(),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Age: %{customdata[1]}"
                "<br>Survivors: %{y:.1f} per 1,000<extra></extra>"
            ),
        ))
    turkey = data[data["country"] == "Türkiye"]
    if not turkey.empty:
        fig.add_trace(go.Scatter(
            x=turkey["age"], y=turkey["survivors_per_1000"],
            mode="markers+text", name="Türkiye",
            marker=dict(size=12, color=TURKIYE, line=dict(width=1.5, color="#FFFFFF")),
            text=[f"{v:.1f}" for v in turkey["survivors_per_1000"]],
            textposition="top center", textfont=dict(size=10, color=TURKIYE),
            customdata=turkey[["country", "age"]].to_numpy(),
            hovertemplate=(
                "<b>Türkiye</b><br>Age: %{customdata[1]}"
                "<br>Survivors: %{y:.1f} per 1,000<extra></extra>"
            ),
        ))
    _base_layout(
        fig,
        "2023: country comparison",
        "Türkiye is highlighted; other countries are neutral gray. Only reported age points are shown.",
    )
    fig.update_xaxes(range=[-2, 67], tickvals=[0, 1, 5, 10, 20, 30, 40, 50, 60])
    return fig


def build_layout(df: pd.DataFrame, show_back_link: bool = True):
    # Normalize the KPI operands explicitly. This keeps the page resilient when a
    # CSV is edited/exported by spreadsheet software and numeric cells become text.
    turkey_both = df[
        (df["country"].astype(str).str.strip().str.casefold().isin({"türkiye", "turkiye", "turkey"}))
        & (pd.to_numeric(df["year"], errors="coerce") == 2023)
        & (df["sex"].astype(str).str.strip().str.casefold() == "both")
        & (pd.to_numeric(df["age"], errors="coerce") == 60)
    ].copy()
    turkey_1950 = df[
        (df["country"].astype(str).str.strip().str.casefold().isin({"türkiye", "turkiye", "turkey"}))
        & (pd.to_numeric(df["year"], errors="coerce") == 1950)
        & (df["sex"].astype(str).str.strip().str.casefold() == "both")
        & (pd.to_numeric(df["age"], errors="coerce") == 60)
    ].copy()
    value_2023 = pd.to_numeric(turkey_both["survivors_per_1000"], errors="coerce").dropna()
    value_1950 = pd.to_numeric(turkey_1950["survivors_per_1000"], errors="coerce").dropna()
    latest = f"{float(value_2023.iloc[0]):.1f}" if not value_2023.empty else "N/A"
    change = (
        f"{float(value_2023.iloc[0]) - float(value_1950.iloc[0]):+.1f}"
        if not value_2023.empty and not value_1950.empty else "N/A"
    )
    countries_2023 = df.loc[df["year"] == 2023, "country"].nunique()
    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g05-header", children=[
            html.Div("G05 · SURVIVAL REVOLUTION", className="g05-eyebrow"),
            html.H1("The survival revolution"),
            html.P(
                "Compare how many people out of every 1,000 born survive to selected ages, "
                "and how Türkiye's survival profile has changed across generations.",
                className="g05-intro",
            ),
        ]),
        html.Section(className="metrics g05-metrics", children=[
            make_metric_card("Türkiye · age 60 (2023)", latest, "Survivors per 1,000 at birth"),
            make_metric_card("Change since 1950", change, "Difference at age 60, per 1,000"),
            make_metric_card("Countries in 2023", str(countries_2023), "Countries represented in the file"),
        ]),
        html.Section(className="g05-panel", children=[
            html.Div(className="g05-controls", children=[
                html.Div(children=[
                    html.Label("Sex", htmlFor="g05-sex", className="g05-label"),
                    dcc.Dropdown(
                        id="g05-sex",
                        options=[
                            {"label": "All sexes (both)", "value": "both"},
                            {"label": "Female", "value": "female"},
                            {"label": "Male", "value": "male"},
                        ],
                        value="both", clearable=False, searchable=False,
                    ),
                ], className="g05-control"),
                html.P(
                    "The file contains observations at ages 0, 1, 5, 40 and 60 for 'both', "
                    "and ages 0, 40 and 60 for female/male. No values are interpolated.",
                    className="g05-note",
                ),
            ]),
        ]),
        html.Section(className="g05-panel", children=[
            html.H2("Türkiye over time", className="g05-section-heading"),
            dcc.Graph(id="g05-history-graph", figure=build_history_figure(df), config={"displayModeBar": False, "responsive": True}, style={"height": "540px", "minHeight": "540px", "width": "100%"}),
        ]),
        html.Section(className="g05-panel", children=[
            html.H2("2023 country benchmark", className="g05-section-heading"),
            dcc.Graph(id="g05-comparison-graph", figure=build_comparison_figure(df), config={"displayModeBar": False, "responsive": True}, style={"height": "540px", "minHeight": "540px", "width": "100%"}),
        ]),
        html.Div(className="g05-method-note", children=[
            html.Strong("Reading the chart. "),
            "Each marker is a reported observation, not an estimate for the ages between markers. "
            "The year colors in the Türkiye comparison use three shades of the same blue. "
            "Country comparison uses neutral gray for peers and blue for Türkiye.",
        ]),
    ])
    return html.Main(className="g05-dashboard", children=children)


def _normalize_sex(value: object) -> str:
    """Normalize the dropdown value before applying it to either chart."""
    sex = str(value or "both").strip().casefold()
    return sex if sex in {"both", "female", "male"} else "both"


def register_callbacks(app, df: pd.DataFrame) -> None:
    # Keep each graph in its own callback. A multi-output callback made both
    # charts depend on the same response; separating them prevents one figure
    # update from blocking the other and makes repeated dropdown changes robust.
    @app.callback(
        Output("g05-history-graph", "figure"),
        Input("g05-sex", "value"),
    )
    def update_g05_history(sex):
        return build_history_figure(df, _normalize_sex(sex))

    @app.callback(
        Output("g05-comparison-graph", "figure"),
        Input("g05-sex", "value"),
    )
    def update_g05_comparison(sex):
        return build_comparison_figure(df, _normalize_sex(sex))
