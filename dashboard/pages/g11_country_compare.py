from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .common import make_metric_card

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "clean" / "countries_clean.csv"

# Shared design tokens (same values as the other Hub modules / style.css).
BG = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BORDER = "#D1D5DB"
COLOR_A = "#0072B2"   # first country: Hub blue
COLOR_B = "#7B1113"   # second country: Hub accent (dark red)
PROJECTION_FILL = "rgba(107,114,128,0.07)"

REQUIRED_COLUMNS = {"Location", "Time", "IsProjection"}

# key -> (group, label, unit, decimals)
# Units follow the source file: counts are in thousands, rates as noted.
INDICATORS: dict[str, tuple[str, str, str, int]] = {
    # ---- Population -------------------------------------------------------
    "TPopulation1Jan": ("Population", "Total population, 1 January", "thousands", 0),
    "TPopulation1July": ("Population", "Total population, 1 July (mid-year)", "thousands", 0),
    "TPopulationMale1July": ("Population", "Male population, 1 July", "thousands", 0),
    "TPopulationFemale1July": ("Population", "Female population, 1 July", "thousands", 0),
    "PopDensity": ("Population", "Population density", "persons per km²", 1),
    "PopSexRatio": ("Population", "Population sex ratio", "males per 100 females", 1),
    "MedianAgePop": ("Population", "Median age", "years", 1),
    "PopChange": ("Population", "Population change", "thousands", 0),
    "PopGrowthRate": ("Population", "Population growth rate", "percent per year", 2),
    "DoublingTime": ("Population", "Population doubling time", "years", 1),
    "NatChange": ("Population", "Natural change (births minus deaths)", "thousands", 0),
    "NatChangeRT": ("Population", "Rate of natural change", "per 1,000 population", 2),
    # ---- Fertility & births ----------------------------------------------
    "TFR": ("Fertility", "Total fertility rate", "live births per woman", 2),
    "NRR": ("Fertility", "Net reproduction rate", "surviving daughters per woman", 2),
    "MAC": ("Fertility", "Mean age of childbearing", "years", 1),
    "CBR": ("Fertility", "Crude birth rate", "births per 1,000 population", 2),
    "Births": ("Fertility", "Births, both sexes", "thousands", 0),
    "BirthsMale": ("Fertility", "Births, male", "thousands", 0),
    "BirthsFemale": ("Fertility", "Births, female", "thousands", 0),
    "Births1519": ("Fertility", "Births to women aged 15–19", "thousands", 1),
    "SRB": ("Fertility", "Sex ratio at birth", "male births per 100 female births", 1),
    # ---- Mortality & life expectancy --------------------------------------
    "LEx": ("Mortality", "Life expectancy at birth, both sexes", "years", 1),
    "LExMale": ("Mortality", "Life expectancy at birth, male", "years", 1),
    "LExFemale": ("Mortality", "Life expectancy at birth, female", "years", 1),
    "LE15": ("Mortality", "Remaining life expectancy at age 15, both sexes", "years", 1),
    "LE15Male": ("Mortality", "Remaining life expectancy at age 15, male", "years", 1),
    "LE15Female": ("Mortality", "Remaining life expectancy at age 15, female", "years", 1),
    "LE60": ("Mortality", "Remaining life expectancy at age 60, both sexes", "years", 1),
    "LE60Male": ("Mortality", "Remaining life expectancy at age 60, male", "years", 1),
    "LE60Female": ("Mortality", "Remaining life expectancy at age 60, female", "years", 1),
    "LE65": ("Mortality", "Remaining life expectancy at age 65, both sexes", "years", 1),
    "LE65Male": ("Mortality", "Remaining life expectancy at age 65, male", "years", 1),
    "LE65Female": ("Mortality", "Remaining life expectancy at age 65, female", "years", 1),
    "LE80": ("Mortality", "Remaining life expectancy at age 80, both sexes", "years", 1),
    "LE80Male": ("Mortality", "Remaining life expectancy at age 80, male", "years", 1),
    "LE80Female": ("Mortality", "Remaining life expectancy at age 80, female", "years", 1),
    "CDR": ("Mortality", "Crude death rate", "deaths per 1,000 population", 2),
    "Deaths": ("Mortality", "Deaths, both sexes", "thousands", 0),
    "DeathsMale": ("Mortality", "Deaths, male", "thousands", 0),
    "DeathsFemale": ("Mortality", "Deaths, female", "thousands", 0),
    "IMR": ("Mortality", "Infant mortality rate", "deaths per 1,000 live births", 2),
    "InfantDeaths": ("Mortality", "Infant deaths", "thousands", 1),
    "LBsurvivingAge1": ("Mortality", "Births surviving to age 1", "thousands", 0),
    "Q5": ("Mortality", "Under-five mortality rate", "deaths per 1,000 live births", 2),
    "Under5Deaths": ("Mortality", "Under-five deaths", "thousands", 1),
    "Q0040": ("Mortality", "Probability of dying between birth and age 40, both sexes", "per 1,000 live births", 1),
    "Q0040Male": ("Mortality", "Probability of dying between birth and age 40, male", "per 1,000 live births", 1),
    "Q0040Female": ("Mortality", "Probability of dying between birth and age 40, female", "per 1,000 live births", 1),
    "Q0060": ("Mortality", "Probability of dying between birth and age 60, both sexes", "per 1,000 live births", 1),
    "Q0060Male": ("Mortality", "Probability of dying between birth and age 60, male", "per 1,000 live births", 1),
    "Q0060Female": ("Mortality", "Probability of dying between birth and age 60, female", "per 1,000 live births", 1),
    "Q1550": ("Mortality", "Probability of dying between ages 15 and 50, both sexes", "per 1,000 persons alive at age 15", 1),
    "Q1550Male": ("Mortality", "Probability of dying between ages 15 and 50, male", "per 1,000 persons alive at age 15", 1),
    "Q1550Female": ("Mortality", "Probability of dying between ages 15 and 50, female", "per 1,000 persons alive at age 15", 1),
    "Q1560": ("Mortality", "Probability of dying between ages 15 and 60, both sexes", "per 1,000 persons alive at age 15", 1),
    "Q1560Male": ("Mortality", "Probability of dying between ages 15 and 60, male", "per 1,000 persons alive at age 15", 1),
    "Q1560Female": ("Mortality", "Probability of dying between ages 15 and 60, female", "per 1,000 persons alive at age 15", 1),
    # ---- Migration --------------------------------------------------------
    "NetMigrations": ("Migration", "Net number of migrants", "thousands", 1),
    "CNMR": ("Migration", "Net migration rate", "per 1,000 population", 2),
}


