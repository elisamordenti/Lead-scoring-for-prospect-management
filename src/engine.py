"""
Runs the one-lead-at-a-time steps in order: classify -> fit score -> route -> region.
Used by main.py (all leads) and tests/run_test_cases.py (the 7 test leads).
"""

import pandas as pd

import config
from classify import classify_use_case, keyword_flags
from fit_score import breakdown_text, fit_score
from routing import region_team, route_lead


def evaluate_lead(lead, industry, country):
    """
    lead: one row of the form (dict or pandas row)
    industry, country: from the enrichment table, or None if the company is missing there
    """
    enrichment_missing = pd.isna(industry) or industry is None
    industry = "unknown" if enrichment_missing else industry

    use_case = lead.get("use_case")  # the field may be missing from some versions of the form
    category = classify_use_case(use_case)
    flags = keyword_flags(use_case)
    if enrichment_missing:
        flags.append("enrichment missing")

    score, breakdown = fit_score(lead, industry, category)
    route, note = route_lead(lead, score, category)
    score_text = breakdown_text(breakdown, score)

    # Students and academics are routed before the score matters, so a number would only mislead.
    if note == "Student" or route == config.ROUTE_RESEARCH:
        not_buyer = "student" if note == "Student" else "academic"
        score, score_text = None, f"not scored ({not_buyer})"

    return {
        "industry": industry,
        "country": None if enrichment_missing else country,
        "team": region_team(None if enrichment_missing else country),
        "use_case_category": category,
        "fit_score": score,
        "score_breakdown": score_text,
        "route": route,
        "reason": note,
        "flags": ", ".join(flags),
    }
