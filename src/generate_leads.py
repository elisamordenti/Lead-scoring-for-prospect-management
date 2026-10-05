"""
Generates ~100 FAKE inbound leads that look like Prior Labs "Book a Demo" sign-ups.

Everything here is invented with the Faker library: no real people, no real emails.
- Company emails use the reserved ".example" domain, which can never exist.
- Personal-email noise uses gmail.com etc. so the "personal email" rule can be shown;
  the addresses are random and nothing is ever sent to them.

Outputs:
  data/fake_leads.csv          the form fields + signup_date (what the CRM would hold)
  data/company_enrichment.csv  company_name -> industry (stands in for Clearbit/Apollo)

Run:  python src/generate_leads.py
"""

import random
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

# Let this script find config.py in the project root folder.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

SEED = 42                      # same seed -> exactly the same leads every run
TODAY = date(2026, 10, 5)      # fixed "today" so the demo never changes
DAYS_BACK = 60                 # sign-ups are spread over the last 60 days

random.seed(SEED)
Faker.seed(SEED)
fake = Faker(["de_DE", "en_US", "en_GB"])

# ---------------------------------------------------------------------------
# Building blocks: fake company name parts, roles and use-case sentences
# ---------------------------------------------------------------------------
COMPANY_SUFFIXES = {
    "finance": ["Bank", "Kapital", "Credit Partners", "Versicherung", "Leasing", "Finanz", "Asset Management"],
    "healthcare": ["Klinikum", "Health", "MedTech", "Diagnostics", "Pharma", "Care Group"],
    "industrials": ["Maschinenbau", "Industries", "Antriebstechnik", "Robotics", "Automation", "Werke"],
    "energy": ["Energie", "Power", "Grid Services", "Solar", "Stadtwerke", "Wind"],
    "tech": ["Software", "Analytics", "Labs", "Cloud", "Commerce", "Apps"],
    "other": ["Marketing Agentur", "Retail", "Consulting", "Events", "Media", "Logistics"],
}
LEGAL_FORMS = ["GmbH", "AG", "Ltd", "Inc", "SE", ""]

STRONG_ROLES = {
    "finance": ["Head of Credit Risk", "Credit Risk Analyst", "Quantitative Analyst", "Head of Data Science",
                "Senior Data Scientist", "Risk Modelling Lead", "Fraud Analytics Manager"],
    "healthcare": ["Clinical Data Scientist", "Head of AI", "Biostatistician", "R&D Lead",
                   "Machine Learning Engineer", "Director of Data & Analytics"],
    "industrials": ["R&D Engineer", "Head of Data Science", "Machine Learning Engineer",
                    "Reliability Data Analyst", "VP of AI", "Process Data Scientist"],
    "energy": ["Data Scientist", "Head of Analytics", "Forecasting Analyst", "ML Engineer", "R&D Manager"],
    "tech": ["ML Engineer", "Data Scientist", "Head of AI", "Staff Machine Learning Engineer",
             "Analytics Lead", "AI Research Scientist"],
}
WEAK_ROLES = ["Marketing Manager", "Sales Director", "HR Business Partner", "Procurement Manager",
              "Product Manager", "Office Manager", "Account Manager", "CFO", "IT Administrator"]

USE_CASE_TEXTS = {
    "risk_credit": [
        "Credit default prediction on our loan portfolio",
        "We want to improve our PD models for SME lending",
        "Underwriting decisions on tabular applicant data",
        "Credit risk scoring, currently using XGBoost",
    ],
    "fraud": [
        "Fraud detection on card transactions",
        "Flagging suspicious payments in real time",
        "Anti money laundering (AML) alert prioritisation",
        "Chargeback and fraud prediction for our merchants",
    ],
    "anomaly_maintenance": [
        "Predictive maintenance from machine sensor data",
        "Detect anomalies in production line measurements",
        "Predict pump failure before it happens",
        "Reduce unplanned downtime using sensor logs",
    ],
    "diagnostics": [
        "Predict patient readmission from hospital records",
        "Support diagnosis from lab results",
        "Clinical risk prediction on structured patient data",
        "Early disease detection from tabular health data",
    ],
    "churn": [
        "Customer churn prediction for our subscription business",
        "Which customers will cancel next quarter?",
        "Improve retention by predicting churn earlier",
    ],
    "forecasting": [
        "Energy demand forecasting for our grid",
        "Forecast spare part demand across warehouses",
        "Time series forecasting of electricity load",
        "Sales forecast per store and product",
    ],
    "vague": [
        "Just exploring what TabPFN can do",
        "Interested in tabular foundation models in general",
        "Want to learn more",
        "Evaluating AI tools for the team",
        "Not sure yet",
    ],
}

