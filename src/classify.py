"""
Reads a lead's free text: use case category + keyword flags.
Also holds has_keyword(), the whole-word matching helper used by the other files.
"""

import re

import pandas as pd

import config


def has_keyword(text, keywords):
    """True if any keyword appears in the text as a whole word, with an optional plural "s"
    (ignoring upper/lower case). So "loan" matches "Loans" but not "loaned"."""
    text = str(text).lower()
    for keyword in keywords:
        # "whole word" = no letter or digit right before or after it
        if re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"s?(?![a-z0-9])", text):
            return True
    return False


def is_empty(use_case):
    """The use case field can be missing from some versions of the form, or left blank."""
    return use_case is None or pd.isna(use_case) or not str(use_case).strip()


def classify_use_case(use_case):
    """'Load forecasting from smart meter data' -> 'forecasting'.
    No target match -> 'generic_tabular' if it's still a prediction task, otherwise 'other'.
    Empty -> 'not provided'."""
    if is_empty(use_case):
        return config.NOT_PROVIDED
    for category, keywords in config.USE_CASE_KEYWORDS.items():  # checked in order, first match wins
        if has_keyword(use_case, keywords):
            return category
    if has_keyword(use_case, config.GENERIC_TABULAR_KEYWORDS):
        return config.GENERIC_TABULAR
    return "other"


def keyword_flags(use_case):
    """'Credit model, must run on-prem' -> ['deployment/compliance']."""
    if is_empty(use_case):
        return []
    return [flag for flag, keywords in config.FLAG_KEYWORDS.items() if has_keyword(use_case, keywords)]
