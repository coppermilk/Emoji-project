"""Bot plumbing, exercised against a stubbed Telegram transport."""

import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

from emojimail import bot


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def ok(result):
    """Build a successful Bot API response."""
    return FakeResponse(json.dumps({"ok": True, "result": result}).encode())


class Transport:
    """Records every API call and replays canned results."""

    def __init__(self, results=None):
        self.calls = []
        self.results = dict(results or {})

    def __call__(self, request, timeout=None):
        url = getattr(request, "full_url", request)
        method = url.rsplit("/", 1)[-1]
        body = json.loads(request.data) if getattr(request, "data", None) else {}
        self.calls.append((method, body))
        return ok(self.results.get(method, []))

    def sent(self):
        return [body["text"] for method, body in self.calls if method == "sendMessage"]


class CallTests(unittest.TestCase):
    def test_builds_url_and_strips_none(self):
        transport = Transport()
        with mock.patch("urllib.request.urlopen", transport):
            bot.call("TOKEN", "getUpdates", offset=None, limit=5)
        method, body = transport.calls[0]
        self.assertEqual(method, "getUpdates")
        self.assertEqual(body, {"limit": 5})

    def test_socket_timeout_is_separate_from_api_timeout(self):
        seen = {}

        def transport(request, timeout=None):
            seen["socket"] = timeout
            seen["api"] = json.loads(request.data)
            return ok([])

        with mock.patch("urllib.request.urlopen", transport):
            bot.call("TOKEN", "getUpdates", http_timeout=45, timeout=30)
        self.assertEqual(seen["socket"], 45)
        self.assertEqual(seen["api"], {"timeout": 30})

    def test_api_error_raises(self):
        def transport(request, timeout=None):
            return FakeResponse(json.dumps({"ok": False, "description": "nope"}).encode())

        with mock.patch("urllib.request.urlopen", transport):
            with self.assertRaises(bot.TelegramError):
                bot.call("TOKEN", "getMe")

    def test_http_error_is_wrapped(self):
        def transport(request, timeout=None):
            raise urllib.error.HTTPError(
                "url", 401, "Unauthorized", {},
                io.BytesIO(b'{"description": "bad token"}'),
            )

        with mock.patch("urllib.request.urlopen", transport):
            with self.assertRaisesRegex(bot.TelegramError, "bad token"):
                bot.call("TOKEN", "getMe")


