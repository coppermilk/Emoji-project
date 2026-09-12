"""Keep the examples in docstrings and the README honest."""

import doctest
import pathlib
import re
import unittest

import emojimail
from emojimail import translate
from emojimail.translate import STYLES


def load_tests(loader, tests, ignore):
    """Run the doctests in the package docstrings as part of the suite."""
    tests.addTests(doctest.DocTestSuite(emojimail))
    return tests


class ReadmeTests(unittest.TestCase):
    """The README quotes real output; make sure it still is real."""

    @classmethod
    def setUpClass(cls):
        cls.readme = pathlib.Path(__file__).resolve().parent.parent / "README.md"
        cls.text = cls.readme.read_text(encoding="utf-8")

    def test_readme_exists(self):
        self.assertTrue(self.text.strip())

    def test_quoted_invoice_summary_is_current(self):
        summary = translate(
            "Subject: URGENT: invoice 4471 is past due\n\n"
            "Your invoice for $1,240.00 is 14 days past due. Please pay by 03/11."
        ).summary
        self.assertIn(summary, self.text, f"README is stale; current summary is {summary}")

    def test_documented_styles_match_the_code(self):
        for style in STYLES:
            self.assertIn(f"`{style}`", self.text)

    def test_test_count_claim_is_not_wildly_wrong(self):
        claimed = [int(n) for n in re.findall(r"(\d+) tests", self.text)]
        self.assertTrue(claimed, "README no longer states a test count")
        loader = unittest.TestLoader()
        actual = loader.discover(
            str(self.readme.parent / "tests"), top_level_dir=str(self.readme.parent)
        ).countTestCases()
        for number in claimed:
            self.assertEqual(
                number, actual, f"README says {number} tests; there are {actual}"
            )


if __name__ == "__main__":
    unittest.main()
