"""
AI Displacement Leading Indicators Dashboard

A Streamlit dashboard that tracks divergences between headline economic data
and white-collar-specific indicators to monitor the AI displacement thesis.
"""

import os
from datetime import date

import pandas as pd
import streamlit as st

from config import SECTIONS, COLORS, DATE_RANGE_OPTIONS
from data import fetch_all_data, get_series_name, build_summary_table, build_export_dataframe, clear_cache, get_fred_client
from signals import evaluate_all, composite_assessment
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
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS for dark theme
# ──────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    /* Main background */
    .stApp {{
        background-color: {COLORS["background"]};
    }}

    /* Signal badges */
    .signal-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
        margin: 2px 0;
    }}
    .signal-green {{
        background-color: rgba(46, 204, 113, 0.15);
        color: {COLORS["green"]};
        border: 1px solid {COLORS["green"]};
    }}
    .signal-yellow {{
        background-color: rgba(243, 156, 18, 0.15);
        color: {COLORS["yellow"]};
        border: 1px solid {COLORS["yellow"]};
    }}
    .signal-red {{
        background-color: rgba(231, 76, 60, 0.15);
        color: {COLORS["red"]};
        border: 1px solid {COLORS["red"]};
    }}

    /* Composite assessment box */
    .assessment-box {{
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
    }}
    .assessment-no-signal {{
        background: linear-gradient(135deg, rgba(46,204,113,0.1), rgba(46,204,113,0.05));
        border: 1px solid {COLORS["green"]};
    }}
    .assessment-early-warning {{
        background: linear-gradient(135deg, rgba(243,156,18,0.1), rgba(243,156,18,0.05));
        border: 1px solid {COLORS["yellow"]};
    }}
    .assessment-elevated-risk {{
        background: linear-gradient(135deg, rgba(231,76,60,0.1), rgba(243,156,18,0.05));
        border: 1px solid {COLORS["orange"]};
    }}
    .assessment-active-crisis {{
        background: linear-gradient(135deg, rgba(231,76,60,0.15), rgba(231,76,60,0.05));
        border: 1px solid {COLORS["red"]};
    }}

    /* Section headers */
    .section-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }}

    /* Data freshness */
    .data-freshness {{
        color: {COLORS["muted_text"]};
        font-size: 0.8rem;
    }}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def signal_badge(status: str, explanation: str) -> str:
    """Render a colored signal badge as HTML."""
    icons = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    labels = {"green": "No Signal", "yellow": "Early Warning", "red": "Active Signal"}
    icon = icons.get(status, "⚪")
    label = labels.get(status, "Unknown")
    return (
        f'<span class="signal-badge signal-{status}">'
        f'{icon} {label}</span>'
        f'<span style="color: {COLORS["muted_text"]}; font-size: 0.85rem; margin-left: 10px;">'
        f'{explanation}</span>'
    )


def get_latest_dates(section_data: dict) -> str:
    """Return a string listing the most recent data point date for each series."""
    dates = []
    for sid, val in section_data.items():
        if isinstance(val, pd.Series) and len(val) > 0:
            dates.append(val.index[-1])
    if dates:
        most_recent = max(dates)
        return most_recent.strftime("%Y-%m-%d")
    return "N/A"


def render_supporting_metrics(section_key: str, section_data: dict, recession_data, start_date: date):
    """Render additional single-series charts for a section."""
    section_config = SECTIONS[section_key]
    displayed = set()

    # Track which series are already shown in composite charts
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


# ──────────────────────────────────────────────────────────────────────────────
# API key check
# ──────────────────────────────────────────────────────────────────────────────

def show_setup_page():
    """Show instructions if no API key is configured."""
    st.title("📉 AI Displacement Dashboard — Setup Required")
    st.markdown("---")
    st.error("**FRED API key not found.** Set the `FRED_API_KEY` environment variable to get started.")
    st.markdown("""
    ### How to get your free API key:

    1. Go to [FRED API Key Registration](https://fred.stlouisfed.org/docs/api/api_key.html)
    2. Create a free account or sign in
    3. Request an API key

    ### How to set it:

    **Option A: Environment variable**
    ```bash
    export FRED_API_KEY=your_key_here
    streamlit run app.py
    ```

    **Option B: `.env` file**

    Create a `.env` file in the project root:
    ```
    FRED_API_KEY=your_key_here
    ```
    Then install `python-dotenv` and it will be loaded automatically.

    **Option C: Streamlit secrets**

    Create `.streamlit/secrets.toml`:
    ```toml
    FRED_API_KEY = "your_key_here"
    ```
    """)
    st.stop()


