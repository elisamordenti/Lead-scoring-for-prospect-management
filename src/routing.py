"""
Routing for ONE lead: 8 rules checked in order, first match wins. Plus the region tag.
All keywords and thresholds come from config.py.
"""

import config
from classify import has_keyword
from fit_score import is_personal_email


def is_student(role):
    return has_keyword(role, config.STUDENT_KEYWORDS)


def is_academic(email, role):
    domain = str(email).split("@")[-1].lower()
    academic_domain = any(pattern in domain for pattern in config.ACADEMIC_EMAIL_PATTERNS)
    return academic_domain or has_keyword(role, config.ACADEMIC_ROLE_KEYWORDS)


def is_consultancy(role, company):
    return has_keyword(role, config.CONSULTANCY_KEYWORDS) or has_keyword(company, config.CONSULTANCY_KEYWORDS)


def route_lead(lead, score, category):
    """Returns (route, note). The note explains which rule fired."""
    strong_use_case = category in config.TARGET_CATEGORIES
    company_email = not is_personal_email(lead["email"])
    already_using = lead["tried_tabpfn"] == config.ALREADY_USING
    large_company = lead["company_size"] in config.LARGE_SIZES

    # 1. Students
    if is_student(lead["role"]):
        return config.ROUTE_NURTURE, "Student"
    # 2. Academics: free users, not buyers
    if is_academic(lead["email"], lead["role"]):
        return config.ROUTE_RESEARCH, "Academic: free user, not a buyer"
    # 3. Consultancies with a target use case: client work needs a commercial license
    if is_consultancy(lead["role"], lead["company_name"]) and strong_use_case:
        return config.ROUTE_ACCOUNT_EXECUTIVE, "Consultancy: client work requires a commercial license"
    # 4 + 5. Already using TabPFN for a real use case, with a company email
    if already_using and strong_use_case and company_email:
        if large_company:
            return config.ROUTE_ACCOUNT_EXECUTIVE, "Already using TabPFN at a large company: needs SE support"
        return config.ROUTE_SOLUTIONS_ENGINEER, "Already using TabPFN at a smaller company"
    # 6-8. Fit score thresholds
    if score >= config.AE_MIN_FIT_SCORE:
        return config.ROUTE_ACCOUNT_EXECUTIVE, f"High fit score ({score})"
    if score < config.NURTURE_BELOW_FIT_SCORE:
        return config.ROUTE_NURTURE, f"Low fit score ({score})"
    return config.ROUTE_REVIEW, f"Medium fit score ({score})"


def region_team(country):
    """'Germany' -> 'Berlin team', 'United States' -> 'NYC team', missing -> 'Unassigned'."""
    region = config.COUNTRY_REGION.get(country)
    return config.REGION_TEAM.get(region, config.UNASSIGNED_TEAM)