class DataValidationError(ValueError):
    """Raised when the G11 CSV is missing or malformed."""


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(
            f"Required input file not found: {DATA_FILE}\n"
            "Place countries_clean.csv in the project's data/out/ folder."
        )
    wanted = REQUIRED_COLUMNS | set(INDICATORS)
    try:
        # Only the columns this dashboard needs are loaded (the file is wide).
        df = pd.read_csv(DATA_FILE, usecols=lambda c: str(c).strip() in wanted, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read {DATA_FILE.name}: {exc}") from exc
    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(f"{DATA_FILE.name} is missing columns: {', '.join(missing)}")
    indicators = [key for key in INDICATORS if key in df.columns]
    if not indicators:
        raise DataValidationError(f"{DATA_FILE.name} contains none of the supported indicator columns.")

    df = df.copy()
    df["Location"] = df["Location"].astype(str).str.strip()
    df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
    df["IsProjection"] = df["IsProjection"].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})
    for key in indicators:
        df[key] = pd.to_numeric(df[key], errors="coerce")
    df = df.dropna(subset=["Location", "Time"])
    df["Time"] = df["Time"].astype(int)
    df = df.drop_duplicates(subset=["Location", "Time"], keep="first")
    df = df.sort_values(["Location", "Time"]).reset_index(drop=True)
    if df.empty:
        raise DataValidationError("G11 CSV contains no usable rows after numeric conversion.")
    return df


def _available_indicators(df: pd.DataFrame) -> list[str]:
    return [key for key in INDICATORS if key in df.columns and df[key].notna().any()]


def _indicator_option_label(key: str) -> str:
    group, label, _unit, _decimals = INDICATORS[key]
    return f"{group} · {label}"


def _default_country(df: pd.DataFrame) -> str:
    locations = set(df["Location"].unique())
    for candidate in ("Türkiye", "Turkiye", "Turkey"):
        if candidate in locations:
            return candidate
    return sorted(locations)[0]


def _default_comparison(df: pd.DataFrame, first: str) -> str:
    locations = sorted(df["Location"].unique())
    for candidate in ("Germany", "Japan", "France"):
        if candidate in locations and candidate != first:
            return candidate
    for candidate in locations:
        if candidate != first:
            return candidate
    return first


def _default_indicator(df: pd.DataFrame) -> str:
    available = _available_indicators(df)
    return "TFR" if "TFR" in available else available[0]


def _series(df: pd.DataFrame, country: str, indicator: str) -> pd.DataFrame:
    rows = df.loc[df["Location"] == country, ["Time", "IsProjection", indicator]]
    return rows.dropna(subset=[indicator]).sort_values("Time")


