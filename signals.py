"""
Signal logic engine.

Evaluates each dashboard section and returns a status:
  "green", "yellow", or "red"
along with a short explanation string.
"""

import pandas as pd

from config import THRESHOLDS


def _safe_yoy(series: pd.Series) -> float | None:
    """Return the most recent year-over-year percent change, or None."""
    if series is None or isinstance(series, str) or len(series) < 13:
        return None
    latest = series.iloc[-1]
    target_date = series.index[-1] - pd.DateOffset(months=12)
    past = series[series.index <= target_date]
    if past.empty or past.iloc[-1] == 0:
        return None
    return (latest - past.iloc[-1]) / abs(past.iloc[-1]) * 100


def _safe_qoq_series(series: pd.Series, n_quarters: int = 4) -> list[float]:
    """Return the last n quarter-over-quarter changes as a list."""
    if series is None or isinstance(series, str) or len(series) < n_quarters + 1:
        return []
    changes = []
    for i in range(-n_quarters, 0):
        if i - 1 < -len(series):
            continue
        prev = series.iloc[i - 1]
        cur = series.iloc[i]
        if prev == 0:
            changes.append(0.0)
        else:
            changes.append((cur - prev) / abs(prev) * 100)
    return changes


def _get(data: dict, series_id: str) -> pd.Series | None:
    """Safely get a series from section data."""
    val = data.get(series_id)
    if val is None or isinstance(val, str):
        return None
    return val


def evaluate_labor(section_data: dict) -> tuple[str, str]:
    """
    Section 1: Labor Market
    Yellow: white-collar openings declining YoY while total flat/up
    Red: white-collar employment declining while total nonfarm flat/up
    """
    t = THRESHOLDS["labor"]

    total_openings = _get(section_data, "JTSJOL")
    pbs_openings = _get(section_data, "JTS540099000000000JOL")
    info_openings = _get(section_data, "JTS510000000000000JOL")
    total_employment = _get(section_data, "PAYEMS")
    pbs_employment = _get(section_data, "USPBS")
    info_employment = _get(section_data, "CES5000000001")

    # Check Red: white-collar employment declining, total nonfarm flat/up
    pbs_emp_yoy = _safe_yoy(pbs_employment)
    info_emp_yoy = _safe_yoy(info_employment)
    total_emp_yoy = _safe_yoy(total_employment)

    if (total_emp_yoy is not None and pbs_emp_yoy is not None and info_emp_yoy is not None):
        wc_declining = pbs_emp_yoy < t["wc_employment_yoy_decline"] or info_emp_yoy < t["wc_employment_yoy_decline"]
        total_ok = total_emp_yoy >= t["total_employment_floor"]
        if wc_declining and total_ok:
            return "red", (
                f"White-collar employment declining (PBS: {pbs_emp_yoy:+.1f}%, "
                f"Info: {info_emp_yoy:+.1f}%) while total nonfarm is {total_emp_yoy:+.1f}%"
            )

    # Check Yellow: white-collar openings declining YoY, total flat/up
    total_open_yoy = _safe_yoy(total_openings)
    pbs_open_yoy = _safe_yoy(pbs_openings)
    info_open_yoy = _safe_yoy(info_openings)

    if (total_open_yoy is not None and pbs_open_yoy is not None):
        wc_open_declining = (
            pbs_open_yoy < t["wc_openings_yoy_decline"]
            or (info_open_yoy is not None and info_open_yoy < t["wc_openings_yoy_decline"])
        )
        total_open_ok = total_open_yoy > t["total_openings_floor"]
        if wc_open_declining and total_open_ok:
            return "yellow", (
                f"White-collar openings declining (PBS: {pbs_open_yoy:+.1f}%) "
                f"while total openings are {total_open_yoy:+.1f}% YoY"
            )

    return "green", "No divergence detected between headline and white-collar labor metrics"


def evaluate_consumer(section_data: dict) -> tuple[str, str]:
    """
    Section 2: Consumer & Household Financial Stress
    Yellow: credit card delinquencies rising QoQ for 2+ quarters
    Red: delinquencies > 3.5% AND revolving credit rising
    """
    t = THRESHOLDS["consumer"]

    delinquency = _get(section_data, "DRCCLACBS")
    revolving = _get(section_data, "REVOLSL")

    # Check Red
    if delinquency is not None and revolving is not None:
        latest_delinq = delinquency.iloc[-1]
        revolving_yoy = _safe_yoy(revolving)
        if latest_delinq > t["delinquency_red_threshold"] and revolving_yoy is not None and revolving_yoy > 0:
            return "red", (
                f"Credit card delinquency at {latest_delinq:.2f}% (>{t['delinquency_red_threshold']}%) "
                f"and revolving credit growing {revolving_yoy:+.1f}% YoY"
            )

    # Check Yellow
    if delinquency is not None and len(delinquency) >= 3:
        qoq = _safe_qoq_series(delinquency, 4)
        consecutive_rises = 0
        for change in reversed(qoq):
            if change > 0:
                consecutive_rises += 1
            else:
                break
        if consecutive_rises >= t["consecutive_qoq_rises"]:
            return "yellow", (
                f"Credit card delinquencies rising for {consecutive_rises} consecutive quarters"
            )

    return "green", "Consumer credit metrics within normal ranges"


