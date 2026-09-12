"""Checks on the lexicon tables themselves."""

import unittest

from emojimail import lexicon


class TableIntegrityTests(unittest.TestCase):
    def test_no_empty_entries(self):
        for table_name in ("WORDS", "PHRASES"):
            table = getattr(lexicon, table_name)
            for key, value in table.items():
                self.assertTrue(key.strip(), f"empty key in {table_name}")
                self.assertTrue(value.strip(), f"{table_name}[{key!r}] is empty")

    def test_keys_are_lowercase(self):
        for table_name in ("WORDS", "PHRASES"):
            for key in getattr(lexicon, table_name):
                self.assertEqual(key, key.lower(), f"{key!r} is not lowercase")

    def test_phrases_are_multiword(self):
        for phrase in lexicon.PHRASES:
            self.assertGreater(len(phrase.split()), 1, f"{phrase!r} is a single word")

    def test_entries_contain_no_ascii_letters(self):
        # A mapping that leaks letters would put words back into "full" style.
        for table_name in ("WORDS", "PHRASES"):
            for key, value in getattr(lexicon, table_name).items():
                self.assertFalse(
                    any(ch.isascii() and ch.isalpha() for ch in value),
                    f"{table_name}[{key!r}] = {value!r} contains ASCII letters",
                )

    def test_stopwords_have_no_emoji(self):
        overlap = set(lexicon.STOPWORDS) & set(lexicon.WORDS)
        self.assertEqual(overlap, set(), f"stopwords also in WORDS: {overlap}")

    def test_phrase_lengths_are_sorted_longest_first(self):
        self.assertEqual(
            lexicon.PHRASES_BY_LENGTH, sorted(lexicon.PHRASES_BY_LENGTH, reverse=True)
        )


class StemmingTests(unittest.TestCase):
    def test_plurals(self):
        self.assertEqual(lexicon.lookup_word("meetings"), lexicon.WORDS["meeting"])
        self.assertEqual(lexicon.lookup_word("invoices"), lexicon.WORDS["invoice"])

    def test_verb_tenses(self):
        self.assertEqual(lexicon.lookup_word("launched"), lexicon.WORDS["launch"])
        self.assertEqual(lexicon.lookup_word("expired"), lexicon.WORDS["expire"])
        self.assertEqual(lexicon.lookup_word("expiring"), lexicon.WORDS["expire"])
        self.assertEqual(lexicon.lookup_word("confirming"), lexicon.WORDS["confirm"])

    def test_exact_entry_beats_the_stem(self):
        # "shipping" is a parcel, not a boat: its own entry must win over the
        # "ship" stem.
        self.assertEqual(lexicon.lookup_word("shipping"), lexicon.WORDS["shipping"])
        self.assertNotEqual(lexicon.WORDS["shipping"], lexicon.WORDS["ship"])

    def test_modal_verbs_are_not_months(self):
        # "you may reply" must not turn into a calendar.
        self.assertIsNone(lexicon.lookup_word("may"))

    def test_adverbs(self):
        self.assertEqual(lexicon.lookup_word("urgently"), lexicon.WORDS["urgent"])

    def test_case_and_apostrophes(self):
        self.assertEqual(lexicon.lookup_word("URGENT"), lexicon.WORDS["urgent"])
        self.assertEqual(lexicon.lookup_word("Meeting"), lexicon.WORDS["meeting"])

    def test_unknown_word_is_none(self):
        self.assertIsNone(lexicon.lookup_word("zzyzx"))

    def test_double_consonant_is_not_over_stripped(self):
        # "ss" endings must not lose their final letter ("less" -> "les").
        self.assertIn("less", list(lexicon.candidates("less")))
        self.assertNotIn("les", list(lexicon.candidates("less")))


if __name__ == "__main__":
    unittest.main()
