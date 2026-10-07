"""
Real-time alerts for sales. Exactly three types, so they stay meaningful:
  1. HOT LEAD             one lead with fit score 80+
  2. HOT ACCOUNT          3+ people from one company within 14 days (+ "Buying group forming")
  3. COMMERCIAL-USE SIGNAL  already using TabPFN for a real use case with a company email
                            (the license boundary), or a consultancy with a target use case

Rules that keep alerts meaningful:
- Students and academics never trigger alerts.
- One alert per lead: people in a hot account only appear in the account alert;
  otherwise COMMERCIAL-USE beats HOT LEAD.

Slack is optional: if SLACK_WEBHOOK_URL is not set in .env, alerts are printed instead.
"""

import os

import requests

import config
from fit_score import is_personal_email

CATEGORY_LABELS = {
    "risk_credit": "risk / credit", "fraud": "fraud", "forecasting": "forecasting",
    "anomaly_maintenance": "anomaly detection / predictive maintenance", "diagnostics": "diagnostics",
    "churn": "churn", "other": "other",
}


def _company_line(row):
    country = row["country"] if isinstance(row["country"], str) else "country unknown"
    return f"{row['company_name']} ({row['industry']}, {row['company_size']}, {country} → {row['team']})"


def _flags(rows):
    flags = sorted({f.strip() for text in rows["flags"] for f in str(text).split(",") if f.strip()})
    return ", ".join(flags) if flags else "none"


def is_commercial_use(row):
    if row["reason"].startswith("Consultancy"):
        return True
    return (row["tried_tabpfn"] == config.ALREADY_USING
            and row["use_case_category"] in config.TARGET_CATEGORIES
            and not is_personal_email(row["email"]))


def build_alerts(results, hot_accounts):
    """Returns a list of alerts (dicts), sorted by date. Also marks results['alert'] per lead."""
    alerts = []
    results["alert"] = ""
    eligible = ~results["route"].isin([config.ROUTE_NURTURE, config.ROUTE_RESEARCH])

    # 2. Hot accounts first, so their members are not alerted twice.
    in_hot_account = set()
    for acc in hot_accounts:
        people = acc["people"]
        first = people.iloc[0]
        roles = ", ".join(people["role"])
        using = (people["tried_tabpfn"] == config.ALREADY_USING).sum()
        why = f"{len(people)} people signed up within {acc['days']} days: a team is actively testing."
        if acc["buying_group"]:
            why += " Technical users AND a senior/business person: the deal is moving to decision-makers."
        if using:
            why += f" {using} already using TabPFN: license conversation is close."
        alerts.append({
            "date": acc["alert_date"],
            "title": "🏢 HOT ACCOUNT" + (" — Buying group forming" if acc["buying_group"] else ""),
            "company": _company_line({**first, "company_name": acc["company_name"]}),
            "people": f"{len(people)} sign-ups in {acc['days']} days: {roles}",
            "why": why,
            "flags": _flags(people),
            "next_step": (f"Account Executive ({first['team']}): map the account and propose a team demo"
                          + (", bring the senior contact in" if acc["buying_group"] else "") + "."),
        })
        in_hot_account.update(results.index[(results["account_key"] == acc["account_key"]) & eligible])
    results.loc[list(in_hot_account), "alert"] = "HOT ACCOUNT"

    # 3 + 1. Per-lead alerts for everyone else.
    for idx, row in results[eligible].iterrows():
        if idx in in_hot_account:
            continue
        category = CATEGORY_LABELS.get(row["use_case_category"], row["use_case_category"])
        if is_commercial_use(row):
            consultancy = row["reason"].startswith("Consultancy")
            why = (f"Consultancy with a {category} use case: client work requires a commercial license."
                   if consultancy else
                   f"Already using TabPFN for {category} with a company email: free use for real work "
                   f"will soon need a commercial license.")
            next_step = (f"{row['route']} ({row['team']}): " +
                         ("start the license conversation for client work." if consultancy else
                          "check if it's heading to production and start the license conversation."
                          if row["route"] == config.ROUTE_ACCOUNT_EXECUTIVE else
                          "help them get to production, then hand over to an Account Executive for the license."))
            title, kind = "💶 COMMERCIAL-USE SIGNAL", "COMMERCIAL-USE"
        elif row["fit_score"] >= config.HOT_LEAD_MIN_FIT_SCORE:
            why = f"Fit score {row['fit_score']} ({row['score_breakdown']}). Use case: {category}."
            next_step = f"{row['route']} ({row['team']}): reach out within 24 hours with a {category} demo."
            title, kind = "🔥 HOT LEAD", "HOT LEAD"
        else:
            continue
        results.loc[idx, "alert"] = kind
        alerts.append({
            "date": row["signup_date"],
            "title": title,
            "company": _company_line(row),
            "people": f"{row['role']}, tried TabPFN: {row['tried_tabpfn']}",
            "why": why,
            "flags": _flags(results.loc[[idx]]),
            "next_step": next_step,
        })

    return sorted(alerts, key=lambda a: a["date"])


def format_alert(alert):
    """Same format for all three types."""
    person_label = "People" if alert["title"].startswith("🏢") else "Person"
    return (f"{alert['title']}   ({alert['date'].date()})\n"
            f"Company: {alert['company']}\n"
            f"{person_label}: {alert['people']}\n"
            f"Why: {alert['why']}\n"
            f"Flags: {alert['flags']}\n"
            f"Next step: {alert['next_step']}")


def send_to_slack(text):
    """Posts to Slack if a webhook is set. Returns True if sent, False if not configured or failed."""
    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return False
    try:
        response = requests.post(webhook, json={"text": text}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        # Never print the webhook URL itself: it is a secret.
        print(f"  (Slack post failed: {type(error).__name__}; printing instead)")
        return False
