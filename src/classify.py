"""
Reads a lead's free text: use case category + keyword flags.
Also holds has_keyword(), the whole-word matching helper used by the other files.
"""

import re

import config


def has_keyword(text, keywords):
    """True if any keyword appears in the text as a whole word (ignoring upper/lower case)."""
    text = str(text).lower()
    for keyword in keywords:
        # "whole word" = no letter or digit right before or after it
        if re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text):
            return True
    return False


def classify_use_case(use_case):
    """'Load forecasting from smart meter data' -> 'forecasting'. No match -> 'other'."""
    for category, keywords in config.USE_CASE_KEYWORDS.items():  # checked in order, first match wins
        if has_keyword(use_case, keywords):
            return category
    return "other"


def keyword_flags(use_case):
    """'Credit model, must run on-prem' -> ['deployment/compliance']."""
    return [flag for flag, keywords in config.FLAG_KEYWORDS.items() if has_keyword(use_case, keywords)]
