"""A Telegram bot that answers emails with emoji.

Talks to the Bot API over plain ``urllib`` long polling, so the whole bot is
dependency-free. Send it an email -- pasted as text, or dropped in as a ``.eml``
file -- and it replies with the emoji translation.
"""

import json
import logging
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

from .emailparse import parse
from .translate import STYLES, translate_email

log = logging.getLogger("emojimail.bot")

API_ROOT = "https://api.telegram.org"

#: Telegram rejects messages longer than this.
MAX_MESSAGE = 4096

#: Refuse to download anything bigger; we only ever want text.
MAX_DOWNLOAD = 1_000_000

#: How long the server holds a getUpdates call open.
POLL_TIMEOUT = 30

HELP = """\U0001F4E7➡️\U0001F600 emojimail

Send me an email and I will send it back as emoji.
 • paste the text of a mail, or
 • attach a .eml / .txt file.

Commands:
/style - show or change how I translate
/sample - see an example
/whoami - show your chat id
/help - this message

Styles:
 summary - one line of emoji with the gist (default)
 inline - the original text with emoji added
 full - emoji only, no words at all
"""

SAMPLE = """\
Subject: URGENT: invoice 4471 is past due

Hi Bob, your invoice for $1,240.00 is 14 days past due.
Please pay by 03/11 or we will suspend the account.
Let me know if there is a problem. Thanks!"""


class TelegramError(RuntimeError):
    """The Bot API returned something we cannot act on."""


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------


def call(token, method, http_timeout=20, **params):
    """Call a Bot API method and return its ``result`` payload.

    ``http_timeout`` is the socket timeout; ``timeout`` stays free because the
    Bot API uses that name itself for long polling.
    """
    url = f"{API_ROOT}/bot{token}/{method}"
    params = {k: v for k, v in params.items() if v is not None}
    data = json.dumps(params).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=http_timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            description = json.loads(body).get("description", body)
        except ValueError:
            description = body
        raise TelegramError(f"{method} failed ({exc.code}): {description}") from exc

    if not payload.get("ok"):
        raise TelegramError(f"{method} failed: {payload.get('description')}")
    return payload.get("result")


def download(token, file_id, limit=MAX_DOWNLOAD):
    """Fetch an uploaded file's bytes, refusing anything oversized."""
    info = call(token, "getFile", file_id=file_id)
    size = info.get("file_size") or 0
    if size > limit:
        raise TelegramError(f"file is {size} bytes; the limit is {limit}")
    path = info["file_path"]
    url = f"{API_ROOT}/file/bot{token}/{urllib.parse.quote(path)}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read(limit + 1)[:limit]


def chunked(text, size=MAX_MESSAGE):
    """Split a long reply on line boundaries so Telegram will accept it."""
    if len(text) <= size:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:size])
            line = line[size:]
        if len(current) + len(line) > size:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------


