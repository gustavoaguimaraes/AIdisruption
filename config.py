"""
Configuration for AI Displacement Leading Indicators Dashboard.

All FRED series IDs, signal thresholds, and dashboard settings are defined here
for easy adjustment.
"""

from datetime import date

# ──────────────────────────────────────────────────────────────────────────────
# FRED Series Definitions — grouped by dashboard section
# Each entry: (series_id, display_name, frequency)
# ──────────────────────────────────────────────────────────────────────────────

SECTIONS = {
    "labor": {
        "title": "Labor Market — White-Collar vs. Headline",
        "series": [
            ("JTSJOL", "Total Job Openings", "Monthly"),
            ("JTS540099000000000JOL", "Job Openings: Professional & Business Services", "Monthly"),
            ("JTS510000000000000JOL", "Job Openings: Information", "Monthly"),
            ("USPBS", "Employment: Professional & Business Services", "Monthly"),
            ("CES5000000001", "Employment: Information", "Monthly"),
            ("PAYEMS", "Total Nonfarm Payrolls", "Monthly"),
            ("ICSA", "Initial Jobless Claims", "Weekly"),
            ("UNRATE", "Unemployment Rate", "Monthly"),
            ("LNS12032194", "Involuntary Part-Time Workers", "Monthly"),
        ],
    },
    "consumer": {
        "title": "Consumer & Household Financial Stress",
        "series": [
            ("PSAVERT", "Personal Savings Rate", "Monthly"),
            ("DRCCLACBS", "Credit Card Delinquency Rate", "Quarterly"),
            ("REVOLSL", "Revolving Consumer Credit Outstanding", "Monthly"),
            ("TOTALSL", "Total Consumer Credit Outstanding", "Monthly"),
            ("DPCERAM1M225NBEA", "Real PCE (% Change)", "Monthly"),
            ("PCE", "Personal Consumption Expenditures", "Monthly"),
            ("UMCSENT", "U. of Michigan Consumer Sentiment", "Monthly"),
        ],
    },
    "housing": {
        "title": "Housing & Mortgage Market",
        "series": [
            ("DRSFRMACBS", "Mortgage Delinquency Rate (Single-Family)", "Quarterly"),
            ("CSUSHPINSA", "Case-Shiller National Home Price Index", "Monthly"),
            ("HOUST", "Housing Starts", "Monthly"),
            ("PERMIT", "Building Permits", "Monthly"),
            ("MORTGAGE30US", "30-Year Fixed Mortgage Rate", "Weekly"),
        ],
    },
    "macro": {
        "title": 'Macro & Productivity Divergence ("Ghost GDP")',
        "series": [
            ("GDPC1", "Real GDP", "Quarterly"),
            ("OPHNFB", "Nonfarm Business: Real Output Per Hour", "Quarterly"),
            ("W270RE1A156NBEA", "Labor Share of GDP", "Annual"),
            ("PRS85006173", "Unit Labor Costs", "Quarterly"),
            ("CP", "Corporate Profits After Tax", "Quarterly"),
            ("A261RL1Q225SBEA", "Real Gross Domestic Income", "Quarterly"),
        ],
    },
    "financial": {
        "title": "Financial System Stress",
        "series": [
            ("BAMLH0A0HYM2", "ICE BofA High Yield OAS", "Daily"),
            ("DRTSCILM", "Bank Lending Standards: C&I Loans (Medium/Large)", "Quarterly"),
            ("T10Y2Y", "10Y-2Y Treasury Spread", "Daily"),
            ("DGS10", "10-Year Treasury Yield", "Daily"),
            ("VIXCLS", "CBOE VIX", "Daily"),
        ],
    },
}

# Recession indicator series
RECESSION_SERIES = "USREC"

# ──────────────────────────────────────────────────────────────────────────────
# Signal Thresholds
# ──────────────────────────────────────────────────────────────────────────────

THRESHOLDS = {
    "labor": {
        # Yellow: white-collar openings declining YoY while total flat/up
        # Red: white-collar employment declining while total nonfarm flat/up
        "wc_openings_yoy_decline": -0.05,  # -5% YoY for white-collar openings
        "total_openings_floor": -0.02,  # total openings considered "flat" if > -2%
        "wc_employment_yoy_decline": 0.0,  # any YoY decline
        "total_employment_floor": 0.0,  # total nonfarm flat or up
    },
    "consumer": {
        # Yellow: credit card delinquencies rising QoQ for 2+ quarters
        # Red: delinquencies > 3.5% AND revolving credit rising
        "delinquency_red_threshold": 3.5,  # percentage
        "consecutive_qoq_rises": 2,
    },
    "housing": {
        # Yellow: mortgage delinquency increases QoQ for 2+ quarters
        # Red: exceeds 3%
        "delinquency_red_threshold": 3.0,
        "consecutive_qoq_rises": 2,
    },
    "macro": {
        # Yellow: labor share drops YoY
        # Red: productivity rising >2% YoY while unit labor costs falling
        "productivity_growth_red": 2.0,  # percentage
    },
    "financial": {
        # Yellow: HY OAS > 450bps
        # Red: HY OAS > 600bps
        "hy_oas_yellow": 450,
        "hy_oas_red": 600,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# AI Milestone Annotations
# ──────────────────────────────────────────────────────────────────────────────

AI_MILESTONES = [
    (date(2022, 11, 30), "ChatGPT Launch"),
    (date(2023, 3, 14), "GPT-4 Release"),
    (date(2024, 2, 15), "Sora / Gemini 1.5"),
    (date(2025, 1, 20), "DeepSeek R1"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Defaults
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_START_DATE = date(2020, 1, 1)
DATE_RANGE_OPTIONS = {
    "2020–Present": date(2020, 1, 1),
    "2015–Present": date(2015, 1, 1),
    "2010–Present": date(2010, 1, 1),
}

# Cache settings
CACHE_DB_PATH = "fred_cache.db"
CACHE_MAX_AGE_HOURS = 12

# Plotly dark theme colors
COLORS = {
    "background": "#0e1117",
    "card_bg": "#1a1d23",
    "text": "#e0e0e0",
    "muted_text": "#888888",
    "green": "#2ecc71",
    "yellow": "#f39c12",
    "red": "#e74c3c",
    "blue": "#3498db",
    "purple": "#9b59b6",
    "cyan": "#1abc9c",
    "orange": "#e67e22",
    "grid": "#2a2d35",
    "recession": "rgba(255, 255, 255, 0.07)",
    "annotation": "rgba(255, 255, 255, 0.3)",
}

# Chart line palette for multi-series overlays
LINE_PALETTE = [
    COLORS["blue"],
    COLORS["orange"],
    COLORS["purple"],
    COLORS["cyan"],
    COLORS["green"],
    COLORS["red"],
]
