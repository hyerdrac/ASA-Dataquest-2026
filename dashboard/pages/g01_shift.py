from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data" / "out"
SHARE_FILE = DATA_DIR / "g01_bolge_pay.csv"
RANK_FILE = DATA_DIR / "g01_medyan_yas_sira.csv"

BACKGROUND = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
AFRICA = "#E69F00"
EUROPE = "#0072B2"
LATAM = "#009E73"

REGION_ORDER = [
    "Africa",
    "Asia",
    "Europe",
    "Latin America and the Caribbean",
    "Northern America",
    "Oceania",
]
REGION_LABELS = {
    "Africa": "Africa",
    "Asia": "Asia",
    "Europe": "Europe",
    "Latin America and the Caribbean": "Latin America & Caribbean",
    "Northern America": "Northern America",
    "Oceania": "Oceania",
}
# Fixed continent palette shared by the G01 area and bump charts.
# Keep these keys aligned with the region values in the input CSV files.
CONTINENT_COLORS = {
    "Asia": "#D55E00",
    "Europe": "#0072B2",
    "Africa": "#E69F00",
    "Northern America": "#56B4E9",
    "Latin America and the Caribbean": "#009E73",
    "Oceania": "#CC79A7",
}

# The area chart uses the full palette; Africa remains emphasized by its thicker outline.
AREA_COLORS = CONTINENT_COLORS.copy()
# The bump chart uses the same continent colors for every region.
RANK_COLORS = CONTINENT_COLORS.copy()
REQUIRED_SHARE = {"region", "year", "pop_millions", "share_pct", "is_projection"}
REQUIRED_RANK = {"region", "year", "median_age", "rank", "is_projection"}


class DataValidationError(ValueError):
    """Raised when G01 inputs are missing or invalid."""


def _read_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise DataValidationError(
            f"Required input file not found: {path}\n"
            "Place the G01 CSV files in the project's data/out/ folder."
        )
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read {path.name}: {exc}") from exc
    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(required - set(df.columns))
    if missing:
        raise DataValidationError(f"{path.name} is missing columns: {', '.join(missing)}")
    return df


def _parse_bool(series: pd.Series, column: str) -> pd.Series:
    mapping = {
        "true": True, "1": True, "yes": True, "y": True,
        "false": False, "0": False, "no": False, "n": False,
    }
    parsed = series.map(
        lambda value: value if isinstance(value, (bool, np.bool_))
        else mapping.get(str(value).strip().casefold()) if pd.notna(value) else np.nan
    )
    if parsed.isna().any():
        raise DataValidationError(f"Column '{column}' contains missing or unrecognized boolean values.")
    return parsed.astype(bool)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    share = _read_csv(SHARE_FILE, REQUIRED_SHARE)
    rank = _read_csv(RANK_FILE, REQUIRED_RANK)

    for df, columns, filename in [
        (share, ["year", "pop_millions", "share_pct"], SHARE_FILE.name),
        (rank, ["year", "median_age", "rank"], RANK_FILE.name),
    ]:
        for column in columns:
            original = df[column]
            converted = pd.to_numeric(original, errors="coerce")
            if (original.notna() & converted.isna()).any() or converted.isna().any():
                raise DataValidationError(f"{filename}: column '{column}' contains invalid or missing numeric values.")
            df[column] = converted

    share["is_projection"] = _parse_bool(share["is_projection"], "is_projection")
    rank["is_projection"] = _parse_bool(rank["is_projection"], "is_projection")
    share["region"] = share["region"].astype(str).str.strip()
    rank["region"] = rank["region"].astype(str).str.strip()

    unknown_share = sorted(set(share["region"]) - set(REGION_ORDER))
    unknown_rank = sorted(set(rank["region"]) - set(REGION_ORDER))
    if unknown_share or unknown_rank:
        unknown = sorted(set(unknown_share + unknown_rank))
        raise DataValidationError("Unexpected region labels: " + ", ".join(unknown))

    share = share.sort_values(["year", "region"]).reset_index(drop=True)
    rank = rank.sort_values(["year", "region"]).reset_index(drop=True)
    if share.empty or rank.empty:
        raise DataValidationError("G01 input files contain no rows.")
    return share, rank


