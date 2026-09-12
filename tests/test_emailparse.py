"""Parsing .eml files and pasted text."""

import unittest

from emojimail import emailparse

EML = b"""From: billing@acme.com
To: bob@example.com
Subject: Invoice 4471
Date: Tue, 11 Mar 2025 09:14:02 +0000
Content-Type: text/plain; charset="utf-8"

Your invoice is past due.

> quoted history here
> more history

-- 
Acme Billing
"""

MULTIPART = b"""From: deals@shop.example
Subject: Sale
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="b1"

--b1
Content-Type: text/plain; charset="utf-8"

Plain body wins.
--b1
Content-Type: text/html; charset="utf-8"

<html><body><p>HTML body loses.</p></body></html>
--b1--
"""

HTML_ONLY = b"""From: news@site.example
Subject: Digest
Content-Type: text/html; charset="utf-8"

<html><body><h1>Weekly digest</h1><p>Two new &amp; shiny posts.</p>
<script>ignore()</script></body></html>
"""


class EmlTests(unittest.TestCase):
    def test_headers(self):
        parsed = emailparse.parse(EML)
        self.assertEqual(parsed.subject, "Invoice 4471")
        self.assertEqual(parsed.sender, "billing@acme.com")
        self.assertEqual(parsed.recipient, "bob@example.com")
        self.assertIn("2025", parsed.date)

    def test_quoted_history_and_signature_removed(self):
        parsed = emailparse.parse(EML)
        self.assertIn("past due", parsed.body)
        self.assertNotIn("quoted history", parsed.body)
        self.assertNotIn("Acme Billing", parsed.body)

    def test_multipart_prefers_plain_text(self):
        parsed = emailparse.parse(MULTIPART)
        self.assertIn("Plain body wins", parsed.body)
        self.assertNotIn("HTML body loses", parsed.body)

    def test_html_only_is_flattened(self):
        parsed = emailparse.parse(HTML_ONLY)
        self.assertIn("Weekly digest", parsed.body)
        self.assertIn("Two new & shiny posts", parsed.body)
        self.assertNotIn("<p>", parsed.body)
        self.assertNotIn("ignore()", parsed.body)

    def test_attachments_are_listed(self):
        raw = (
            b'From: a@b.c\nSubject: Files\nMIME-Version: 1.0\n'
            b'Content-Type: multipart/mixed; boundary="x"\n\n'
            b'--x\nContent-Type: text/plain\n\nSee attached.\n'
            b'--x\nContent-Type: application/pdf\n'
            b'Content-Disposition: attachment; filename="report.pdf"\n\n%PDF-1.4\n'
            b'--x--\n'
        )
        parsed = emailparse.parse(raw)
        self.assertEqual(parsed.attachments, ["report.pdf"])
        self.assertIn("See attached", parsed.body)


class PastedTextTests(unittest.TestCase):
    def test_plain_note_has_no_subject(self):
        parsed = emailparse.parse("just a note about lunch tomorrow")
        self.assertEqual(parsed.subject, "")
        self.assertEqual(parsed.body, "just a note about lunch tomorrow")

    def test_pasted_headers_are_honoured(self):
        parsed = emailparse.parse("Subject: Hello\nFrom: a@b.c\n\nBody here.")
        self.assertEqual(parsed.subject, "Hello")
        self.assertEqual(parsed.body, "Body here.")

    def test_body_colon_does_not_become_a_header(self):
        # A body sentence with a colon must not swallow the rest of the mail.
        text = "Note: I will be late\nand here is the rest of the message"
        parsed = emailparse.parse(text)
        self.assertIn("rest of the message", parsed.body)

    def test_reply_attribution_truncates(self):
        text = "My answer is yes.\nOn Mon, Mar 10, Sam wrote:\nthe original question"
        parsed = emailparse.parse(text)
        self.assertIn("My answer is yes", parsed.body)
        self.assertNotIn("original question", parsed.body)

    def test_empty_input(self):
        parsed = emailparse.parse("")
        self.assertEqual(parsed.body, "")
        self.assertEqual(parsed.text, "")


class DetectionTests(unittest.TestCase):
    def test_looks_like_eml(self):
        self.assertTrue(emailparse.looks_like_eml(EML))
        self.assertFalse(emailparse.looks_like_eml("hey are we still on for lunch?"))
        self.assertFalse(emailparse.looks_like_eml(""))


if __name__ == "__main__":
    unittest.main()
