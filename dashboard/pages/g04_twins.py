from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash import Dash, Input, Output, dcc, html, dash_table
from dash.exceptions import PreventUpdate

from .common import make_metric_card

# ============================================================
# 1. Paths and visual identity
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data" / "out"
CHART_DIR = PROJECT_DIR / "charts"

DISTANCE_FILE = DATA_DIR / "g04_mesafe.csv"
TRAJECTORY_FILE = DATA_DIR / "g04_yorunge.csv"
TWIN_FILE = DATA_DIR / "g04_zaman_makinesi.csv"

# --- INTERFACE COLORS (From Spec) ---
BACKGROUND = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT_COLOR = "#1F2937"
MUTED_COLOR = "#6B7280"
GRID_COLOR = "#E5E7EB"
BORDER_COLOR = "#E5E7EB"
PROJECTION_COLOR = "#9CA3AF"

# Accent Colors
ACCENT_TURKEY = "#D32F2F"
ACCENT_OTHER = "#D1D5DB"

# Required Columns
REQUIRED_DISTANCE_COLUMNS = {"year", "nearest_distance", "threshold", "has_twin"}
REQUIRED_TRAJECTORY_COLUMNS = {"iso3", "country", "year", "tfr", "lex", "median_age", "is_projection"}
REQUIRED_TWIN_COLUMNS = {"query_year", "rank", "twin_iso3", "twin_country", "twin_year", "distance", "within_threshold", "tfr", "lex", "median_age"}


# ============================================================
# 2. Errors and input helpers
# ============================================================

class DataValidationError(ValueError):
    """Raised when an input dataset cannot safely support the charts."""

def require_file(path: Path, optional: bool = False) -> bool:
    if path.is_file():
        return True
    if optional:
        return False
    raise DataValidationError(
        f"Required input file not found: {path}\n"
        "Check the project structure and the CSV filename."
    )

def read_csv_checked(path: Path, required_columns: set[str]) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read {path.name}: {exc}") from exc

    frame.columns = frame.columns.astype(str).str.strip()
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise DataValidationError(
            f"{path.name} is missing required columns: " + ", ".join(missing)
        )
    return frame

def numeric_column(frame: pd.DataFrame, column: str, *, allow_missing: bool = False) -> pd.Series:
    original = frame[column]
    converted = pd.to_numeric(original, errors="coerce")

    invalid = original.notna() & converted.isna()
    if invalid.any():
        examples = original[invalid].astype(str).head(5).tolist()
        raise DataValidationError(f"Column '{column}' contains invalid numeric values: {examples}")

    if not allow_missing and converted.isna().any():
        raise DataValidationError(f"Column '{column}' contains missing numeric values.")

    return converted

def parse_bool(value) -> bool | None:
    if pd.isna(value): return None
    if isinstance(value, (bool, np.bool_)): return bool(value)
    if isinstance(value, (int, np.integer, float, np.floating)):
        if value == 1: return True
        if value == 0: return False
        return None
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}: return True
    if normalized in {"false", "0", "no", "n"}: return False
    return None

def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.3f})"

def make_base_layout(fig: go.Figure, *, height: int = 460, margin: dict | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="'Inter', sans-serif",
            size=14,
            color=TEXT_COLOR,
        ),
        title_font=dict(size=18, color=TEXT_COLOR, family="'Inter', sans-serif"),
        height=height,
        margin=margin or dict(l=45, r=30, t=65, b=45),
        hoverlabel=dict(
            bgcolor=PANEL,
            bordercolor=GRID_COLOR,
            font=dict(color=TEXT_COLOR, size=14),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            borderwidth=0,
            font=dict(size=14),
            orientation="h",
            yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    return fig

def style_cartesian_axes(fig: go.Figure) -> None:
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR, size=14),
        title_font=dict(color=MUTED_COLOR, size=13),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR, size=14),
        title_font=dict(color=MUTED_COLOR, size=13),
    )