def _base_layout(fig: go.Figure, height: int = 440) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color=TEXT),
        height=height,
        margin=dict(l=48, r=28, t=74, b=48),
        hoverlabel=dict(bgcolor=PANEL, bordercolor=GRID, font=dict(color=TEXT)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, bgcolor="rgba(255,255,255,0.75)",
            font=dict(size=11),
        ),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BORDER, tickfont=dict(color=TEXT))
    fig.update_yaxes(gridcolor=GRID, linecolor=BORDER, tickfont=dict(color=TEXT))
    return fig


def build_share_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for region in REGION_ORDER:
        sub = df[df["region"] == region].sort_values("year")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["share_pct"],
            mode="lines",
            name=REGION_LABELS[region],
            stackgroup="regions",
            groupnorm="percent",
            line=dict(color=AREA_COLORS[region], width=2.2 if region == "Africa" else 0.8),
            fillcolor=AREA_COLORS[region],
            opacity=1.0 if region == "Africa" else 0.86,
            customdata=np.column_stack([sub["pop_millions"], sub["is_projection"]]),
            hovertemplate=(
                f"<b>{REGION_LABELS[region]}</b><br>"
                "Year: %{x}<br>World population share: %{y:.1f}%"
                "<br>Population: %{customdata[0]:,.0f} million"
                "<br>Projection: %{customdata[1]}<extra></extra>"
            ),
        ))

    projection_start = int(df.loc[df["is_projection"], "year"].min()) if df["is_projection"].any() else None
    if projection_start is not None:
        boundary = projection_start - 1
        fig.add_vline(x=boundary, line_width=1.5, line_dash="dash", line_color=MUTED)
        fig.add_annotation(
            x=boundary, y=1.08, xref="x", yref="paper",
            text="Projection →", showarrow=False, xanchor="left",
            font=dict(size=11, color=MUTED),
        )
    _base_layout(fig, 450)
    fig.update_layout(
        title=dict(text="World population share by region", x=0.02, xanchor="left", font=dict(size=18)),
        yaxis_title="Share of world population (%)",
        xaxis_title="Year",
        yaxis=dict(range=[0, 100], ticksuffix="%", dtick=20),
        hovermode="x unified",
    )
    return fig


def build_rank_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    projection_start = int(df.loc[df["is_projection"], "year"].min()) if df["is_projection"].any() else None

    for region in REGION_ORDER:
        sub = df[df["region"] == region].sort_values("year")
        if sub.empty:
            continue
        color = RANK_COLORS[region]
        width = 3.4 if region in {"Europe", "Latin America and the Caribbean"} else 1.8
        size = 8 if region in {"Europe", "Latin America and the Caribbean"} else 5
        historical = sub[~sub["is_projection"]]
        projected = sub[sub["is_projection"]]
        if not historical.empty:
            fig.add_trace(go.Scatter(
                x=historical["year"], y=historical["rank"],
                mode="lines+markers", name=REGION_LABELS[region],
                legendgroup=region, showlegend=True,
                line=dict(color=color, width=width),
                marker=dict(size=size, color=color),
                customdata=historical[["median_age"]],
                hovertemplate=f"<b>{REGION_LABELS[region]}</b><br>Year: %{{x}}<br>Rank: %{{y}}<br>Median age: %{{customdata[0]:.1f}}<extra></extra>",
            ))
        if not projected.empty:
            if not historical.empty:
                projected = pd.concat([historical.iloc[[-1]], projected]).drop_duplicates("year", keep="last")
            fig.add_trace(go.Scatter(
                x=projected["year"], y=projected["rank"],
                mode="lines+markers", name=f"{REGION_LABELS[region]} (projection)",
                legendgroup=region, showlegend=False,
                line=dict(color=color, width=width, dash="dash"),
                marker=dict(size=size, color=color, symbol="circle-open"),
                customdata=projected[["median_age"]],
                hovertemplate=f"<b>{REGION_LABELS[region]}</b> (projection)<br>Year: %{{x}}<br>Rank: %{{y}}<br>Median age: %{{customdata[0]:.1f}}<extra></extra>",
            ))

    if projection_start is not None:
        boundary = projection_start - 10
        fig.add_vline(x=boundary, line_width=1.5, line_dash="dash", line_color=MUTED)
    # The provided decennial ranks switch between Europe and Latin America & Caribbean
    # from 2080 to 2090; mark the transition interval without inventing an exact year.
    fig.add_annotation(
        x=2085, y=1.52, xref="x", yref="y",
        text="Latin America–Europe<br>ranking crossover (2080–2090)",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
        arrowcolor=LATAM, ax=-95, ay=-48,
        bgcolor="rgba(255,255,255,0.92)", bordercolor=LATAM, borderwidth=1,
        font=dict(size=11, color=TEXT),
    )
    _base_layout(fig, 450)
    fig.update_layout(
        title=dict(text="Regional median-age ranking", x=0.02, xanchor="left", font=dict(size=18)),
        xaxis_title="Year",
        yaxis_title="Rank (1 = oldest median age)",
        yaxis=dict(autorange="reversed", dtick=1, tickmode="linear"),
        hovermode="closest",
    )
    return fig


