from __future__ import annotations

from pathlib import Path
from collections import Counter
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash import Dash, Input, Output, dcc, html

from .common import make_metric_card


# ============================================================
# 1. Paths and visual identity
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data" / "out"
CHART_DIR = PROJECT_DIR / "charts"

TRANSITIONS_FILE = DATA_DIR / "g03_kume_gecisi.csv"
COUNTRIES_FILE = DATA_DIR / "g03_ulke_yolculuklari.csv"
BACKWARD_FILE = DATA_DIR / "g03_geri_adimlar.csv"

# --- ARAYÜZ RENKLERİ ---
BACKGROUND = "#F3F4F6"
PANEL = "#FFFFFF"
TEXT_COLOR = "#1F2937"
MUTED_COLOR = "#6B7280"
GRID_COLOR = "#E5E7EB"
PROJECTION_COLOR = "#9CA3AF"

# Vurgu Renkleri
ACCENT_TURKEY = "#7B1113"
ACCENT_OTHER = "#C4BBAF"

# Küme Renkleri (Mavi-Kırmızı Palet, 3. Küme Gri)
CLUSTER_COLORS = {
    1: "#2166AC",
    2: "#67A9CF",
    3: "#D9D9D9",
    4: "#EF8A62",
    5: "#B2182B",
}

CLUSTER_NAMES = {
    1: "Pre-transition",
    2: "Early transition",
    3: "Mid-transition",
    4: "Late-transition",
    5: "Post-transition",
}

CLUSTER_ORDER = [5, 4, 3, 2, 1]
YEARS = [1990, 2023, 2050]
YEAR_LABELS = {
    1990: "1990",
    2023: "2023",
    2050: "2050 (Projection)",
}

REQUIRED_TRANSITION_COLUMNS = {
    "source_year",
    "source_cluster",
    "target_year",
    "target_cluster",
    "n_countries",
    "pop_2023_millions",
    "countries",
    "source_name",
    "target_name",
    "target_is_projection",
}

REQUIRED_COUNTRY_COLUMNS = {
    "iso3",
    "c1990",
    "c2023",
    "c2050",
    "country",
    "pop_2023_millions",
}

COUNTRY_CLUSTER_COLUMNS = {
    1990: "c1990",
    2023: "c2023",
    2050: "c2050",
}

SUMMARY_LABELS = {
    "no_change": "No change across all periods",
    "historical_only": "Historical change only",
    "projection_only": "Projected change only",
    "both": "Change in both periods",
}

SUMMARY_ORDER = [
    "no_change",
    "historical_only",
    "projection_only",
    "both",
]


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


def parse_cluster_series(series: pd.Series, column_name: str) -> pd.Series:
    raw = series.astype("string").str.strip()
    empty = raw.isna() | raw.eq("")
    numeric = pd.to_numeric(raw.mask(empty), errors="coerce")

    invalid_numeric = (~empty) & numeric.isna()
    if invalid_numeric.any():
        examples = raw[invalid_numeric].head(5).tolist()
        raise DataValidationError(f"Invalid cluster IDs in '{column_name}': {examples}")

    non_integer = numeric.notna() & (numeric % 1 != 0)
    if non_integer.any():
        examples = numeric[non_integer].head(5).tolist()
        raise DataValidationError(f"Cluster IDs in '{column_name}' must be integers: {examples}")

    invalid_range = numeric.notna() & ~numeric.isin(CLUSTER_ORDER)
    if invalid_range.any():
        examples = numeric[invalid_range].head(5).tolist()
        raise DataValidationError(f"Cluster IDs in '{column_name}' must be in 1–5: {examples}")

    return numeric.astype("Int64")


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
        margin=margin or dict(l=45, r=30, t=75, b=45),
        hoverlabel=dict(
            bgcolor=PANEL,
            bordercolor=GRID_COLOR,
            font=dict(color=TEXT_COLOR, size=14),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            borderwidth=0,
            font=dict(size=14),
        ),
    )
    return fig


