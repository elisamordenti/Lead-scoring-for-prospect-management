"""
Honest benchmark: TabPFN vs two standard baselines on a PUBLIC lead-scoring dataset with REAL outcomes.

Why a separate dataset? The fake leads have no real outcome (nobody bought anything), and inventing
outcomes would prove nothing. So TabPFN is tested here on the Kaggle "Lead Scoring Dataset"
(X Education, an online-course company, ~9,000 anonymized leads, column "Converted" = 1/0).
This does NOT score the fake leads.

Setup:
- Only columns known when the lead signs up. Columns filled in later by the sales team
  (Tags, Lead Quality, Asymmetrique scores, activity after contact...) are dropped: they would let models "cheat".
- Same 80/20 train/test split for every model. Main metric: ROC-AUC (1.0 = perfect ranking, 0.5 = random).
- Also trained on only 100 and 500 leads: a startup's own sales history is small.

Needs: data/raw/<the Kaggle csv> and TABPFN_TOKEN in .env.
Run:   python src/compare_models.py
"""

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
TRAIN_SIZES = [100, 500, None]  # None = all training rows

# Columns known at sign-up time (the lead's own behaviour and form answers).
SIGNUP_COLUMNS = [
    "Lead Origin", "Lead Source", "Do Not Email", "Do Not Call", "TotalVisits",
    "Total Time Spent on Website", "Page Views Per Visit", "Country", "Specialization",
    "How did you hear about X Education", "What is your current occupation",
    "What matters most to you in choosing a course", "Search", "Magazine", "Newspaper Article",
    "X Education Forums", "Newspaper", "Digital Advertisement", "Through Recommendations",
    "Receive More Updates About Our Courses", "Update me on Supply Chain Content",
    "Get updates on DM Content", "City", "I agree to pay the amount through cheque",
    "A free copy of Mastering The Interview",
]
# Dropped on purpose (filled in by the sales team after contact, or IDs).
DROPPED_COLUMNS = [
    "Prospect ID", "Lead Number", "Tags", "Lead Quality", "Lead Profile", "Last Activity",
    "Last Notable Activity", "Asymmetrique Activity Index", "Asymmetrique Profile Index",
    "Asymmetrique Activity Score", "Asymmetrique Profile Score",
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def find_dataset():
    for path in sorted((ROOT / "data" / "raw").glob("*.csv")):
        if "Converted" in pd.read_csv(path, nrows=0).columns:
            return path
    sys.exit("No Kaggle lead-scoring CSV with a 'Converted' column found in data/raw/. See README.")


def load_data():
    path = find_dataset()
    df = pd.read_csv(path)
    print(f"Dataset: {path.name}: {len(df)} leads, {df['Converted'].mean():.0%} converted")

    features = [c for c in SIGNUP_COLUMNS if c in df.columns]
    X = df[features].replace("Select", np.nan)  # "Select" = the form's default, i.e. not answered
    X = X.loc[:, X.nunique(dropna=True) > 1]    # drop columns with a single value (no information)
    y = df["Converted"].astype(int)
    categorical = [c for c in X.columns if X[c].dtype == object]
    numeric = [c for c in X.columns if c not in categorical]
    print(f"Using {len(X.columns)} sign-up columns ({len(numeric)} numeric, {len(categorical)} categorical); "
          f"dropped {len([c for c in DROPPED_COLUMNS if c in df.columns])} sales-filled columns")
    return X, y, numeric, categorical


def to_codes(X, categorical):
    """Categories -> integer codes (NaN stays NaN). Used for TabPFN and the tree model."""
    X = X.copy()
    for c in categorical:
        X[c] = X[c].astype("category").cat.codes.replace(-1, np.nan)
    return X.astype(float)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def logistic_regression(numeric, categorical):
    prep = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric),
        ("cat", make_pipeline(SimpleImputer(strategy="most_frequent"), OneHotEncoder(handle_unknown="ignore")), categorical),
    ])
    return make_pipeline(prep, LogisticRegression(max_iter=2000))


def gradient_boosting(columns, categorical):
    return HistGradientBoostingClassifier(categorical_features=[c in categorical for c in columns], random_state=SEED)