def build_layout(df_share: pd.DataFrame, df_rank: pd.DataFrame, show_back_link: bool = True):
    start_year = int(df_share["year"].min())
    end_year = int(df_share["year"].max())
    africa = df_share[df_share["region"] == "Africa"].sort_values("year")
    start_africa = float(africa.iloc[0]["share_pct"])
    end_africa = float(africa.iloc[-1]["share_pct"])
    proj_start = int(df_share.loc[df_share["is_projection"], "year"].min()) if df_share["is_projection"].any() else end_year
    crossing = "2080–2090"

    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g01-page-header", children=[
            html.Div("DEMOGRAPHIC CHANGE · G01", className="g01-eyebrow"),
            html.H1("The Great Population Shift"),
            html.P(
                "How the world's population share and regional age ranking change from "
                f"{start_year} to {end_year}, with projections beginning in {proj_start}.",
                className="g01-intro",
            ),
        ]),
        html.Section(className="metrics", children=[
            make_metric_card("AFRICA'S SHARE", f"{start_africa:.1f}%", f"{start_year} world population"),
            make_metric_card("PROJECTED SHARE", f"{end_africa:.1f}%", f"Africa, {end_year}"),
            make_metric_card("RANK CROSSOVER", crossing, "Latin America & Caribbean / Europe"),
            make_metric_card("PROJECTION START", str(proj_start), "Dashed lines distinguish projections"),
        ]),
        html.Section(className="g01-panel", children=[
            html.H2("Population share by region", className="g01-section-heading"),
            dcc_graph("g01-share-chart", build_share_chart(df_share)),
            html.P(
                "Africa is emphasized in red. The stack uses a fixed region order; the dashed divider marks the projection period.",
                className="g01-caption",
            ),
        ]),
        html.Section(className="g01-panel", children=[
            html.H2("Median-age ranking over time", className="g01-section-heading"),
            dcc_graph("g01-rank-chart", build_rank_chart(df_rank)),
            html.P(
                "Rank 1 indicates the highest median age. Europe and Latin America & the Caribbean are highlighted; the crossover is bounded by the supplied decennial observations.",
                className="g01-caption",
            ),
        ]),
        html.Section(className="g01-method-note", children=[
            html.Strong("Reading the charts"),
            html.P(
                "The population-share chart uses the supplied share_pct values and is normalized to 100% for display. "
                "Solid lines represent historical estimates; dashed lines represent projections. "
                "The ranking chart uses the provided rank field and does not interpolate an exact crossover year."
            ),
        ]),
    ])
    return html.Main(className="g01-dashboard", children=children)


def dcc_graph(graph_id: str, figure: go.Figure):
    from dash import dcc
    return dcc.Graph(id=graph_id, figure=figure, config={"displaylogo": False, "responsive": True})
