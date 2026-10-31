from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "g08_selale.csv"

BG = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
POSITIVE = "#0072B2"
NEGATIVE = "#C62828"
NEUTRAL = "#9CA3AF"


# Display-only translations for Turkish labels in the source CSV. Original values
# are retained for filtering and data calculations. Add terms here as new labels appear.
DISPLAY_TRANSLATIONS = {
    # Complete values observed in the supplied g08.unique() output.
    "1. Göç etkisi": "1. Migration effect",
    "2. Doğurganlık etkisi": "2. Fertility effect",
    "3. Ölüm etkisi": "3. Mortality effect",
    "Doğurganlık + Ölüm + Göç": "Fertility + Mortality + Migration",
    "Doğurganlık + Göç": "Fertility + Migration",
    "Doğurganlık + Ölüm": "Fertility + Mortality",
    "Ayrıştırma": "Decomposition",
    "Senaryo": "Scenario",
    "Göç etkisi": "Migration effect",
    "Doğurganlık etkisi": "Fertility effect",
    "Ölüm etkisi": "Mortality effect",
    "Ergen doğurganlığı": "Adolescent fertility",
    "Göç": "Migration",
    "Doğurganlık": "Fertility",
    "Ölüm": "Mortality",
    "Sıfır göç": "Zero migration",
    "Anlık yenileme sıfır göç": "Instant replacement zero migration",
    "Medyan nüfus tahmini": "Median population estimate",
    "Ülke/Bölge": "Country/Area",
}

def _display_text(value) -> str:
    """Translate known Turkish data labels for display without changing source data."""
    text = "" if value is None else str(value)
    # Longer phrases first so a phrase is translated before its individual words.
    for source in sorted(DISPLAY_TRANSLATIONS, key=len, reverse=True):
        text = text.replace(source, DISPLAY_TRANSLATIONS[source])
    return text

REQUIRED_COLUMNS = {
    "LocID", "LocTypeName", "Location", "Time", "Tur", "Adim",
    "Varsayim_grubu", "Nufus_milyon", "Referans", "Referans_milyon",
    "Fark_milyon", "Fark_yuzde",
}


class DataValidationError(ValueError):
    """Raised when the G08 input file is missing or malformed."""


def load_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(
            f"Required input file not found: {DATA_FILE}\n"
            "Place g08_selale.csv in the project's data/out/ folder."
        )
    try:
        df = pd.read_csv(DATA_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read G08 CSV: {exc}") from exc

    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(f"{DATA_FILE.name} missing columns: {', '.join(missing)}")

    df = df.copy()
    for col in ("LocID", "Time", "Nufus_milyon", "Referans_milyon", "Fark_milyon", "Fark_yuzde"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Location", "Time", "Tur", "Adim", "Nufus_milyon", "Fark_milyon"])
    df["Time"] = df["Time"].astype(int)
    for col in ("Location", "LocTypeName", "Tur", "Adim", "Varsayim_grubu", "Referans"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[df["Tur"].isin(["Ayrıştırma", "Senaryo"])]
    if df.empty:
        raise DataValidationError("G08 CSV contains no usable decomposition or scenario rows.")
    return df.sort_values(["Location", "Time", "Tur", "Adim"]).reset_index(drop=True)


def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=21, color=TEXT)),
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        margin=dict(l=65, r=145, t=105, b=125),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        xaxis=dict(title="", gridcolor=GRID, showline=True, linecolor=BORDER,
                   tickangle=-18, automargin=True),
        yaxis=dict(title="Population (millions)", gridcolor=GRID, showline=True,
                   linecolor=BORDER, rangemode="tozero", zeroline=True,
                   zerolinecolor=BORDER),
        showlegend=False,
    )
    return fig