def check_tabpfn_limits(X_train, X_test):
    """Check the API's data-size limits before sending anything (sample if needed)."""
    from tabpfn_client.client import ServiceClient
    limits = ServiceClient.get_settings().max_model_limit
    rows, cols = X_train.shape
    print(f"TabPFN API limits: {limits.train_set_max_rows:,} train rows, {limits.train_set_max_cells:,} train cells, "
          f"{limits.test_set_max_rows:,} test rows. Ours: {rows:,} train rows x {cols} columns, {len(X_test):,} test rows")
    if rows > limits.train_set_max_rows or rows * cols > limits.train_set_max_cells:
        keep = min(limits.train_set_max_rows, limits.train_set_max_cells // cols)
        print(f"  Over the limit: sampling {keep:,} training rows")
        return keep
    print("  Within limits: no sampling needed")
    return None


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------
def main():
    load_dotenv(ROOT / ".env")
    token = os.getenv("TABPFN_TOKEN", "").strip()
    if not token:
        sys.exit("TABPFN_TOKEN is missing in .env")
    import tabpfn_client
    from tabpfn_client import TabPFNClassifier
    tabpfn_client.set_access_token(token)

    X, y, numeric, categorical = load_data()
    X_train_all, X_test, y_train_all, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    max_rows = check_tabpfn_limits(X_train_all, X_test)
    print(tabpfn_client.get_api_usage())

    X_codes = to_codes(X, categorical)  # encode once, so "Google" gets the same number in train and test
    X_test_codes = X_codes.loc[X_test.index]
    rows = []
    for size in TRAIN_SIZES:
        n = size or (max_rows or len(X_train_all))
        if n < len(X_train_all):
            X_train, _, y_train, _ = train_test_split(X_train_all, y_train_all, train_size=n, stratify=y_train_all,
                                                      random_state=SEED)
        else:
            X_train, y_train = X_train_all, y_train_all
        X_train_codes = X_codes.loc[X_train.index]

        models = {
            "Logistic regression": (logistic_regression(numeric, categorical), X_train, X_test),
            "Gradient boosting (trees)": (gradient_boosting(X.columns, categorical), X_train_codes, X_test_codes),
            "TabPFN (API)": (TabPFNClassifier(), X_train_codes.to_numpy(), X_test_codes.to_numpy()),
        }
        for name, (model, X_tr, X_te) in models.items():
            start = time.time()
            model.fit(X_tr, y_train)
            proba = model.predict_proba(X_te)[:, 1]
            rows.append({"train_rows": len(X_train), "model": name,
                         "roc_auc": roc_auc_score(y_test, proba),
                         "accuracy": accuracy_score(y_test, proba >= 0.5),
                         "seconds": time.time() - start})
            print(f"  {len(X_train):>5} rows | {name:<26} ROC-AUC {rows[-1]['roc_auc']:.3f} | "
                  f"accuracy {rows[-1]['accuracy']:.3f} | {rows[-1]['seconds']:.1f}s")

    print(tabpfn_client.get_api_usage())
    results = pd.DataFrame(rows)
    write_report(results, len(X), y.mean(), X.columns, len(X_test))


def write_report(results, n_leads, conversion_rate, columns, n_test):
    lines = ["# TabPFN vs standard baselines: lead conversion prediction", "",
             "**Dataset:** Kaggle *Lead Scoring Dataset* (X Education, an online-course company): "
             f"{n_leads:,} real, anonymized leads; {conversion_rate:.0%} converted. "
             "Public data, not Prior Labs' data, and it does **not** score the fake leads.", "",
             f"**Setup:** same stratified 80/20 split for every model ({n_test:,} test leads). "
             f"{len(columns)} columns known at sign-up time; columns filled in later by the sales team "
             "(Tags, Lead Quality, activity scores, last activity) were dropped to avoid leakage. "
             "TabPFN runs with default settings through the Prior Labs API; baselines are scikit-learn defaults.", "",
             "**Metric:** ROC-AUC = how well the model ranks converters above non-converters "
             "(1.0 = perfect, 0.5 = random). Accuracy at a 0.5 threshold shown for reference.", "",
             "| Training leads | Model | ROC-AUC | Accuracy | Time (s) |", "|---|---|---|---|---|"]
    for _, r in results.iterrows():
        lines.append(f"| {r['train_rows']:,} | {r['model']} | {r['roc_auc']:.3f} | {r['accuracy']:.3f} | {r['seconds']:.1f} |")

    lines += ["", "## Reading", ""]
    for n, group in results.groupby("train_rows", sort=True):
        best = group.sort_values("roc_auc", ascending=False)
        tabpfn = group[group["model"] == "TabPFN (API)"]["roc_auc"].iloc[0]
        best_other = group[group["model"] != "TabPFN (API)"]["roc_auc"].max()
        diff = tabpfn - best_other
        verdict = ("TabPFN is best" if diff > 0.01 else
                   "TabPFN is behind the best baseline" if diff < -0.01 else
                   "TabPFN and the best baseline are within 0.01 (practically a tie)")
        lines.append(f"- **{n:,} training leads:** {verdict} "
                     f"(TabPFN {tabpfn:.3f} vs best baseline {best_other:.3f}; best overall: {best.iloc[0]['model']}).")
    lines += ["", "## Limits", "",
              "- One dataset, one split: differences of ~0.01 AUC are within noise.",
              "- A different business (online courses, B2C) from Prior Labs (B2B, enterprise).",
              "- No tuning for any model; a tuned baseline might do better, and so might TabPFN's advanced options.",
              "- Next step with real data: train on Prior Labs' own won/lost deals and add the probability "
              "as a predictive score next to the rule-based fit score.", ""]
    out = ROOT / "outputs" / "model_comparison.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport -> outputs/model_comparison.md")


if __name__ == "__main__":
    main()
