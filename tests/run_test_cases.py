"""
Runs the 7 test leads from the FINAL RULES through the engine and checks the expected results.
These are made-up test leads (not in the fake data file).

Run:  python tests/run_test_cases.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
from engine import evaluate_lead  # noqa: E402

AE, SE, NURTURE, REVIEW, RESEARCH = (config.ROUTE_ACCOUNT_EXECUTIVE, config.ROUTE_SOLUTIONS_ENGINEER,
                                     config.ROUTE_NURTURE, config.ROUTE_REVIEW, config.ROUTE_RESEARCH)

# (description, lead, industry, country, expected route, expected score or None)
TEST_CASES = [
    ("1. Head of Credit Risk, large bank, just exploring, credit default",
     dict(email="test.one@bigbank.example", company_name="Big Bank AG", role="Head of Credit Risk",
          company_size="1000+", tried_tabpfn="Just started exploring",
          use_case="Credit default prediction on our loan portfolio"),
     "finance", "Germany", AE, None),
    ("2. Postdoc, large university, already using, diagnostics",
     dict(email="test.two@uni-example.example", company_name="University of Example", role="Postdoc",
          company_size="1000+", tried_tabpfn=config.ALREADY_USING,
          use_case="Diagnosis support from clinical lab results"),
     "education", "Germany", RESEARCH, None),
    ("3. Data consultant, 40-person consulting firm, fraud",
     dict(email="test.three@example-consulting.example", company_name="Example Consulting GmbH",
          role="Data Consultant", company_size="1-49", tried_tabpfn="Tried it a few times",
          use_case="Fraud detection models for a banking client"),
     "consulting", "Germany", AE, None),
    ("4. Data scientist, 120-person fintech, already using, churn",
     dict(email="test.four@fintech.example", company_name="Fintech Inc", role="Data Scientist",
          company_size="50-249", tried_tabpfn=config.ALREADY_USING,
          use_case="Customer churn prediction for our app users"),
     "finance", "United States", SE, None),
    ("5. Account Manager, retail company, not yet, vague use case",
     dict(email="test.five@retailer.example", company_name="Retailer Ltd", role="Account Manager",
          company_size="50-249", tried_tabpfn="Not yet", use_case="Evaluating AI tools for the team"),
     "retail", "United Kingdom", NURTURE, None),
    ("6. Innovation Manager, 1000+ industrial company, not yet, predictive maintenance",
     dict(email="test.six@industrial.example", company_name="Industrial SE", role="Innovation Manager",
          company_size="1000+", tried_tabpfn="Not yet", use_case="Predictive maintenance for our machines"),
     "industrials", "Germany", REVIEW, 72),   # was AE until the AE threshold moved from 70 to 75
    ("7. Gmail freelancer, already using, churn",
     dict(email="test.seven@gmail.com", company_name="Self-employed", role="Freelance Data Scientist",
          company_size="1-49", tried_tabpfn=config.ALREADY_USING,
          use_case="Churn prediction for e-commerce clients"),
     None, None, REVIEW, 49),   # was 46 until "other industry" points went from 2 to 5
]


def main():
    passed = 0
    for description, lead, industry, country, expected_route, expected_score in TEST_CASES:
        result = evaluate_lead(lead, industry, country)
        ok = result["route"] == expected_route and (expected_score is None or result["fit_score"] == expected_score)
        passed += ok

        print(f"\n{'PASS' if ok else 'FAIL'}  {description}")
        print(f"   Score:  {result['score_breakdown']}")
        print(f"   Route:  {result['route']}  ({result['reason']})")
        print(f"   Team:   {result['team']}  |  Category: {result['use_case_category']}"
              + (f"  |  Flags: {result['flags']}" if result["flags"] else ""))
        if not ok:
            print(f"   Expected: {expected_route}" + (f", score {expected_score}" if expected_score else ""))

    print(f"\n{passed}/{len(TEST_CASES)} test cases passed")
    sys.exit(0 if passed == len(TEST_CASES) else 1)


if __name__ == "__main__":
    main()
