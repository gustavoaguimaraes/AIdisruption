"""
Chart generation module using Plotly.

Each function returns a plotly Figure with dark theme, recession shading,
and AI milestone annotations.
"""

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import COLORS, LINE_PALETTE, AI_MILESTONES


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _base_layout() -> dict:
    """Return the common dark-theme layout dict."""
    return dict(
        template="plotly_dark",
        paper_bgcolor=COLORS["card_bg"],
        plot_bgcolor=COLORS["card_bg"],
        font=dict(color=COLORS["text"], size=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=60, r=30, t=40, b=50),
        xaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
        yaxis=dict(gridcolor=COLORS["grid"], showgrid=True),
        hovermode="x unified",
    )


def _add_recession_shading(fig: go.Figure, recession_data: pd.Series | None, start_date: date):
    """Add grey shading for NBER recession periods."""
    if recession_data is None or isinstance(recession_data, str):
        return
    rec = recession_data[recession_data.index >= pd.Timestamp(start_date)]
    if rec.empty:
        return

    in_recession = False
    rec_start = None
    for dt, val in rec.items():
        if val == 1 and not in_recession:
            rec_start = dt
            in_recession = True
        elif val == 0 and in_recession:
            fig.add_vrect(
                x0=rec_start, x1=dt,
                fillcolor=COLORS["recession"],
                layer="below",
                line_width=0,
            )
            in_recession = False
    if in_recession and rec_start is not None:
        fig.add_vrect(
            x0=rec_start, x1=rec.index[-1],
            fillcolor=COLORS["recession"],
            layer="below",
            line_width=0,
        )


def _add_ai_annotations(fig: go.Figure, start_date: date):
    """Add vertical lines for AI milestones."""
    for milestone_date, label in AI_MILESTONES:
        if milestone_date < start_date:
            continue
        fig.add_vline(
            x=datetime.combine(milestone_date, datetime.min.time()),
            line_dash="dot",
            line_color=COLORS["annotation"],
            line_width=1,
        )
        fig.add_annotation(
            x=datetime.combine(milestone_date, datetime.min.time()),
            y=1.0,
            yref="paper",
            text=label,
            showarrow=False,
            textangle=-90,
            font=dict(size=9, color=COLORS["muted_text"]),
            xanchor="right",
            yanchor="top",
        )

    # Current date dashed line
    today = date.today()
    if today >= start_date:
        fig.add_vline(
            x=datetime.combine(today, datetime.min.time()),
            line_dash="dash",
            line_color=COLORS["muted_text"],
            line_width=1,
        )


def _index_to_100(series: pd.Series, start_date: date) -> pd.Series:
    """Rebase a series to 100 at the start_date."""
    s = series[series.index >= pd.Timestamp(start_date)].copy()
    if s.empty:
        return s
    base = s.iloc[0]
    if base == 0:
        return s
    return (s / base) * 100


def _safe_get(data: dict, key: str) -> pd.Series | None:
    """Safely retrieve a series, returning None if missing or errored."""
    val = data.get(key)
    if val is None or isinstance(val, str):
        return None
    return val


# ──────────────────────────────────────────────────────────────────────────────
# Section 1: Labor Market charts
# ──────────────────────────────────────────────────────────────────────────────

def chart_labor_openings(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Job openings: total vs. professional services vs. information (indexed to 100)."""
    fig = go.Figure()
    fig.update_layout(**_base_layout(), title="Job Openings Divergence (Indexed to 100)")

    series_map = [
        ("JTSJOL", "Total Job Openings", LINE_PALETTE[0]),
        ("JTS540099000000000JOL", "Prof. & Business Services", LINE_PALETTE[1]),
        ("JTS510000000000000JOL", "Information Sector", LINE_PALETTE[2]),
    ]

    for sid, name, color in series_map:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            fig.add_trace(go.Scatter(
                x=indexed.index, y=indexed.values,
                name=name, line=dict(color=color, width=2),
                hovertemplate="%{y:.1f}<extra>" + name + "</extra>",
            ))

    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    fig.update_yaxes(title_text="Index (100 = start)")
    return fig


def chart_labor_employment(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Employment: total nonfarm vs. professional services vs. information (indexed)."""
    fig = go.Figure()
    fig.update_layout(**_base_layout(), title="Employment Divergence (Indexed to 100)")

    series_map = [
        ("PAYEMS", "Total Nonfarm Payrolls", LINE_PALETTE[0]),
        ("USPBS", "Prof. & Business Services", LINE_PALETTE[1]),
        ("CES5000000001", "Information Sector", LINE_PALETTE[2]),
    ]

    for sid, name, color in series_map:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            fig.add_trace(go.Scatter(
                x=indexed.index, y=indexed.values,
                name=name, line=dict(color=color, width=2),
                hovertemplate="%{y:.1f}<extra>" + name + "</extra>",
            ))

    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    fig.update_yaxes(title_text="Index (100 = start)")
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Section 2: Consumer stress
# ──────────────────────────────────────────────────────────────────────────────

def chart_consumer_stress(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Dual-axis: revolving credit + credit card delinquency."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    revolving = _safe_get(section_data, "REVOLSL")
    delinquency = _safe_get(section_data, "DRCCLACBS")

    if revolving is not None:
        r = revolving[revolving.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=r.index, y=r.values,
                name="Revolving Credit ($B)", line=dict(color=LINE_PALETTE[0], width=2),
                hovertemplate="$%{y:,.0f}B<extra>Revolving Credit</extra>",
            ),
            secondary_y=False,
        )

    if delinquency is not None:
        d = delinquency[delinquency.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=d.index, y=d.values,
                name="CC Delinquency Rate (%)", line=dict(color=LINE_PALETTE[5], width=2),
                hovertemplate="%{y:.2f}%<extra>CC Delinquency</extra>",
            ),
            secondary_y=True,
        )

    layout = _base_layout()
    layout["title"] = "Consumer Credit Stress: Revolving Credit vs. Delinquency"
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Revolving Credit ($B)", secondary_y=False, gridcolor=COLORS["grid"])
    fig.update_yaxes(title_text="Delinquency Rate (%)", secondary_y=True, gridcolor=COLORS["grid"])
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Section 3: Housing
# ──────────────────────────────────────────────────────────────────────────────

