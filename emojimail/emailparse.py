"""Turn whatever the user hands us into a ``ParsedEmail``.

Two shapes arrive in practice:

* a real ``.eml`` file (RFC 5322), which ``email.parser`` handles for us; and
* text pasted into a chat window, which may or may not carry ``Subject:`` style
  header lines at the top.

Both end up as the same small dataclass so the translator does not care which
one it got.
"""

import email
import email.policy
import html
import re
from dataclasses import dataclass, field

#: Header lines people actually paste along with a forwarded mail.
_PASTED_HEADER_RE = re.compile(
    r"^\s*(from|to|cc|bcc|subject|date|sent|reply-to)\s*:\s*(.*)$", re.I
)

#: A line that is part of a quoted reply chain.
_QUOTE_RE = re.compile(r"^\s*>")

#: "On <date>, <someone> wrote:" attribution above a quoted reply.
_ATTRIBUTION_RE = re.compile(
    r"^\s*(on .{5,120}\bwrote:|-{2,}\s*(original|forwarded) message\s*-{2,})\s*$",
    re.I,
)

#: The conventional "-- " signature delimiter.
_SIG_RE = re.compile(r"^--\s?$")

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_BLOCK_END_RE = re.compile(r"</(p|div|tr|li|h[1-6])\s*>|<br\s*/?>", re.I)


@dataclass
class ParsedEmail:
    """A mail reduced to the bits worth translating."""

    subject: str = ""
    sender: str = ""
    recipient: str = ""
    date: str = ""
    body: str = ""
    #: Filenames of non-inline attachments, if any.
    attachments: list = field(default_factory=list)

    @property
    def text(self):
        """Subject and body together, for whole-message signal detection."""
        return f"{self.subject}\n{self.body}".strip()


def html_to_text(markup):
    """Flatten HTML into something close enough to plain text for matching."""
    text = _SCRIPT_RE.sub(" ", markup)
    text = _BLOCK_END_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def strip_quoted(body, keep_signature=False):
    """Drop quoted reply chains and the trailing signature block.

    Quoted history is almost always someone *else's* words, so translating it
    buries the part the user actually received.
    """
    lines = []
    for line in body.splitlines():
        if _ATTRIBUTION_RE.match(line):
            break
        if not keep_signature and _SIG_RE.match(line):
            break
        if _QUOTE_RE.match(line):
            continue
        lines.append(line)
    # Collapse the blank lines the removals leave behind.
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_like_eml(raw):
    """True if ``raw`` starts with something that parses as a mail header block."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "replace")
        except Exception:
            return False
    head = raw.lstrip()[:2000]
    if not head:
        return False
    # A real .eml has several headers before the first blank line.
    header_block = head.split("\n\n", 1)[0]
    hits = sum(
        1
        for line in header_block.splitlines()
        if re.match(r"^[A-Za-z-]{2,40}:\s", line)
    )
    return hits >= 2


def _best_body(message):
    """Pick the most readable body part out of a possibly multipart message."""
    if not message.is_multipart():
        payload = message.get_content()
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        if message.get_content_type() == "text/html":
            return html_to_text(payload)
        return payload

    plain, rich = None, None
    for part in message.walk():
        if part.is_multipart():
            continue
        if part.get_filename():
            continue
        ctype = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:
            continue
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        if ctype == "text/plain" and plain is None:
            plain = payload
        elif ctype == "text/html" and rich is None:
            rich = html_to_text(payload)
    return plain if plain is not None else (rich or "")


def parse_eml(raw):
    """Parse RFC 5322 bytes or text into a :class:`ParsedEmail`."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "replace")
    message = email.message_from_bytes(raw, policy=email.policy.default)

    attachments = []
    if message.is_multipart():
        for part in message.walk():
            name = part.get_filename()
            if name:
                attachments.append(name)

    return ParsedEmail(
        subject=str(message.get("Subject", "") or "").strip(),
        sender=str(message.get("From", "") or "").strip(),
        recipient=str(message.get("To", "") or "").strip(),
        date=str(message.get("Date", "") or "").strip(),
        body=strip_quoted(_best_body(message)),
        attachments=attachments,
    )


def parse_pasted(text):
    """Parse loose text, honouring ``Subject:``-style lines if the user kept them."""
    lines = text.splitlines()
    headers = {}
    index = 0
    # Only treat the very top of the message as headers, and only while every
    # line still looks like one -- a body sentence containing a colon must not
    # swallow the rest of the mail.
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            if headers:
                index += 1
            break
        match = _PASTED_HEADER_RE.match(line)
        if not match:
            break
        headers[match.group(1).lower()] = match.group(2).strip()
        index += 1

    body = "\n".join(lines[index:])
    return ParsedEmail(
        subject=headers.get("subject", ""),
        sender=headers.get("from", ""),
        recipient=headers.get("to", ""),
        date=headers.get("date", headers.get("sent", "")),
        body=strip_quoted(body),
    )


def parse(raw):
    """Parse ``raw`` as an ``.eml`` when it looks like one, else as pasted text."""
    if isinstance(raw, bytes):
        if looks_like_eml(raw):
            return parse_eml(raw)
        raw = raw.decode("utf-8", "replace")
    if looks_like_eml(raw):
        return parse_eml(raw)
    return parse_pasted(raw)
