"""
Chart generation module using Plotly.

Clean, minimal charts inspired by Apple's design language —
light backgrounds, thin lines, generous whitespace, subtle details.
"""

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import COLORS, LINE_PALETTE, AI_MILESTONES


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _base_layout(title: str = "") -> dict:
    """Return the common Apple-inspired light layout dict."""
    return dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            color=COLORS["text"],
            size=13,
        ),
        title=dict(
            text=title,
            font=dict(size=16, color=COLORS["text"]),
            x=0,
            xanchor="left",
            pad=dict(l=8),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color=COLORS["text_secondary"]),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            itemclick="toggle",
            itemsizing="constant",
        ),
        margin=dict(l=56, r=24, t=56, b=40),
        xaxis=dict(
            gridcolor=COLORS["grid_line"],
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor=COLORS["grid_line"],
            linewidth=1,
            tickfont=dict(size=11, color=COLORS["muted_text"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["grid_line"],
            showgrid=True,
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=COLORS["muted_text"]),
            title_font=dict(size=12, color=COLORS["text_secondary"]),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family='-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
            bordercolor=COLORS["border"],
        ),
    )


def _add_recession_shading(fig: go.Figure, recession_data: pd.Series | None, start_date: date):
    """Add subtle shading for NBER recession periods."""
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
                annotation_text="",
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
    """Add minimal vertical markers for AI milestones."""
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


def _add_trace_line(fig, x, y, name, color, width=2.5, dash=None, secondary_y=None, hover_template=None):
    """Add a clean line trace with optional area fill."""
    kwargs = dict(
        x=x, y=y,
        name=name,
        line=dict(color=color, width=width, shape="spline", smoothing=0.3),
        hovertemplate=hover_template or "%{y:.1f}<extra>" + name + "</extra>",
    )
    if dash:
        kwargs["line"]["dash"] = dash
    if secondary_y is not None:
        fig.add_trace(go.Scatter(**kwargs), secondary_y=secondary_y)
    else:
        fig.add_trace(go.Scatter(**kwargs))


# ──────────────────────────────────────────────────────────────────────────────
# Section 1: Labor Market charts
# ──────────────────────────────────────────────────────────────────────────────

