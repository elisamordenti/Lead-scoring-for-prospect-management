# TabPFN vs standard baselines: lead conversion prediction

**Dataset:** Kaggle *Lead Scoring Dataset* (X Education, an online-course company): 9,240 real, anonymized leads; 39% converted. Public data, not Prior Labs' data, and it does **not** score the fake leads.

**Setup:** same stratified 80/20 split for every model (1,848 test leads). 20 columns known at sign-up time; columns filled in later by the sales team (Tags, Lead Quality, activity scores, last activity) were dropped to avoid leakage. TabPFN runs with default settings through the Prior Labs API; baselines are scikit-learn defaults.

**Metric:** ROC-AUC = how well the model ranks converters above non-converters (1.0 = perfect, 0.5 = random). Accuracy at a 0.5 threshold shown for reference.

| Training leads | Model | ROC-AUC | Accuracy | Time (s) |
|---|---|---|---|---|
| 100 | Logistic regression | 0.768 | 0.731 | 0.1 |
| 100 | Gradient boosting (trees) | 0.784 | 0.727 | 0.2 |
| 100 | TabPFN (API) | 0.803 | 0.778 | 14.6 |
| 500 | Logistic regression | 0.809 | 0.767 | 0.1 |
| 500 | Gradient boosting (trees) | 0.831 | 0.772 | 0.6 |
| 500 | TabPFN (API) | 0.852 | 0.795 | 4.9 |
| 7,392 | Logistic regression | 0.827 | 0.776 | 0.2 |
| 7,392 | Gradient boosting (trees) | 0.859 | 0.794 | 0.7 |
| 7,392 | TabPFN (API) | 0.869 | 0.803 | 12.3 |

## Reading

- **100 training leads:** TabPFN is best (TabPFN 0.803 vs best baseline 0.784; best overall: TabPFN (API)).
- **500 training leads:** TabPFN is best (TabPFN 0.852 vs best baseline 0.831; best overall: TabPFN (API)).
- **7,392 training leads:** TabPFN and the best baseline are within 0.01 (practically a tie) (TabPFN 0.869 vs best baseline 0.859; best overall: TabPFN (API)).

## Limits

- One dataset, one split: differences of ~0.01 AUC are within noise.
- A different business (online courses, B2C) from Prior Labs (B2B, enterprise).
- No tuning for any model; a tuned baseline might do better, and so might TabPFN's advanced options.
- Next step with real data: train on Prior Labs' own won/lost deals and add the probability as a predictive score next to the rule-based fit score.
