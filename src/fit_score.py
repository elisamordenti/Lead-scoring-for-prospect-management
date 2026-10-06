"""
Rule-based fit score (0-100) for ONE lead, with a breakdown of where the points came from.
All the numbers come from config.py.
"""

import config
from classify import has_keyword


def is_personal_email(email):
    domain = str(email).split("@")[-1].lower()
    return domain in config.PERSONAL_EMAIL_DOMAINS


def role_tier(role):
    """'technical', 'business' or 'other'. Technical is checked first."""
    if has_keyword(role, config.TECHNICAL_ROLE_KEYWORDS):
        return "technical"
    if has_keyword(role, config.BUSINESS_ROLE_KEYWORDS):
        return "business"
    return "other"


def fit_score(lead, industry, category):
    """
    lead: one row of the form (first_name, email, role, company_size, tried_tabpfn, use_case...)
    industry: from the enrichment table, or "unknown"
    category: use case category from classify_use_case()
    Returns (score, breakdown) where breakdown is a dict of points per signal.
    """
    strong_use_case = category in config.TARGET_CATEGORIES

    # Small companies only get size points if the use case is strong.
    size = lead["company_size"]
    size_points = config.SIZE_POINTS.get(size, 0)
    if size in config.SMALL_SIZES and not strong_use_case:
        size_points = 0

    role_points = {
        "technical": config.ROLE_POINTS_TECHNICAL,
        "business": config.ROLE_POINTS_BUSINESS,
        "other": config.ROLE_POINTS_OTHER,
    }[role_tier(lead["role"])]

    breakdown = {
        "tried": config.TRIED_TABPFN_POINTS.get(lead["tried_tabpfn"], 0),
        "industry": config.INDUSTRY_POINTS.get(industry, config.OTHER_INDUSTRY_POINTS),
        "size": size_points,
        "role": role_points,
        "use_case": config.USE_CASE_POINTS_TARGET if strong_use_case else config.USE_CASE_POINTS_OTHER,
        "personal_email": config.PERSONAL_EMAIL_PENALTY if is_personal_email(lead["email"]) else 0,
    }
    score = max(0, sum(breakdown.values()))  # floor at 0
    return score, breakdown


def breakdown_text(breakdown, score):
    """{'tried': 10, 'industry': 15, ...} -> 'tried 10 + industry 15 + ... = 85' (zero items left out)."""
    text = ""
    for name, points in breakdown.items():
        if points == 0:
            continue
        sign = "-" if points < 0 else "+"
        text += f" {sign} {name.replace('_', ' ')} {abs(points)}"
    return text.removeprefix(" + ").strip() + f" = {score}"