class Preferences:
    """Per-chat style choices, persisted as a small JSON file."""

    def __init__(self, path, default="summary"):
        self.path = pathlib.Path(path)
        self.default = default
        self._styles = {}
        self.load()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._styles = {str(k): v for k, v in raw.get("styles", {}).items()}
        except (OSError, ValueError):
            self._styles = {}

    def save(self):
        try:
            self.path.write_text(
                json.dumps({"styles": self._styles}, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            log.warning("could not save preferences to %s: %s", self.path, exc)

    def style_for(self, chat_id):
        return self._styles.get(str(chat_id), self.default)

    def set_style(self, chat_id, style):
        self._styles[str(chat_id)] = style
        self.save()


# --------------------------------------------------------------------------
# Message handling
# --------------------------------------------------------------------------


def render_reply(raw, style):
    """Translate ``raw`` and format it the way the bot should say it."""
    parsed = parse(raw)
    if not parsed.text.strip():
        return "That looked empty \U0001F937 send me some email text or a .eml file."

    result = translate_email(parsed, style=style)
    lines = [result.summary]
    if style != "summary":
        if result.subject:
            lines.append("")
            lines.append(result.subject)
        if result.body:
            lines.append("")
            lines.append(result.body)
    if result.total:
        lines.append("")
        lines.append(f"─ {result.coverage:.0%} of words mapped · {style}")
    return "\n".join(lines)


class Bot:
    """Long-polling Telegram bot."""

    def __init__(self, token, prefs, allowed=None):
        self.token = token
        self.prefs = prefs
        self.allowed = set(allowed or ())
        self.offset = None
        self.username = None

    # -- plumbing ---------------------------------------------------------

    def send(self, chat_id, text):
        for chunk in chunked(text):
            call(self.token, "sendMessage", chat_id=chat_id, text=chunk,
                 disable_web_page_preview=True)

    def permitted(self, chat_id):
        return not self.allowed or str(chat_id) in self.allowed

    # -- handlers ---------------------------------------------------------

    def handle_command(self, chat_id, text):
        """Return True if ``text`` was a command and has been dealt with."""
        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0].lower()
        argument = argument.strip().lower()

        if command in ("/start", "/help"):
            self.send(chat_id, HELP)
        elif command == "/whoami":
            self.send(chat_id, f"This chat's id is {chat_id}")
        elif command == "/sample":
            style = self.prefs.style_for(chat_id)
            self.send(chat_id, SAMPLE + "\n\n↓↓↓\n\n" + render_reply(SAMPLE, style))
        elif command == "/style":
            if argument in STYLES:
                self.prefs.set_style(chat_id, argument)
                self.send(chat_id, f"Style set to {argument}. ✅")
            elif argument:
                self.send(chat_id, f"Unknown style {argument!r}. Pick one of: {', '.join(STYLES)}")
            else:
                current = self.prefs.style_for(chat_id)
                self.send(
                    chat_id,
                    f"Current style: {current}\nChange it with /style "
                    f"<{' | '.join(STYLES)}>",
                )
        else:
            return False
        return True

    def handle_message(self, message):
        chat_id = message.get("chat", {}).get("id")
        if chat_id is None:
            return
        if not self.permitted(chat_id):
            log.info("ignoring chat %s (not in the allow list)", chat_id)
            return

        text = message.get("text") or message.get("caption") or ""
        if text.startswith("/") and self.handle_command(chat_id, text):
            return

        document = message.get("document")
        if document:
            try:
                raw = download(self.token, document["file_id"])
            except TelegramError as exc:
                self.send(chat_id, f"Could not read that file: {exc}")
                return
            style = self.prefs.style_for(chat_id)
            self.send(chat_id, render_reply(raw, style))
            return

        if not text.strip():
            self.send(chat_id, "Send me email text or a .eml file. /help for more.")
            return

        self.send(chat_id, render_reply(text, self.prefs.style_for(chat_id)))

    def handle_update(self, update):
        self.offset = update["update_id"] + 1
        message = update.get("message") or update.get("edited_message")
        if message:
            self.handle_message(message)

    # -- main loop --------------------------------------------------------

    def poll_once(self):
        updates = call(
            self.token,
            "getUpdates",
            http_timeout=POLL_TIMEOUT + 15,
            timeout=POLL_TIMEOUT,
            offset=self.offset,
            allowed_updates=["message", "edited_message"],
        )
        for update in updates or []:
            try:
                self.handle_update(update)
            except TelegramError as exc:
                log.error("could not answer update %s: %s", update.get("update_id"), exc)
            except Exception:  # one bad mail must not kill the bot
                log.exception("failed handling update %s", update.get("update_id"))
        return len(updates or [])

    def run(self):
        me = call(self.token, "getMe")
        self.username = me.get("username")
        log.info("connected as @%s", self.username)
        print(f"emojimail bot running as @{self.username} — Ctrl-C to stop")

        backoff = 1
        while True:
            try:
                self.poll_once()
                backoff = 1
            except KeyboardInterrupt:
                raise
            except TelegramError as exc:
                log.error("%s", exc)
                if "conflict" in str(exc).lower():
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                log.warning("network hiccup (%s); retrying in %ss", exc, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)


def _load_dotenv(path=".env"):
    """Minimal .env reader so there is no python-dotenv dependency."""
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def run_bot(token=None, style=None, prefs_path=None, env_file=".env"):
    """Entry point used by ``emojimail bot``. Returns a process exit code."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    _load_dotenv(env_file)

    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print(
            "No bot token. Create one with @BotFather on Telegram, then either\n"
            "  export TELEGRAM_BOT_TOKEN=123456:ABC...\n"
            "or copy .env.example to .env and put it there."
        )
        return 2

    default_style = style or os.environ.get("EMOJIMAIL_STYLE", "summary")
    if default_style not in STYLES:
        print(f"Unknown style {default_style!r}; expected one of {', '.join(STYLES)}")
        return 2

    allowed = [
        item.strip()
        for item in os.environ.get("TELEGRAM_ALLOWED_CHATS", "").split(",")
        if item.strip()
    ]
    prefs = Preferences(
        prefs_path or os.environ.get("EMOJIMAIL_PREFS", "emojimail_prefs.json"),
        default=default_style,
    )

    bot = Bot(token, prefs, allowed=allowed)
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nstopped")
        return 0
    except TelegramError as exc:
        print(f"Telegram rejected the connection: {exc}")
        if "401" in str(exc) or "unauthorized" in str(exc).lower():
            print(
                "That token is not valid. Get a fresh one with /token or /newbot "
                "from @BotFather."
            )
        return 1
    except (urllib.error.URLError, OSError) as exc:
        # The startup getMe deliberately fails fast: once the bot is polling,
        # run() retries network errors instead of exiting.
        print(
            f"Could not reach {API_ROOT}: {exc}\n"
            "Check your connection, and whether a firewall or proxy is blocking "
            "api.telegram.org."
        )
        return 1
    return 0
