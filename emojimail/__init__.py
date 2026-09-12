"""emojimail -- translate emails into emoji, offline.

    >>> from emojimail import translate
    >>> translate("Subject: lunch tomorrow?").summary
    '🌅🍽️❓'

The whole pipeline is ``parse`` -> ``find_matches`` -> render, with no network
call and no third-party dependency anywhere in it.
"""

from .emailparse import ParsedEmail, parse
from .translate import (
    STYLES,
    Match,
    Translation,
    find_matches,
    summarize,
    translate,
    translate_email,
)

__version__ = "0.1.0"

__all__ = [
    "STYLES",
    "Match",
    "ParsedEmail",
    "Translation",
    "find_matches",
    "parse",
    "summarize",
    "translate",
    "translate_email",
    "__version__",
]