# ──────────────────────────────────────────────────────────────────────────────
# Load .env if python-dotenv is available
# ──────────────────────────────────────────────────────────────────────────────

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Also check streamlit secrets
if not os.environ.get("FRED_API_KEY") and hasattr(st, "secrets"):
    try:
        key = st.secrets.get("FRED_API_KEY", "")
        if key:
            os.environ["FRED_API_KEY"] = key
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Main app
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Check API key
    if get_fred_client() is None:
        show_setup_page()

    # ── Sidebar ──
    with st.sidebar:
        st.title("📉 AI Displacement")
        st.caption("Leading Indicators Dashboard")
        st.markdown("---")

        # Date range
        date_range_label = st.selectbox(
            "Date Range",
            options=list(DATE_RANGE_OPTIONS.keys()),
            index=0,
        )
        start_date = DATE_RANGE_OPTIONS[date_range_label]

        st.markdown("---")

        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            clear_cache()
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown(
            f'<div class="data-freshness">Cache: SQLite (auto-refreshes every 12h)<br>'
            f'Source: FRED (Federal Reserve Economic Data)</div>',
            unsafe_allow_html=True,
        )

    # ── Load data ──
    @st.cache_data(ttl=3600, show_spinner="Fetching economic data from FRED...")
    def load_data():
        return fetch_all_data(force_refresh=False)

    data = load_data()

    if not data:
        st.error("Failed to load data. Check your FRED API key.")
        st.stop()

    # Get recession data
    recession_data = data.get("_meta", {}).get("USREC")
    if isinstance(recession_data, str):
        recession_data = None

    # ── Evaluate signals ──
    signals = evaluate_all(data)
    assessment_label, assessment_desc = composite_assessment(signals)

    # ── Header ──
    st.markdown(
        '<h1 style="margin-bottom: 0;">AI Displacement Leading Indicators</h1>',
        unsafe_allow_html=True,
    )
    st.caption("Tracking divergences between headline economic data and white-collar indicators")

    # ── Overall Thesis Tracker ──
    assessment_class = assessment_label.lower().replace(" ", "-")
    statuses = [s for s, _ in signals.values()]
    green_n = statuses.count("green")
    yellow_n = statuses.count("yellow")
    red_n = statuses.count("red")

    st.markdown(f"""
    <div class="assessment-box assessment-{assessment_class}">
        <h2 style="margin: 0 0 8px 0;">Thesis Status: {assessment_label}</h2>
        <p style="margin: 0; color: {COLORS['muted_text']};">{assessment_desc}</p>
        <p style="margin: 8px 0 0 0;">
            <span class="signal-badge signal-green">🟢 {green_n}</span>
            <span class="signal-badge signal-yellow">🟡 {yellow_n}</span>
            <span class="signal-badge signal-red">🔴 {red_n}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Latest data freshness ──
    freshness_cols = st.columns(5)
    for i, (section_key, section) in enumerate(SECTIONS.items()):
        with freshness_cols[i]:
            section_data = data.get(section_key, {})
            latest = get_latest_dates(section_data)
            short_title = section["title"].split("—")[0].split(":")[0].strip()
            if len(short_title) > 18:
                short_title = short_title[:18] + "…"
            st.markdown(
                f'<div class="data-freshness"><strong>{short_title}</strong><br>Latest: {latest}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────
    # Section 1: Labor Market
    # ──────────────────────────────────────────────────────────────────────
    section_key = "labor"
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    with st.expander(f"**{SECTIONS[section_key]['title']}**", expanded=True):
        st.markdown(signal_badge(status, explanation), unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = chart_labor_openings(section_data, recession_data, start_date)
            st.plotly_chart(fig, use_container_width=True, key="labor_openings")
        with col2:
            fig = chart_labor_employment(section_data, recession_data, start_date)
            st.plotly_chart(fig, use_container_width=True, key="labor_employment")

        with st.expander("Supporting Metrics", expanded=False):
            render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────────
    # Section 2: Consumer Stress
    # ──────────────────────────────────────────────────────────────────────
    section_key = "consumer"
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    with st.expander(f"**{SECTIONS[section_key]['title']}**", expanded=True):
        st.markdown(signal_badge(status, explanation), unsafe_allow_html=True)

        fig = chart_consumer_stress(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="consumer_stress")

        with st.expander("Supporting Metrics", expanded=False):
            render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────────
    # Section 3: Housing
    # ──────────────────────────────────────────────────────────────────────
    section_key = "housing"
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    with st.expander(f"**{SECTIONS[section_key]['title']}**", expanded=True):
        st.markdown(signal_badge(status, explanation), unsafe_allow_html=True)

        fig = chart_housing(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="housing_chart")

        with st.expander("Supporting Metrics", expanded=False):
            render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────────
    # Section 4: Ghost GDP
    # ──────────────────────────────────────────────────────────────────────
    section_key = "macro"
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    with st.expander(f"**{SECTIONS[section_key]['title']}**", expanded=True):
        st.markdown(signal_badge(status, explanation), unsafe_allow_html=True)

        fig = chart_ghost_gdp(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="ghost_gdp")

        with st.expander("Supporting Metrics", expanded=False):
            render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────────
    # Section 5: Financial Stress
    # ──────────────────────────────────────────────────────────────────────
    section_key = "financial"
    section_data = data.get(section_key, {})
    status, explanation = signals.get(section_key, ("green", ""))

    with st.expander(f"**{SECTIONS[section_key]['title']}**", expanded=True):
        st.markdown(signal_badge(status, explanation), unsafe_allow_html=True)

        fig = chart_financial_stress(section_data, recession_data, start_date)
        st.plotly_chart(fig, use_container_width=True, key="financial_stress")

        with st.expander("Supporting Metrics", expanded=False):
            render_supporting_metrics(section_key, section_data, recession_data, start_date)

    # ──────────────────────────────────────────────────────────────────────
    # Summary Table & Export
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("YoY Change Summary")

    summary_df = build_summary_table(data)
    if not summary_df.empty:
        # Style the direction column
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Direction": st.column_config.TextColumn(width="small"),
                "Section": st.column_config.TextColumn(width="medium"),
            },
        )

    # Export
    st.subheader("Export")
    export_df = build_export_dataframe(data)
    if not export_df.empty:
        csv = export_df.to_csv()
        st.download_button(
            label="📥 Download All Data as CSV",
            data=csv,
            file_name=f"ai_displacement_data_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.info("No data available to export.")

    # Footer
    st.markdown("---")
    st.markdown(
        f'<div style="text-align: center; color: {COLORS["muted_text"]}; font-size: 0.8rem;">'
        f'Data source: Federal Reserve Economic Data (FRED) · '
        f'Dashboard tracks the AI intelligence displacement thesis · '
        f'Signal thresholds are configurable in config.py'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