def style_cartesian_axes(fig: go.Figure) -> None:
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR, size=14),
        title_font=dict(color=TEXT_COLOR, size=14),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR, size=14),
        title_font=dict(color=TEXT_COLOR, size=14),
    )


# ============================================================
# 3. Load and validate country assignments
# ============================================================

def load_country_data(path: Path) -> pd.DataFrame:
    frame = read_csv_checked(path, REQUIRED_COUNTRY_COLUMNS)
    frame["iso3"] = frame["iso3"].astype("string").str.strip()
    frame["country"] = frame["country"].astype("string").str.strip()
    frame["iso3"] = frame["iso3"].mask(frame["iso3"].eq(""))
    frame["country"] = frame["country"].mask(frame["country"].eq(""))

    if frame["country"].isna().any():
        rows = frame.index[frame["country"].isna()].tolist()[:10]
        raise DataValidationError(f"Country names are missing. Example row indices: {rows}")

    populated_iso = frame["iso3"].dropna()
    duplicate_iso = populated_iso[populated_iso.duplicated(keep=False)]

    if not duplicate_iso.empty:
        raise DataValidationError(
            "Duplicate ISO3 identifiers found: " + ", ".join(duplicate_iso.unique()[:10].tolist())
        )

    for year, column in COUNTRY_CLUSTER_COLUMNS.items():
        frame[column] = parse_cluster_series(frame[column], column)

    frame["pop_2023_millions"] = numeric_column(frame, "pop_2023_millions", allow_missing=True)

    if (frame["pop_2023_millions"].dropna() < 0).any():
        raise DataValidationError("Population values cannot be negative.")

    frame["_country_key"] = [
        f"ISO3:{iso}" if pd.notna(iso) else f"NAME:{name}"
        for iso, name in zip(frame["iso3"], frame["country"])
    ]

    if frame["_country_key"].duplicated().any():
        duplicates = frame.loc[
            frame["_country_key"].duplicated(keep=False),
            ["iso3", "country", "_country_key"],
        ]
        raise DataValidationError(
            "Duplicate country identifiers found:\n" + duplicates.head(10).to_string(index=False)
        )

    frame["_display_country"] = frame["country"].astype(str)
    repeated_display = frame["_display_country"].duplicated(keep=False)
    frame.loc[repeated_display, "_display_country"] = (
        frame.loc[repeated_display, "country"].astype(str)
        + " ("
        + frame.loc[repeated_display, "iso3"].fillna(frame.loc[repeated_display, "_country_key"]).astype(str)
        + ")"
    )

    return frame


# ============================================================
# 4. Load and validate transition-flow data
# ============================================================

def load_transition_data(path: Path, countries: pd.DataFrame) -> pd.DataFrame:
    frame = read_csv_checked(path, REQUIRED_TRANSITION_COLUMNS)

    for column in ("source_year", "target_year"):
        values = numeric_column(frame, column)
        if (values % 1 != 0).any():
            raise DataValidationError(f"'{column}' must contain integer years.")
        frame[column] = values.astype(int)

    frame["source_cluster"] = parse_cluster_series(frame["source_cluster"], "source_cluster")
    frame["target_cluster"] = parse_cluster_series(frame["target_cluster"], "target_cluster")
    frame["n_countries"] = numeric_column(frame, "n_countries")
    
    if ((frame["n_countries"] < 0).any() or (frame["n_countries"] % 1 != 0).any()):
        raise DataValidationError("'n_countries' must contain nonnegative integer counts.")
    frame["n_countries"] = frame["n_countries"].astype(int)

    frame["pop_2023_millions"] = numeric_column(frame, "pop_2023_millions", allow_missing=True)
    if (frame["pop_2023_millions"].dropna() < 0).any():
        raise DataValidationError("'pop_2023_millions' cannot contain negative values.")

    parsed_projection = frame["target_is_projection"].map(parse_bool)
    frame["target_is_projection"] = parsed_projection.astype(bool)

    return frame


# ============================================================
# 5. Sankey diagram
# ============================================================

