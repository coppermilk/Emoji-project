"""The matching pass and the three rendering styles."""

import unittest

from emojimail import lexicon
from emojimail.emailparse import ParsedEmail, parse
from emojimail.translate import (
    STYLES,
    _graphemes,
    coverage,
    find_matches,
    render_full,
    render_inline,
    summarize,
    translate,
    translate_email,
)


class MatchingTests(unittest.TestCase):
    def test_matches_are_in_reading_order(self):
        matches = find_matches("meeting tomorrow about the invoice")
        starts = [m.start for m in matches]
        self.assertEqual(starts, sorted(starts))

    def test_matches_do_not_overlap(self):
        matches = find_matches("please pay the $40.00 invoice by 3:30pm tomorrow")
        for earlier, later in zip(matches, matches[1:]):
            self.assertLessEqual(earlier.end, later.start)

    def test_phrase_beats_the_words_inside_it(self):
        matches = find_matches("I am out of office until Monday")
        sources = [m.source.lower() for m in matches]
        self.assertIn("out of office", sources)
        self.assertNotIn("office", sources)

    def test_phrase_needs_adjacent_words(self):
        # Punctuation between the words means it is not really the phrase.
        matches = find_matches("out. of. office.")
        self.assertNotIn("out. of. office", [m.source.lower() for m in matches])

    def test_patterns_beat_word_lookups(self):
        matches = {m.kind: m for m in find_matches("write to bob@example.com today")}
        self.assertIn("email", matches)
        self.assertEqual(matches["email"].source, "bob@example.com")

    def test_money_time_and_urls(self):
        kinds = {m.kind for m in find_matches("$1,240.00 at 3:30pm see https://a.example")}
        self.assertLessEqual({"money", "time", "url"}, kinds)

    def test_empty_text_has_no_matches(self):
        self.assertEqual(find_matches(""), [])


class CoverageTests(unittest.TestCase):
    def test_coverage_is_a_fraction(self):
        ratio, matched, total = coverage("meeting tomorrow about the invoice")
        self.assertGreater(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)
        self.assertLessEqual(matched, total)

    def test_unknown_text_has_zero_coverage(self):
        ratio, matched, _ = coverage("zzyzx qwertyuiop flibbertigibbet")
        self.assertEqual(matched, 0)
        self.assertEqual(ratio, 0.0)

    def test_no_content_words(self):
        self.assertEqual(coverage("the and of"), (0.0, 0, 0))


class InlineStyleTests(unittest.TestCase):
    def test_original_words_survive(self):
        out = render_inline("The meeting is tomorrow")
        for word in ("The", "meeting", "is", "tomorrow"):
            self.assertIn(word, out)

    def test_emoji_follows_its_word(self):
        out = render_inline("meeting")
        self.assertEqual(out, "meeting " + lexicon.WORDS["meeting"])

    def test_unmatched_text_is_untouched(self):
        self.assertEqual(render_inline("zzyzx qwertyuiop"), "zzyzx qwertyuiop")

    def test_punctuation_is_preserved(self):
        self.assertTrue(render_inline("Is the meeting today?").endswith("?"))


class FullStyleTests(unittest.TestCase):
    def test_no_ascii_letters_remain(self):
        out = render_full("The urgent meeting is tomorrow about the invoice")
        self.assertFalse(any(ch.isascii() and ch.isalpha() for ch in out))
        self.assertTrue(out)

    def test_line_structure_is_kept(self):
        out = render_full("meeting tomorrow\ninvoice today")
        self.assertEqual(len(out.splitlines()), 2)

    def test_question_marks_become_emoji(self):
        self.assertIn("❓", render_full("is the meeting today?"))

    def test_repeated_emoji_collapse(self):
        # "invoice" and "bill" are both receipts; do not print two in a row.
        out = render_full("invoice bill")
        self.assertEqual(out, lexicon.WORDS["invoice"])

    def test_unmatched_line_is_dropped(self):
        self.assertEqual(render_full("zzyzx qwertyuiop"), "")


class SummaryTests(unittest.TestCase):
    def test_summary_is_emoji_only(self):
        summary = summarize(parse("Subject: invoice overdue\n\nPlease pay the bill."))
        self.assertTrue(summary)
        self.assertFalse(any(ch.isascii() and ch.isalpha() for ch in summary))

    def test_summary_has_no_repeated_emoji(self):
        text = "Subject: your order has shipped\n\nYour package is out for delivery. Tracking number 1Z999."
        graphemes = _graphemes(summarize(parse(text)))
        self.assertEqual(len(graphemes), len(set(graphemes)), graphemes)

    def test_summary_is_deterministic(self):
        parsed = parse("Subject: invoice overdue\n\nPlease pay the bill urgently.")
        self.assertEqual(summarize(parsed), summarize(parsed))

    def test_category_banner_leads(self):
        parsed = parse("Subject: invoice 12 overdue\n\nPayment for the bill is due.")
        self.assertTrue(summarize(parsed).startswith(lexicon.CATEGORIES["billing"][0]))

    def test_urgency_is_flagged(self):
        urgent = summarize(parse("Subject: URGENT\n\nThis is critical, respond immediately."))
        self.assertIn("\U0001F6A8", urgent)

    def test_question_is_flagged(self):
        self.assertIn("❓", summarize(parse("Are you free on Tuesday?")))

    def test_empty_mail_falls_back(self):
        self.assertTrue(summarize(ParsedEmail()))


class TranslateEmailTests(unittest.TestCase):
    RAW = "Subject: invoice overdue\n\nPlease pay the $40.00 bill by tomorrow."

    def test_every_style_produces_output(self):
        for style in STYLES:
            with self.subTest(style=style):
                result = translate(self.RAW, style=style)
                self.assertTrue(result.summary)
                self.assertEqual(result.style, style)

    def test_summary_style_leaves_body_empty(self):
        self.assertEqual(translate(self.RAW, "summary").body, "")

    def test_full_style_body_has_no_words(self):
        body = translate(self.RAW, "full").body
        self.assertFalse(any(ch.isascii() and ch.isalpha() for ch in body))

    def test_inline_style_keeps_the_subject_text(self):
        self.assertIn("invoice", translate(self.RAW, "inline").subject)

    def test_full_style_falls_back_to_summary(self):
        result = translate("zzyzx qwertyuiop", "full")
        self.assertEqual(result.body, result.summary)

    def test_unknown_style_is_rejected(self):
        with self.assertRaises(ValueError):
            translate_email(parse(self.RAW), style="hieroglyphs")

    def test_categories_are_detected(self):
        self.assertIn("billing", translate(self.RAW).categories)

    def test_eml_bytes_work_too(self):
        raw = b"From: a@b.c\nSubject: Invoice\n\nPay the bill."
        self.assertTrue(translate(raw).summary)


class GraphemeTests(unittest.TestCase):
    def test_variation_selector_stays_attached(self):
        self.assertEqual(_graphemes("✈️"), ["✈️"])

    def test_zero_width_joiner_sequence_is_one_grapheme(self):
        self.assertEqual(len(_graphemes("\U0001F9D1‍\U0001F4BC")), 1)

    def test_keycap_is_one_grapheme(self):
        self.assertEqual(len(_graphemes("1️⃣")), 1)

    def test_separate_emoji_stay_separate(self):
        self.assertEqual(len(_graphemes("\U0001F4C5\U0001F9FE")), 2)


if __name__ == "__main__":
    unittest.main()
