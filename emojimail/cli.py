"""Command line front end: translate files or stdin, or start the bot."""

import argparse
import json
import pathlib
import sys

from . import __version__
from .emailparse import parse
from .translate import STYLES, translate_email

#: Extensions picked up when a directory is passed instead of a file.
MAIL_SUFFIXES = (".eml", ".txt", ".msg")


def _iter_inputs(paths):
    """Yield ``(label, raw_bytes)`` for every path, expanding directories."""
    for raw_path in paths:
        path = pathlib.Path(raw_path)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() in MAIL_SUFFIXES:
                    yield str(child), child.read_bytes()
        elif path.is_file():
            yield str(path), path.read_bytes()
        else:
            print(f"emojimail: no such file: {path}", file=sys.stderr)


def format_result(label, parsed, result, show_stats=True):
    """Render one translation for a terminal."""
    lines = []
    if label:
        lines.append(f"── {label}")
    if parsed.subject:
        lines.append(f"   {parsed.subject}")

    lines.append(result.summary)
    if result.style != "summary":
        if result.subject:
            lines.append(result.subject)
        if result.body:
            lines.append(result.body)

    if show_stats:
        categories = ", ".join(result.categories) or "uncategorised"
        lines.append(
            f"   [{categories} · {result.matched}/{result.total} words mapped"
            f" · {result.coverage:.0%}]"
        )
    return "\n".join(lines)


def _as_dict(label, parsed, result):
    return {
        "source": label,
        "subject": parsed.subject,
        "from": parsed.sender,
        "style": result.style,
        "summary": result.summary,
        "emoji_subject": result.subject,
        "emoji_body": result.body,
        "categories": result.categories,
        "coverage": round(result.coverage, 3),
        "words_matched": result.matched,
        "words_total": result.total,
    }


def cmd_translate(args):
    if args.paths:
        sources = list(_iter_inputs(args.paths))
    else:
        data = sys.stdin.buffer.read()
        if not data.strip():
            print("emojimail: nothing on stdin", file=sys.stderr)
            return 1
        sources = [("", data)]

    if not sources:
        print("emojimail: no readable mail found", file=sys.stderr)
        return 1

    payload = []
    for label, raw in sources:
        parsed = parse(raw)
        result = translate_email(parsed, style=args.style)
        if args.json:
            payload.append(_as_dict(label, parsed, result))
        elif args.quiet:
            print(result.summary if args.style == "summary" else result.body)
        else:
            print(format_result(label, parsed, result, show_stats=not args.no_stats))
            print()

    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


def cmd_bot(args):
    # Imported lazily so ``translate`` never pays for the bot's import.
    from .bot import run_bot

    return run_bot(token=args.token, style=args.style)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="emojimail",
        description="Translate emails into emoji. No API keys, no network.",
    )
    parser.add_argument("--version", action="version", version=f"emojimail {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    translate_parser = subparsers.add_parser(
        "translate", help="translate .eml files, a directory, or stdin"
    )
    translate_parser.add_argument(
        "paths", nargs="*", help="files or directories; omit to read stdin"
    )
    translate_parser.add_argument(
        "-s", "--style", choices=STYLES, default="summary",
        help="summary: one emoji line; inline: text plus emoji; full: emoji only",
    )
    translate_parser.add_argument("--json", action="store_true", help="machine-readable output")
    translate_parser.add_argument("-q", "--quiet", action="store_true", help="emoji only")
    translate_parser.add_argument("--no-stats", action="store_true", help="hide the coverage line")
    translate_parser.set_defaults(func=cmd_translate)

    bot_parser = subparsers.add_parser("bot", help="run the Telegram bot")
    bot_parser.add_argument(
        "--token", default=None, help="bot token (defaults to $TELEGRAM_BOT_TOKEN)"
    )
    bot_parser.add_argument(
        "-s", "--style", choices=STYLES, default=None, help="default style for new chats"
    )
    bot_parser.set_defaults(func=cmd_bot)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # Bare `emojimail` with piped input is a reasonable shorthand.
        if not sys.stdin.isatty():
            args = parser.parse_args(["translate"])
        else:
            parser.print_help()
            return 0
    return args.func(args)
