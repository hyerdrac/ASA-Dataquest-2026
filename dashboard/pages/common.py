from __future__ import annotations

from dash import html


def make_metric_card(label: str, value: str, description: str):
    """Shared KPI card used by every dashboard in the Hub.

    Keep this markup and the shared .metric-* CSS classes consistent across
    current and future dashboards.
    """
    return html.Div(
        [
            html.Div(label, className="metric-label"),
            html.Div(value, className="metric-value"),
            html.Div(description, className="metric-description"),
        ],
        className="metric-card",
    )