def chart_labor_openings(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Job openings: total vs. professional services vs. information (indexed to 100)."""
    fig = go.Figure()
    fig.update_layout(**_base_layout("Job Openings Divergence"))

    series_map = [
        ("JTSJOL", "Total", LINE_PALETTE[0]),
        ("JTS540099000000000JOL", "Prof. & Business", LINE_PALETTE[1]),
        ("JTS510000000000000JOL", "Information", LINE_PALETTE[2]),
    ]

    for sid, name, color in series_map:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            _add_trace_line(fig, indexed.index, indexed.values, name, color)

    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5, opacity=0.5)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    fig.update_yaxes(title_text="Indexed (100 = start)")
    return fig


def chart_labor_employment(section_data: dict, recession_data, start_date: date) -> go.Figure:
    """Employment: total nonfarm vs. professional services vs. information (indexed)."""
    fig = go.Figure()
    fig.update_layout(**_base_layout("Employment Divergence"))

    series_map = [
        ("PAYEMS", "Total Nonfarm", LINE_PALETTE[0]),
        ("USPBS", "Prof. & Business", LINE_PALETTE[1]),
        ("CES5000000001", "Information", LINE_PALETTE[2]),
    ]

    for sid, name, color in series_map:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            _add_trace_line(fig, indexed.index, indexed.values, name, color)

    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5, opacity=0.5)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    fig.update_yaxes(title_text="Indexed (100 = start)")
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
        _add_trace_line(fig, r.index, r.values, "Revolving Credit", LINE_PALETTE[0],
                        secondary_y=False, hover_template="$%{y:,.0f}B<extra>Revolving Credit</extra>")

    if delinquency is not None:
        d = delinquency[delinquency.index >= pd.Timestamp(start_date)]
        _add_trace_line(fig, d.index, d.values, "CC Delinquency Rate", LINE_PALETTE[5],
                        secondary_y=True, hover_template="%{y:.2f}%<extra>CC Delinquency</extra>")

    layout = _base_layout("Consumer Credit Stress")
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Revolving Credit ($B)", secondary_y=False, gridcolor=COLORS["grid_line"])
    fig.update_yaxes(title_text="Delinquency Rate (%)", secondary_y=True, gridcolor=COLORS["grid_line"])
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
        _add_trace_line(fig, d.index, d.values, "Mortgage Delinquency", LINE_PALETTE[5],
                        secondary_y=False, hover_template="%{y:.2f}%<extra>Mortgage Delinquency</extra>")

    if cs is not None:
        c = cs[cs.index >= pd.Timestamp(start_date)]
        _add_trace_line(fig, c.index, c.values, "Case-Shiller Index", LINE_PALETTE[0],
                        secondary_y=True, hover_template="%{y:.1f}<extra>Case-Shiller</extra>")

    layout = _base_layout("Mortgage Delinquency vs. Home Prices")
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Delinquency Rate (%)", secondary_y=False, gridcolor=COLORS["grid_line"])
    fig.update_yaxes(title_text="Case-Shiller Index", secondary_y=True, gridcolor=COLORS["grid_line"])
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
        ("CP", "Corp. Profits", LINE_PALETTE[2]),
    ]

    for sid, name, color in indexed_series:
        s = _safe_get(section_data, sid)
        if s is not None:
            indexed = _index_to_100(s, start_date)
            _add_trace_line(fig, indexed.index, indexed.values, name, color, secondary_y=False)

    labor_share = _safe_get(section_data, "W270RE1A156NBEA")
    if labor_share is not None:
        ls = labor_share[labor_share.index >= pd.Timestamp(start_date)]
        _add_trace_line(fig, ls.index, ls.values, "Labor Share (%)", LINE_PALETTE[5],
                        dash="dash", secondary_y=True,
                        hover_template="%{y:.1f}%<extra>Labor Share</extra>")

    layout = _base_layout("Productivity vs. Labor Share")
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="Indexed (100 = start)", secondary_y=False, gridcolor=COLORS["grid_line"])
    fig.update_yaxes(title_text="Labor Share (%)", secondary_y=True, gridcolor=COLORS["grid_line"])
    fig.add_hline(y=100, line_dash="dot", line_color=COLORS["muted_text"], line_width=0.5, opacity=0.5, secondary_y=False)
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
        _add_trace_line(fig, h.index, h.values, "HY OAS (bps)", LINE_PALETTE[5],
                        secondary_y=False, hover_template="%{y:.0f} bps<extra>HY OAS</extra>")

    if vix is not None:
        v = vix[vix.index >= pd.Timestamp(start_date)]
        _add_trace_line(fig, v.index, v.values, "VIX", LINE_PALETTE[1],
                        secondary_y=True, hover_template="%{y:.1f}<extra>VIX</extra>")

    layout = _base_layout("High Yield Spreads & Volatility")
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="HY OAS (bps)", secondary_y=False, gridcolor=COLORS["grid_line"])
    fig.update_yaxes(title_text="VIX", secondary_y=True, gridcolor=COLORS["grid_line"])
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
    """Generic single-series chart with subtle area fill."""
    fig = go.Figure()
    fig.update_layout(**_base_layout(name))

    s = series[series.index >= pd.Timestamp(start_date)]

    # Parse hex color for subtle fill
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        name=name,
        line=dict(color=color, width=2.5, shape="spline", smoothing=0.3),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.06)",
    ))

    fig.update_yaxes(title_text=y_title or name)
    _add_recession_shading(fig, recession_data, start_date)
    _add_ai_annotations(fig, start_date)
    return fig
