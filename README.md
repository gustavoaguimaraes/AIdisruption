# AI Displacement Leading Indicators Dashboard

A Streamlit dashboard that tracks leading indicators for the "AI intelligence displacement" thesis — the risk that AI replaces white-collar workers faster than new jobs are created, triggering a consumption-led recession.

The dashboard monitors divergences between headline economic data and white-collar-specific indicators across 5 sectors using data from the Federal Reserve Economic Data (FRED) API.

## Dashboard Sections

| Section | Key Signal |
|---|---|
| **Labor Market** | White-collar job openings/employment declining while headline metrics hold steady |
| **Consumer Stress** | Rising credit card delinquencies alongside growing revolving credit |
| **Housing** | Mortgage delinquency rate rising above historical norms |
| **Ghost GDP** | GDP and productivity surging while labor share collapses |
| **Financial Stress** | High yield credit spreads widening beyond 450–600bps |

Each section shows a signal badge (Green / Yellow / Red) with an overall thesis tracker at the top.

## Setup

### 1. Get a FRED API Key

Register for a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Your API Key

**Option A** — Environment variable:
```bash
export FRED_API_KEY=your_key_here
```

**Option B** — `.env` file:
```bash
cp .env.example .env
# Edit .env and add your key
```

**Option C** — Streamlit secrets:
```bash
mkdir -p .streamlit
echo 'FRED_API_KEY = "your_key_here"' > .streamlit/secrets.toml
```

### 4. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

## Features

- **5 section composite charts** with Plotly — divergence overlays, dual-axis plots, indexed comparisons
- **Signal status badges** — automated Green/Yellow/Red based on configurable thresholds
- **Overall thesis tracker** — composite assessment from "No Signal" to "Active Crisis"
- **NBER recession shading** on all charts
- **AI milestone annotations** — ChatGPT launch, GPT-4, Sora/Gemini 1.5, DeepSeek R1
- **Date range selector** — 2020, 2015, or 2010 to present
- **YoY change summary table** — latest value, 3M/6M/YoY changes, direction arrows
- **CSV export** — download all data series
- **SQLite caching** — avoids redundant API calls; refresh with the sidebar button
- **Dark theme** — information-dense monitoring layout

## Configuration

All FRED series IDs, signal thresholds, and dashboard settings are in `config.py`. Key thresholds to tune:

```python
THRESHOLDS = {
    "labor": {"wc_openings_yoy_decline": -0.05, ...},
    "consumer": {"delinquency_red_threshold": 3.5, ...},
    "housing": {"delinquency_red_threshold": 3.0, ...},
    "macro": {"productivity_growth_red": 2.0, ...},
    "financial": {"hy_oas_yellow": 450, "hy_oas_red": 600},
}
```

## Project Structure

```
├── app.py           # Streamlit dashboard (main entry point)
├── config.py        # All series IDs, thresholds, colors, settings
├── data.py          # FRED API integration + SQLite caching
├── signals.py       # Signal evaluation logic for all 5 sections
├── charts.py        # Plotly chart generation with dark theme
├── requirements.txt
├── .env.example
└── README.md
```

## Data Sources

All data is sourced from [FRED](https://fred.stlouisfed.org/) (Federal Reserve Economic Data), which aggregates data from the Bureau of Labor Statistics, Bureau of Economic Analysis, Census Bureau, and other federal agencies.