def create_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=15, color=MUTED_COLOR)
    )
    make_base_layout(fig)
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=False)
    return fig

# ============================================================
# 3. Data Loading and Validation
# ============================================================

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    require_file(DISTANCE_FILE)
    require_file(TRAJECTORY_FILE)
    require_file(TWIN_FILE)

    # Load and validate distance data
    df_dist = read_csv_checked(DISTANCE_FILE, REQUIRED_DISTANCE_COLUMNS)
    df_dist["year"] = numeric_column(df_dist, "year", allow_missing=False)
    df_dist["nearest_distance"] = numeric_column(df_dist, "nearest_distance", allow_missing=True)
    df_dist["threshold"] = numeric_column(df_dist, "threshold", allow_missing=True)
    df_dist["has_twin"] = df_dist["has_twin"].map(parse_bool).astype("boolean")

    # Load and validate trajectory data
    df_traj = read_csv_checked(TRAJECTORY_FILE, REQUIRED_TRAJECTORY_COLUMNS)
    df_traj["year"] = numeric_column(df_traj, "year", allow_missing=False)
    df_traj["tfr"] = numeric_column(df_traj, "tfr", allow_missing=True)
    df_traj["lex"] = numeric_column(df_traj, "lex", allow_missing=True)
    df_traj["median_age"] = numeric_column(df_traj, "median_age", allow_missing=True)
    df_traj["is_projection"] = df_traj["is_projection"].map(parse_bool).astype("boolean")

    # Load and validate twin data
    df_twin = read_csv_checked(TWIN_FILE, REQUIRED_TWIN_COLUMNS)
    df_twin["query_year"] = numeric_column(df_twin, "query_year", allow_missing=False)
    df_twin["rank"] = numeric_column(df_twin, "rank", allow_missing=True)
    df_twin["twin_year"] = numeric_column(df_twin, "twin_year", allow_missing=True)
    df_twin["distance"] = numeric_column(df_twin, "distance", allow_missing=True)
    df_twin["tfr"] = numeric_column(df_twin, "tfr", allow_missing=True)
    df_twin["lex"] = numeric_column(df_twin, "lex", allow_missing=True)
    df_twin["median_age"] = numeric_column(df_twin, "median_age", allow_missing=True)
    df_twin["within_threshold"] = df_twin["within_threshold"].map(parse_bool).astype("boolean")

    return df_dist, df_traj, df_twin

# ============================================================
# 4. Chart Builders
# ============================================================

def build_distance_chart(df_dist: pd.DataFrame) -> go.Figure:
    plot_data = df_dist.dropna(subset=["year", "nearest_distance"]).sort_values("year")
    if plot_data.empty:
        return create_empty_figure("No distance data available.")

    fig = go.Figure()

    # Threshold Line
    fig.add_trace(go.Scatter(
        x=plot_data["year"], y=plot_data["threshold"],
        mode="lines", line=dict(color=PROJECTION_COLOR, width=2, dash="dash"),
        name="Threshold", hoverinfo="skip"
    ))

    # Nearest Distance Line
    fig.add_trace(go.Scatter(
        x=plot_data["year"], y=plot_data["nearest_distance"],
        mode="lines+markers", 
        line=dict(color=ACCENT_TURKEY, width=2.5),
        marker=dict(size=8, color=ACCENT_TURKEY, line=dict(width=1, color=PANEL)),
        name="Nearest Distance",
        customdata=plot_data[["threshold", "has_twin"]],
        hovertemplate=(
            "Year: %{x}<br>"
            "Distance: %{y:.3f}<br>"
            "Threshold: %{customdata[0]:.3f}<br>"
            "Twin Exists: %{customdata[1]}<extra></extra>"
        )
    ))

    make_base_layout(fig, height=400)
    style_cartesian_axes(fig)
    fig.update_layout(title="Nearest-Twin Distance Over Time")
    fig.update_yaxes(title_text="Distance")
    return fig

