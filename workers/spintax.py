import random
import re

_SPINTAX_RE = re.compile(r"\{([^{}]+)\}")


def render_spintax(text: str) -> str:
    """Resolves `{a|b|c}` groups to a random choice, recursively (for nested groups)."""
    while _SPINTAX_RE.search(text):
        text = _SPINTAX_RE.sub(lambda m: random.choice(m.group(1).split("|")), text)
    return text