# Which use cases each industry tends to have.
INDUSTRY_USE_CASES = {
    "finance": ["risk_credit", "risk_credit", "fraud", "fraud", "churn", "vague"],
    "healthcare": ["diagnostics", "diagnostics", "forecasting", "vague"],
    "industrials": ["anomaly_maintenance", "anomaly_maintenance", "forecasting", "vague"],
    "energy": ["forecasting", "forecasting", "anomaly_maintenance", "vague"],
    "tech": ["churn", "churn", "fraud", "forecasting", "vague"],
}

# Typical company sizes per industry (weights for 1-49, 50-249, 250-999, 1000+).
SIZE_WEIGHTS = {
    "finance": [5, 15, 30, 50],
    "healthcare": [10, 25, 35, 30],
    "industrials": [5, 20, 40, 35],
    "energy": [10, 25, 35, 30],
    "tech": [30, 35, 20, 15],
    "other": [40, 35, 15, 10],
}

# Most people have not tried TabPFN yet (weights follow config.TRIED_TABPFN_OPTIONS order).
TRIED_WEIGHTS = [10, 20, 30, 40]

PERSONAL_DOMAINS = ["gmail.com", "gmail.com", "gmail.com", "yahoo.com", "outlook.com", "gmx.de", "web.de"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ascii_slug(text, sep="."):
    """'Jürgen Müller' -> 'juergen.mueller' (safe for email addresses)."""
    text = text.lower()
    for german, plain in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        text = text.replace(german, plain)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = "".join(c if c.isalnum() else " " for c in text).split()
    return sep.join(words)


used_company_names = set()


def new_company(industry):
    """A unique, made-up company name such as 'Hoffmann Kapital AG'."""
    while True:
        name = f"{fake.last_name()} {random.choice(COMPANY_SUFFIXES[industry])} {random.choice(LEGAL_FORMS)}".strip()
        if name not in used_company_names:
            used_company_names.add(name)
            return name


def company_email(first, last, company):
    domain = ascii_slug(company.replace("GmbH", "").replace(" AG", "").replace(" SE", ""), sep="-")
    return f"{ascii_slug(first)}.{ascii_slug(last)}@{domain}.example"


def personal_email(first, last):
    return f"{ascii_slug(first)}.{ascii_slug(last)}{random.randint(1, 99)}@{random.choice(PERSONAL_DOMAINS)}"


def random_date(days_back=DAYS_BACK):
    return TODAY - timedelta(days=random.randint(0, days_back))


def use_case_for(industry):
    return random.choice(USE_CASE_TEXTS[random.choice(INDUSTRY_USE_CASES[industry])])


def person_name():
    """First and last name from the same country, e.g. 'Anna Schneider' or 'Tom Baker'."""
    locale = random.choice(["de_DE", "de_DE", "en_US", "en_GB"])
    last = fake[locale].last_name().split(" ")[0]  # drop suffixes like 'II'
    return fake[locale].first_name(), last


def make_lead(company, role, size, tried, use_case, signup_date, email=None):
    first, last = person_name()
    return {
        "first_name": first,
        "last_name": last,
        "email": email or company_email(first, last, company),
        "company_name": company,
        "role": role,
        "company_size": size,
        "tried_tabpfn": tried,
        "use_case": use_case,
        "signup_date": signup_date.isoformat(),
    }


# ---------------------------------------------------------------------------
# Lead groups
# ---------------------------------------------------------------------------
def target_industry_leads(industry, count):
    """Leads from target industries: mostly strong roles, some weak ones."""
    leads, companies = [], []
    for _ in range(count):
        company = new_company(industry)
        role = random.choice(STRONG_ROLES[industry]) if random.random() < 0.7 else random.choice(WEAK_ROLES)
        size = random.choices(config.COMPANY_SIZES, weights=SIZE_WEIGHTS[industry])[0]
        tried = random.choices(config.TRIED_TABPFN_OPTIONS, weights=TRIED_WEIGHTS)[0]
        leads.append(make_lead(company, role, size, tried, use_case_for(industry), random_date()))
        companies.append((company, industry))
    return leads, companies


def noise_leads():
    """Students, personal-email sign-ups and irrelevant roles."""
    leads, companies = [], []

    # 8 students: university emails or Gmail, thesis-style use cases.
    for _ in range(8):
        uni = f"{random.choice(['Technische Universitaet', 'University of', 'Hochschule'])} {fake.city()}"
        role = random.choice(["Student", "MSc Student", "PhD Candidate", "Working Student Data Science", "Intern"])
        use_case = random.choice(["Master thesis on tabular ML", "Course project", "Comparing TabPFN to XGBoost for my thesis",
                                  "Want to learn more"])
        first, last = person_name()
        email = personal_email(first, last) if random.random() < 0.5 else company_email(first, last, uni)
        lead = make_lead(uni, role, random.choice(["1000+", "250-999"]),
                         random.choices(config.TRIED_TABPFN_OPTIONS, weights=[5, 25, 35, 35])[0],
                         use_case, random_date(), email=email)
        lead["first_name"], lead["last_name"] = first, last
        leads.append(lead)
        companies.append((uni, "other"))

    # 7 freelancers / tiny startups signing up with a personal email.
    for _ in range(7):
        company = random.choice(["Freelance", "Self-employed", new_company("tech")])
        first, last = person_name()
        role = random.choice(["Freelance Data Scientist", "Founder", "Consultant", "Developer"])
        lead = make_lead(company, role, "1-49", random.choices(config.TRIED_TABPFN_OPTIONS, weights=TRIED_WEIGHTS)[0],
                         random.choice(USE_CASE_TEXTS["vague"] + USE_CASE_TEXTS["churn"]), random_date(),
                         email=personal_email(first, last))
        lead["first_name"], lead["last_name"] = first, last
        leads.append(lead)
        companies.append((company, "other" if company in ("Freelance", "Self-employed") else "tech"))

    # 7 irrelevant roles at non-target companies.
    for _ in range(7):
        company = new_company("other")
        lead = make_lead(company, random.choice(WEAK_ROLES), random.choices(config.COMPANY_SIZES, weights=SIZE_WEIGHTS["other"])[0],
                         "Not yet", random.choice(USE_CASE_TEXTS["vague"] + ["Marketing campaign analysis", "Event planning"]),
                         random_date())
        leads.append(lead)
        companies.append((company, "other"))

    return leads, companies


def planted_accounts():
    """2 hot accounts + 1 near miss, planted on purpose to show detection works."""
    leads, companies = [], []

    # Hot account A: a large bank, 4 people within 10 days.
    bank, start = "Nordhafen Bank AG", TODAY - timedelta(days=12)
    for offset, role, uc, tried in [
        (0, "Head of Credit Risk", "Credit default prediction on our loan portfolio", "Just started exploring"),
        (3, "Senior Data Scientist", "We want to improve our PD models for SME lending", "Tried it a few times"),
        (7, "Fraud Analytics Manager", "Fraud detection on card transactions", "Not yet"),
        (10, "Head of Data Science", "Credit risk scoring, currently using XGBoost", "Yes, I'm already using it"),
    ]:
        leads.append(make_lead(bank, role, "1000+", tried, uc, start + timedelta(days=offset)))
    companies.append((bank, "finance"))

    # Hot account B: a mid-size manufacturer, 3 people within 12 days.
    maker, start = "Rheinberg Antriebstechnik GmbH", TODAY - timedelta(days=20)
    for offset, role, uc, tried in [
        (0, "R&D Engineer", "Predictive maintenance from machine sensor data", "Tried it a few times"),
        (5, "Reliability Data Analyst", "Reduce unplanned downtime using sensor logs", "Just started exploring"),
        (12, "Head of Operations", "Predict pump failure before it happens", "Not yet"),
    ]:
        leads.append(make_lead(maker, role, "250-999", tried, uc, start + timedelta(days=offset)))
    companies.append((maker, "industrials"))

    # Near miss: 3 people from one company, but spread over 36 days -> must NOT be flagged.
    slow, start = "Lumio Analytics GmbH", TODAY - timedelta(days=50)
    for offset, role in [(0, "Data Scientist"), (18, "Product Manager"), (36, "ML Engineer")]:
        leads.append(make_lead(slow, role, "50-249", "Just started exploring",
                               "Customer churn prediction for our subscription business", start + timedelta(days=offset)))
    companies.append((slow, "tech"))

    return leads, companies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    all_leads, all_companies = [], []
    for industry, count in [("finance", 20), ("healthcare", 13), ("industrials", 13), ("energy", 10), ("tech", 14)]:
        leads, companies = target_industry_leads(industry, count)
        all_leads += leads
        all_companies += companies
    for group in (noise_leads(), planted_accounts()):
        all_leads += group[0]
        all_companies += group[1]

    leads_df = pd.DataFrame(all_leads).sort_values("signup_date").reset_index(drop=True)
    enrichment_df = pd.DataFrame(all_companies, columns=["company_name", "industry"]).drop_duplicates("company_name")

    data_dir = ROOT / "data"
    leads_df.to_csv(data_dir / "fake_leads.csv", index=False)
    enrichment_df.to_csv(data_dir / "company_enrichment.csv", index=False)

    print(f"Wrote {len(leads_df)} fake leads to data/fake_leads.csv")
    print(f"Wrote {len(enrichment_df)} companies to data/company_enrichment.csv")
    print("Planted hot accounts: Nordhafen Bank AG (4 people), Rheinberg Antriebstechnik GmbH (3 people)")
    print("Planted near miss (should NOT be flagged): Lumio Analytics GmbH (3 people over 36 days)")


if __name__ == "__main__":
    main()