def build_twin_ranking_chart(df_twin: pd.DataFrame, query_year: float) -> go.Figure:
    sub = df_twin[df_twin["query_year"] == query_year].dropna(subset=["distance", "rank"]).sort_values("rank", ascending=False)
    
    if sub.empty:
        return create_empty_figure("No demographic twin profiles are available for this query year.")

    min_rank = sub["rank"].min()
    colors = [ACCENT_TURKEY if r == min_rank else ACCENT_OTHER for r in sub["rank"]]
    
    # Transparency for out of threshold
    opacities = [1.0 if pd.isna(w) or w else 0.4 for w in sub["within_threshold"]]
    marker_colors = [hex_to_rgba(c, o) for c, o in zip(colors, opacities)]

    fig = go.Figure(go.Bar(
        x=sub["distance"],
        y=sub["twin_country"],
        orientation="h",
        marker=dict(color=marker_colors, line=dict(width=1, color=BORDER_COLOR)),
        customdata=sub[["rank", "twin_year", "within_threshold"]],
        hovertemplate=(
            "Rank %{customdata[0]}<br>"
            "Country: %{y}<br>"
            "Profile Year: %{customdata[1]}<br>"
            "Distance: %{x:.3f}<br>"
            "Within Threshold: %{customdata[2]}<extra></extra>"
        )
    ))

    chart_height = max(350, len(sub) * 35 + 80)
    make_base_layout(fig, height=chart_height, margin=dict(l=150, r=30, t=60, b=45))
    style_cartesian_axes(fig)
    fig.update_layout(title=f"Demographic Twin Ranking ({int(query_year)})", showlegend=False)
    fig.update_xaxes(title_text="Distance")
    return fig

def build_profile_charts(df_traj: pd.DataFrame, df_twin: pd.DataFrame, query_year: float, selected_iso3s: list[str]) -> go.Figure:
    tur = df_traj[df_traj["iso3"] == "TUR"].sort_values("year")
    if tur.empty:
        return create_empty_figure("Türkiye trajectory data is missing.")

    fig = make_subplots(
        rows=1, cols=3, 
        subplot_titles=("Total Fertility Rate", "Life Expectancy", "Median Age"),
        horizontal_spacing=0.08
    )

    indicators = [
        ("tfr", 1, "TFR"), 
        ("lex", 2, "Life Expectancy (Years)"), 
        ("median_age", 3, "Median Age (Years)")
    ]

    for ind_col, col_idx, title in indicators:
        tur_hist = tur[~tur["is_projection"].fillna(False)]
        fig.add_trace(go.Scatter(
            x=tur_hist["year"], y=tur_hist[ind_col],
            mode="lines", line=dict(color=ACCENT_TURKEY, width=3),
            name="Türkiye (Historical)", legendgroup="TUR_H", showlegend=(col_idx==1),
            hovertemplate="Türkiye (Hist) %{x}: %{y:.2f}<extra></extra>"
        ), row=1, col=col_idx)

        tur_proj = tur[tur["is_projection"].fillna(False)]
        if not tur_proj.empty:
            if not tur_hist.empty:
                tur_proj = pd.concat([tur_hist.iloc[-1:], tur_proj])
            fig.add_trace(go.Scatter(
                x=tur_proj["year"], y=tur_proj[ind_col],
                mode="lines", line=dict(color=ACCENT_TURKEY, width=3, dash="dash"),
                name="Türkiye (Projected)", legendgroup="TUR_P", showlegend=(col_idx==1),
                hovertemplate="Türkiye (Proj) %{x}: %{y:.2f}<extra></extra>"
            ), row=1, col=col_idx)

        if selected_iso3s:
            twin_sub = df_twin[(df_twin["query_year"] == query_year) & (df_twin["twin_iso3"].isin(selected_iso3s))]
            for _, row in twin_sub.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row["twin_year"]], y=[row[ind_col]],
                    mode="markers", marker=dict(color=MUTED_COLOR, size=9, symbol="diamond", line=dict(width=1, color=PANEL)),
                    name=str(row["twin_country"]), legendgroup=str(row["twin_iso3"]), showlegend=False,
                    hovertemplate=f"{row['twin_country']} ({row['twin_year']}): %{{y:.2f}}<extra></extra>"
                ), row=1, col=col_idx)

    make_base_layout(fig, height=480, margin=dict(l=45, r=20, t=75, b=50))
    style_cartesian_axes(fig)
    fig.update_layout(title=f"Demographic Profile Comparison for {int(query_year)}")
    for i, (_, _, title) in enumerate(indicators, 1):
        fig.update_yaxes(title_text=title, row=1, col=i)
        
    return fig