def build_sankey(flows: pd.DataFrame) -> go.Figure:
    stages = [1990, 2023, 2050]
    node_index = {}
    node_labels = []
    node_colors = []
    node_customdata = []

    for year in stages:
        for cluster in CLUSTER_ORDER:
            node_index[(year, cluster)] = len(node_labels)
            node_labels.append(f"{year}\n{CLUSTER_NAMES[cluster]}")

            opacity = 0.58 if year == 2050 else 1.0
            node_colors.append(hex_to_rgba(CLUSTER_COLORS[cluster], opacity))
            node_customdata.append(
                [year, cluster, CLUSTER_NAMES[cluster],
                 "Projection" if year == 2050 else "Historical estimate"]
            )

    sources, targets, values, link_colors, link_customdata = [], [], [], [], []

    for row in flows.itertuples(index=False):
        source_year, target_year = int(row.source_year), int(row.target_year)
        source_cluster, target_cluster = int(row.source_cluster), int(row.target_cluster)
        count = int(row.n_countries)
        projected = bool(row.target_is_projection)

        sources.append(node_index[(source_year, source_cluster)])
        targets.append(node_index[(target_year, target_cluster)])
        values.append(count)

        alpha = 0.30 if projected else 0.62
        link_colors.append(hex_to_rgba(CLUSTER_COLORS[source_cluster], alpha))
        link_customdata.append([
            source_year, CLUSTER_NAMES[source_cluster], target_year, CLUSTER_NAMES[target_cluster], count,
            "Projection" if projected else "Historical transition",
        ])

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=16,
                    thickness=19,
                    line=dict(color=TEXT_COLOR, width=0.7),
                    label=node_labels,
                    color=node_colors,
                    customdata=node_customdata,
                    hovertemplate="Year: %{customdata[0]}<br>Cluster: %{customdata[2]}<br>Status: %{customdata[3]}<extra></extra>",
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=link_colors,
                    customdata=link_customdata,
                    hovertemplate="Source: %{customdata[0]} — %{customdata[1]}<br>Target: %{customdata[2]} — %{customdata[3]}<br>Countries: %{customdata[4]}<br>Status: %{customdata[5]}<extra></extra>",
                ),
            )
        ]
    )

    fig.update_layout(
        title="Demographic Cluster Transitions: 1990 → 2023 → 2050",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'Inter', sans-serif", size=14, color=TEXT_COLOR),
        height=610,
        margin=dict(l=20, r=20, t=95, b=110),
        annotations=[
            dict(
                x=0.50, y=-0.12, xref="paper", yref="paper",
                showarrow=False, align="center",
                text="1990 and 2023: historical estimates  |  2050: projection; projected links use reduced opacity",
                font=dict(size=14, color=MUTED_COLOR),
            )
        ],
    )
    return fig


# ============================================================
# 6. Transition matrix
# ============================================================

def make_transition_matrix(flows: pd.DataFrame, source_year: int, target_year: int) -> np.ndarray:
    matrix = np.zeros((5, 5), dtype=int)
    subset = flows[(flows["source_year"] == source_year) & (flows["target_year"] == target_year)]
    positions = {cluster: i for i, cluster in enumerate(CLUSTER_ORDER)}
    for row in subset.itertuples(index=False):
        matrix[positions[int(row.source_cluster)], positions[int(row.target_cluster)]] = int(row.n_countries)
    return matrix

