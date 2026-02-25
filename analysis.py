"""
AI Market Analysis Engine

Uses Claude Sonnet 4 to generate intelligent, persistent market analysis.
Features:
  - Memory: reads its own previous analysis for continuity
  - Fingerprinting: only regenerates when underlying data changes
  - News context: fetches recent headlines to enrich the analysis
  - Change tracking: highlights what changed and what it means
"""

import os
import sqlite3
import hashlib
from datetime import datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import pandas as pd
import requests

from config import SECTIONS

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

ANALYSIS_DB = "analysis_memory.db"

SYSTEM_PROMPT = """You are a senior macroeconomic strategist writing a private briefing for an investor who tracks the "AI displacement thesis" — the idea that artificial intelligence is beginning to displace white-collar workers in ways that standard economic indicators obscure.

YOUR ANALYTICAL FRAMEWORK:
You monitor five channels of evidence, in order of importance:

1. LABOR DIVERGENCE (most important early signal)
   White-collar job openings (Professional & Business Services, Information sector) declining while total nonfarm employment stays flat or grows. This divergence is the clearest sign that AI is replacing cognitive work while the headline jobs number masks it.

2. GHOST GDP
   GDP and productivity rising while labor's share of income falls and unit labor costs decline. This "jobless growth" pattern means output grows without proportional human contribution — the macro fingerprint of automation.

3. CONSUMER & HOUSEHOLD STRESS
   Rising credit card delinquencies and revolving credit growth signal that displaced workers are borrowing to maintain spending. This is a lagging but confirming indicator.

4. HOUSING WEAKNESS
   Mortgage delinquency increases in a strong housing market suggest income disruption among professionals, not a housing bubble.

5. FINANCIAL STRESS
   Widening high-yield spreads or elevated VIX that equity markets ignore suggest credit markets are pricing in structural risk.

YOUR OUTPUT FORMAT:
Write a concise investor briefing (400-600 words) using markdown:

- Start with a single bold sentence: your overall verdict
- If this is an UPDATE (previous analysis provided), begin with a "### What Changed" section that explains exactly which data points moved, in which direction, and what it means for the thesis. Be specific — cite numbers.
- Then provide "### Assessment" with your current read across the five channels
- End with "### Watch These in the Data Below" — 3 to 5 specific, actionable bullet points telling the reader exactly which charts and metrics to scrutinize, and what patterns to look for

STYLE RULES:
- Be direct and opinionated. This is analysis, not a summary.
- Use **bold** for every key number, metric name, or conclusion the reader must not miss
- Do not hedge excessively. State your view and the evidence for it.
- If data is mixed or inconclusive, say so clearly — ambiguity is information too.
- Reference the news headlines ONLY when they add genuine insight. Do not summarize news for its own sake.
- Maintain analytical continuity with previous analyses. Your views should evolve incrementally as data changes, not reset each time."""


# ──────────────────────────────────────────────────────────────────────────────
# SQLite Memory System
# ──────────────────────────────────────────────────────────────────────────────

