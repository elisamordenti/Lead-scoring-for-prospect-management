"""
Weekly digest for founders and the growth team (markdown). Four short sections:
  1. Use case trends: hot segments + a suggested growth action (last 28 days)
  2. Account activity: companies with 2+ people, and any buying group (last 28 days)
  3. Mix: leads by industry and by team, this week vs last week
  4. Signals: compliance/deployment and comparison mentions, share already using TabPFN, this week vs last week
"""

from datetime import timedelta

import config
from alerts import CATEGORY_LABELS
from patterns import account_activity, find_hot_segments


def _growth_action(industry, category):
    label = CATEGORY_LABELS[category]
    return (f"Outbound to similar {industry} companies; publish a case study and a ready-made "
            f"demo notebook on {label} for {industry}.")


def _change(now, before):
    diff = now - before
    return f"{now} ({'+' if diff >= 0 else ''}{diff} vs last week)"


def build_digest(results, hot_accounts, as_of):
    this_week = results[results["signup_date"] > as_of - timedelta(days=7)]
    last_week = results[(results["signup_date"] > as_of - timedelta(days=14)) &
                        (results["signup_date"] <= as_of - timedelta(days=7))]
    lines = [f"# Weekly lead digest: week ending {as_of.date()}", "",
             f"{len(this_week)} new leads this week ({len(last_week)} last week). "
             "All leads are FAKE demo data.", ""]

    # 1. Use case trends
    hot, watch = find_hot_segments(results, as_of)
    lines += ["## 1. Use case trends (last 28 days)", ""]
    if hot.empty:
        lines.append("No hot segment this period.")
    for _, s in hot.iterrows():
        lines.append(f"- **🔥 {s['industry']} × {CATEGORY_LABELS[s['use_case_category']]}**: "
                     f"{s['leads']} leads from {s['companies']} different companies. "
                     f"Suggested action: {_growth_action(s['industry'], s['use_case_category'])}")
    if not watch.empty:
        lines.append("- Watch list (not hot yet): " + "; ".join(
            f"{s['industry']} × {CATEGORY_LABELS[s['use_case_category']]} ({s['companies']} companies)"
            for _, s in watch.iterrows()))
    lines.append("")

    # 2. Account activity
    activity = account_activity(results, hot_accounts)
    lines += ["## 2. Account activity (last 28 days)", ""]
    if activity.empty:
        lines.append("No company with 2+ people.")
    else:
        lines += ["| Company | People | Roles | Dates | Status |", "|---|---|---|---|---|"]
        for _, a in activity.sort_values("people", ascending=False).iterrows():
            lines.append(f"| {a['company']} | {a['people']} | {a['roles']} | {a['first']} → {a['last']} | {a['status']} |")
    lines.append("")

    # 3. Mix
    lines += ["## 3. Mix (this week vs last week)", "",
              "| Industry | This week | Last week |", "|---|---|---|"]
    for industry in sorted(set(results["industry"])):
        now, before = (this_week["industry"] == industry).sum(), (last_week["industry"] == industry).sum()
        if now or before:
            lines.append(f"| {industry} | {now} | {before} |")
    lines += ["", "| Team | This week | Last week |", "|---|---|---|"]
    for team in sorted(set(results["team"])):
        lines.append(f"| {team} | {(this_week['team'] == team).sum()} | {(last_week['team'] == team).sum()} |")
    lines.append("")

    # 4. Signals
    def count_flag(df, flag):
        return int(df["flags"].str.contains(flag, regex=False).sum())

    def share_using(df):
        return round(100 * (df["tried_tabpfn"] == config.ALREADY_USING).mean()) if len(df) else 0

    lines += ["## 4. Signals (this week vs last week)", "",
              f"- Deployment / compliance mentions (on-prem, GDPR…): "
              f"{_change(count_flag(this_week, 'deployment/compliance'), count_flag(last_week, 'deployment/compliance'))}",
              f"- Comparison mentions (XGBoost, AutoML…): "
              f"{_change(count_flag(this_week, 'comparison'), count_flag(last_week, 'comparison'))}",
              f"- Share of leads already using TabPFN: {share_using(this_week)}% "
              f"(last week {share_using(last_week)}%). A rising share = the free version is turning users into buyers.",
              ""]
    return "\n".join(lines)
