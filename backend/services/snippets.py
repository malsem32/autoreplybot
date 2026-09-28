"""Quick phrases (AGENTS.md 4.17): the owner sends `!shortcut` from any of
their devices and the worker replaces that message with the saved text."""

import re

TRIGGER_PREFIX = "!"
FREE_MAX_SNIPPETS = 3
PRO_MAX_SNIPPETS = 100
SHORTCUT_RE = re.compile(r"^[0-9a-zа-яё_]{1,32}$")


def normalize_shortcut(value: str) -> str:
    return value.strip().removeprefix(TRIGGER_PREFIX).lower()


def parse_trigger(text: str | None) -> str | None:
    """The shortcut if the whole message is `!shortcut`, else None — so a
    "!" inside normal text never fires."""
    if not text or not text.startswith(TRIGGER_PREFIX):
        return None
    shortcut = text[len(TRIGGER_PREFIX) :].strip().lower()
    return shortcut if SHORTCUT_RE.match(shortcut) else None