def build_transition_matrices(flows: pd.DataFrame) -> go.Figure:
    historical = make_transition_matrix(flows, 1990, 2023)
    projected = make_transition_matrix(flows, 2023, 2050)
    shared_max = max(int(historical.max()) if historical.size else 0, int(projected.max()) if projected.size else 0, 1)

    labels = [CLUSTER_NAMES[c] for c in CLUSTER_ORDER]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("1990 → 2023 (Historical)", "2023 → 2050 (Projection)"), horizontal_spacing=0.15)

    for col, matrix in ((1, historical), (2, projected)):
        text_values = np.where(matrix > 0, matrix.astype(str), "")
        fig.add_trace(
            go.Heatmap(
                z=matrix, x=labels, y=labels, zmin=0, zmax=shared_max,
                # YENİ: Küme renklerinden ayrışan Turuncu Isı Haritası Gradyanı
                colorscale=[
                    [0.0, "#FFFFFF"], 
                    [0.25, "#FDD0A2"], 
                    [0.5, "#FDAE6B"], 
                    [0.75, "#F16913"], 
                    [1.0, "#8C2D04"]
                ],
                showscale=(col == 2),
                colorbar=dict(title="Countries", thickness=13, len=0.78) if col == 2 else None,
                text=text_values, texttemplate="%{text}",
                textfont=dict(size=14, color=TEXT_COLOR),
                customdata=np.stack([
                    np.tile(np.array(CLUSTER_ORDER, dtype=int)[:, None], (1, 5)),
                    np.tile(np.array(CLUSTER_ORDER, dtype=int)[None, :], (5, 1)),
                    matrix,
                ], axis=-1),
                hovertemplate="Source cluster: %{customdata[0]} — %{y}<br>Target cluster: %{customdata[1]} — %{x}<br>Countries: %{customdata[2]}<extra></extra>",
                xgap=2, ygap=2,
            ),
            row=1, col=col,
        )

    fig.update_xaxes(tickangle=-35, title_text="Target cluster", tickfont=dict(size=14))
    fig.update_yaxes(title_text="Source cluster", autorange="reversed", tickfont=dict(size=14))
    make_base_layout(fig, height=550, margin=dict(l=150, r=55, t=95, b=145))
    style_cartesian_axes(fig)
    fig.update_layout(
        title="Country Transition Matrix",
        annotations=[dict(
            x=0.5, y=-0.35, xref="paper", yref="paper", showarrow=False,
            text="Cell color represents the number of countries, not demographic similarity. Both panels use the same scale.",
            font=dict(size=14, color=MUTED_COLOR),
        )],
    )
    return fig


# ============================================================
# 7. Country-level mutually exclusive summary
# ============================================================

def classify_country_changes(countries: pd.DataFrame) -> pd.DataFrame:
    result = countries.copy()
    result["_historical_change"] = result["c1990"].notna() & result["c2023"].notna() & result["c1990"].ne(result["c2023"]).fillna(False)
    result["_projected_change"] = result["c2023"].notna() & result["c2050"].notna() & result["c2023"].ne(result["c2050"]).fillna(False)
    complete = result[["c1990", "c2023", "c2050"]].notna().all(axis=1)
    result["_change_class"] = pd.Series(pd.NA, index=result.index, dtype="string")
    
    result.loc[complete & ~result["_historical_change"] & ~result["_projected_change"], "_change_class"] = "no_change"
    result.loc[complete & result["_historical_change"] & ~result["_projected_change"], "_change_class"] = "historical_only"
    result.loc[complete & ~result["_historical_change"] & result["_projected_change"], "_change_class"] = "projection_only"
    result.loc[complete & result["_historical_change"] & result["_projected_change"], "_change_class"] = "both"
    return result

def build_country_summary(countries: pd.DataFrame) -> go.Figure:
    classified = classify_country_changes(countries)
    counts = classified["_change_class"].value_counts().reindex(SUMMARY_ORDER, fill_value=0)
    labels = [SUMMARY_LABELS[key] for key in SUMMARY_ORDER]
    values = [int(counts[key]) for key in SUMMARY_ORDER]

    # YENİ: Çubuk grafiği renkleri de ısı haritasındaki turuncu palete uyarlandı
    colors = ["#FDD0A2", "#FDAE6B", "#F16913", "#8C2D04"]

    fig = go.Figure(
        go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color=colors, line=dict(color=TEXT_COLOR, width=0.5)),
            text=values, textposition="outside", cliponaxis=False,
            customdata=np.array(labels, dtype=object),
            hovertemplate="%{y}<br>Countries: %{x}<br>Classification: %{customdata}<extra></extra>",
        )
    )

    fig.update_layout(title="Country-Level Cluster Change Summary", xaxis_title="Number of countries", yaxis_title="", showlegend=False)
    make_base_layout(fig, height=360, margin=dict(l=240, r=45, t=75, b=75))
    style_cartesian_axes(fig)
    fig.update_yaxes(autorange="reversed")

    incomplete = int((~classified[["c1990", "c2023", "c2050"]].notna().all(axis=1)).sum())
    fig.add_annotation(
        x=1, y=-0.28, xref="paper", yref="paper", xanchor="right", showarrow=False,
        text=f"{incomplete} countries excluded (missing at least one assignment).",
        font=dict(size=14, color=MUTED_COLOR),
    )
    return fig