def chart_housing(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Mortgage delinquency rate and Case-Shiller index."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    delinq = _safe_get(section_data, "DRSFRMACBS")
    cs = _safe_get(section_data, "CSUSHPINSA")

    if delinq is not None:
        d = delinq[delinq.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=d.index, y=d.values,
                name="Mortgage Delinquency (%)", line=dict(color=LINE_PALETTE[5], width=2),
                hovertemplate="%{y:.2f}%<extra>Mortgage Delinquency</extra>",
            ),
            secondary_y=False,
        )

    if cs is not None:
        c = cs[cs.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=c.index, y=c.values,
                name="Case-Shiller Home Price Index", line=dict(color=LINE_PALETTE[0], width=2),
                hovertemplate="%{y:.1f}<extra>Case-Shiller</extra>",
            ),
            secondary_y=True,
        )

    layout = _base_layout()
    layout["title"] = "Housing: Mortgage Delinquency vs. Home Prices"
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Delinquency Rate (%)", secondary_y=False, gridcolor=COLORS["grid"])
    fig.update_yaxes(title_text="Case-Shiller Index", secondary_y=True, gridcolor=COLORS["grid"])
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Section 4: Ghost GDP
# ──────────────────────────────────────────────────────────────────────────────

def chart_ghost_gdp(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """The key Ghost GDP chart: GDP, productivity, labor share, corporate profits."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    indexed_series = [
        ("GDPC1", "Real GDP", LINE_PALETTE[0]),
        ("OPHNFB", "Productivity", LINE_PALETTE[1]),
        ("CP", "Corporate Profits", LINE_PALETTE[2]),
    ]

    for sid, name, color in indexed_series:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            fig.add_trace(
                go.Scatter(
                    x=indexed.index, y=indexed.values,
                    name=name, line=dict(color=color, width=2),
                    hovertemplate="%{y:.1f}<extra>" + name + "</extra>",
                ),
                secondary_y=False,
            )

    # Labor share on secondary axis (different scale)
    labor_share = _safe_get(section_data, "W270RE1A156NBEA")
    if labor_share is not None:
        ls = labor_share[labor_share.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=ls.index, y=ls.values,
                name="Labor Share of GDP (%)", line=dict(color=LINE_PALETTE[5], width=2, dash="dash"),
                hovertemplate="%{y:.1f}%<extra>Labor Share</extra>",
            ),
            secondary_y=True,
        )

    layout = _base_layout()
    layout["title"] = '"Ghost GDP" — Productivity vs. Labor Share Divergence'
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Index (100 = start)", secondary_y=False, gridcolor=COLORS["grid"])
    fig.update_yaxes(title_text="Labor Share (%)", secondary_y=True, gridcolor=COLORS["grid"])
    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5, secondary_y=False)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Section 5: Financial Stress
# ──────────────────────────────────────────────────────────────────────────────

def chart_financial_stress(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """HY OAS spread and VIX on the same chart."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    hy_oas = _safe_get(section_data, "BAMLH0A0HYM2")
    vix = _safe_get(section_data, "VIXCLS")

    if hy_oas is not None:
        h = hy_oas[hy_oas.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=h.index, y=h.values,
                name="HY OAS (bps)", line=dict(color=LINE_PALETTE[5], width=2),
                hovertemplate="%{y:.0f} bps<extra>HY OAS</extra>",
            ),
            secondary_y=False,
        )

    if vix is not None:
        v = vix[vix.index >= pd.Timestamp(start_date)]
        fig.add_trace(
            go.Scatter(
                x=v.index, y=v.values,
                name="VIX", line=dict(color=LINE_PALETTE[1], width=2),
                hovertemplate="%{y:.1f}<extra>VIX</extra>",
            ),
            secondary_y=True,
        )

    layout = _base_layout()
    layout["title"] = "Financial Stress: High Yield Spreads & VIX"
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="HY OAS (bps)", secondary_y=False, gridcolor=COLORS["grid"])
    fig.update_yaxes(title_text="VIX", secondary_y=True, gridcolor=COLORS["grid"])
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Supporting charts for additional metrics
# ──────────────────────────────────────────────────────────────────────────────

def chart_single_series(
    series: pd.Series,
    name: str,
    recession_data,
    start_date: date,
    y_title: str = "",
    color: str = LINE_PALETTE[0],
) -> go.Figure:
    """Generic single-series chart with recession shading and annotations."""
    fig = go.Figure()
    fig.update_layout(**_base_layout(), title=name)

    s = series[series.index >= pd.Timestamp(start_date)]
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        name=name, line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
    ))

    fig.update_yaxes(title_text=y_title or name)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig
