"""
Data layer: FRED API integration with SQLite caching.

Provides functions to fetch, cache, and retrieve economic time series data.
"""

import os
import sqlite3
import pickle
from datetime import datetime, timedelta

import pandas as pd
from fredapi import Fred

from config import SECTIONS, RECESSION_SERIES, CACHE_DB_PATH, CACHE_MAX_AGE_HOURS


def get_fred_client() -> Fred | None:
    """Return a Fred client if API key is available, else None."""
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return None
    return Fred(api_key=api_key)


# ──────────────────────────────────────────────────────────────────────────────
# SQLite Cache
# ──────────────────────────────────────────────────────────────────────────────

def _init_cache_db():
    """Create the cache table if it doesn't exist."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS series_cache (
            series_id TEXT PRIMARY KEY,
            data BLOB NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _get_cached(series_id: str) -> pd.Series | None:
    """Return cached series if fresh enough, else None."""
    _init_cache_db()
    conn = sqlite3.connect(CACHE_DB_PATH)
    row = conn.execute(
        "SELECT data, fetched_at FROM series_cache WHERE series_id = ?",
        (series_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    fetched_at = datetime.fromisoformat(row[1])
    if datetime.now() - fetched_at > timedelta(hours=CACHE_MAX_AGE_HOURS):
        return None

    return pickle.loads(row[0])


def _set_cached(series_id: str, data: pd.Series):
    """Store a series in the cache."""
    _init_cache_db()
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute(
        """INSERT OR REPLACE INTO series_cache (series_id, data, fetched_at)
           VALUES (?, ?, ?)""",
        (series_id, pickle.dumps(data), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def clear_cache():
    """Delete all cached data (used by Refresh button)."""
    _init_cache_db()
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("DELETE FROM series_cache")
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Data Fetching
# ──────────────────────────────────────────────────────────────────────────────

def fetch_series(fred: Fred, series_id: str, force_refresh: bool = False) -> pd.Series:
    """
    Fetch a single FRED series, using cache unless force_refresh is True.
    Returns a pandas Series indexed by date.
    Raises an exception if the series cannot be fetched.
    """
    if not force_refresh:
        cached = _get_cached(series_id)
        if cached is not None:
            return cached

    data = fred.get_series(series_id)
    data = data.dropna()
    data.index = pd.to_datetime(data.index)
    data.name = series_id

    _set_cached(series_id, data)
    return data


def fetch_all_data(force_refresh: bool = False) -> dict[str, dict[str, pd.Series | str]]:
    """
    Fetch all configured series across all sections.

    Returns a nested dict:
        {section_key: {series_id: pd.Series or error_string}}
    """
    fred = get_fred_client()
    if fred is None:
        return {}

    results: dict[str, dict[str, pd.Series | str]] = {}

    # Collect all unique series IDs (some may appear in multiple sections)
    all_series: list[tuple[str, str]] = []  # (section_key, series_id)
    for section_key, section in SECTIONS.items():
        results[section_key] = {}
        for series_id, _name, _freq in section["series"]:
            all_series.append((section_key, series_id))

    # Also fetch recession indicator
    all_series.append(("_meta", RECESSION_SERIES))
    results["_meta"] = {}

    for section_key, series_id in all_series:
        try:
            data = fetch_series(fred, series_id, force_refresh=force_refresh)
            results[section_key][series_id] = data
        except Exception as e:
            results[section_key][series_id] = f"Error fetching {series_id}: {e}"

    return results


def get_series_name(series_id: str) -> str:
    """Look up the display name for a series ID."""
    for section in SECTIONS.values():
        for sid, name, _freq in section["series"]:
            if sid == series_id:
                return name
    if series_id == RECESSION_SERIES:
        return "NBER Recession Indicator"
    return series_id


def build_summary_table(data: dict[str, dict[str, pd.Series | str]]) -> pd.DataFrame:
    """
    Build a summary table with latest value, 3m / 6m / YoY changes, and direction.
    """
    rows = []
    for section_key, section in SECTIONS.items():
        for series_id, name, freq in section["series"]:
            section_data = data.get(section_key, {})
            series = section_data.get(series_id)
            if series is None or isinstance(series, str):
                rows.append({
                    "Section": section["title"],
                    "Series": name,
                    "Series ID": series_id,
                    "Frequency": freq,
                    "Latest Date": "N/A",
                    "Latest Value": "N/A",
                    "3M Change": "N/A",
                    "6M Change": "N/A",
                    "YoY Change": "N/A",
                    "Direction": "—",
                })
                continue

            latest_val = series.iloc[-1]
            latest_date = series.index[-1]

            def _pct_change(months: int) -> tuple[str, str]:
                target = latest_date - pd.DateOffset(months=months)
                past = series[series.index <= target]
                if past.empty:
                    return "N/A", "—"
                past_val = past.iloc[-1]
                if past_val == 0:
                    return "N/A", "—"
                change = (latest_val - past_val) / abs(past_val) * 100
                direction = "↑" if change > 0.5 else ("↓" if change < -0.5 else "→")
                return f"{change:+.1f}%", direction

            c3, d3 = _pct_change(3)
            c6, d6 = _pct_change(6)
            c12, d12 = _pct_change(12)

            rows.append({
                "Section": section["title"],
                "Series": name,
                "Series ID": series_id,
                "Frequency": freq,
                "Latest Date": latest_date.strftime("%Y-%m-%d"),
                "Latest Value": f"{latest_val:,.2f}" if abs(latest_val) >= 1 else f"{latest_val:.4f}",
                "3M Change": c3,
                "6M Change": c6,
                "YoY Change": c12,
                "Direction": d12,
            })

    return pd.DataFrame(rows)


def build_export_dataframe(data: dict[str, dict[str, pd.Series | str]]) -> pd.DataFrame:
    """Combine all series into a single wide DataFrame for CSV export."""
    frames = {}
    for section_key, section in SECTIONS.items():
        section_data = data.get(section_key, {})
        for series_id, name, _freq in section["series"]:
            series = section_data.get(series_id)
            if series is not None and not isinstance(series, str):
                frames[f"{series_id} ({name})"] = series

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df.index.name = "Date"
    df = df.sort_index()
    return df