# ============================================================
# 8. Interactive country trajectory chart
# ============================================================

def build_country_trajectories(countries: pd.DataFrame, selected_keys: list[str] | None) -> go.Figure:
    fig = go.Figure()

    if not selected_keys:
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, text="Select one or more countries to explore their trajectories.", font=dict(size=14, color=MUTED_COLOR))
        fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
        return make_base_layout(fig, height=470, margin=dict(l=40, r=30, t=80, b=55))

    selected = countries[countries["_country_key"].isin(selected_keys)].copy()
    
    # Türkiye'yi en üste sabitle
    selected["is_turkey"] = selected["iso3"].eq("TUR") | selected["country"].str.upper().str.contains("TÜRKİYE|TURKEY")
    selected = selected.sort_values(by="is_turkey") 
    
    y_positions = {cluster: index for index, cluster in enumerate(CLUSTER_ORDER)}

    for idx, row in enumerate(selected.itertuples(index=False)):
        source = selected.iloc[idx]
        country = str(source["_display_country"])
        iso3 = str(source["iso3"]) if pd.notna(source["iso3"]) else "Not available"
        is_turkey = source["is_turkey"]

        # Vurgu Rengi: Türkiye (Bordo), Diğerleri (Silik Mat Bej)
        line_color = ACCENT_TURKEY if is_turkey else ACCENT_OTHER
        line_width = 4.0 if is_turkey else 2.5
        line_opacity = 1.0 if is_turkey else 0.6

        assigned_years, assigned_clusters = [], []
        for year, column in COUNTRY_CLUSTER_COLUMNS.items():
            if pd.notna(source[column]):
                assigned_years.append(year)
                assigned_clusters.append(int(source[column]))

        if not assigned_years: continue

        historical_x = [year for year in assigned_years if year <= 2023]
        historical_y = [y_positions[cluster] for year, cluster in zip(assigned_years, assigned_clusters) if year <= 2023]

        if historical_x:
            fig.add_trace(
                go.Scatter(
                    x=historical_x, y=historical_y, mode="lines+markers",
                    name=country, legendgroup=country, showlegend=True,
                    opacity=line_opacity, line=dict(color=line_color, width=line_width),
                    marker=dict(
                        size=10 if is_turkey else 8,
                        color=[CLUSTER_COLORS[int(source[COUNTRY_CLUSTER_COLUMNS[y]])] for y in historical_x],
                        line=dict(color=TEXT_COLOR, width=1.0 if is_turkey else 0.5),
                    ),
                    customdata=[[country, iso3, CLUSTER_NAMES[int(source[COUNTRY_CLUSTER_COLUMNS[y]])], "Historical estimate"] for y in historical_x],
                    hovertemplate="Country: %{customdata[0]}<br>ISO3: %{customdata[1]}<br>Year: %{x}<br>Cluster: %{customdata[2]}<br>Status: %{customdata[3]}<extra></extra>",
                )
            )

        if pd.notna(source["c2023"]) and pd.notna(source["c2050"]):
            c2023, c2050 = int(source["c2023"]), int(source["c2050"])
            fig.add_trace(
                go.Scatter(
                    x=[2023, 2050], y=[y_positions[c2023], y_positions[c2050]], mode="lines+markers",
                    name=f"{country} (projection)", legendgroup=country, showlegend=False,
                    opacity=line_opacity * 0.7, line=dict(color=line_color, width=line_width, dash="dash"),
                    marker=dict(
                        size=10 if is_turkey else 8,
                        color=[CLUSTER_COLORS[c2023], CLUSTER_COLORS[c2050]],
                        symbol=["circle", "diamond"],
                        line=dict(color=TEXT_COLOR, width=1.0 if is_turkey else 0.5),
                    ),
                    customdata=[
                        [country, iso3, CLUSTER_NAMES[c2023], "Historical estimate"],
                        [country, iso3, CLUSTER_NAMES[c2050], "Projection"],
                    ],
                    hovertemplate="Country: %{customdata[0]}<br>ISO3: %{customdata[1]}<br>Year: %{x}<br>Cluster: %{customdata[2]}<br>Status: %{customdata[3]}<extra></extra>",
                )
            )

    fig.add_vline(
        x=2023, line_width=1.5, line_dash="dash", line_color=PROJECTION_COLOR,
        annotation_text="Projection begins", annotation_position="top", annotation_font_color=MUTED_COLOR,
    )
    fig.update_layout(title="Country Trajectories Across Demographic Clusters", xaxis_title="Year", yaxis_title="Demographic cluster", legend_title="Country")
    fig.update_xaxes(tickmode="array", tickvals=YEARS, ticktext=["1990", "2023", "2050 (Projection)"], range=[1987, 2053])
    fig.update_yaxes(tickmode="array", tickvals=list(range(5)), ticktext=[CLUSTER_NAMES[c] for c in CLUSTER_ORDER], range=[-0.5, 4.5], title_text="Cluster (categorical)")

    make_base_layout(fig, height=max(470, 350 + min(len(selected), 12) * 7), margin=dict(l=165, r=30, t=95, b=85))
    style_cartesian_axes(fig)
    return fig



