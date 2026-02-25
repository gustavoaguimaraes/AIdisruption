"""
AI Displacement Leading Indicators Dashboard

A Streamlit dashboard that tracks divergences between headline economic data
and white-collar-specific indicators to monitor the AI displacement thesis.
"""

import os
from pathlib import Path
from datetime import date

# Load .env early, before any module reads env vars
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import pandas as pd
import streamlit as st

from config import SECTIONS, COLORS, DATE_RANGE_OPTIONS
from data import fetch_all_data, build_summary_table, build_export_dataframe, clear_cache, get_fred_client
from signals import evaluate_all, composite_assessment
from analysis import generate_analysis
from charts import (
    chart_labor_openings,
    chart_labor_employment,
    chart_consumer_stress,
    chart_housing,
    chart_ghost_gdp,
    chart_financial_stress,
    chart_single_series,
)

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Displacement Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Apple-inspired CSS
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                     'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }

    /* ── Background ── */
    .stApp {
        background-color: #f5f5f7;
    }

    [data-testid="stSidebar"] {
        background-color: rgba(251, 251, 253, 0.92);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0, 0, 0, 0.06);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #1d1d1f;
    }

    /* ── Top header area ── */
    .dashboard-header {
        padding: 8px 0 24px 0;
    }

    .dashboard-header h1 {
        font-size: 2.4rem;
        font-weight: 700;
        color: #1d1d1f;
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.15;
    }

    .dashboard-subtitle {
        font-size: 1.05rem;
        color: #86868b;
        font-weight: 400;
        margin-top: 4px;
        letter-spacing: -0.01em;
    }

    /* ── Assessment hero card ── */
    .assessment-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 32px 36px;
        margin: 0 0 32px 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.03);
        border: 1px solid rgba(0, 0, 0, 0.06);
        text-align: center;
    }

    .assessment-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }

    .assessment-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1d1d1f;
        letter-spacing: -0.02em;
        margin: 4px 0 8px 0;
    }

    .assessment-desc {
        font-size: 0.95rem;
        color: #86868b;
        font-weight: 400;
        margin-bottom: 16px;
    }

    /* Assessment status colors */
    .status-no-signal .assessment-label { color: #34c759; }
    .status-no-signal .assessment-card { border-top: 3px solid #34c759; }

    .status-early-warning .assessment-label { color: #ff9f0a; }
    .status-early-warning .assessment-card { border-top: 3px solid #ff9f0a; }

    .status-elevated-risk .assessment-label { color: #ff6723; }
    .status-elevated-risk .assessment-card { border-top: 3px solid #ff6723; }

    .status-active-crisis .assessment-label { color: #ff3b30; }
    .status-active-crisis .assessment-card { border-top: 3px solid #ff3b30; }

    /* ── Signal pills ── */
    .signal-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 100px;
        font-weight: 500;
        font-size: 0.8rem;
        margin: 0 4px;
        letter-spacing: -0.01em;
    }

    .pill-green {
        background-color: rgba(52, 199, 89, 0.10);
        color: #248a3d;
    }

    .pill-yellow {
        background-color: rgba(255, 159, 10, 0.10);
        color: #c77c02;
    }

    .pill-red {
        background-color: rgba(255, 59, 48, 0.10);
        color: #d70015;
    }

    /* ── Count badges in the header ── */
    .signal-counts {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 16px;
    }

    .count-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 20px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .count-green {
        background: rgba(52, 199, 89, 0.08);
        color: #248a3d;
    }

    .count-yellow {
        background: rgba(255, 159, 10, 0.08);
        color: #c77c02;
    }

    .count-red {
        background: rgba(255, 59, 48, 0.08);
        color: #d70015;
    }

    .count-number {
        font-size: 1.3rem;
        font-weight: 700;
    }

    /* ── Section cards ── */
    .section-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 28px 32px 20px 32px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.03);
        border: 1px solid rgba(0, 0, 0, 0.06);
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1d1d1f;
        letter-spacing: -0.02em;
        margin: 0 0 2px 0;
    }

    .section-subtitle {
        font-size: 0.85rem;
        color: #86868b;
        font-weight: 400;
        margin-bottom: 12px;
    }

    .section-signal {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
    }

    .signal-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    .dot-green { background-color: #34c759; }
    .dot-yellow { background-color: #ff9f0a; }
    .dot-red { background-color: #ff3b30; }

    .signal-text {
        font-size: 0.85rem;
        color: #6e6e73;
        font-weight: 400;
    }

    .signal-status-label {
        font-size: 0.8rem;
        font-weight: 600;
    }

    .label-green { color: #248a3d; }
    .label-yellow { color: #c77c02; }
    .label-red { color: #d70015; }

    /* ── Freshness row ── */
    .freshness-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }

    .freshness-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #1d1d1f;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }

    .freshness-date {
        font-size: 0.8rem;
        color: #86868b;
        font-weight: 400;
    }

    /* ── Sidebar styling ── */
    .sidebar-brand {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1d1d1f;
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }

    .sidebar-caption {
        font-size: 0.82rem;
        color: #86868b;
        margin-bottom: 16px;
    }

    .sidebar-meta {
        font-size: 0.75rem;
        color: #aeaeb2;
        line-height: 1.6;
    }

    /* ── Summary table ── */
    .summary-heading {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1d1d1f;
        letter-spacing: -0.02em;
        margin: 8px 0 16px 0;
    }

    /* ── Footer ── */
    .footer-text {
        text-align: center;
        font-size: 0.78rem;
        color: #aeaeb2;
        padding: 24px 0 16px 0;
        letter-spacing: -0.01em;
    }

    /* ── Streamlit overrides for clean look ── */
    .stExpander {
        background: transparent;
        border: none !important;
        box-shadow: none !important;
    }

    [data-testid="stExpander"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    [data-testid="stExpander"] details {
        border: none !important;
    }

    [data-testid="stExpander"] summary {
        font-weight: 500;
        color: #007aff;
        font-size: 0.9rem;
    }

    /* Download button */
    .stDownloadButton > button {
        background: #007aff !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
    }

    .stDownloadButton > button:hover {
        background: #0066d6 !important;
        transform: scale(1.01);
    }

    /* Regular buttons */
    .stButton > button {
        border-radius: 12px !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        background: #ffffff !important;
        color: #1d1d1f !important;
        font-weight: 500 !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        background: #f5f5f7 !important;
        border-color: rgba(0, 0, 0, 0.15) !important;
    }

    /* Select box */
    [data-testid="stSelectbox"] > div > div {
        border-radius: 10px !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(0, 0, 0, 0.06);
    }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Dividers */
    hr {
        border: none;
        border-top: 1px solid rgba(0, 0, 0, 0.06);
        margin: 24px 0;
    }

    /* ── AI Briefing Card ── */
    .briefing-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 32px 40px;
        margin: 0 0 28px 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04);
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-left: 4px solid #007aff;
    }

    .briefing-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }

    .briefing-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #007aff;
    }

    .briefing-meta {
        font-size: 0.75rem;
        color: #aeaeb2;
    }

    .briefing-cached {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 6px;
        background: rgba(0, 122, 255, 0.06);
        color: #007aff;
        font-size: 0.7rem;
        font-weight: 500;
        margin-left: 8px;
    }

    .briefing-fresh {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 6px;
        background: rgba(52, 199, 89, 0.08);
        color: #248a3d;
        font-size: 0.7rem;
        font-weight: 500;
        margin-left: 8px;
    }

    .briefing-body {
        font-size: 0.92rem;
        line-height: 1.75;
        color: #1d1d1f;
    }

    .briefing-body h3 {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1d1d1f;
        margin: 20px 0 8px 0;
        letter-spacing: -0.01em;
    }

    .briefing-body p {
        margin: 0 0 12px 0;
    }

    .briefing-body strong {
        color: #1d1d1f;
        font-weight: 600;
    }

    .briefing-body ul, .briefing-body ol {
        padding-left: 20px;
        margin: 8px 0 12px 0;
    }

    .briefing-body li {
        margin-bottom: 6px;
        line-height: 1.65;
    }

    .briefing-setup {
        background: #ffffff;
        border-radius: 16px;
        padding: 24px 32px;
        margin: 0 0 28px 0;
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-left: 4px solid #aeaeb2;
        color: #86868b;
        font-size: 0.9rem;
    }

    .briefing-setup a {
        color: #007aff;
        text-decoration: none;
    }

    .briefing-setup code {
        background: #f5f5f7;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def render_signal(status: str, explanation: str) -> str:
    """Render a minimal signal indicator."""
    labels = {"green": "Normal", "yellow": "Watch", "red": "Alert"}
    label = labels.get(status, "Unknown")
    return (
        f'<div class="section-signal">'
        f'<span class="signal-dot dot-{status}"></span>'
        f'<span class="signal-status-label label-{status}">{label}</span>'
        f'<span class="signal-text">{explanation}</span>'
        f'</div>'
    )


def get_latest_dates(section_data: dict) -> str:
    """Return the most recent data point date for each series."""
    dates = []
    for sid, val in section_data.items():
        if isinstance(val, pd.Series) and len(val) > 0:
            dates.append(val.index[-1])
    if dates:
        most_recent = max(dates)
        return most_recent.strftime("%b %d, %Y")
    return "N/A"


def render_supporting_metrics(section_key: str, section_data: dict, recession_data, start_date: date):
    """Render additional single-series charts for a section."""
    section_config = SECTIONS[section_key]
    displayed = set()

    if section_key == "labor":
        displayed = {"JTSJOL", "JTS540099000000000JOL", "JTS510000000000000JOL", "PAYEMS", "USPBS", "CES5000000001"}
    elif section_key == "consumer":
        displayed = {"REVOLSL", "DRCCLACBS"}
    elif section_key == "housing":
        displayed = {"DRSFRMACBS", "CSUSHPINSA"}
    elif section_key == "macro":
        displayed = {"GDPC1", "OPHNFB", "CP", "W270RE1A156NBEA"}
    elif section_key == "financial":
        displayed = {"BAMLH0A0HYM2", "VIXCLS"}

    remaining = [
        (sid, name) for sid, name, _freq in section_config["series"]
        if sid not in displayed
    ]

    if not remaining:
        return

    cols = st.columns(min(len(remaining), 2))
    for i, (sid, name) in enumerate(remaining):
        series = section_data.get(sid)
        if series is None or isinstance(series, str):
            with cols[i % len(cols)]:
                if isinstance(series, str):
                    st.warning(f"{name}: {series}")
                else:
                    st.info(f"{name}: No data available")
            continue
        with cols[i % len(cols)]:
            fig = chart_single_series(series, name, recession_data, start_date)
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{sid}")


def render_section(section_key: str, data: dict, signals: dict, recession_data, start_date: date, chart_func, chart_kwargs=None):
    """Render a full section card with signal, chart, and supporting metrics."""
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    if chart_kwargs:
        chart_kwargs_resolved = {k: (section_data if v == "_section_data" else v) for k, v in chart_kwargs.items()}
        fig = chart_func(**chart_kwargs_resolved)
    else:
        fig = chart_func(section_data, recession_data, start_date)

    st.plotly_chart(fig, use_container_width=True, key=f"main_{section_key}")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)


def _render_ai_briefing(data: dict, signals: dict, assessment: tuple):
    """Render the AI analysis briefing card at the top of the dashboard."""
    import markdown as _md_module

    has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    if not has_anthropic_key:
        st.markdown(
            '<div class="briefing-setup">'
            '<strong>AI Briefing</strong> — Add your Anthropic API key to enable AI-powered market analysis. '
            'Set <code>ANTHROPIC_API_KEY</code> in your <code>.env</code> file. '
            'Uses Claude Opus 4.6 for deep analysis with persistent memory.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Generating AI briefing..."):
        result = generate_analysis(data, signals, assessment)

    if result["error"] and result["analysis"] is None:
        st.warning(f"AI Briefing unavailable: {result['error']}")
        return

    analysis_md = result["analysis"]
    is_cached = result["is_cached"]
    created_at = result["created_at"]

    # Format timestamp
    timestamp_str = ""
    if created_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at)
            timestamp_str = dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            timestamp_str = created_at[:16]

    status_badge = (
        '<span class="briefing-cached">cached — data unchanged</span>'
        if is_cached
        else '<span class="briefing-fresh">updated — new data</span>'
    )

    # Convert markdown to HTML
    try:
        analysis_html = _md_module.markdown(analysis_md, extensions=["extra"])
    except Exception:
        analysis_html = analysis_md.replace("\n", "<br>")

    # Show error note if API failed but previous analysis is available
    error_note = ""
    if result["error"] and result["analysis"]:
        error_note = (
            f'<div style="color: #aeaeb2; font-size: 0.78rem; margin-top: 12px; '
            f'padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.05);">'
            f'Note: {result["error"]}</div>'
        )

    st.markdown(f"""
    <div class="briefing-card">
        <div class="briefing-header">
            <div>
                <span class="briefing-title">AI Market Briefing</span>
                {status_badge}
            </div>
            <div class="briefing-meta">{timestamp_str}</div>
        </div>
        <div class="briefing-body">
            {analysis_html}
        </div>
        {error_note}
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# API key check
# ──────────────────────────────────────────────────────────────────────────────

def show_setup_page():
    """Show a clean setup page if no API key is configured."""
    st.markdown("""
    <div style="max-width: 560px; margin: 80px auto; text-align: center;">
        <h1 style="font-size: 2.2rem; font-weight: 700; color: #1d1d1f; letter-spacing: -0.03em;">
            AI Displacement Dashboard
        </h1>
        <p style="color: #86868b; font-size: 1rem; margin: 8px 0 32px 0;">
            A FRED API key is required to get started.
        </p>
        <div style="background: #fff; border-radius: 16px; padding: 32px; text-align: left;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
                    border: 1px solid rgba(0,0,0,0.06);">
            <p style="font-weight: 600; color: #1d1d1f; margin-bottom: 16px;">How to set up</p>
            <ol style="color: #6e6e73; line-height: 2; padding-left: 20px;">
                <li>Register for a free key at <a href="https://fred.stlouisfed.org/docs/api/api_key.html"
                    style="color: #007aff; text-decoration: none;">fred.stlouisfed.org</a></li>
                <li>Create a <code style="background: #f5f5f7; padding: 2px 8px; border-radius: 6px;
                    font-size: 0.85em;">.env</code> file with <code style="background: #f5f5f7;
                    padding: 2px 8px; border-radius: 6px; font-size: 0.85em;">FRED_API_KEY=your_key</code></li>
                <li>Restart the dashboard</li>
            </ol>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# Also check streamlit secrets
if hasattr(st, "secrets"):
    try:
        if not os.environ.get("FRED_API_KEY"):
            key = st.secrets.get("FRED_API_KEY", "")
            if key:
                os.environ["FRED_API_KEY"] = key
        if not os.environ.get("ANTHROPIC_API_KEY"):
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
            if key:
                os.environ["ANTHROPIC_API_KEY"] = key
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Main app
# ──────────────────────────────────────────────────────────────────────────────

def main():
    if get_fred_client() is None:
        show_setup_page()

    # ── Sidebar ──
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">AI Displacement</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-caption">Leading Indicators Dashboard</div>', unsafe_allow_html=True)

        st.markdown("---")

        date_range_label = st.selectbox(
            "Time Range",
            options=list(DATE_RANGE_OPTIONS.keys()),
            index=0,
        )
        start_date = DATE_RANGE_OPTIONS[date_range_label]

        st.markdown("")

        if st.button("Refresh Data", use_container_width=True):
            clear_cache()
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown(
            '<div class="sidebar-meta">'
            'Cache refreshes every 12 hours<br>'
            'Source: Federal Reserve Economic Data'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Load data ──
    @st.cache_data(ttl=3600, show_spinner="Loading economic data...")
    def load_data():
        return fetch_all_data(force_refresh=False)

    data = load_data()

    if not data:
        st.error("Failed to load data. Check your FRED API key.")
        st.stop()

    recession_data = data.get("_meta", {}).get("USREC")
    if isinstance(recession_data, str):
        recession_data = None

    # ── Evaluate signals ──
    signals = evaluate_all(data)
    assessment_label, assessment_desc = composite_assessment(signals)

    # ── Header ──
    st.markdown("""
    <div class="dashboard-header">
        <h1>AI Displacement<br>Leading Indicators</h1>
        <div class="dashboard-subtitle">Tracking divergences between headline economic data and white-collar indicators</div>
    </div>
    """, unsafe_allow_html=True)

    # ── AI Briefing ──
    _render_ai_briefing(data, signals, (assessment_label, assessment_desc))

    # ── Assessment card ──
    statuses = [s for s, _ in signals.values()]
    green_n = statuses.count("green")
    yellow_n = statuses.count("yellow")
    red_n = statuses.count("red")

    assessment_class = assessment_label.lower().replace(" ", "-")

    st.markdown(f"""
    <div class="status-{assessment_class}">
        <div class="assessment-card">
            <div class="assessment-label">Current Assessment</div>
            <div class="assessment-title">{assessment_label}</div>
            <div class="assessment-desc">{assessment_desc}</div>
            <div class="signal-counts">
                <div class="count-badge count-green">
                    <span class="count-number">{green_n}</span> Normal
                </div>
                <div class="count-badge count-yellow">
                    <span class="count-number">{yellow_n}</span> Watch
                </div>
                <div class="count-badge count-red">
                    <span class="count-number">{red_n}</span> Alert
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Data freshness row ──
    freshness_cols = st.columns(5)
    for i, (section_key, section) in enumerate(SECTIONS.items()):
        with freshness_cols[i]:
            section_data = data.get(section_key, {})
            latest = get_latest_dates(section_data)
            st.markdown(
                f'<div class="freshness-card">'
                f'<div class="freshness-title">{section["title"]}</div>'
                f'<div class="freshness-date">{latest}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.markdown("")

    # ──────────────────────────────────────────────────────────────────
    # Section 1: Labor Market
    # ──────────────────────────────────────────────────────────────────
    section_key = "labor"
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = chart_labor_openings(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="labor_openings")
    with col2:
        fig = chart_labor_employment(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="labor_employment")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)

    st.markdown("")

    # ──────────────────────────────────────────────────────────────────
    # Section 2: Consumer Stress
    # ──────────────────────────────────────────────────────────────────
    section_key = "consumer"
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    fig = chart_consumer_stress(section_data, recession_data, start_date)
    st.plotly_chart(fig, use_container_width=True, key="consumer_stress")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)

    st.markdown("")

    # ──────────────────────────────────────────────────────────────────
    # Section 3: Housing
    # ──────────────────────────────────────────────────────────────────
    section_key = "housing"
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    fig = chart_housing(section_data, recession_data, start_date)
    st.plotly_chart(fig, use_container_width=True, key="housing_chart")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)

    st.markdown("")

    # ──────────────────────────────────────────────────────────────────
    # Section 4: Ghost GDP
    # ──────────────────────────────────────────────────────────────────
    section_key = "macro"
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    fig = chart_ghost_gdp(section_data, recession_data, start_date)
    st.plotly_chart(fig, use_container_width=True, key="ghost_gdp")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)

    st.markdown("")

    # ──────────────────────────────────────────────────────────────────
    # Section 5: Financial Stress
    # ──────────────────────────────────────────────────────────────────
    section_key = "financial"
    section = SECTIONS[section_key]
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    st.markdown(
        f'<div class="section-card">'
        f'<div class="section-title">{section["title"]}</div>'
        f'<div class="section-subtitle">{section["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_signal(status, explanation), unsafe_allow_html=True)

    fig = chart_financial_stress(section_data, recession_data, start_date)
    st.plotly_chart(fig, use_container_width=True, key="financial_stress")

    with st.expander("More metrics"):
        render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────
    # Summary & Export
    # ──────────────────────────────────────────────────────────────────
    st.markdown("---")

    st.markdown('<div class="summary-heading">YoY Change Summary</div>', unsafe_allow_html=True)

    summary_df = build_summary_table(data)
    if not summary_df.empty:
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Direction": st.column_config.TextColumn(width="small"),
                "Section": st.column_config.TextColumn(width="medium"),
            },
        )

    st.markdown("")

    export_df = build_export_dataframe(data)
    if not export_df.empty:
        csv = export_df.to_csv()
        st.download_button(
            label="Download All Data (CSV)",
            data=csv,
            file_name=f"ai_displacement_data_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.info("No data available to export.")

    # Footer
    st.markdown(
        '<div class="footer-text">'
        'Data from Federal Reserve Economic Data (FRED) '
        '&middot; Signal thresholds configurable in config.py'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