def _fmt(value: float, decimals: int, signed: bool = False) -> str:
    return f"{value:+,.{decimals}f}" if signed else f"{value:,.{decimals}f}"


# --------------------------------------------------------------------------
# Figure
# --------------------------------------------------------------------------
def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=14, color=MUTED),
    )
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=76, r=40, t=120, b=62),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def build_figure(df: pd.DataFrame, country_a: str | None, country_b: str | None, indicator: str | None) -> go.Figure:
    if indicator not in INDICATORS or indicator not in df.columns:
        return _empty_figure("Select an indicator to draw the time series.")
    if not country_a or not country_b:
        return _empty_figure("Select two countries to compare.")
    if country_a == country_b:
        return _empty_figure("Please choose two different countries to compare.")

    _group, label, unit, decimals = INDICATORS[indicator]
    value_format = f",.{decimals}f"
    boundary_year = df.loc[~df["IsProjection"], "Time"].max()

    fig = go.Figure()
    missing: list[str] = []
    x_values: list[int] = []

    for country, color in ((country_a, COLOR_A), (country_b, COLOR_B)):
        rows = _series(df, country, indicator)
        if rows.empty:
            missing.append(country)
            continue
        observed = rows[~rows["IsProjection"]]
        projected = rows[rows["IsProjection"]]
        x_values.extend(rows["Time"].tolist())

        if not observed.empty:
            fig.add_trace(go.Scatter(
                x=observed["Time"], y=observed[indicator], mode="lines",
                name=country, legendgroup=country, showlegend=True,
                line=dict(color=color, width=3),
                hovertemplate=f"<b>{country}</b>: %{{y:{value_format}}}<extra></extra>",
            ))
        if not projected.empty:
            if not observed.empty and observed["Time"].iloc[-1] < projected["Time"].iloc[0]:
                # Visual bridge between the last observation and the first projection; no hover.
                fig.add_trace(go.Scatter(
                    x=[observed["Time"].iloc[-1], projected["Time"].iloc[0]],
                    y=[observed[indicator].iloc[-1], projected[indicator].iloc[0]],
                    mode="lines", legendgroup=country, showlegend=False,
                    line=dict(color=color, width=2.5, dash="dash"),
                    hoverinfo="skip",
                ))
            fig.add_trace(go.Scatter(
                x=projected["Time"], y=projected[indicator], mode="lines",
                name=country, legendgroup=country, showlegend=observed.empty,
                line=dict(color=color, width=2.5, dash="dash"),
                hovertemplate=f"<b>{country}</b>: %{{y:{value_format}}} (projection)<extra></extra>",
            ))

    if not x_values:
        return _empty_figure(f"No data available for {' and '.join(missing)} for this indicator.")

    x_min, x_max = int(min(x_values)), int(max(x_values))
    if x_max > boundary_year:
        fig.add_vrect(x0=int(boundary_year), x1=x_max, fillcolor=PROJECTION_FILL, line_width=0, layer="below")
        fig.add_annotation(
            x=int(boundary_year), y=1.0, xref="x", yref="paper", text="Projection →",
            showarrow=False, xanchor="left", yanchor="bottom", xshift=4, yshift=4,
            font=dict(size=11, color=MUTED),
        )
    if missing:
        fig.add_annotation(
            text=f"No data for {' and '.join(missing)} for this indicator.",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
            font=dict(size=13, color=MUTED), bgcolor="rgba(255,255,255,0.9)",
        )

    # Title stays inside Plotly's 0–1 range; the subtitle is an annotation positioned in pixels
    # above the plot area, and the top margin keeps title, subtitle and legend apart.
    fig.update_layout(
        title=dict(text=f"{country_a} vs {country_b}", x=0.02, y=0.99, xanchor="left", yanchor="top",
                   font=dict(size=21, color=TEXT)),
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=76, r=40, t=120, b=62),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        xaxis=dict(title="Year", gridcolor=GRID, showline=True, linecolor=BORDER,
                   range=[x_min, x_max], dtick=10),
        yaxis=dict(title=unit[:1].upper() + unit[1:], gridcolor=GRID, showline=True, linecolor=BORDER,
                   zeroline=True, zerolinecolor=BORDER),
        annotations=list(fig.layout.annotations or ()) + [dict(
            text=f"{label} · {unit}", x=0, y=1.0, xref="paper", yref="paper", yshift=50,
            xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=12, color=MUTED),
        )],
    )
    return fig


# --------------------------------------------------------------------------
# KPI cards
# --------------------------------------------------------------------------
def _placeholder_cards(message: str) -> list:
    return [
        make_metric_card("Country A", "—", message),
        make_metric_card("Country B", "—", message),
        make_metric_card("Gap (A − B)", "—", message),
    ]


