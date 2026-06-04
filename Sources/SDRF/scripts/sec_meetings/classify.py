"""
Classification of a free-text work/scheme description into:
  - work_type      (what kind of work)
  - disaster_phase (preparedness / mitigation / response-repair-restoration)

Rule-based and deterministic. The same rubric (config.py) is also handed to
the LLM extractor, so an LLM run and an offline run produce comparable labels.
A confidence flag is returned so ambiguous items can be reviewed.
"""
from __future__ import annotations
from typing import Tuple
import config


def _match(text: str, rules) -> Tuple[str, int]:
    """Return (label, num_keyword_hits) for the first rule with any hit."""
    low = (text or "").lower()
    for label, keywords in rules:
        hits = sum(1 for k in keywords if k in low)
        if hits:
            return label, hits
    return None, 0


def classify_work_type(text: str) -> str:
    label, _ = _match(text, config.WORK_TYPE_RULES)
    return label or config.WORK_TYPE_DEFAULT


def classify_phase(text: str) -> str:
    label, _ = _match(text, config.PHASE_RULES)
    return label or config.PHASE_DEFAULT


def classify(text: str) -> dict:
    """Full classification with a crude confidence signal.

    confidence = 'low' when nothing matched, 'medium' for a single weak hit,
    'high' when both work-type and phase matched. Lets you filter the long
    tail of ambiguous descriptions for manual / LLM review.
    """
    wt, wt_hits = _match(text, config.WORK_TYPE_RULES)
    ph, ph_hits = _match(text, config.PHASE_RULES)
    if wt and ph:
        conf = "high"
    elif wt or ph:
        conf = "medium"
    else:
        conf = "low"
    return {
        "work_type": wt or config.WORK_TYPE_DEFAULT,
        "disaster_phase": ph or config.PHASE_DEFAULT,
        "classify_confidence": conf,
    }
