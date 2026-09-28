"""Keyword matching shared by the worker (workers/responder.py) and the
rule tester in the Mini App (POST /api/autoresponder/{id}/test), so the
tester says exactly what the autopilot will do."""

import re

MATCH_MODES = ("contains", "word", "exact")


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


def keyword_hit(keyword: str, text: str, mode: str) -> bool:
    kw, msg = _normalize(keyword), _normalize(text)
    if not kw:
        return False
    if mode == "exact":
        return msg == kw
    if mode == "word":
        # Whole word/phrase: not glued to letters or digits on either side.
        return re.search(rf"(?<![\w]){re.escape(kw)}(?![\w])", msg) is not None
    return kw in msg


def matched_keyword(trigger_type: str, keywords: list[str], mode: str, text: str) -> str | None:
    """The keyword that fired, "" for trigger_type "all", None for no match."""
    if trigger_type == "all":
        return ""
    return next((k for k in keywords if keyword_hit(k, text, mode)), None)


def matches(trigger_type: str, keywords: list[str], mode: str, text: str) -> bool:
    return matched_keyword(trigger_type, keywords, mode, text) is not None