def _build_decomposition(data: pd.DataFrame, location: str, year: int) -> go.Figure:
    data = data[data["Tur"] == "Ayrıştırma"].copy()
    data = data.sort_values("Adim")
    fig = go.Figure()
    if data.empty:
        fig.add_annotation(text="No decomposition rows available for this selection.",
                           x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        return _base_layout(fig, f"Waterfall decomposition · {location} · {year}")

    # The first reference is the starting point; subsequent Fark_milyon values
    # are sequential contributions. The final row is the resulting population.
    first = data.iloc[0]
    start = float(first["Referans_milyon"]) if pd.notna(first["Referans_milyon"]) else float(first["Nufus_milyon"] - first["Fark_milyon"])
    labels = [_display_text(first["Referans"] or "Starting population")]
    measures = ["absolute"]
    values = [start]
    hover_refs = [start]

    for _, row in data.iterrows():
        labels.append(_display_text(row["Adim"]))
        measures.append("relative")
        values.append(float(row["Fark_milyon"]))
        hover_refs.append(float(row["Nufus_milyon"]))

    last = data.iloc[-1]
    labels.append("Final population")
    measures.append("total")
    values.append(float(last["Nufus_milyon"]))
    hover_refs.append(float(last["Nufus_milyon"]))

    fig.add_trace(go.Waterfall(
        name="Population change",
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        text=[f"{v:+,.2f}" if m == "relative" else f"{v:,.2f}" for v, m in zip(values, measures)],
        textposition="outside",
        connector={"line": {"color": "#9CA3AF", "width": 1}},
        increasing={"marker": {"color": POSITIVE}},
        decreasing={"marker": {"color": NEGATIVE}},
        totals={"marker": {"color": NEUTRAL}},
        customdata=hover_refs,
        hovertemplate="%{x}<br>Change / value: %{y:,.3f} million<extra></extra>",
    ))
    return _base_layout(fig, f"Population decomposition · {location} · {year}")


def _build_scenarios(data: pd.DataFrame, location: str, year: int) -> go.Figure:
    data = data[data["Tur"] == "Senaryo"].copy()
    fig = go.Figure()
    if data.empty:
        fig.add_annotation(text="No scenario rows available for this selection.",
                           x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        return _base_layout(fig, f"Scenario comparison · {location} · {year}")
    data = data.sort_values("Fark_milyon")
    colors = [POSITIVE if v >= 0 else NEGATIVE for v in data["Fark_milyon"]]
    fig.add_trace(go.Bar(
        x=data["Fark_milyon"],
        y=[_display_text(v) for v in data["Adim"]],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+,.2f}M ({p:+.1f}%)" for v, p in zip(data["Fark_milyon"], data["Fark_yuzde"].fillna(0))],
        textposition="outside",
        customdata=[[v, _display_text(ref), _display_text(group)]
                   for v, ref, group in data[["Nufus_milyon", "Referans", "Varsayim_grubu"]].to_numpy()],
        hovertemplate=(
            "<b>%{y}</b><br>Difference: %{x:+,.3f} million"
            "<br>Population: %{customdata[0]:,.3f} million"
            "<br>Reference: %{customdata[1]}<br>Assumption: %{customdata[2]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        yaxis=dict(title="", gridcolor=GRID, showline=True, linecolor=BORDER, automargin=True),
        xaxis=dict(title="Difference from reference (millions)", gridcolor=GRID, zeroline=True,
                   zerolinecolor="#6B7280", showline=True, linecolor=BORDER),
        margin=dict(l=210, r=90, t=88, b=60),
    )
    fig.update_layout(
        title=dict(text=f"Scenario differences · {location} · {year}", x=0.02, xanchor="left",
                   font=dict(size=21, color=TEXT)),
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        paper_bgcolor=BG, plot_bgcolor=PANEL, showlegend=False,
    )
    return fig


def build_figure(df: pd.DataFrame, location: str, year: int, chart_type: str) -> go.Figure:
    subset = df[(df["Location"] == location) & (df["Time"] == int(year))]
    if chart_type == "Senaryo":
        return _build_scenarios(subset, location, int(year))
    return _build_decomposition(subset, location, int(year))


def _kpis(df: pd.DataFrame, location: str, year: int, chart_type: str) -> tuple[str, str, str]:
    data = df[(df["Location"] == location) & (df["Time"] == int(year)) & (df["Tur"] == chart_type)]
    if data.empty:
        return "—", "—", "0"
    end_value = float(data["Nufus_milyon"].iloc[-1])
    max_diff = float(data["Fark_milyon"].max())
    min_diff = float(data["Fark_milyon"].min())
    return f"{end_value:,.2f}M", f"{max_diff:+,.2f}M / {min_diff:+,.2f}M", str(len(data))


def build_layout(df: pd.DataFrame, show_back_link: bool = True):
    locations = sorted(df["Location"].dropna().unique().tolist())
    default_location = "Türkiye" if "Türkiye" in locations else ("Turkey" if "Turkey" in locations else locations[0])
    location_data = df[df["Location"] == default_location]
    years = sorted(location_data["Time"].unique().tolist())
    default_year = 2050 if 2050 in years else years[-1]
    types = sorted(df["Tur"].unique().tolist())
    default_type = "Ayrıştırma" if "Ayrıştırma" in types else types[0]
    kpi_value, kpi_diff, kpi_count = _kpis(df, default_location, default_year, default_type)
    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g08-header", children=[
            html.Div("G08 · WATERFALL", className="g08-eyebrow"),
            html.H1("Population change waterfall"),
            html.P(
                "Separate sequential demographic contributions from alternative scenario comparisons. "
                "The starting and ending population are gray, positive effects blue, and negative effects red.",
                className="g08-intro",
            ),
        ]),
        html.Section(className="metrics g08-metrics", children=[
            html.Div([html.Div("Population value", className="metric-label"),
                      html.Div(kpi_value, id="g08-metric-value", className="metric-value"),
                      html.Div(f"{default_location} · {default_year}", className="metric-description")],
                     className="metric-card"),
            html.Div([html.Div("Largest / smallest difference", className="metric-label"),
                      html.Div(kpi_diff, id="g08-metric-diff", className="metric-value"),
                      html.Div(_display_text(default_type), className="metric-description")],
                     className="metric-card"),
            html.Div([html.Div("Steps / scenarios", className="metric-label"),
                      html.Div(kpi_count, id="g08-metric-count", className="metric-value"),
                      html.Div("Rows in selected view", className="metric-description")],
                     className="metric-card"),
        ]),
        html.Section(className="g08-panel", children=[
            html.Div(className="g08-controls", children=[
                html.Div([html.Label("Location", htmlFor="g08-location", className="g08-label"),
                          dcc.Dropdown(id="g08-location",
                                       options=[{"label": v, "value": v} for v in locations],
                                       value=default_location, clearable=False, searchable=True)],
                         className="g08-control"),
                html.Div([html.Label("Year", htmlFor="g08-year", className="g08-label"),
                          dcc.Dropdown(id="g08-year",
                                       options=[{"label": str(int(v)), "value": int(v)}
                                                for v in sorted(df["Time"].unique())],
                                       value=default_year, clearable=False)],
                         className="g08-control"),
                html.Div([html.Label("View", htmlFor="g08-type", className="g08-label"),
                          dcc.Dropdown(id="g08-type",
                                       options=[{"label": _display_text(v), "value": v} for v in types],
                                       value=default_type, clearable=False)],
                         className="g08-control"),
            ]),
        ]),
        html.Section(className="g08-panel g08-chart-panel", children=[
            dcc.Graph(id="g08-waterfall-graph",
                      figure=build_figure(df, default_location, default_year, default_type),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "720px", "minHeight": "720px", "width": "100%"}),
        ]),
        html.P(
            "Reading note: decomposition rows are treated as sequential effects (Fark_milyon); "
            "scenario rows are shown as signed differences from their stated references. "
            "All values are displayed in millions. The chart does not interpolate missing steps.",
            className="g08-method-note",
        ),
    ])
    return html.Main(className="g08-dashboard", children=children)


def register_callbacks(app, df: pd.DataFrame) -> None:
    @app.callback(
        Output("g08-waterfall-graph", "figure"),
        Output("g08-metric-value", "children"),
        Output("g08-metric-diff", "children"),
        Output("g08-metric-count", "children"),
        Input("g08-location", "value"),
        Input("g08-year", "value"),
        Input("g08-type", "value"),
    )
    def update_g08(location, year, chart_type):
        if location not in set(df["Location"].unique()):
            location = "Türkiye" if "Türkiye" in set(df["Location"]) else ("Turkey" if "Turkey" in set(df["Location"]) else sorted(df["Location"].unique())[0])
        location_years = sorted(df.loc[df["Location"] == location, "Time"].unique())
        if year not in location_years:
            year = 2050 if 2050 in location_years else location_years[-1]
        if chart_type not in set(df["Tur"].unique()):
            chart_type = "Ayrıştırma" if "Ayrıştırma" in set(df["Tur"]) else sorted(df["Tur"].unique())[0]
        value, diff, count = _kpis(df, location, int(year), chart_type)
        return build_figure(df, location, int(year), chart_type), value, diff, count
