"""
All tunable rules live in this one file.
Change the numbers and keyword lists here; the code reads them from here.

Keywords are matched as WHOLE WORDS, ignoring upper/lower case.
So "cto" matches "CTO" but not "Director", and "ai" matches "Head of AI" but not "maintenance".
That's why some lists spell out variants (e.g. "forecast", "forecasting").

Fit score: a perfect lead scores 25 (tried TabPFN) + 15 (industry) + 20 (size) + 20 (role) + 20 (use case) = 100.
"""

# ---------------------------------------------------------------------------
# Book a Demo form options (copied from the Prior Labs website form)
# ---------------------------------------------------------------------------
COMPANY_SIZES = ["1-49", "50-249", "250-999", "1000+"]

ALREADY_USING = "Yes, I'm already using it"
TRIED_TABPFN_OPTIONS = [
    ALREADY_USING,
    "Tried it a few times",
    "Just started exploring",
    "Not yet",
]

# ---------------------------------------------------------------------------
# Fit score: points per signal
# ---------------------------------------------------------------------------

# Product usage is the strongest buying signal. "Not yet" is a normal top-down path, not a negative.
TRIED_TABPFN_POINTS = {
    ALREADY_USING: 25,
    "Tried it a few times": 18,
    "Just started exploring": 10,
    "Not yet": 5,
}

# Industry is not on the form: it comes from data/company_enrichment.csv
# (stands in for an enrichment tool such as Clearbit or Apollo).
# Any industry not listed here (consulting, education, retail, unknown...) gets OTHER_INDUSTRY_POINTS.
INDUSTRY_POINTS = {
    "finance": 15,
    "healthcare": 12,
    "pharma": 12,      # part of Healthcare on the Prior Labs website
    "biotech": 12,
    "industrials": 12,
    "energy": 8,
    "tech": 8,
    "retail": 8,
    "logistics": 8,
}
OTHER_INDUSTRY_POINTS = 5

SIZE_POINTS = {
    "1000+": 20,
    "250-999": 15,
    "50-249": 8,
    "1-49": 4,
}
# Small companies only get their size points if the use case is in a target category.
SMALL_SIZES = ["1-49", "50-249"]
LARGE_SIZES = ["250-999", "1000+"]

# Role tiers, checked in this order. Senior titles get NO extra points:
# the person booking a demo is often not the decision-maker.
TECHNICAL_ROLE_KEYWORDS = [
    "data", "data science", "data scientist", "machine learning", "ml", "ai",
    "statistics", "statistician", "biostatistician", "r&d", "research", "researcher",
    "risk", "quant", "quantitative", "analytics",
]
BUSINESS_ROLE_KEYWORDS = [  # people who evaluate or buy tools, often for their data team
    "innovation", "strategy", "product", "operations", "procurement",
    "business development", "cto", "cio", "founder", "co-founder",
]
# Checked first: these roles get the "other" tier even though they contain a technical word ("data").
NON_TECHNICAL_ROLE_KEYWORDS = ["data entry"]
ROLE_POINTS_TECHNICAL = 20
ROLE_POINTS_BUSINESS = 15
ROLE_POINTS_OTHER = 5

USE_CASE_POINTS_TARGET = 20
USE_CASE_POINTS_GENERIC = 10   # "generic_tabular": a prediction task, but not one of the target categories
USE_CASE_POINTS_OTHER = 0      # also used for "not provided" (empty use case)

# Personal email users may be freelancers or people testing privately: penalise, don't exclude.
PERSONAL_EMAIL_DOMAINS = [
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "gmx.de", "web.de", "proton.me",
]
PERSONAL_EMAIL_PENALTY = -25   # total score never goes below 0

# ---------------------------------------------------------------------------
# Use case categories: keyword rules (checked in this order, first match wins)
# ---------------------------------------------------------------------------
# Each keyword also matches with a trailing "s" ("loan" matches "loans"), so plurals are not listed.
# Fraud is checked before risk/credit, so "credit card fraud" counts as fraud.
USE_CASE_KEYWORDS = {
    "fraud": ["fraud", "fraudulent", "suspicious", "money laundering", "aml", "chargeback"],
    "risk_credit": ["credit", "default", "loan", "underwriting", "lending", "pd", "mortgage", "claim"],
    "anomaly_maintenance_quality": ["anomaly", "anomalies", "predictive maintenance", "maintenance", "failure",
                                    "sensor", "downtime", "defect", "fault", "quality control", "outage",
                                    "safety incident"],
    "clinical_diagnostics": ["diagnosis", "diagnostic", "diagnostics", "patient", "clinical", "disease",
                             "readmission", "biomarker",
                             # pharma / biotech (from the Prior Labs Healthcare page)
                             "drug", "drug discovery", "genomic", "treatment response", "adverse",
                             "proteomic", "immunoprofiling", "mortality"],
    "churn": ["churn", "customer retention", "attrition", "cancel"],
    "forecasting": ["forecast", "forecasting", "demand", "time series", "load prediction", "nowcasting",
                    "volatility", "trading", "price movement"],
    "customer_commercial": ["cross-sell", "cross sell", "upsell", "propensity", "lifetime value", "clv",
                            "conversion", "lead scoring", "segmentation", "campaign", "pricing", "valuation"],
    "operations_supply_chain": ["supply chain", "supplier", "inventory", "delivery time", "route",
                                "payment delay", "late payment", "ticket classification"],
}
TARGET_CATEGORIES = list(USE_CASE_KEYWORDS)   # the 8 above