# ============================================================
# 5. Hub integration: layout and callbacks
# ============================================================

def build_layout(
    df_dist: pd.DataFrame,
    df_traj: pd.DataFrame,
    df_twin: pd.DataFrame,
    show_back_link: bool = True,
):
    """Build the G04 page inside the central Dashboard Hub app."""
    valid_query_years = sorted(df_twin["query_year"].dropna().unique())
    default_year = 2050.0 if 2050.0 in valid_query_years else (valid_query_years[-1] if valid_query_years else None)
    total_query_years = df_dist["year"].nunique()
    years_with_twin = int(df_dist["has_twin"].sum()) if "has_twin" in df_dist.columns else 0

    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))

    children.extend([
        html.Header(className="g04-page-header", children=[
            html.Div("GRAPH 4 / DEMOGRAPHIC TWINS", className="g04-eyebrow"),
            html.H1("Türkiye's Demographic Twins Across Time"),
            html.P(
                "Explore how Türkiye's demographic profile changes over time, which countries most closely resemble it at selected years, and how their demographic trajectories compare.",
                className="g04-intro",
            ),
        ]),
        html.Div(className="metrics", children=[
            make_metric_card("Query years", f"{total_query_years:,}", "Years covered by the nearest-twin analysis."),
            make_metric_card("Years with a twin", f"{years_with_twin:,}", "Years with a qualifying nearest twin."),
            html.Div(id="g04-kpi-candidates-container"),
        ]),
        html.Section(className="g04-panel", children=[
            dcc.Graph(id="g04-distance-chart", figure=build_distance_chart(df_dist), config={"responsive": True, "displaylogo": False}),
        ]),
        html.Div(className="g04-two-column", children=[
            html.Section(className="g04-panel", children=[
                html.H2("Twin Exploration", className="g04-section-heading"),
                html.Div(className="g04-controls-row", children=[
                    html.Label("Query Year:", className="g04-control-label"),
                    dcc.Dropdown(
                        id="g04-query-year-selector",
                        options=[{"label": str(int(y)), "value": y} for y in valid_query_years],
                        value=default_year,
                        clearable=False,
                        style={"width": "140px"},
                        className="g04-dash-dropdown",
                    ),
                ]),
                dcc.Graph(id="g04-ranking-chart", config={"responsive": True, "displaylogo": False}),
            ]),
            html.Section(className="g04-panel", children=[
                html.H2("Profile Comparison", className="g04-section-heading"),
                html.Div(className="g04-controls-row", children=[
                    html.Label("Compare with:", className="g04-control-label"),
                    html.Div(style={"flexGrow": 1}, children=[
                        dcc.Dropdown(id="g04-twin-country-selector", multi=True, className="g04-dash-dropdown"),
                    ]),
                ]),
                dcc.Graph(id="g04-profile-charts", config={"responsive": True, "displaylogo": False}),
            ]),
        ]),
        html.Section(className="g04-panel", children=[
            html.H2("Twin Profile Details", className="g04-section-heading"),
            dash_table.DataTable(
                id="g04-twin-table",
                style_header={"backgroundColor": BACKGROUND, "fontWeight": "600", "border": f"1px solid {BORDER_COLOR}"},
                style_cell={"padding": "14px", "textAlign": "left", "border": f"1px solid {BORDER_COLOR}", "fontSize": "14px"},
                style_data={"whiteSpace": "normal", "height": "auto", "color": TEXT_COLOR},
                style_as_list_view=True,
            ),
        ]),
        html.Section(className="g04-method-note", children=[
            html.Strong("Methodological Notes: "),
            html.Span("The supplied datasets contain precomputed analytical results. The nearest-twin distance and threshold are taken directly from the analysis outputs. A query year and a twin profile year are not necessarily the same. A missing qualifying twin does not necessarily mean that no comparison profile exists; it may mean no candidate meets the defined threshold."),
        ]),
    ])
    return html.Main(className="g04-dashboard", children=children)


