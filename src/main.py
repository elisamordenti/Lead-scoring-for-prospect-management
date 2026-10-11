"""
Runs the whole lead engine:
  form submissions + enrichment -> classify -> fit score -> route -> hot accounts / segments
  -> alerts (Slack or console) -> weekly digest -> results CSV

Run:  python src/main.py
"""

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402,F401
from alerts import build_alerts, format_alert, send_to_slack  # noqa: E402
from digest import build_digest  # noqa: E402
from engine import evaluate_lead  # noqa: E402
from patterns import account_key, find_hot_accounts, normalize_company  # noqa: E402

DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"


def load_leads():
    leads = pd.read_csv(DATA / "form_submissions.csv", parse_dates=["signup_date"])
    enrichment = pd.read_csv(DATA / "company_enrichment.csv")
    # Join on a normalized name so "Altmark Insurance" finds "Altmark Insurance AG".
    lookup = {normalize_company(r.company_name): (r.industry, r.country) for r in enrichment.itertuples()}
    found = leads["company_name"].map(lambda name: lookup.get(normalize_company(name), (None, None)))
    return leads, [industry for industry, _ in found], [country for _, country in found]


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # so emojis print on Windows
    load_dotenv(ROOT / ".env")
    OUTPUTS.mkdir(exist_ok=True)

    # 1. One lead at a time: classify, score, route.
    leads, industries, countries = load_leads()
    scored = pd.DataFrame([evaluate_lead(lead, industries[i], countries[i]) for i, lead in leads.iterrows()])
    scored["fit_score"] = scored["fit_score"].astype("Int64")  # whole numbers; empty for students/academics
    results = pd.concat([leads, scored], axis=1)
    results["account_key"] = [account_key(e, c) for e, c in zip(results["email"], results["company_name"])]

    # Same person submitting the form again: keep the row, but flag it.
    repeat = results.sort_values("signup_date")["email"].str.lower().duplicated()
    results.loc[repeat[repeat].index, "flags"] = (results.loc[repeat[repeat].index, "flags"]
                                                  .map(lambda f: f + ", duplicate submission" if f else "duplicate submission"))

    # 2. Across leads: hot accounts.
    hot_accounts = find_hot_accounts(results)
    results["hot_account"] = results["account_key"].isin([h["account_key"] for h in hot_accounts])

    # 3. Alerts: Slack if configured, otherwise console. Always saved to a file too.
    alerts = build_alerts(results, hot_accounts)
    alert_texts = [format_alert(a) for a in alerts]
    sent = sum(send_to_slack(text) for text in alert_texts)
    print(f"\n===== {len(alerts)} REAL-TIME ALERTS ({'sent to Slack' if sent else 'no Slack webhook: printed here'}) =====\n")
    if not sent:
        print("\n\n".join(alert_texts))
    (OUTPUTS / "alerts.md").write_text(
        "# Real-time alerts (fake demo data)\n\n" + "\n\n".join(f"```\n{t}\n```" for t in alert_texts) + "\n",
        encoding="utf-8")

    # 4. Weekly digest (as of the latest sign-up date, so the demo is reproducible).
    as_of = results["signup_date"].max()
    digest = build_digest(results, hot_accounts, as_of)
    (OUTPUTS / "weekly_digest.md").write_text(digest, encoding="utf-8")
    send_to_slack(digest)

    # 5. Results CSV.
    columns = ["first_name", "last_name", "email", "company_name", "role", "company_size", "tried_tabpfn",
               "use_case", "signup_date", "industry", "country", "team", "use_case_category", "fit_score",
               "score_breakdown", "route", "reason", "flags", "hot_account", "alert"]
    results["signup_date"] = results["signup_date"].dt.date
    output = results.sort_values("fit_score", ascending=False)[columns]  # not scored rows go last
    output["fit_score"] = output["fit_score"].astype(object).where(output["fit_score"].notna(), "not scored")
    output.to_csv(OUTPUTS / "scored_leads.csv", index=False, encoding="utf-8-sig")

    print(f"\n===== SUMMARY =====")
    print(f"{len(results)} leads scored -> outputs/scored_leads.csv")
    print("Routes:", results["route"].value_counts().to_dict())
    print(f"Hot accounts: {[h['company_name'] for h in hot_accounts]}")
    print(f"Alerts: {len(alerts)} -> outputs/alerts.md")
    print("Weekly digest -> outputs/weekly_digest.md")


if __name__ == "__main__":
    main()
