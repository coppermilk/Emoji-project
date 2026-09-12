# emojimail 📧➡️😀

Translate your email into emoji. Paste a mail to a Telegram bot, or pipe `.eml`
files through the command line, and get the message back as pictures.

```
Subject: URGENT: invoice 4471 is past due
Your invoice for $1,240.00 is 14 days past due. Please pay by 03/11.

                    ↓

👉🧾💰📆⏰💸🙏💰📅
```

**No API keys. No network calls in the translator. No dependencies.** The whole
thing runs on the Python standard library, so the only thing you need to set up
is a Telegram bot token — and even that is optional if you only want the CLI.

## Quick start

```bash
git clone https://github.com/coppermilk/Emoji-project.git
cd Emoji-project

# Translate the bundled examples
python3 -m emojimail translate samples

# Translate anything on stdin
echo "Can we move the meeting to 3:30pm tomorrow?" | python3 -m emojimail translate
```

Python 3.9 or newer. There is nothing to `pip install`.

## The three styles

| Style | What you get | Good for |
|---|---|---|
| `summary` | One line of emoji with the gist | Triaging an inbox at a glance |
| `inline` | The original text with emoji added beside each word | Reading it and still understanding it |
| `full` *(default)* | Every word it knows, as emoji, in order | What the bot replies with |

Conversational text works the same way:

```
hello, how do you do, my bird          →  👋🤝🙋🐦
are you free tomorrow? let's go swim   →  👉🆓🌅❓🚶🏊
```

```bash
python3 -m emojimail translate samples/invoice.eml --style summary
python3 -m emojimail translate samples/invoice.eml --style inline
python3 -m emojimail translate samples/invoice.eml --style full
```

```
summary  🧾⏰💸🚨💰⏱️⚠️🙋
inline   Your 👉 invoice 🧾 for $1,240.00 💰 is now ⏱️ 14 days 📆 past due ⏰💸. Please 🙏 arrange payment 💰
full     👉🧾💰⏱️📆⏰💸🙏💰
```

### How a summary is built

It reads left to right as **what kind of mail** → **what it is about** →
**how urgent** → **what it wants from you** → **how it feels**:

```
🧾        billing category
⏰💸💰    the topics it actually mentions, most frequent first
🚨        urgency detected
🙋        it is asking you to do something
😟        overall tone
```

## The Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram and send `/newbot`.
2. Copy the token it gives you.
3. Point the bot at it and run:

```bash
cp .env.example .env      # then paste your token into .env
python3 -m emojimail bot
```

Now send the bot an email — pasted as text, or dropped in as a `.eml`
attachment — and it replies with the translation.

| Command | Does |
|---|---|
| `/help` | Show what it can do |
| `/style` | Show or change the style for your chat (`summary`, `inline`, `full`) |
| `/sample` | Translate a built-in example |
| `/whoami` | Print your chat id, for the allow list |

Your style choice is remembered per chat in `emojimail_prefs.json`.

### Keeping it private

A Telegram bot will talk to anyone who finds it. To lock it to just you, send
`/whoami`, then put the id in `.env`:

```
TELEGRAM_ALLOWED_CHATS=123456789
```

Anyone else is ignored.

## Getting mail to the bot

You picked "no mailbox access", so nothing here ever touches your account.
Three ways to feed it real mail:

- **Forward it.** In Gmail, forward a message to yourself, copy the text, paste
  it to the bot. Fine for the occasional mail.
- **Download the `.eml`.** In Gmail: `⋮` → *Download message*. Send that file to
  the bot as an attachment; it parses the real headers.
- **Batch a folder.** Export a pile of mails and run
  `python3 -m emojimail translate ~/mail-export --json > emoji.json`.

If you later decide you want it reading your inbox by itself, the piece to add
is a mailbox poller that produces `ParsedEmail` objects — everything downstream
of `emojimail/emailparse.py` stays exactly as it is.

## How it works

```
raw mail ──▶ emailparse.py ──▶ translate.py ──▶ summary / inline / full
             strips quoting     matches against
             and signatures     lexicon.py
```

Matching runs in one left-to-right pass with three layers, each beating the one
below it:

1. **Patterns** — regexes for things that are not words: `$1,240.00` → 💰,
   `3:30pm` → 🕐, URLs → 🔗.
2. **Phrases** — multi-word entries, longest first, so *out of office* → 🏖️
   rather than 🚪🏢.
3. **Words** — single words, after light suffix stripping so *meetings*,
   *shipped* and *expiring* all land on the right entry.

Because every match keeps its original character offsets, all three styles are
rendered from the same match list.

### Teaching it new words

Everything the translator knows lives in `emojimail/lexicon.py`, and it is
plain data:

```python
WORDS = {
    "invoice": "🧾",
    "deadline": "⏰",
}

PHRASES = {
    "out of office": "🏖️",
    "past due": "⏰💸",
}
```

There are 689 words and 109 phrases today, covering both business mail
and ordinary conversation. Add an entry and it works everywhere — all three styles
and the bot. The tests
enforce the rules that keep the tables sane (keys lowercase, phrases actually
multi-word, no ASCII letters leaking into the emoji, no stopword collisions).

One rule worth knowing: an exact entry beats a stem, which is why `shipping` is
🚚 (a parcel) and not 🚢 (a boat).

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

116 tests, no network, under a second.

## Project layout

```
emojimail/
  lexicon.py      the emoji tables and topic signals  ← edit this one
  emailparse.py   .eml and pasted-text parsing
  translate.py    matching and the three render styles
  bot.py          Telegram long-polling bot (stdlib urllib)
  cli.py          command line front end
samples/          example emails to try it on
tests/            116 unit tests
```

## Limits, honestly

- It is a dictionary, not a language model. It does not understand sarcasm,
  context or anything outside `lexicon.py`, and coverage on an unusual mail can
  be low. The upside is that it is instant, free, private and deterministic.
- English only.
- `full` is a word-by-word substitution, not a paraphrase. Word order and
  repetition survive, so a long mail becomes a long emoji string.
- Anything outside `lexicon.py` is simply dropped rather than guessed at.