class ChunkingTests(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(bot.chunked("hello"), ["hello"])

    def test_long_text_is_split_within_the_limit(self):
        chunks = bot.chunked("line of text\n" * 2000)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), bot.MAX_MESSAGE)

    def test_nothing_is_lost(self):
        text = "line of text\n" * 2000
        self.assertEqual("".join(bot.chunked(text)), text)

    def test_a_single_overlong_line_is_still_split(self):
        chunks = bot.chunked("x" * 9000)
        self.assertTrue(all(len(c) <= bot.MAX_MESSAGE for c in chunks))
        self.assertEqual("".join(chunks), "x" * 9000)


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "prefs.json"
        self.addCleanup(self.dir.cleanup)

    def test_default_when_unset(self):
        prefs = bot.Preferences(self.path, default="summary")
        self.assertEqual(prefs.style_for(42), "summary")

    def test_set_and_persist(self):
        bot.Preferences(self.path).set_style(42, "full")
        self.assertEqual(bot.Preferences(self.path).style_for(42), "full")

    def test_chat_ids_are_normalised_to_strings(self):
        prefs = bot.Preferences(self.path)
        prefs.set_style(42, "inline")
        self.assertEqual(prefs.style_for("42"), "inline")

    def test_corrupt_file_falls_back_to_defaults(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(bot.Preferences(self.path).style_for(1), "summary")

    def test_missing_file_is_fine(self):
        missing = pathlib.Path(self.dir.name) / "nope" / "prefs.json"
        self.assertEqual(bot.Preferences(missing).style_for(1), "summary")


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.prefs = bot.Preferences(pathlib.Path(self.dir.name) / "p.json")
        self.bot = bot.Bot("TOKEN", self.prefs)

    def run_message(self, message, transport=None):
        transport = transport or Transport()
        with mock.patch("urllib.request.urlopen", transport):
            self.bot.handle_message(message)
        return transport

    @staticmethod
    def text_message(text, chat_id=7):
        return {"chat": {"id": chat_id}, "text": text}

    def test_help_command(self):
        transport = self.run_message(self.text_message("/help"))
        self.assertIn("emojimail", transport.sent()[0])

    def test_command_with_bot_username_suffix(self):
        transport = self.run_message(self.text_message("/help@emojimail_bot"))
        self.assertIn("emojimail", transport.sent()[0])

    def test_whoami_reports_the_chat_id(self):
        transport = self.run_message(self.text_message("/whoami", chat_id=99))
        self.assertIn("99", transport.sent()[0])

    def test_style_command_changes_the_style(self):
        self.run_message(self.text_message("/style full"))
        self.assertEqual(self.prefs.style_for(7), "full")

    def test_style_command_rejects_nonsense(self):
        transport = self.run_message(self.text_message("/style hieroglyphs"))
        self.assertIn("Unknown style", transport.sent()[0])
        self.assertEqual(self.prefs.style_for(7), "summary")

    def test_bare_style_command_reports_current(self):
        transport = self.run_message(self.text_message("/style"))
        self.assertIn("summary", transport.sent()[0])

    def test_unknown_command_is_translated_not_swallowed(self):
        transport = self.run_message(self.text_message("/invoice is due"))
        self.assertTrue(transport.sent())

    def test_plain_text_is_translated(self):
        transport = self.run_message(self.text_message("The invoice is past due"))
        reply = transport.sent()[0]
        self.assertIn("\U0001F9FE", reply)

    def test_empty_message_gets_guidance(self):
        transport = self.run_message(self.text_message("   "))
        self.assertIn(".eml", transport.sent()[0])

    def test_allow_list_blocks_strangers(self):
        guarded = bot.Bot("TOKEN", self.prefs, allowed=["7"])
        transport = Transport()
        with mock.patch("urllib.request.urlopen", transport):
            guarded.handle_message(self.text_message("hello", chat_id=8))
            guarded.handle_message(self.text_message("invoice", chat_id=7))
        self.assertEqual(len(transport.sent()), 1)

    def test_document_is_downloaded_and_translated(self):
        transport = Transport({"getFile": {"file_path": "docs/mail.eml", "file_size": 80}})
        message = {"chat": {"id": 7}, "document": {"file_id": "abc", "file_name": "mail.eml"}}
        with mock.patch("urllib.request.urlopen", transport), mock.patch.object(
            bot, "download", return_value=b"Subject: Invoice\n\nPay the bill."
        ):
            self.bot.handle_message(message)
        self.assertIn("\U0001F9FE", transport.sent()[0])

    def test_oversized_document_is_refused_politely(self):
        transport = Transport()
        message = {"chat": {"id": 7}, "document": {"file_id": "abc"}}
        with mock.patch("urllib.request.urlopen", transport), mock.patch.object(
            bot, "download", side_effect=bot.TelegramError("file is too big")
        ):
            self.bot.handle_message(message)
        self.assertIn("Could not read that file", transport.sent()[0])

    def test_a_failing_update_does_not_stop_the_loop(self):
        transport = Transport({"getUpdates": [
            {"update_id": 1, "message": {"chat": {"id": 7}, "text": "invoice"}},
            {"update_id": 2},
        ]})
        with mock.patch("urllib.request.urlopen", transport):
            handled = self.bot.poll_once()
        self.assertEqual(handled, 2)
        self.assertEqual(self.bot.offset, 3)


class RenderReplyTests(unittest.TestCase):
    def test_summary_reply_mentions_coverage(self):
        reply = bot.render_reply("Subject: Invoice\n\nPay the bill.", "summary")
        self.assertIn("mapped", reply)

    def test_inline_reply_keeps_the_words(self):
        self.assertIn("invoice", bot.render_reply("the invoice is due", "inline"))

    def test_empty_input_is_handled(self):
        self.assertIn("empty", bot.render_reply("   ", "summary"))

    def test_sample_translates(self):
        self.assertTrue(bot.render_reply(bot.SAMPLE, "summary"))


class StartupFailureTests(unittest.TestCase):
    """Starting the bot must explain itself instead of dumping a traceback."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.prefs_path = str(pathlib.Path(self.dir.name) / "p.json")
        self.no_env = str(pathlib.Path(self.dir.name) / "absent.env")

    def run_bot_capturing(self, side_effect):
        import contextlib
        import io

        out = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            with contextlib.redirect_stdout(out):
                code = bot.run_bot(
                    token="TOKEN", prefs_path=self.prefs_path, env_file=self.no_env
                )
        return code, out.getvalue()

    def test_unreachable_api_is_explained(self):
        code, output = self.run_bot_capturing(
            urllib.error.URLError("Tunnel connection failed: 403 Forbidden")
        )
        self.assertEqual(code, 1)
        self.assertIn("Could not reach", output)
        self.assertIn("api.telegram.org", output)
        self.assertNotIn("Traceback", output)

    def test_bad_token_points_at_botfather(self):
        def unauthorized(request, timeout=None):
            raise urllib.error.HTTPError(
                "url", 401, "Unauthorized", {},
                io.BytesIO(b'{"description": "Unauthorized"}'),
            )

        code, output = self.run_bot_capturing(unauthorized)
        self.assertEqual(code, 1)
        self.assertIn("BotFather", output)

    def test_unknown_style_is_rejected_before_connecting(self):
        import contextlib
        import io as _io

        out = _io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bot.run_bot(token="TOKEN", style="hieroglyphs", env_file=self.no_env)
        self.assertEqual(code, 2)
        self.assertIn("Unknown style", out.getvalue())


if __name__ == "__main__":
    unittest.main()
