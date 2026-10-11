"""
The real-time path: ONE new lead, the moment someone submits the Book a Demo form.
  score + route -> check it against earlier sign-ups (hot account) -> alert to Slack, or console
The weekly digest stays in main.py: it's a weekly summary, not a reaction to one lead.

The earlier sign-ups in data/form_submissions.csv play the role of the CRM history.
The new lead is NOT saved into that file, so the demo data never changes.

Run:  python src/new_lead.py                                 (default: the 3rd person from Lumio -> hot account)
      python src/new_lead.py data/examples/hot_lead.json     (a single hot lead)
"""

import json
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402,F401
from alerts import build_alerts, format_alert, send_to_slack  # noqa: E402
from engine import evaluate_lead  # noqa: E402
from main import load_leads  # noqa: E402
from patterns import account_key, find_hot_accounts, normalize_company  # noqa: E402

DEFAULT_LEAD = ROOT / "data" / "examples" / "hot_account_lead.json"


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # so emojis print on Windows
    load_dotenv(ROOT / ".env")

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LEAD
    lead = json.loads(path.read_text(encoding="utf-8"))
    lead["signup_date"] = pd.Timestamp(lead.get("signup_date") or pd.Timestamp.today().normalize())

    # 1. Enrich and score the new lead (same lookup as main.py).
    enrichment = pd.read_csv(ROOT / "data" / "company_enrichment.csv")
    lookup = {normalize_company(r.company_name): (r.industry, r.country) for r in enrichment.itertuples()}
    industry, country = lookup.get(normalize_company(lead["company_name"]), (None, None))
    result = evaluate_lead(lead, industry, country)

    print(f"\nNEW LEAD: {lead['first_name']} {lead['last_name']}, {lead['role']} at {lead['company_name']}")
    print(f"  Use case: {lead.get('use_case') or '(not provided)'}  ->  {result['use_case_category']}")
    print(f"  Score:    {result['score_breakdown']}")
    print(f"  Route:    {result['route']} ({result['reason']})  ->  {result['team']}")
    if result["flags"]:
        print(f"  Flags:    {result['flags']}")

    # 2. Put it next to the earlier sign-ups to see if it completes a hot account.
    history, industries, countries = load_leads()
    scored = pd.DataFrame([evaluate_lead(row, industries[i], countries[i]) for i, row in history.iterrows()])
    results = pd.concat([pd.concat([history, scored], axis=1), pd.DataFrame([{**lead, **result}])],
                        ignore_index=True)
    results["fit_score"] = results["fit_score"].astype("Int64")  # whole numbers, as in main.py
    results["account_key"] = [account_key(e, c) for e, c in zip(results["email"], results["company_name"])]
    new_index = results.index[-1]
    hot_accounts = [h for h in find_hot_accounts(results) if new_index in h["people"].index]

    # 3. Alert: hot account if this lead is part of one, otherwise the lead's own alert (if any).
    if hot_accounts:
        alerts = [a for a in build_alerts(results.copy(), hot_accounts) if a["title"].startswith("🏢")]
    else:
        alerts = build_alerts(results.loc[[new_index]].copy(), [])

    if not alerts:
        print("\nNo alert: this lead doesn't qualify for one. It still goes to the route above.")
    for alert in alerts:
        text = format_alert(alert)
        sent = send_to_slack(text)
        print(f"\n===== ALERT ({'sent to Slack' if sent else 'no Slack webhook: printed here'}) =====\n")
        print(text)


if __name__ == "__main__":
    main()