# No target category, but clearly a tabular prediction task: partial credit, category "generic_tabular".
# Not a target category: it does not unlock small-company size points or routing rules 3-5.
GENERIC_TABULAR_KEYWORDS = ["prediction", "predict", "predicting", "predictive", "classification", "classify",
                            "classifier", "regression", "tabular"]
GENERIC_TABULAR = "generic_tabular"
NOT_PROVIDED = "not provided"   # empty or missing use case field

# ---------------------------------------------------------------------------
# Keyword flags (no score impact; shown in alerts and the results CSV)
# ---------------------------------------------------------------------------
FLAG_KEYWORDS = {
    # Enterprise deal: security / procurement will be involved.
    "deployment/compliance": ["on-prem", "on-premise", "private cloud", "gdpr",
                              "regulatory", "compliance", "production"],
    # Actively evaluating options.
    "comparison": ["xgboost", "automl", "lightgbm", "catboost", "compared to", "alternative"],
}

# ---------------------------------------------------------------------------
# Routing (checked in order, first match wins)
# ---------------------------------------------------------------------------
ROUTE_ACCOUNT_EXECUTIVE = "Account Executive"
ROUTE_SOLUTIONS_ENGINEER = "Solutions Engineer"
ROUTE_NURTURE = "Automated nurture email"
ROUTE_REVIEW = "Sales team review"
ROUTE_RESEARCH = "Research / community"   # academics are free users, not buyers

STUDENT_KEYWORDS = ["student", "phd candidate", "intern", "thesis"]
ACADEMIC_ROLE_KEYWORDS = ["postdoc", "professor", "lecturer"]
ACADEMIC_EMAIL_PATTERNS = [".edu", ".ac.uk", "uni-", "university", "ethz.ch", "epfl.ch", "tum.de", "mpg.de"]   # matched anywhere in the email domain
CONSULTANCY_KEYWORDS = ["consulting", "consultancy", "advisory"]     # in role or company name

AE_MIN_FIT_SCORE = 75       # fit score at or above this -> Account Executive
NURTURE_BELOW_FIT_SCORE = 40 # fit score below this -> nurture email

# Region tag from the enrichment country.
COUNTRY_REGION = {
    "Germany": "Europe", "Austria": "Europe", "Switzerland": "Europe", "United Kingdom": "Europe",
    "France": "Europe", "Netherlands": "Europe", "Sweden": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Denmark": "Europe",
    "United States": "US", "Canada": "US",
}
REGION_TEAM = {"Europe": "Berlin team", "US": "NYC team"}
UNASSIGNED_TEAM = "Unassigned"

# ---------------------------------------------------------------------------
# Real-time alerts
# ---------------------------------------------------------------------------
HOT_LEAD_MIN_FIT_SCORE = 80   # re-check the alert count after rebuilding realistic fake data

HOT_ACCOUNT_MIN_PEOPLE = 3
HOT_ACCOUNT_WINDOW_DAYS = 14
# Generic "company names" that are not real accounts, so never count as hot.
HOT_ACCOUNT_IGNORE_COMPANIES = ["freelance", "self-employed", "none", "n/a", "-", "student"]
# "Buying group forming" = a technical role AND a senior or business role in the same hot account.
SENIORITY_KEYWORDS = ["head", "director", "vp", "vice president", "chief", "cto", "cio", "ceo",
                      "founder", "co-founder", "lead", "principal"]

# ---------------------------------------------------------------------------
# Weekly digest
# ---------------------------------------------------------------------------
# Hot segment = same industry + same use case category, across different companies.
HOT_SEGMENT_MIN_LEADS = 7
HOT_SEGMENT_MIN_COMPANIES = 7
HOT_SEGMENT_WINDOW_DAYS = 28
