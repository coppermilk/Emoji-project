"""The translator: text in, emoji out.

Matching happens in one left-to-right pass over the raw text so that every
match keeps its original character offsets. That is what lets ``inline`` style
rebuild the message with emoji slotted in beside the words they came from,
while ``full`` and ``summary`` reuse the very same match list.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from . import lexicon
from .emailparse import ParsedEmail, parse

STYLES = ("summary", "inline", "full")

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")
_SENTENCE_END_RE = re.compile(r"[?!]")

#: Emoji used as the banner when nothing else matched.
FALLBACK = "\U0001F4E7\U0001F937"


@dataclass(frozen=True)
class Match:
    """One stretch of source text and the emoji it translated to."""

    start: int
    end: int
    emoji: str
    source: str
    #: "pattern", "phrase" or "word" -- mostly useful for debugging the lexicon.
    kind: str


@dataclass
class Translation:
    """The result of translating one email."""

    summary: str = ""
    subject: str = ""
    body: str = ""
    style: str = "summary"
    categories: list = field(default_factory=list)
    coverage: float = 0.0
    matched: int = 0
    total: int = 0


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def _pattern_matches(text):
    """Regex hits (URLs, money, times...), which outrank word lookups."""
    found = []
    taken = []
    for kind, regex, emoji in lexicon.PATTERNS:
        for hit in regex.finditer(text):
            span = (hit.start(), hit.end())
            if any(span[0] < end and start < span[1] for start, end in taken):
                continue
            taken.append(span)
            found.append(Match(span[0], span[1], emoji, hit.group(0), kind))
    return found


def _only_spaces(text):
    return text != "" and text.strip(" \t") == ""


def _phrase_and_word_matches(words, text, blocked):
    """Greedy longest-phrase matching, falling back to single words."""
    found = []
    index = 0
    while index < len(words):
        word = words[index]
        if any(word.start() < end and start < word.end() for start, end in blocked):
            index += 1
            continue

        matched = False
        # Try the longest phrase that still fits, so "out of office" is
        # preferred over "office".
        for size in lexicon.PHRASES_BY_LENGTH:
            if index + size > len(words):
                continue
            group = words[index : index + size]
            # Phrase words must be separated by spaces only; punctuation in
            # between means they are not really one phrase.
            gaps = [
                text[group[i].end() : group[i + 1].start()]
                for i in range(len(group) - 1)
            ]
            if not all(_only_spaces(gap) for gap in gaps):
                continue
            key = " ".join(w.group(0).lower() for w in group)
            emoji = lexicon.PHRASES.get(key)
            if emoji:
                found.append(
                    Match(
                        group[0].start(),
                        group[-1].end(),
                        emoji,
                        text[group[0].start() : group[-1].end()],
                        "phrase",
                    )
                )
                index += size
                matched = True
                break
        if matched:
            continue

        emoji = lexicon.lookup_word(word.group(0))
        if emoji:
            found.append(
                Match(word.start(), word.end(), emoji, word.group(0), "word")
            )
        index += 1
    return found


def find_matches(text):
    """Return every non-overlapping match in ``text``, in reading order."""
    if not text:
        return []
    patterns = _pattern_matches(text)
    blocked = [(m.start, m.end) for m in patterns]
    words = list(_WORD_RE.finditer(text))
    lexical = _phrase_and_word_matches(words, text, blocked)
    return sorted(patterns + lexical, key=lambda m: m.start)


def coverage(text, matches=None):
    """Fraction of content words that found an emoji, plus the raw counts."""
    matches = find_matches(text) if matches is None else matches
    content = [
        w.group(0)
        for w in _WORD_RE.finditer(text)
        if w.group(0).lower() not in lexicon.STOPWORDS and len(w.group(0)) > 1
    ]
    if not content:
        return 0.0, 0, 0
    matched = sum(
        len(_WORD_RE.findall(m.source)) for m in matches if m.kind != "pattern"
    )
    matched = min(matched, len(content))
    return matched / len(content), matched, len(content)


# --------------------------------------------------------------------------
# Signals used by the summary
# --------------------------------------------------------------------------


def _stems(text):
    return Counter(lexicon.stem(w.group(0)) for w in _WORD_RE.finditer(text))


def _is_shouty(text):
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 8:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) > 0.6


def detect_categories(parsed, limit=2):
    """Rank the topic categories this mail belongs to, strongest first."""
    # Subject words count double: they are the author's own summary.
    stems = _stems(parsed.body)
    stems.update({k: v * 2 for k, v in _stems(parsed.subject).items()})

    scores = {}
    for name, (_, triggers) in lexicon.CATEGORIES.items():
        score = sum(count for stem, count in stems.items() if stem in triggers)
        if score:
            scores[name] = score
    ranked = sorted(scores, key=lambda n: (-scores[n], n))
    return ranked[:limit]


def _urgency_emoji(parsed):
    stems = _stems(parsed.text)
    if any(stem in lexicon.URGENT_WORDS for stem in stems):
        return "\U0001F6A8"
    if "!!" in parsed.text or _is_shouty(parsed.subject):
        return "❗"
    return ""


def _action_emoji(parsed):
    if "?" in parsed.text:
        return "❓"
    stems = _stems(parsed.text)
    if any(stem in lexicon.ACTION_WORDS for stem in stems):
        return "\U0001F64B"
    return ""


def _sentiment_emoji(parsed):
    stems = _stems(parsed.text)
    positive = sum(c for s, c in stems.items() if s in lexicon.POSITIVE_WORDS)
    negative = sum(c for s, c in stems.items() if s in lexicon.NEGATIVE_WORDS)
    if positive > negative * 2 and positive:
        return "\U0001F389"
    if negative > positive * 2 and negative:
        return "\U0001F61F"
    return ""


def _graphemes(text):
    """Split a string into user-perceived characters.

    Lexicon entries like "out for delivery" are two emoji in one string, so
    de-duplicating whole entries is not enough to stop the same truck showing
    up three times in a summary. Joiners, variation selectors, keycaps and skin
    tone modifiers all glue onto the character before them.
    """
    out = []
    for ch in text:
        glue = (
            ch in "\uFE0F\u200D\u20E3"
            or unicodedata.category(ch) in ("Mn", "Sk")
            or (out and out[-1].endswith("\u200D"))
        )
        if out and glue:
            out[-1] += ch
        else:
            out.append(ch)
    return out


def _dedupe(sequence):
    """Order-preserving de-duplication."""
    seen = set()
    out = []
    for item in sequence:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def summarize(parsed, topics=5):
    """Build the one-line emoji gist of a mail.

    Reads left to right as: what kind of mail it is, what it is about, how
    urgent it is, whether it wants something from you, and how it feels.
    """
    head = [lexicon.CATEGORIES[name][0] for name in detect_categories(parsed)]

    # Topic emoji, ranked by how often they appear, subject weighted heavier
    # because it is the author's own summary of the mail.
    counts = Counter()
    for weight, chunk in ((3, parsed.subject), (1, parsed.body)):
        for match in find_matches(chunk):
            counts[match.emoji] += weight
    ranked = sorted(counts, key=lambda e: (-counts[e], e))
    head.extend(e for e in ranked if e not in lexicon.SUMMARY_SKIP)

    # Signals go last so the line reads "what it is, then what it wants".
    tail = [
        _urgency_emoji(parsed),
        _action_emoji(parsed),
        _sentiment_emoji(parsed),
    ]

    kept = _dedupe(_graphemes("".join(head)))[: topics + 2]
    kept = _dedupe(kept + _graphemes("".join(tail)))
    return "".join(kept) or FALLBACK


# --------------------------------------------------------------------------
# Rendering styles
# --------------------------------------------------------------------------


def render_inline(text):
    """Keep the original wording, slot each emoji in beside its word."""
    matches = find_matches(text)
    if not matches:
        return text
    out = []
    cursor = 0
    for match in matches:
        out.append(text[cursor : match.end])
        out.append(" " + match.emoji)
        cursor = match.end
    out.append(text[cursor:])
    return "".join(out)


def render_full(text):
    """Emoji only. Line breaks survive; everything else becomes pictures."""
    lines = []
    for line in text.splitlines():
        emoji = [m.emoji for m in find_matches(line)]
        # Punctuation carries tone, so keep the shouting and the asking.
        for mark in _SENTENCE_END_RE.findall(line):
            emoji.append("❓" if mark == "?" else "❗")
        rendered = "".join(_collapse_repeats(emoji))
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def _collapse_repeats(sequence):
    """Drop an emoji that immediately repeats the one before it."""
    out = []
    for item in sequence:
        if not out or out[-1] != item:
            out.append(item)
    return out


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------


def translate_email(parsed, style="summary"):
    """Translate a :class:`ParsedEmail` in the requested style."""
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; expected one of {STYLES}")

    ratio, matched, total = coverage(parsed.text)
    result = Translation(
        summary=summarize(parsed),
        style=style,
        categories=detect_categories(parsed),
        coverage=ratio,
        matched=matched,
        total=total,
    )

    if style == "summary":
        result.subject = summarize(ParsedEmail(subject=parsed.subject)) if parsed.subject else ""
        result.body = ""
    elif style == "inline":
        result.subject = render_inline(parsed.subject)
        result.body = render_inline(parsed.body)
    else:  # full
        result.subject = render_full(parsed.subject)
        result.body = render_full(parsed.body) or result.summary
    return result


def translate(raw, style="summary"):
    """Parse ``raw`` (``.eml`` bytes or pasted text) and translate it."""
    return translate_email(parse(raw), style=style)