# ============================================================
# 9. Dashboard Hub interface
# ============================================================

def load_data():
    """Load and validate the G03 datasets using paths relative to the project root."""
    require_file(TRANSITIONS_FILE)
    require_file(COUNTRIES_FILE)
    countries = load_country_data(COUNTRIES_FILE)
    flows = load_transition_data(TRANSITIONS_FILE, countries)

    backward_info = None
    if require_file(BACKWARD_FILE, optional=True):
        try:
            backward = pd.read_csv(BACKWARD_FILE, low_memory=False)
            if {"Location", "Time", "onceki", "kume"}.issubset(backward.columns):
                backward_info = "Optional backward-transition file detected. Semantics unestablished."
            else:
                backward_info = "Optional backward-transition file incomplete."
        except Exception as exc:
            backward_info = f"Optional backward-transition file error: {exc}"
    return countries, flows, backward_info


def build_layout(countries: pd.DataFrame, flows: pd.DataFrame, backward_info=None, *, show_back_link: bool = False):
    """Return the G03 page layout; the central Hub owns the Dash application."""
    classified = classify_country_changes(countries)
    complete_countries = int(countries[["c1990", "c2023", "c2050"]].notna().all(axis=1).sum())
    total_countries = len(countries)

    options = [{"label": row["_display_country"], "value": row["_country_key"]}
               for _, row in countries.sort_values("_display_country").iterrows()]

    turkey_key = next((row["_country_key"] for _, row in countries.iterrows()
                       if row["iso3"] == "TUR" or "TÜRKİYE" in str(row["country"]).upper()), None)
    default_keys = [turkey_key] if turkey_key else []
    for k in countries.sort_values("_display_country")["_country_key"]:
        if len(default_keys) < 3 and k not in default_keys:
            default_keys.append(k)

    sankey_fig = build_sankey(flows)
    matrix_fig = build_transition_matrices(flows)
    summary_fig = build_country_summary(countries)
    trajectory_fig = build_country_trajectories(countries, default_keys)

    children = [
            *([html.A("← Back to Dashboard Hub", href="/", className="hub-back")] if show_back_link else []),
            html.Header(
                className="page-header",
                children=[
                    html.Div("GRAPH 3  /  DEMOGRAPHIC CHANGE", className="eyebrow"),
                    html.H1("Demographic Cluster Transitions: 1990 → 2023 → 2050"),
                    html.P("Explore how countries move between five demographic transition clusters.", className="intro"),
                ],
            ),
            html.Div(
                className="metrics",
                children=[
                    make_metric_card("Countries analyzed", f"{total_countries:,}", "Rows with unique identifiers."),
                    make_metric_card("Complete trajectories", f"{complete_countries:,}", "Assignments for all periods."),
                    make_metric_card("Transition records", f"{len(flows):,}", "Validated source-target flows."),
                ],
            ),
            html.Section(
                className="panel",
                children=[
                    html.H2("Demographic Cluster Transitions", className="section-heading"),
                    html.P("Link width represents the number of countries. Projected links use reduced opacity.", className="section-description"),
                    dcc.Graph(id="g03-sankey-chart", figure=sankey_fig, config={"responsive": True, "displaylogo": False}),
                ],
            ),
            html.Div(
                className="two-column",
                children=[
                    html.Section(
                        className="panel",
                        children=[
                            html.H2("Country Transition Matrix", className="section-heading"),
                            html.P("Compare country counts across historical and projected periods.", className="section-description"),
                            dcc.Graph(id="g03-matrix-chart", figure=matrix_fig, config={"responsive": True, "displaylogo": False}),
                        ],
                    ),
                    html.Section(
                        className="panel",
                        children=[
                            html.H2("Country-Level Cluster Change Summary", className="section-heading"),
                            html.P("Mutually exclusive categories from cluster assignments.", className="section-description"),
                            dcc.Graph(id="g03-summary-chart", figure=summary_fig, config={"responsive": True, "displaylogo": False}),
                        ],
                    ),
                ],
            ),
            html.Section(
                className="panel",
                children=[
                    html.H2("Country Trajectories", className="section-heading"),
                    html.P("Inspect categorical cluster assignments over time. Turkey is highlighted to focus the audience.", className="section-description"),
                    html.Div(
                        className="country-controls",
                        children=[
                            html.Label("Select countries", htmlFor="g03-country-selector", className="control-label"),
                            dcc.Dropdown(id="g03-country-selector", options=options, value=default_keys, multi=True, className="dash-dropdown"),
                        ],
                    ),
                    dcc.Graph(id="g03-trajectory-chart", figure=trajectory_fig, config={"responsive": True, "displaylogo": False}),
                ],
            ),
            html.Section(
                className="method-note",
                children=[
                    html.Strong("Methodological note: "),
                    html.Span("1990–2023 values are UN population estimates; 2050 values are projections. Cluster IDs are categorical."),
                ],
            ),
        ]
    return html.Div(className="dashboard", children=children)



