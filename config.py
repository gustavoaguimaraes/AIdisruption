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
        "title": "Labor Market",
        "subtitle": "White-collar vs. headline employment divergence",
        "icon": "briefcase",
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
        "title": "Consumer Stress",
        "subtitle": "Household financial health and credit conditions",
        "icon": "credit-card",
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
        "title": "Housing Market",
        "subtitle": "Mortgage health and home price dynamics",
        "icon": "home",
        "series": [
            ("DRSFRMACBS", "Mortgage Delinquency Rate (Single-Family)", "Quarterly"),
            ("CSUSHPINSA", "Case-Shiller National Home Price Index", "Monthly"),
            ("HOUST", "Housing Starts", "Monthly"),
            ("PERMIT", "Building Permits", "Monthly"),
            ("MORTGAGE30US", "30-Year Fixed Mortgage Rate", "Weekly"),
        ],
    },
    "macro": {
        "title": "Ghost GDP",
        "subtitle": "Productivity vs. labor share divergence",
        "icon": "trending-up",
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
        "title": "Financial Stress",
        "subtitle": "Credit spreads and market volatility",
        "icon": "activity",
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
        "wc_openings_yoy_decline": -0.05,
        "total_openings_floor": -0.02,
        "wc_employment_yoy_decline": 0.0,
        "total_employment_floor": 0.0,
    },
    "consumer": {
        "delinquency_red_threshold": 3.5,
        "consecutive_qoq_rises": 2,
    },
    "housing": {
        "delinquency_red_threshold": 3.0,
        "consecutive_qoq_rises": 2,
    },
    "macro": {
        "productivity_growth_red": 2.0,
    },
    "financial": {
        "hy_oas_yellow": 450,
        "hy_oas_red": 600,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# AI Milestone Annotations
# ──────────────────────────────────────────────────────────────────────────────

AI_MILESTONES = [
    (date(2022, 11, 30), "ChatGPT"),
    (date(2023, 3, 14), "GPT-4"),
    (date(2024, 2, 15), "Sora / Gemini 1.5"),
    (date(2025, 1, 20), "DeepSeek R1"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Defaults
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_START_DATE = date(2020, 1, 1)
DATE_RANGE_OPTIONS = {
    "2020 - Present": date(2020, 1, 1),
    "2015 - Present": date(2015, 1, 1),
    "2010 - Present": date(2010, 1, 1),
}

# Cache settings
CACHE_DB_PATH = "fred_cache.db"
CACHE_MAX_AGE_HOURS = 12

# ──────────────────────────────────────────────────────────────────────────────
# Apple-inspired light theme palette
# ──────────────────────────────────────────────────────────────────────────────

COLORS = {
    # Backgrounds
    "background": "#f5f5f7",
    "card_bg": "#ffffff",
    "sidebar_bg": "#fbfbfd",

    # Text
    "text": "#1d1d1f",
    "text_secondary": "#6e6e73",
    "muted_text": "#86868b",

    # Signals — Apple system colors (refined)
    "green": "#34c759",
    "yellow": "#ff9f0a",
    "red": "#ff3b30",
    "orange": "#ff9f0a",

    # Chart palette — refined and harmonious
    "blue": "#007aff",
    "indigo": "#5856d6",
    "purple": "#af52de",
    "teal": "#5ac8fa",
    "cyan": "#32ade6",
    "mint": "#00c7be",

    # Chart elements
    "grid": "#f0f0f2",
    "grid_line": "rgba(0, 0, 0, 0.06)",
    "recession": "rgba(0, 0, 0, 0.04)",
    "annotation": "rgba(0, 0, 0, 0.20)",

    # UI
    "border": "rgba(0, 0, 0, 0.08)",
    "divider": "#d2d2d7",
    "hover": "rgba(0, 0, 0, 0.03)",
}

# Chart line palette for multi-series overlays
LINE_PALETTE = [
    COLORS["blue"],
    COLORS["orange"],
    COLORS["indigo"],
    COLORS["teal"],
    COLORS["green"],
    COLORS["red"],
]
