"""
All tunable rules live in this one file.
Change the numbers and keyword lists here; the code reads them from here.

The fit score is built from points. With the numbers below, a perfect lead
scores 100 (25 industry + 20 size + 20 role + 15 tried TabPFN + 20 use case).
"""

# ---------------------------------------------------------------------------
# Book a Demo form options (copied from the Prior Labs website form)
# ---------------------------------------------------------------------------
COMPANY_SIZES = ["1-49", "50-249", "250-999", "1000+"]

TRIED_TABPFN_OPTIONS = [
    "Yes, I'm already using it",
    "Tried it a few times",
    "Just started exploring",
    "Not yet",
]

# ---------------------------------------------------------------------------
# Fit score: points per signal
# ---------------------------------------------------------------------------

# Industry is not on the form. It comes from data/company_enrichment.csv,
# which stands in for an enrichment tool such as Clearbit or Apollo.
INDUSTRY_POINTS = {
    "finance": 25,
    "healthcare": 20,
    "industrials": 20,
    "energy": 12,
    "tech": 12,
    "other": 3,
}

SIZE_POINTS = {
    "1000+": 20,
    "250-999": 15,
    "50-249": 8,
    "1-49": 4,
}
# Small companies only get their size points if the use case is strong
# (i.e. it falls into one of the TARGET_CATEGORIES below).
SMALL_SIZES = ["1-49", "50-249"]

# A role counts as "high" if it contains any of these words (case-insensitive).
HIGH_VALUE_ROLE_KEYWORDS = [
    "data scien", "machine learning", "ml", "ai", "artificial intelligence",
    "statistic", "r&d", "research", "risk", "quant", "analytics", "data",
]
ROLE_POINTS_HIGH = 20
ROLE_POINTS_LOW = 3

TRIED_TABPFN_POINTS = {
    "Yes, I'm already using it": 15,
    "Tried it a few times": 10,
    "Just started exploring": 6,
    "Not yet": 0,
}

# ---------------------------------------------------------------------------
# Use case categories: keyword rules (checked in this order, first match wins)
# ---------------------------------------------------------------------------
USE_CASE_KEYWORDS = {
    "risk_credit": ["credit", "default", "loan", "underwriting", "risk scor", "pd model", "lending"],
    "fraud": ["fraud", "suspicious", "money laundering", "aml", "chargeback"],
    "anomaly_maintenance": ["anomaly", "anomalies", "predictive maintenance", "failure", "sensor", "downtime", "defect"],
    "diagnostics": ["diagnos", "patient", "clinical", "disease", "readmission", "lab result"],
    "churn": ["churn", "retention", "cancel", "attrition"],
    "forecasting": ["forecast", "demand", "predict sales", "load prediction", "time series", "price prediction"],
}
# Everything that matches none of the above becomes "other".

# Use cases in these categories earn USE_CASE_POINTS_TARGET.
TARGET_CATEGORIES = ["risk_credit", "fraud", "forecasting", "anomaly_maintenance", "diagnostics", "churn"]
USE_CASE_POINTS_TARGET = 20
USE_CASE_POINTS_OTHER = 0

# ---------------------------------------------------------------------------
# Negative signals
# ---------------------------------------------------------------------------
PERSONAL_EMAIL_DOMAINS = [
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "gmx.de", "web.de", "proton.me",
]
PERSONAL_EMAIL_PENALTY = -40

STUDENT_KEYWORDS = ["student", "phd candidate", "intern", "thesis"]

# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
ROUTE_ACCOUNT_EXECUTIVE = "Account Executive"
ROUTE_SOLUTIONS_ENGINEER = "Solutions Engineer"
ROUTE_NURTURE = "Automated nurture email"
ROUTE_REVIEW = "Sales team review"  # middle scores: a human takes a look

AE_MIN_FIT_SCORE = 70        # fit score at or above this -> Account Executive
NURTURE_MAX_FIT_SCORE = 40   # fit score below this -> nurture email
# Already using TabPFN + a use case in one of these -> Solutions Engineer
TECHNICAL_CATEGORIES = TARGET_CATEGORIES

# ---------------------------------------------------------------------------
# Hot accounts and alerts
# ---------------------------------------------------------------------------
HOT_ACCOUNT_MIN_PEOPLE = 3
HOT_ACCOUNT_WINDOW_DAYS = 14
# Generic "company names" that are not real accounts, so never count as hot.
HOT_ACCOUNT_IGNORE_COMPANIES = ["freelance", "self-employed", "none", "n/a", "-", "student"]

ALERT_MIN_FIT_SCORE = 80     # leads at or above this get an individual Slack alert