def register_callbacks(app: Dash, countries: pd.DataFrame):
    """Register G03 interactions on the shared Hub application."""
    @app.callback(
        Output("g03-trajectory-chart", "figure"),
        Input("g03-country-selector", "value"),
    )
    def update_trajectory(selected_keys):
        if not selected_keys:
            return build_country_trajectories(countries, [])
        if not isinstance(selected_keys, list):
            selected_keys = [selected_keys]
        valid = set(countries["_country_key"])
        keys = [key for key in selected_keys if key in valid]
        return build_country_trajectories(countries, keys)


def create_app(countries: pd.DataFrame, flows: pd.DataFrame, backward_info=None):
    """Compatibility helper for running this dashboard independently."""
    app = Dash(__name__, assets_folder=str(PROJECT_DIR / "dashboard" / "assets"))
    app.title = "Graph 3 — Demographic Cluster Transitions"
    app.layout = build_layout(countries, flows, backward_info)
    register_callbacks(app, countries)
    return app


if __name__ == "__main__":
    try:
        c_data, t_data, o_note = load_data()
        app = create_app(c_data, t_data, backward_info=o_note)
    except DataValidationError as exc:
        raise SystemExit(f"\\nERROR\\n-----\\n{exc}\\n") from exc
    app.run(debug=True)