def register_callbacks(app: Dash, df_dist: pd.DataFrame, df_traj: pd.DataFrame, df_twin: pd.DataFrame) -> None:
    """Register G04 callbacks on the Hub's one shared Dash app."""
    @app.callback(
        Output("g04-kpi-candidates-container", "children"),
        Input("g04-query-year-selector", "value"),
    )
    def update_kpi(query_year):
        if query_year is None:
            raise PreventUpdate
        count = len(df_twin[df_twin["query_year"] == query_year])
        return make_metric_card("Selected-year candidates", f"{count:,}", "Candidate profiles available for the selected year.")

    @app.callback(
        Output("g04-ranking-chart", "figure"),
        Input("g04-query-year-selector", "value"),
    )
    def update_ranking(query_year):
        if query_year is None:
            return create_empty_figure("Please select a query year.")
        return build_twin_ranking_chart(df_twin, query_year)

    @app.callback(
        [Output("g04-twin-country-selector", "options"), Output("g04-twin-country-selector", "value")],
        Input("g04-query-year-selector", "value"),
    )
    def update_country_dropdown(query_year):
        if query_year is None:
            return [], []
        sub = df_twin[df_twin["query_year"] == query_year].sort_values(["within_threshold", "rank"], ascending=[False, True])
        options = [{"label": str(row["twin_country"]), "value": str(row["twin_iso3"])} for _, row in sub.iterrows()]
        default_val = sub["twin_iso3"].head(6).tolist()
        return options, default_val

    @app.callback(
        Output("g04-profile-charts", "figure"),
        [Input("g04-query-year-selector", "value"), Input("g04-twin-country-selector", "value")],
    )
    def update_profiles(query_year, selected_iso3s):
        if query_year is None:
            return create_empty_figure("Please select a query year.")
        return build_profile_charts(df_traj, df_twin, query_year, selected_iso3s or [])

    @app.callback(
        [Output("g04-twin-table", "data"), Output("g04-twin-table", "columns")],
        Input("g04-query-year-selector", "value"),
    )
    def update_table(query_year):
        if query_year is None:
            raise PreventUpdate
        sub = df_twin[df_twin["query_year"] == query_year].sort_values("rank").copy()
        display_cols = [
            ("rank", "Rank"), ("twin_country", "Twin Country"), ("twin_year", "Profile Year"),
            ("distance", "Distance"), ("within_threshold", "Within Threshold"),
            ("tfr", "Total Fertility Rate"), ("lex", "Life Expectancy"), ("median_age", "Median Age"),
        ]
        columns = [{"name": name, "id": col} for col, name in display_cols]
        for col in ["distance", "tfr", "lex", "median_age"]:
            sub[col] = sub[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "—")
        sub["within_threshold"] = sub["within_threshold"].map({True: "Yes", False: "No", pd.NA: "—"})
        sub["twin_year"] = sub["twin_year"].apply(lambda x: str(int(x)) if pd.notnull(x) else "—")
        return sub.to_dict("records"), columns