def build_metric_cards(df: pd.DataFrame, country_a: str | None, country_b: str | None, indicator: str | None) -> list:
    if indicator not in INDICATORS or indicator not in df.columns:
        return _placeholder_cards("Select an indicator.")
    if not country_a or not country_b:
        return _placeholder_cards("Select two countries.")
    if country_a == country_b:
        return _placeholder_cards("Choose two different countries.")

    _group, label, unit, decimals = INDICATORS[indicator]
    observed_a = _series(df, country_a, indicator)
    observed_b = _series(df, country_b, indicator)
    observed_a = observed_a[~observed_a["IsProjection"]].set_index("Time")[indicator]
    observed_b = observed_b[~observed_b["IsProjection"]].set_index("Time")[indicator]
    common_years = sorted(set(observed_a.index) & set(observed_b.index))
    if not common_years:
        return _placeholder_cards("No overlapping observed years for this indicator.")

    year = int(common_years[-1])
    value_a, value_b = float(observed_a.loc[year]), float(observed_b.loc[year])
    description = f"{label} ({unit})"
    return [
        make_metric_card(f"{country_a} · {year}", _fmt(value_a, decimals), description),
        make_metric_card(f"{country_b} · {year}", _fmt(value_b, decimals), description),
        make_metric_card(f"Gap · {year}", _fmt(value_a - value_b, decimals, signed=True),
                         f"{country_a} minus {country_b}"),
    ]


# --------------------------------------------------------------------------
# Layout & callbacks
# --------------------------------------------------------------------------
def build_layout(df: pd.DataFrame, show_back_link: bool = True):
    locations = sorted(df["Location"].unique().tolist())
    country_options = [{"label": name, "value": name} for name in locations]
    indicator_options = [{"label": _indicator_option_label(key), "value": key} for key in _available_indicators(df)]
    default_a = _default_country(df)
    default_b = _default_comparison(df, default_a)
    default_indicator = _default_indicator(df)

    children = []
    if show_back_link:
        children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g11-header", children=[
            html.Div("G11 · COUNTRY COMPARISON", className="g11-eyebrow"),
            html.H1("Compare two countries over time"),
            html.P("Choose two countries and one indicator to compare how they have changed since 1950. "
                   "Solid lines show observed values; dashed lines show projections.",
                   className="g11-intro"),
        ]),
        html.Section(className="metrics g11-metrics", id="g11-metrics",
                     children=build_metric_cards(df, default_a, default_b, default_indicator)),
        html.Section(className="g11-panel", children=[
            html.Div(className="g11-controls", children=[
                html.Div([html.Label("Country A", htmlFor="g11-country-a", className="g11-label"),
                          dcc.Dropdown(id="g11-country-a", options=country_options, value=default_a,
                                       clearable=False, searchable=True)],
                         className="g11-control"),
                html.Div([html.Label("Country B", htmlFor="g11-country-b", className="g11-label"),
                          dcc.Dropdown(id="g11-country-b", options=country_options, value=default_b,
                                       clearable=False, searchable=True)],
                         className="g11-control"),
                html.Div([html.Label("Indicator", htmlFor="g11-indicator", className="g11-label"),
                          dcc.Dropdown(id="g11-indicator", options=indicator_options, value=default_indicator,
                                       clearable=False, searchable=True)],
                         className="g11-control g11-control-wide"),
            ]),
        ]),
        html.Section(className="g11-panel g11-chart-panel", children=[
            dcc.Graph(id="g11-time-graph", figure=build_figure(df, default_a, default_b, default_indicator),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "560px", "minHeight": "560px", "width": "100%"}),
        ]),
        html.Div(className="g11-method-note", children=[
            html.Strong("How to read this chart. "),
            "Each line follows one country for the selected indicator. Solid lines are observed values and dashed lines "
            "in the shaded area are projections. The cards above compare the two countries in the latest year observed "
            "for both. Population counts, births and deaths are in thousands; rates use the units shown under the chart "
            "title. Values are shown as supplied, with no interpolation; years without a value are left blank.",
        ]),
    ])
    return html.Main(className="g11-dashboard", children=children)


def register_callbacks(app, df: pd.DataFrame) -> None:
    @app.callback(
        Output("g11-time-graph", "figure"),
        Output("g11-metrics", "children"),
        Input("g11-country-a", "value"),
        Input("g11-country-b", "value"),
        Input("g11-indicator", "value"),
    )
    def update_g11(country_a, country_b, indicator):
        return (
            build_figure(df, country_a, country_b, indicator),
            build_metric_cards(df, country_a, country_b, indicator),
        )
