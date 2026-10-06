"""
Generates ~100 FAKE inbound leads that look like Prior Labs "Book a Demo" sign-ups.

Everything here is invented with the Faker library: no real people, no real emails.
- Company emails use the reserved ".example" domain, which can never exist.
- Personal-email noise uses gmail.com etc. so the "personal email" rule can be shown;
  the addresses are random and nothing is ever sent to them.

Outputs:
  data/form_submissions.csv    the 8 form fields + signup_date (what the CRM would hold)
  data/company_enrichment.csv  company_name -> industry, country (stands in for Clearbit/Apollo).
                               A few companies are deliberately missing, like in real life.

Some patterns are PLANTED on purpose so the demo can show detection working
(hot accounts, a hot segment, consultancies, academics...). See planted_patterns().

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
DAYS_BACK = 27                 # sign-ups are spread over the last 4 weeks

random.seed(SEED)
Faker.seed(SEED)

# Country -> Faker language for names, and typical legal forms for company names.
COUNTRIES = {
    "Germany": ("de_DE", ["GmbH", "AG", "SE"]),
    "Austria": ("de_DE", ["GmbH", "AG"]),
    "Switzerland": ("de_DE", ["AG"]),
    "United Kingdom": ("en_GB", ["Ltd", "plc"]),
    "France": ("fr_FR", ["SAS", "SA"]),
    "Netherlands": ("nl_NL", ["B.V."]),
    "United States": ("en_US", ["Inc", "LLC", "Corp"]),
}
COUNTRY_WEIGHTS = {"Germany": 34, "United States": 30, "United Kingdom": 12, "France": 7,
                   "Netherlands": 7, "Switzerland": 6, "Austria": 4}
fake = Faker([locale for locale, _ in COUNTRIES.values()])

# ---------------------------------------------------------------------------
# Building blocks: company name parts, roles and use-case sentences
# ---------------------------------------------------------------------------
COMPANY_SUFFIXES = {
    "finance": ["Bank", "Capital", "Credit", "Insurance", "Leasing", "Finance", "Asset Management"],
    "healthcare": ["Health", "MedTech", "Diagnostics", "Pharma", "Care Group", "Clinics"],
    "industrials": ["Industries", "Manufacturing", "Robotics", "Automation", "Machinery", "Components"],
    "energy": ["Energy", "Power", "Grid", "Solar", "Utilities", "Wind"],
    "tech": ["Software", "Analytics", "Labs", "Cloud", "Commerce", "Apps"],
    "other": ["Retail", "Media", "Logistics", "Events", "Agency", "Hospitality"],
}

TECHNICAL_ROLES = {
    "finance": ["Credit Risk Analyst", "Quantitative Analyst", "Senior Data Scientist", "Risk Modelling Lead",
                "Fraud Analytics Manager", "ML Engineer"],
    "healthcare": ["Clinical Data Scientist", "Biostatistician", "R&D Lead", "Machine Learning Engineer",
                   "Head of AI"],
    "industrials": ["R&D Engineer", "Data Scientist", "Machine Learning Engineer", "Reliability Data Analyst",
                    "Process Data Scientist"],
    "energy": ["Data Scientist", "Head of Analytics", "ML Engineer", "R&D Manager"],
    "tech": ["ML Engineer", "Data Scientist", "Head of AI", "Staff Machine Learning Engineer", "Analytics Lead"],
}
BUSINESS_ROLES = ["Innovation Manager", "Head of Strategy", "Product Manager", "Head of Operations",
                  "Procurement Manager", "Business Development Manager", "CTO", "CIO"]
OTHER_ROLES = ["Marketing Manager", "Sales Director", "HR Business Partner", "Office Manager",
               "Account Manager", "IT Administrator", "Finance Manager"]

USE_CASE_TEXTS = {
    "risk_credit": [
        "Credit default prediction on our loan portfolio",
        "We want to improve our PD models for SME lending",
        "Underwriting decisions on tabular applicant data",
    ],
    "fraud": [
        "Fraud detection on card transactions",
        "Flagging suspicious payments in real time",
        "Anti money laundering (AML) alert prioritisation",
    ],
    "anomaly_maintenance": [
        "Predictive maintenance from machine sensor data",
        "Detect anomalies in assembly line measurements",
        "Predict pump failure before it happens",
        "Reduce unplanned downtime using sensor logs",
    ],
    "diagnostics": [
        "Predict patient readmission from hospital records",
        "Support diagnosis from lab results",
        "Early disease detection from tabular health data",
    ],
    "churn": [
        "Customer churn prediction for our subscription business",
        "Which customers will cancel next quarter?",
        "Improve retention by predicting churn earlier",
    ],
    "forecasting": [
        "Forecast spare part demand across warehouses",
        "Sales forecast per store and product",
        "Demand planning for our product lines",
    ],
    "vague": [
        "Just exploring what TabPFN can do",
        "Interested in tabular foundation models in general",
        "Want to learn more",
        "Evaluating AI tools for the team",
        "Not sure yet",
    ],
}

# Which use cases each industry tends to have (spread out so no accidental hot segment appears).
INDUSTRY_USE_CASES = {
    "finance": ["risk_credit", "fraud", "churn", "forecasting", "vague", "vague"],
    "healthcare": ["diagnostics", "diagnostics", "forecasting", "churn", "vague"],
    "industrials": ["anomaly_maintenance", "forecasting", "churn", "vague"],
    "energy": ["anomaly_maintenance", "churn", "vague"],
    "tech": ["churn", "fraud", "forecasting", "vague"],
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
# "Already using" is 0 here: every already-using lead is planted below, so the commercial-use alerts stay meaningful.
TRIED_WEIGHTS = [0, 20, 35, 45]

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


def random_country():
    return random.choices(list(COUNTRY_WEIGHTS), weights=list(COUNTRY_WEIGHTS.values()))[0]


def clean_last_name(name):
    """Drop suffixes like 'II' or 'MD', but keep Dutch names like 'de Vries' whole."""
    words = [w for w in name.split() if w not in ("II", "III", "IV", "Jr.", "Sr.", "MD", "DDS", "PhD", "DVM")]
    return " ".join(words)


def person_name(country):
    """First and last name from the same country, e.g. 'Anna Schneider' or 'Tom Baker'."""
    locale = COUNTRIES[country][0]
    return fake[locale].first_name(), clean_last_name(fake[locale].last_name())


used_company_names = set()


def new_company(industry, country):
    """A unique, made-up company name such as 'Hoffmann Capital AG'."""
    locale, legal_forms = COUNTRIES[country]
    while True:
        name = f"{clean_last_name(fake[locale].last_name())} {random.choice(COMPANY_SUFFIXES[industry])} {random.choice(legal_forms)}"
        if name not in used_company_names:
            used_company_names.add(name)
            return name


def company_domain(company):
    """'Hoffmann Capital AG' -> 'hoffmann-capital.example' (reserved domain, can never exist)."""
    words = [w for w in company.split() if w not in ("GmbH", "AG", "SE", "Ltd", "plc", "SAS", "SA", "B.V.", "Inc", "LLC", "Corp")]
    return ascii_slug(" ".join(words), sep="-") + ".example"


def personal_email(first, last):
    return f"{ascii_slug(first)}.{ascii_slug(last)}{random.randint(1, 99)}@{random.choice(PERSONAL_DOMAINS)}"


def random_date():
    return TODAY - timedelta(days=random.randint(0, DAYS_BACK))


def random_tried(weights=TRIED_WEIGHTS):
    return random.choices(config.TRIED_TABPFN_OPTIONS, weights=weights)[0]


def make_lead(company, role, size, tried, use_case, signup_date, country, domain=None, personal=False):
    first, last = person_name(country)
    if personal:
        email = personal_email(first, last)
    else:
        email = f"{ascii_slug(first)}.{ascii_slug(last)}@{domain or company_domain(company)}"
    return {
        "first_name": first,
        "last_name": last,
        "email": email,
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
def regular_leads(industry, count):
    """Leads from target industries: mostly technical roles, some business roles, a few others."""
    leads, companies = [], []
    for _ in range(count):
        country = random_country()
        company = new_company(industry, country)
        r = random.random()
        if r < 0.6:
            role = random.choice(TECHNICAL_ROLES[industry])
        elif r < 0.8:
            role = random.choice(BUSINESS_ROLES)
        else:
            role = random.choice(OTHER_ROLES)
        size = random.choices(config.COMPANY_SIZES, weights=SIZE_WEIGHTS[industry])[0]
        use_case = random.choice(USE_CASE_TEXTS[random.choice(INDUSTRY_USE_CASES[industry])])
        leads.append(make_lead(company, role, size, random_tried(), use_case, random_date(), country))
        companies.append((company, industry, country))
    return leads, companies


def noise_leads():
    """Low-fit leads, which are the majority of a real demo form: students, freelancers,
    irrelevant roles, tiny companies that are just curious, non-target industries."""
    leads, companies = [], []

    # 8 students: university emails or Gmail, thesis-style use cases.
    for _ in range(8):
        country = random.choice(["Germany", "United Kingdom", "United States", "Netherlands"])
        uni = f"University of {fake[COUNTRIES[country][0]].city()}"
        role = random.choice(["Student", "MSc Student", "PhD Candidate", "Working Student Data Science", "Intern"])
        use_case = random.choice(["Master thesis on tabular ML", "Course project", "Comparing TabPFN to XGBoost for my thesis",
                                  "Want to learn more"])
        leads.append(make_lead(uni, role, random.choice(["1000+", "250-999"]), random_tried([5, 25, 35, 35]),
                               use_case, random_date(), country, personal=random.random() < 0.5))
        companies.append((uni, "education", country))

    # 6 freelancers / self-employed with personal emails. Not in the enrichment table (nothing to look up).
    for _ in range(6):
        country = random.choice(["Germany", "United States", "United Kingdom"])
        company = random.choice(["Self-employed", "Self-employed", "Freelance"])
        role = random.choice(["Freelance Data Scientist", "Consultant", "Developer", "Founder"])
        use_case = random.choice(USE_CASE_TEXTS["vague"] + ["Small side project with tabular data"])
        leads.append(make_lead(company, role, "1-49", random_tried(), use_case, random_date(), country, personal=True))

    # 10 irrelevant roles at non-target companies.
    for _ in range(10):
        country = random_country()
        company = new_company("other", country)
        lead = make_lead(company, random.choice(OTHER_ROLES), random.choices(config.COMPANY_SIZES, weights=SIZE_WEIGHTS["other"])[0],
                         "Not yet", random.choice(USE_CASE_TEXTS["vague"] + ["Marketing campaign analysis", "Event planning"]),
                         random_date(), country)
        leads.append(lead)
        companies.append((company, "other", country))

    # 6 tiny tech companies that are just curious.
    for _ in range(6):
        country = random_country()
        company = new_company("tech", country)
        role = random.choice(["Founder", "Developer", "Software Engineer", "CTO", "Product Manager"])
        use_case = random.choice(USE_CASE_TEXTS["vague"] + ["Exploring TabPFN for our MVP", "Hackathon idea"])
        leads.append(make_lead(company, role, "1-49", random_tried(), use_case, random_date(), country))
        companies.append((company, "tech", country))

    # 5 non-target industries with a real-sounding use case (they still score in the middle).
    for text in ["Sales forecast per store and product", "Forecast delivery volumes per depot",
                 "Predict which hotel guests will cancel their booking", "Forecast ticket demand for our events",
                 "Which advertisers will churn next month?"]:
        country = random_country()
        company = new_company("other", country)
        role = random.choice(["Data Analyst", "Head of Operations", "Marketing Manager", "Business Analyst"])
        leads.append(make_lead(company, role, random.choices(config.COMPANY_SIZES, weights=SIZE_WEIGHTS["other"])[0],
                               random_tried(), text, random_date(), country))
        companies.append((company, "other", country))

    return leads, companies


def add_people(leads, companies, company, industry, country, people, size, start, domain=None, personal=False):
    """Adds several leads from one company. people = list of (day offset, role, tried_tabpfn, use_case).
    industry=None means the company is left OUT of the enrichment table."""
    for offset, role, tried, use_case in people:
        leads.append(make_lead(company, role, size, tried, use_case, start + timedelta(days=offset), country,
                               domain=domain, personal=personal))
    if industry:
        companies.append((company, industry, country))


def planted_patterns():
    """Patterns planted on purpose so the demo can show detection working."""
    leads, companies = [], []

    def add(*args, **kwargs):
        add_people(leads, companies, *args, **kwargs)

    # HOT ACCOUNT A (buying group): a data scientist first, Head of Data ~2 weeks later (inside 14 days).
    add("Nordhafen Bank AG", "finance", "Germany", [
        (0, "Senior Data Scientist", "Tried it a few times", "Credit default prediction on our loan portfolio, must run on-prem"),
        (4, "Credit Risk Analyst", "Just started exploring", "We want to improve our PD models for SME lending"),
        (8, "ML Engineer", "Tried it a few times", "Fraud detection on card transactions"),
        (13, "Head of Data", "Not yet", "Credit risk models for our retail lending book"),
    ], "1000+", TODAY - timedelta(days=15))

    # HOT ACCOUNT B: only technical people (no buying group yet).
    add("Cobalt Ridge Manufacturing Inc", "industrials", "United States", [
        (0, "R&D Engineer", "Tried it a few times", "Predictive maintenance from machine sensor data"),
        (5, "Reliability Data Analyst", "Just started exploring", "Reduce unplanned downtime using sensor logs"),
        (11, "Process Data Scientist", "Not yet", "Predict pump failure before it happens"),
    ], "250-999", TODAY - timedelta(days=12))

    # NEAR MISS: 3 people from one company, but spread over 27 days -> must NOT be flagged.
    add("Lumio Analytics GmbH", "tech", "Germany", [
        (0, "Data Scientist", "Just started exploring", "Customer churn prediction for our subscription business"),
        (15, "Product Manager", "Just started exploring", "Improve retention by predicting churn earlier"),
        (27, "ML Engineer", "Tried it a few times", "Which customers will cancel next quarter?"),
    ], "50-249", TODAY - timedelta(days=27))

    # HOT SEGMENT: 8 energy companies, all forecasting from smart-meter data.
    segment_texts = [
        "Load forecasting from smart meter data",
        "Forecast household energy consumption from meter readings",
        "Short-term demand forecasting for our grid",
        "Forecasting electricity demand per substation",
        "Smart meter data: forecast peak load",
        "Energy demand forecasting for our customers",
        "Forecast heat pump demand from meter data",
        "Forecasting EV charging load from meter data",
    ]
    for text in segment_texts:
        country = random.choice(["Germany", "Netherlands", "United Kingdom", "Austria", "United States"])
        company = new_company("energy", country)
        role = random.choice(TECHNICAL_ROLES["energy"] + ["Head of Operations"])
        add(company, "energy", country, [(0, role, random_tried(), text)],
            random.choice(["250-999", "1000+", "50-249"]), TODAY - timedelta(days=random.randint(0, 20)))

    # CONSULTANCIES with target use cases (client work needs a commercial license).
    add("Brightline Advisory Ltd", "consulting", "United Kingdom",
        [(0, "Data Consultant", "Tried it a few times", "Fraud detection models for a banking client")],
        "1-49", TODAY - timedelta(days=6))
    add("Kessler Consulting GmbH", "consulting", "Germany",
        [(0, "Senior Consultant Analytics", "Just started exploring", "Credit risk scoring for an insurance client")],
        "50-249", TODAY - timedelta(days=17))
    add("Harbor Point Consulting LLC", "consulting", "United States",
        [(0, "Managing Consultant", "Not yet", "Churn prediction for a telecom client, compared to our AutoML stack")],
        "250-999", TODAY - timedelta(days=9))

    # ACADEMICS (university domains, postdoc/professor roles) -> Research / community.
    add("University of Lindenau", "education", "Germany",
        [(0, "Postdoc", config.ALREADY_USING, "Diagnosis support from clinical lab results")],
        "1000+", TODAY - timedelta(days=3), domain="uni-lindenau.example")
    add("Stanbridge University", "education", "United States",
        [(0, "Assistant Professor", "Tried it a few times", "Teaching tabular ML, benchmarking against XGBoost")],
        "1000+", TODAY - timedelta(days=19), domain="stanbridge.edu.example")
    add("Northgate College", "education", "United Kingdom",
        [(0, "Lecturer in Statistics", "Just started exploring", "Research on small tabular datasets")],
        "250-999", TODAY - timedelta(days=11), domain="northgate.ac.uk.example")

    # SMALL COMPANIES ALREADY USING TabPFN -> Solutions Engineer + commercial-use signal.
    add("Velora Analytics GmbH", "tech", "Germany",
        [(0, "Data Scientist", config.ALREADY_USING, "Customer churn prediction in production for our SaaS clients")],
        "1-49", TODAY - timedelta(days=2))
    add("Payflux Inc", "finance", "United States",
        [(0, "ML Engineer", config.ALREADY_USING, "Chargeback and fraud prediction for our merchants")],
        "50-249", TODAY - timedelta(days=8))

    # LARGE COMPANIES with deployment/compliance or comparison keywords.
    add("Helvia Health AG", "healthcare", "Switzerland",
        [(0, "Clinical Data Scientist", "Tried it a few times", "Predict patient readmission, GDPR compliant deployment needed")],
        "1000+", TODAY - timedelta(days=5))
    add("Ostwind Versicherung AG", "finance", "Germany",
        [(0, "Head of Credit Risk", config.ALREADY_USING, "Underwriting model with regulatory approval, private cloud only")],
        "1000+", TODAY - timedelta(days=1))
    add("Granite Peak Power Corp", "energy", "United States",
        [(0, "Innovation Manager", "Not yet", "Predictive maintenance for turbines, needs on-premise deployment")],
        "1000+", TODAY - timedelta(days=14))
    add("Maribel Commerce SAS", "tech", "France",
        [(0, "Head of AI", "Just started exploring", "Churn model, looking for an alternative to LightGBM")],
        "250-999", TODAY - timedelta(days=10))

    # GMAIL USER ALREADY USING TabPFN with a strong use case (penalised, but not excluded).
    leads.append(make_lead("Self-employed", "Freelance Data Scientist", "1-49", config.ALREADY_USING,
                           "Churn prediction for e-commerce clients", TODAY - timedelta(days=4), "Germany", personal=True))

    # ENRICHMENT MISSING: these companies exist in the form data but not in the enrichment table.
    for industry, role, text in [
        ("finance", "Risk Analyst", "Credit default prediction on our loan portfolio"),
        ("industrials", "Operations Manager", "Detect anomalies in assembly line measurements"),
        ("tech", "Data Engineer", "Interested in tabular foundation models in general"),
    ]:
        country = random_country()
        add(new_company(industry, country), None, country,
            [(0, role, random_tried(), text)], random.choice(config.COMPANY_SIZES), random_date())

    return leads, companies


def tricky_leads():
    """Edge cases, each testing one rule. Some are handled by the engine; others are
    expected to fool the keyword rules on purpose, to show honest limits of v1."""
    leads, companies = [], []

    def add(*args, **kwargs):
        add_people(leads, companies, *args, **kwargs)

    def day(n):
        return TODAY - timedelta(days=n)

    # --- Should be handled correctly ---
    # Big company alone is not enough: HR at a large bank, vague use case.
    add("Falkenried Bank AG", "finance", "Germany",
        [(0, "HR Business Partner", "Not yet", "Evaluating AI tools for the team")], "1000+", day(16))
    # Senior technical role, but a tiny company that is just curious -> no size points.
    add("Quillby Labs Ltd", "tech", "United Kingdom",
        [(0, "Head of Data Science", "Just started exploring", "Just curious what TabPFN can do")], "1-49", day(7))
    # Strong profile, but signs up with a personal email -> penalised, not excluded.
    add("Westbrook Capital Inc", "finance", "United States",
        [(0, "Data Scientist", "Tried it a few times", "Credit default prediction for consumer loans")],
        "1000+", day(9), personal=True)
    # Working student with a company email at a big bank -> student rule wins.
    add("Elbtal Sparkasse AG", "finance", "Germany",
        [(0, "Working Student Risk Analytics", "Tried it a few times", "Credit risk scoring for my team")], "1000+", day(12))
    # Already using TabPFN, but no concrete use case -> no commercial-use signal.
    add("Tessaro Software GmbH", "tech", "Germany",
        [(0, "ML Engineer", config.ALREADY_USING, "Want to learn more about enterprise options")], "250-999", day(3))
    # Large consultancy without a target use case -> no consultancy route.
    add("Brennan & Cole Advisory LLP", "consulting", "United Kingdom",
        [(0, "Partner", "Not yet", "Exploring AI offerings for our clients")], "1000+", day(18))
    # Same person submitting the form 3 times -> must NOT look like a hot account (1 person, not 3).
    first, last = person_name("Netherlands")
    for offset in (0, 2, 5):
        leads.append({"first_name": first, "last_name": last,
                      "email": f"{ascii_slug(first)}.{ascii_slug(last)}@zuiderveld-health.example",
                      "company_name": "Zuiderveld Health B.V.", "role": "Biostatistician", "company_size": "250-999",
                      "tried_tabpfn": "Just started exploring", "use_case": "Predict patient readmission from hospital records",
                      "signup_date": day(10 - offset).isoformat()})
    companies.append(("Zuiderveld Health B.V.", "healthcare", "Netherlands"))

    # --- Expected to fool the v1 keyword rules (honest limits) ---
    # "Data" in the title makes a non-technical role look technical.
    add("Kronfeld Kliniken AG", "healthcare", "Germany",
        [(0, "Data Protection Officer", "Not yet", "GDPR review of AI tools before procurement")], "1000+", day(8))
    # Use cases written in German -> not recognised.
    add("Isarbank AG", "finance", "Germany",
        [(0, "Senior Data Scientist", "Tried it a few times", "Betrugserkennung bei Kartenzahlungen")], "1000+", day(5))
    add("Lechwerk Maschinenbau GmbH", "industrials", "Germany",
        [(0, "R&D Engineer", "Just started exploring", "Vorhersage von Maschinenausfällen")], "250-999", day(13))
    # Typos and jargon -> partly missed.
    add("Penrose Retail Analytics Inc", "tech", "United States",
        [(0, "Data Scientist", "Just started exploring", "forcasting sales per region")], "250-999", day(6))
    add("Thames Mutual plc", "finance", "United Kingdom",
        [(0, "Quantitative Analyst", "Tried it a few times", "PD/LGD models for IFRS 9")], "1000+", day(15))
    # Same company typed 3 different ways -> a hot account split in three (and enrichment only knows one spelling).
    for offset, name, role in [(0, "Altmark Insurance AG", "Data Scientist"), (4, "Altmark Insurance", "Head of Analytics"),
                               (9, "ALTMARK Insurance AG", "Risk Analyst")]:
        add(name, None, "Germany", [(0, role, "Just started exploring", "Claims fraud detection on policy data")],
            "1000+", day(14 - offset), domain="altmark-insurance.example")
    companies.append(("Altmark Insurance AG", "finance", "Germany"))
    # A partner, not a client: wants to build TabPFN into its own product (no partner route in v1).
    add("Vantor Data Platform Inc", "tech", "United States",
        [(0, "Head of Partnerships", "Tried it a few times", "Integrate TabPFN into our ML platform for our customers")],
        "250-999", day(4))
    # Uses TabPFN through a marketplace, so ticks "Not yet" (attribution blind spot).
    add("Rheingold Logistik SE", "industrials", "Germany",
        [(0, "Data Scientist", "Not yet", "We already run TabPFN through Databricks for demand forecasting")],
        "1000+", day(2))
    add("Corvane Utilities Corp", "energy", "United States",
        [(0, "Analytics Lead", "Not yet", "Using TabPFN in SAP for anomaly detection on meter data")], "1000+", day(11))

    return leads, companies


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    all_leads, all_companies = [], []
    groups = [regular_leads(industry, count) for industry, count in
              [("finance", 4), ("healthcare", 3), ("industrials", 3), ("energy", 1), ("tech", 2)]]
    groups += [noise_leads(), planted_patterns(), tricky_leads()]
    for leads, companies in groups:
        all_leads += leads
        all_companies += companies

    leads_df = pd.DataFrame(all_leads).sort_values("signup_date").reset_index(drop=True)
    enrichment_df = (pd.DataFrame(all_companies, columns=["company_name", "industry", "country"])
                     .drop_duplicates("company_name").sort_values("company_name"))

    data_dir = ROOT / "data"
    # utf-8-sig so Excel shows German umlauts (ä, ö, ü) correctly.
    leads_df.to_csv(data_dir / "form_submissions.csv", index=False, encoding="utf-8-sig")
    enrichment_df.to_csv(data_dir / "company_enrichment.csv", index=False, encoding="utf-8-sig")

    print(f"Wrote {len(leads_df)} fake leads to data/form_submissions.csv")
    print(f"Wrote {len(enrichment_df)} companies to data/company_enrichment.csv")


if __name__ == "__main__":
    main()
