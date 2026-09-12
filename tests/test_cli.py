"""End-to-end checks on the command line front end."""

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

from emojimail import cli

MAIL = "Subject: Invoice 4471 past due\n\nPlease pay the $40.00 bill by tomorrow.\n"


class FakeStdin:
    """Just enough of ``sys.stdin`` for the CLI: ``.buffer`` and ``.isatty``."""

    def __init__(self, text):
        self.buffer = io.BytesIO(text.encode())

    def isatty(self):
        return False

    def read(self):
        return self.buffer.read().decode()


@contextlib.contextmanager
def captured(stdin=None):
    """Capture stdout/stderr, optionally feeding ``stdin`` to the command."""
    out, err = io.StringIO(), io.StringIO()
    original = sys.stdin
    if stdin is not None:
        sys.stdin = FakeStdin(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield out, err
    finally:
        sys.stdin = original


class ArgumentTests(unittest.TestCase):
    def test_default_style_is_summary(self):
        args = cli.build_parser().parse_args(["translate"])
        self.assertEqual(args.style, "summary")

    def test_style_is_validated(self):
        with captured(), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["translate", "--style", "hieroglyphs"])

    def test_bot_subcommand_exists(self):
        args = cli.build_parser().parse_args(["bot"])
        self.assertEqual(args.command, "bot")


class TranslateCommandTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = pathlib.Path(self.dir.name) / "mail.eml"
        self.path.write_text(MAIL, encoding="utf-8")

    def run_cli(self, argv, stdin=None):
        with captured(stdin) as (out, err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_translate_a_file(self):
        code, out, _ = self.run_cli(["translate", str(self.path)])
        self.assertEqual(code, 0)
        self.assertIn("\U0001F9FE", out)

    def test_translate_stdin(self):
        code, out, _ = self.run_cli(["translate"], stdin=MAIL)
        self.assertEqual(code, 0)
        self.assertIn("\U0001F9FE", out)

    def test_empty_stdin_is_an_error(self):
        code, _, err = self.run_cli(["translate"], stdin="   ")
        self.assertEqual(code, 1)
        self.assertIn("nothing on stdin", err)

    def test_directory_is_expanded(self):
        (pathlib.Path(self.dir.name) / "second.eml").write_text(MAIL, encoding="utf-8")
        (pathlib.Path(self.dir.name) / "ignored.pdf").write_text("x", encoding="utf-8")
        code, out, _ = self.run_cli(["translate", self.dir.name])
        self.assertEqual(code, 0)
        self.assertEqual(out.count("mail.eml") + out.count("second.eml"), 2)
        self.assertNotIn("ignored.pdf", out)

    def test_json_output_is_valid(self):
        code, out, _ = self.run_cli(["translate", str(self.path), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload[0]["subject"], "Invoice 4471 past due")
        self.assertIn("billing", payload[0]["categories"])
        self.assertTrue(payload[0]["summary"])

    def test_quiet_prints_only_emoji(self):
        _, out, _ = self.run_cli(["translate", str(self.path), "--quiet"])
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertFalse(any(ch.isascii() and ch.isalpha() for ch in out))

    def test_every_style_runs(self):
        for style in ("summary", "inline", "full"):
            with self.subTest(style=style):
                code, out, _ = self.run_cli(["translate", str(self.path), "-s", style])
                self.assertEqual(code, 0)
                self.assertTrue(out.strip())

    def test_missing_file_reports_to_stderr(self):
        code, _, err = self.run_cli(["translate", "/nope/missing.eml"])
        self.assertEqual(code, 1)
        self.assertIn("no such file", err)

    def test_bot_without_a_token_exits_cleanly(self):
        import os

        original = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        try:
            with captured() as (out, _):
                code = cli.main(["bot"])
            self.assertEqual(code, 2)
            self.assertIn("BotFather", out.getvalue())
        finally:
            if original is not None:
                os.environ["TELEGRAM_BOT_TOKEN"] = original


if __name__ == "__main__":
    unittest.main()