def _init_db():
    """Create the analysis memory table if it doesn't exist."""
    conn = sqlite3.connect(ANALYSIS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_fingerprint TEXT NOT NULL,
            analysis_md TEXT NOT NULL,
            data_summary TEXT,
            news_context TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_data_fingerprint(data: dict) -> str:
    """Hash the latest date + value of every series to detect new data releases."""
    parts = []
    for section_key in sorted(SECTIONS.keys()):
        section_data = data.get(section_key, {})
        for series_id, _, _ in SECTIONS[section_key]["series"]:
            s = section_data.get(series_id)
            if isinstance(s, pd.Series) and len(s) > 0:
                parts.append(f"{series_id}:{s.index[-1].isoformat()}:{s.iloc[-1]:.6f}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def get_latest_analysis() -> dict | None:
    """Retrieve the most recent analysis from the memory database."""
    _init_db()
    conn = sqlite3.connect(ANALYSIS_DB)
    row = conn.execute(
        "SELECT data_fingerprint, analysis_md, data_summary, news_context, created_at "
        "FROM analyses ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "fingerprint": row[0],
        "analysis": row[1],
        "data_summary": row[2],
        "news": row[3],
        "created_at": row[4],
    }


def save_analysis(fingerprint: str, analysis: str, data_summary: str, news: str):
    """Persist analysis to the memory database."""
    _init_db()
    conn = sqlite3.connect(ANALYSIS_DB)
    conn.execute(
        "INSERT INTO analyses (data_fingerprint, analysis_md, data_summary, news_context, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (fingerprint, analysis, data_summary, news, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Data Summary Builder
# ──────────────────────────────────────────────────────────────────────────────

def build_data_summary(data: dict, signals: dict, assessment: tuple) -> str:
    """Convert the current dashboard data into a text summary for the AI."""
    lines = [f"OVERALL SIGNAL STATUS: {assessment[0]} — {assessment[1]}", ""]

    for section_key, section in SECTIONS.items():
        status, explanation = signals.get(section_key, ("green", ""))
        lines.append(f"### {section['title']} [Signal: {status.upper()}]")
        lines.append(f"{explanation}")

        section_data = data.get(section_key, {})
        for series_id, name, freq in section["series"]:
            s = section_data.get(series_id)
            if isinstance(s, pd.Series) and len(s) > 0:
                latest_val = s.iloc[-1]
                latest_date = s.index[-1].strftime("%Y-%m-%d")

                # Compute YoY change
                target = s.index[-1] - pd.DateOffset(months=12)
                past = s[s.index <= target]
                if not past.empty and past.iloc[-1] != 0:
                    yoy = (latest_val - past.iloc[-1]) / abs(past.iloc[-1]) * 100
                    lines.append(
                        f"  {name}: {latest_val:,.2f} (as of {latest_date}, YoY: {yoy:+.1f}%)"
                    )
                else:
                    lines.append(f"  {name}: {latest_val:,.2f} (as of {latest_date})")
        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# News Fetching
# ──────────────────────────────────────────────────────────────────────────────

def fetch_recent_news() -> str:
    """Fetch recent financial/AI news headlines from Google News RSS."""
    queries = [
        "AI artificial intelligence white collar jobs displacement",
        "US labor market employment layoffs technology sector",
        "economy GDP productivity consumer spending",
    ]

    all_headlines = []

    for query in queries:
        try:
            url = (
                f"https://news.google.com/rss/search?"
                f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
            )
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                root = ElementTree.fromstring(resp.content)
                items = root.findall(".//item")[:5]
                for item in items:
                    title_el = item.find("title")
                    pub_date_el = item.find("pubDate")
                    if title_el is not None and title_el.text:
                        date_str = ""
                        if pub_date_el is not None and pub_date_el.text:
                            date_str = pub_date_el.text[:16]
                        all_headlines.append(f"- {title_el.text} ({date_str})")
        except Exception:
            continue

    if not all_headlines:
        return "(Could not fetch recent news — analysis will proceed with data only.)"

    # Deduplicate
    seen = set()
    unique = []
    for h in all_headlines:
        if h not in seen:
            seen.add(h)
            unique.append(h)

    return "\n".join(unique[:15])


# ──────────────────────────────────────────────────────────────────────────────
# Main Analysis Generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_analysis(data: dict, signals: dict, assessment: tuple) -> dict:
    """
    Generate AI analysis or return cached version if data hasn't changed.

    Returns:
        {
            "analysis": str | None,     # Markdown text
            "is_cached": bool,          # True if returned from memory
            "created_at": str | None,   # ISO timestamp
            "error": str | None,        # Error message if failed
        }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {
            "analysis": None,
            "is_cached": False,
            "created_at": None,
            "error": "no_api_key",
        }

    fingerprint = get_data_fingerprint(data)
    previous = get_latest_analysis()

    # ── Cache hit: data unchanged → return stored analysis ──
    if previous and previous["fingerprint"] == fingerprint:
        return {
            "analysis": previous["analysis"],
            "is_cached": True,
            "created_at": previous["created_at"],
            "error": None,
        }

    # ── Cache miss: new data detected → generate fresh analysis ──
    data_summary = build_data_summary(data, signals, assessment)
    news_context = fetch_recent_news()

    # Build the user message
    parts = [
        "## Current Economic Data\n",
        data_summary,
        "\n## Recent News Headlines\n",
        news_context,
    ]

    if previous:
        parts.append("\n\n## Your Previous Analysis\n")
        parts.append(f"(Written on {previous['created_at'][:10]})\n\n")
        parts.append(previous["analysis"])
        parts.append(
            "\n\n---\n"
            "DATA HAS BEEN UPDATED since your last analysis. "
            "Start with a '### What Changed' section. Be specific about which numbers moved "
            "and in which direction. Then provide your updated assessment. "
            "Your views should evolve with the data, not reset."
        )
    else:
        parts.append(
            "\n\nThis is your FIRST analysis. No previous analysis exists. "
            "Provide a comprehensive initial assessment of the AI displacement thesis "
            "based on the current data and news."
        )

    user_message = "\n".join(parts)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        analysis_text = response.content[0].text

        save_analysis(fingerprint, analysis_text, data_summary, news_context)

        return {
            "analysis": analysis_text,
            "is_cached": False,
            "created_at": datetime.now().isoformat(),
            "error": None,
        }

    except Exception as e:
        # On failure, return previous analysis if available
        if previous:
            return {
                "analysis": previous["analysis"],
                "is_cached": True,
                "created_at": previous["created_at"],
                "error": f"API call failed: {e}. Showing previous analysis.",
            }
        return {
            "analysis": None,
            "is_cached": False,
            "created_at": None,
            "error": f"Failed to generate analysis: {e}",
        }