def evaluate_housing(section_data: dict) -> tuple[str, str]:
    """
    Section 3: Housing & Mortgage Market
    Yellow: mortgage delinquency increases QoQ for 2+ quarters
    Red: exceeds 3%
    """
    t = THRESHOLDS["housing"]

    delinquency = _get(section_data, "DRSFRMACBS")

    if delinquency is not None and len(delinquency) >= 2:
        latest = delinquency.iloc[-1]

        # Check Red
        if latest > t["delinquency_red_threshold"]:
            return "red", f"Mortgage delinquency rate at {latest:.2f}% (>{t['delinquency_red_threshold']}%)"

        # Check Yellow
        qoq = _safe_qoq_series(delinquency, 4)
        consecutive_rises = 0
        for change in reversed(qoq):
            if change > 0:
                consecutive_rises += 1
            else:
                break
        if consecutive_rises >= t["consecutive_qoq_rises"]:
            return "yellow", (
                f"Mortgage delinquency rising for {consecutive_rises} consecutive quarters "
                f"(current: {latest:.2f}%)"
            )

    return "green", "Housing and mortgage metrics within normal ranges"


def evaluate_macro(section_data: dict) -> tuple[str, str]:
    """
    Section 4: Macro & Productivity Divergence ("Ghost GDP")
    Yellow: labor share drops YoY
    Red: productivity rising >2% YoY while unit labor costs falling
    """
    t = THRESHOLDS["macro"]

    productivity = _get(section_data, "OPHNFB")
    ulc = _get(section_data, "PRS85006173")
    labor_share = _get(section_data, "W270RE1A156NBEA")

    # Check Red
    prod_yoy = _safe_yoy(productivity)
    ulc_yoy = _safe_yoy(ulc)
    if prod_yoy is not None and ulc_yoy is not None:
        if prod_yoy > t["productivity_growth_red"] and ulc_yoy < 0:
            return "red", (
                f"Productivity surging ({prod_yoy:+.1f}% YoY) while unit labor costs falling "
                f"({ulc_yoy:+.1f}% YoY) — classic Ghost GDP pattern"
            )

    # Check Yellow
    if labor_share is not None and len(labor_share) >= 2:
        ls_yoy = _safe_yoy(labor_share)
        if ls_yoy is not None and ls_yoy < 0:
            return "yellow", f"Labor share of GDP declining ({ls_yoy:+.1f}% YoY)"

    return "green", "No significant macro divergence detected"


def evaluate_financial(section_data: dict) -> tuple[str, str]:
    """
    Section 5: Financial System Stress
    Yellow: HY OAS > 450bps
    Red: HY OAS > 600bps
    """
    t = THRESHOLDS["financial"]

    hy_oas = _get(section_data, "BAMLH0A0HYM2")

    if hy_oas is not None and len(hy_oas) > 0:
        latest = hy_oas.iloc[-1]
        if latest > t["hy_oas_red"]:
            return "red", f"High yield OAS at {latest:.0f}bps (>{t['hy_oas_red']}bps)"
        if latest > t["hy_oas_yellow"]:
            return "yellow", f"High yield OAS elevated at {latest:.0f}bps (>{t['hy_oas_yellow']}bps)"

    return "green", "Financial stress indicators within normal ranges"


# Dispatcher
EVALUATORS = {
    "labor": evaluate_labor,
    "consumer": evaluate_consumer,
    "housing": evaluate_housing,
    "macro": evaluate_macro,
    "financial": evaluate_financial,
}


def evaluate_all(data: dict[str, dict]) -> dict[str, tuple[str, str]]:
    """
    Evaluate all sections and return {section_key: (status, explanation)}.
    """
    results = {}
    for key, func in EVALUATORS.items():
        section_data = data.get(key, {})
        try:
            results[key] = func(section_data)
        except Exception as e:
            results[key] = ("green", f"Could not evaluate: {e}")
    return results


def composite_assessment(signals: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """
    Return an overall assessment based on the section signals.
    """
    statuses = [s for s, _ in signals.values()]
    red_count = statuses.count("red")
    yellow_count = statuses.count("yellow")

    if red_count >= 3:
        return "Active Crisis", "Multiple sectors showing active displacement signals"
    if red_count >= 1:
        return "Elevated Risk", f"{red_count} sector(s) at red, {yellow_count} at yellow"
    if yellow_count >= 2:
        return "Early Warning", f"{yellow_count} sectors showing early warning signs"
    if yellow_count >= 1:
        return "Early Warning", "Some early warning signs emerging"
    return "No Signal", "All sectors within historical norms"
