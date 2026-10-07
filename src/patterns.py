"""
Looks ACROSS leads to find patterns:
- hot accounts: 3+ different people from the same company within 14 days (+ "Buying group forming")
- hot segments: same industry + same use case category across many different companies

Two clean-ups make this robust to messy form data:
- a company is identified by its EMAIL DOMAIN when the email is a company email,
  so "Altmark Insurance AG" / "Altmark Insurance" / "ALTMARK Insurance AG" count as one account
- people are counted by unique email, so one person submitting the form 3 times is still 1 person
"""

import re
from datetime import timedelta

import pandas as pd

import config
from classify import has_keyword
from fit_score import is_personal_email, role_tier

LEGAL_FORMS = ["gmbh", "ag", "se", "ltd", "plc", "sas", "sa", "b.v.", "bv", "inc", "llc", "corp", "llp"]


def normalize_company(name):
    """'ALTMARK Insurance AG' -> 'altmark insurance' (lower case, no legal form, no punctuation)."""
    words = str(name).lower().replace(",", " ").split()
    words = [w for w in words if w not in LEGAL_FORMS]
    return re.sub(r"\s+", " ", " ".join(words)).strip()


def account_key(email, company_name):
    """Company email -> its domain. Personal email -> the normalized company name."""
    if not is_personal_email(email):
        return "domain:" + str(email).split("@")[-1].lower()
    return "name:" + normalize_company(company_name)


def is_ignored_company(company_name):
    return normalize_company(company_name) in config.HOT_ACCOUNT_IGNORE_COMPANIES


def unique_people(group):
    """One row per person (by email, ignoring upper/lower case), keeping their first sign-up."""
    return (group.assign(email_lower=group["email"].str.lower())
            .sort_values("signup_date")
            .drop_duplicates("email_lower"))


def _not_buyers(results):
    """Students and academics are never sales accounts."""
    return (results["reason"] == "Student") | (results["route"] == config.ROUTE_RESEARCH)


def find_hot_accounts(results):
    """
    results: one row per lead (form fields + engine output + account_key).
    Returns a list of dicts, one per hot account.
    """
    hot = []
    candidates = results[~_not_buyers(results)]
    for key, group in candidates.groupby("account_key"):
        if is_ignored_company(group["company_name"].iloc[0]):
            continue
        people = unique_people(group)
        if len(people) < config.HOT_ACCOUNT_MIN_PEOPLE:
            continue

        # Find the largest group of people who signed up within any 14-day window.
        best = None
        for start in people["signup_date"]:
            window = people[(people["signup_date"] >= start) &
                            (people["signup_date"] <= start + timedelta(days=config.HOT_ACCOUNT_WINDOW_DAYS))]
            if best is None or len(window) > len(best):
                best = window
        if len(best) < config.HOT_ACCOUNT_MIN_PEOPLE:
            continue

        hot.append({
            "account_key": key,
            "company_name": _display_name(best),
            "people": best,
            "days": (best["signup_date"].max() - best["signup_date"].min()).days,
            "buying_group": is_buying_group(best["role"]),
            "alert_date": best["signup_date"].max(),  # the day the 3rd (or later) person signed up
        })
    return hot


def is_buying_group(roles):
    """A technical person AND a different person who is senior or in a business role."""
    roles = list(roles)
    senior = [r for r in roles if has_keyword(r, config.SENIORITY_KEYWORDS) or role_tier(r) == "business"]
    technical_not_senior = [r for r in roles if role_tier(r) == "technical" and r not in senior]
    return len(senior) >= 1 and len(technical_not_senior) >= 1


def _display_name(rows):
    """The company name as typed by the first person who signed up."""
    return rows.sort_values("signup_date")["company_name"].iloc[0]


def find_hot_segments(results, as_of):
    """
    Same industry + same use case category, across different companies, in the last N days.
    Returns (hot_segments, watch_list) as DataFrames with columns industry, category, leads, companies.
    """
    since = as_of - timedelta(days=config.HOT_SEGMENT_WINDOW_DAYS)
    recent = results[(results["signup_date"] > since) & ~_not_buyers(results)
                     & results["use_case_category"].isin(config.TARGET_CATEGORIES)
                     & ~results["industry"].isin(["unknown", "other"])]
    segments = (recent.groupby(["industry", "use_case_category"])
                .agg(leads=("email", "nunique"), companies=("account_key", "nunique"))
                .reset_index().sort_values(["companies", "leads"], ascending=False))
    is_hot = (segments["leads"] >= config.HOT_SEGMENT_MIN_LEADS) & (segments["companies"] >= config.HOT_SEGMENT_MIN_COMPANIES)
    # Watch list: not hot yet, but at least 4 different companies.
    watch = segments[~is_hot & (segments["companies"] >= 4)]
    return segments[is_hot], watch


def account_activity(results, hot_accounts):
    """Companies with 2+ different people (students, academics and generic names left out)."""
    hot_by_key = {h["account_key"]: h for h in hot_accounts}
    rows = []
    candidates = results[~_not_buyers(results)]
    for key, group in candidates.groupby("account_key"):
        if is_ignored_company(group["company_name"].iloc[0]):
            continue
        people = unique_people(group)
        if len(people) < 2:
            continue
        hot = hot_by_key.get(key)
        rows.append({
            "company": _display_name(group),
            "people": len(people),
            "roles": ", ".join(people["role"]),
            "first": people["signup_date"].min().date(),
            "last": people["signup_date"].max().date(),
            "status": ("Hot account, buying group forming" if hot and hot["buying_group"]
                       else "Hot account" if hot else "Not hot yet"),
        })
    return pd.DataFrame(rows)
