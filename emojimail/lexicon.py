"""Word/phrase -> emoji tables plus the topic signals used for summaries.

This module is pure data and a couple of tiny helpers. There is no model and no
network call anywhere in the translator: everything it knows lives here, so
improving the output means editing these tables.

Three lookup layers, applied in this order:

1. ``PATTERNS``  -- regexes for things that are not words (URLs, money, times).
2. ``PHRASES``   -- multi-word entries, longest first, so "out of office"
                    wins over "office".
3. ``WORDS``     -- single words, matched after light suffix stripping.
"""

import re

# --------------------------------------------------------------------------
# Layer 1: regex patterns, matched before the text is split into words.
# --------------------------------------------------------------------------

PATTERNS = [
    ("url", re.compile(r"https?://\S+|www\.\S+"), "\U0001F517"),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "\U0001F4E7"),
    ("money", re.compile(r"[$€£¥]\s?\d[\d,]*(?:\.\d+)?(?:\s?[kKmM])?"), "\U0001F4B0"),
    ("percent", re.compile(r"\b\d+(?:\.\d+)?\s?%"), "\U0001F4CA"),
    ("time", re.compile(r"\b\d{1,2}:\d{2}\s?(?:[ap]\.?m\.?)?\b", re.I), "\U0001F550"),
    ("clock", re.compile(r"\b\d{1,2}\s?[ap]\.?m\.?\b", re.I), "\U0001F550"),
    ("date", re.compile(r"\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b"), "\U0001F4C5"),
    ("phone", re.compile(r"\+?\d[\d\s().-]{8,}\d"), "\U0001F4DE"),
]

# --------------------------------------------------------------------------
# Layer 2: multi-word phrases.
# --------------------------------------------------------------------------

PHRASES = {
    # Etiquette and email plumbing
    "thank you": "\U0001F64F",
    "thanks in advance": "\U0001F64F",
    "best regards": "\U0001F44B",
    "kind regards": "\U0001F44B",
    "looking forward": "\U0001F60A\U0001F440",
    "let me know": "\U0001F4AC❓",
    "please find attached": "\U0001F4CE",
    "see attached": "\U0001F4CE",
    "reply all": "↩️\U0001F465",
    "forwarded message": "➡️\U0001F4E7",
    "heads up": "⚠️",
    "quick question": "⚡❓",
    "any questions": "❓",
    "follow up": "\U0001F501",
    "circle back": "\U0001F504",
    "touch base": "\U0001F91D",
    "out of office": "\U0001F3D6️",
    "as soon as possible": "⚡",
    "action required": "❗✅",
    "no action required": "\U0001F60C",

    # Meetings and calendars
    "conference call": "\U0001F4DE\U0001F465",
    "video call": "\U0001F4F9",
    "zoom call": "\U0001F4BB\U0001F4F9",
    "meeting invite": "\U0001F4C5✉️",
    "calendar invite": "\U0001F4C5✉️",
    "double booked": "\U0001F4C5⚔️",
    "end of day": "\U0001F306⏰",
    "end of week": "\U0001F5D3️⏰",
    "first thing": "\U0001F305",
    "next week": "\U0001F5D3️➡️",
    "last week": "\U0001F5D3️⬅️",
    "this week": "\U0001F5D3️",
    "next month": "\U0001F4C5➡️",

    # Money
    "credit card": "\U0001F4B3",
    "bank account": "\U0001F3E6",
    "wire transfer": "\U0001F3E6➡️",
    "purchase order": "\U0001F9FE",
    "invoice attached": "\U0001F9FE\U0001F4CE",
    "past due": "⏰\U0001F4B8",
    "payment received": "\U0001F4B0✅",
    "payment failed": "\U0001F4B3❌",
    "money back": "\U0001F4B8↩️",

    # Security
    "password reset": "\U0001F511\U0001F504",
    "two factor": "\U0001F510",
    "suspicious activity": "\U0001F575️\U0001F6A8",
    "security alert": "\U0001F512\U0001F6A8",
    "verify your account": "\U0001F512❓",
    "log in": "\U0001F511",
    "sign up": "✍️",

    # Engineering
    "pull request": "\U0001F500",
    "merge conflict": "⚔️",
    "code review": "\U0001F440\U0001F4BB",
    "unit test": "\U0001F9EA",
    "build failed": "\U0001F534\U0001F528",
    "build passed": "\U0001F7E2\U0001F528",
    "production outage": "\U0001F525\U0001F5A5️",
    "in progress": "\U0001F504",
    "on hold": "⏸️",
    "at risk": "⚠️",
    "blocked by": "\U0001F6A7",

    # Work and life events
    "job offer": "\U0001F91D\U0001F4BC",
    "job application": "\U0001F4C4\U0001F4BC",
    "cover letter": "\U0001F4C4",
    "performance review": "\U0001F4CA\U0001F454",
    "time off": "\U0001F3D6️",
    "sick leave": "\U0001F912",
    "maternity leave": "\U0001F476",
    "welcome aboard": "\U0001F389\U0001F6A2",
    "happy birthday": "\U0001F382\U0001F389",
    "happy holidays": "\U0001F384",
    "good news": "\U0001F389",
    "bad news": "\U0001F61E",

    # Shopping, shipping, travel
    "order confirmation": "\U0001F4E6✅",
    "your order": "\U0001F4E6",
    "has shipped": "\U0001F69A",
    "out for delivery": "\U0001F69A\U0001F4CD",
    "delivery attempt": "\U0001F69A❓",
    "tracking number": "\U0001F522\U0001F69A",
    "boarding pass": "\U0001F3AB✈️",
    "flight confirmation": "✈️✅",
    "hotel booking": "\U0001F3E8✅",

    # Marketing
    "black friday": "\U0001F6CD️\U0001F525",
    "limited time": "⏳\U0001F525",
    "act now": "\U0001F3C3\U0001F4A8",
    "click here": "\U0001F446",
    "free trial": "\U0001F193⏳",
    "last chance": "⏳❗",

    # Legal
    "terms of service": "\U0001F4DC",
    "privacy policy": "\U0001F512\U0001F4DC",
}

# --------------------------------------------------------------------------
# Layer 3: single words. Keys are lowercase and get matched after the light
# suffix stripping in ``candidates()``, so "meetings" and "shipped" both land.
# --------------------------------------------------------------------------

WORDS = {
    # Greetings and etiquette
    "hi": "\U0001F44B", "hello": "\U0001F44B", "hey": "\U0001F44B",
    "dear": "\U0001F44B", "regards": "\U0001F44B", "cheers": "\U0001F37B",
    "bye": "\U0001F44B", "welcome": "\U0001F389", "please": "\U0001F64F",
    "thanks": "\U0001F64F", "thank": "\U0001F64F", "sorry": "\U0001F614",
    "apologize": "\U0001F614", "congratulations": "\U0001F389",
    "congrats": "\U0001F389",

    # People
    "team": "\U0001F465", "boss": "\U0001F454", "manager": "\U0001F454",
    "client": "\U0001F935", "customer": "\U0001F6D2", "colleague": "\U0001F9D1‍\U0001F4BC",
    "friend": "\U0001F91D", "family": "\U0001F468‍\U0001F469‍\U0001F467",
    "everyone": "\U0001F465", "staff": "\U0001F465", "ceo": "\U0001F451",
    "recruiter": "\U0001F3AF", "candidate": "\U0001F9D1‍\U0001F4BC",
    "doctor": "\U0001F468‍⚕️", "lawyer": "⚖️",
    "teacher": "\U0001F9D1‍\U0001F3EB", "student": "\U0001F393",
    "landlord": "\U0001F3E0", "neighbor": "\U0001F3D8️", "guest": "\U0001F64B",
    "partner": "\U0001F91D", "vendor": "\U0001F3EA", "supplier": "\U0001F4E6",

    # Work
    "meeting": "\U0001F4C5", "call": "\U0001F4DE", "agenda": "\U0001F4CB",
    "minutes": "\U0001F4DD", "slides": "\U0001F4CA", "presentation": "\U0001F4CA",
    "report": "\U0001F4CA", "deck": "\U0001F4CA", "project": "\U0001F5C2️",
    "task": "☑️", "todo": "☑️", "deadline": "⏰",
    "milestone": "\U0001F3C1", "goal": "\U0001F3AF", "target": "\U0001F3AF",
    "budget": "\U0001F4B0", "invoice": "\U0001F9FE", "receipt": "\U0001F9FE",
    "payment": "\U0001F4B0", "refund": "\U0001F4B8", "salary": "\U0001F4B5",
    "bonus": "\U0001F381", "contract": "\U0001F4DC", "proposal": "\U0001F4C4",
    "offer": "\U0001F381", "deal": "\U0001F91D", "launch": "\U0001F680",
    "ship": "\U0001F6A2", "release": "\U0001F4E6", "deploy": "\U0001F680",
    "demo": "\U0001F5A5️", "feedback": "\U0001F4AC", "review": "\U0001F440",
    "approve": "✅", "approved": "✅", "reject": "❌",
    "cancel": "❌", "cancelled": "❌", "confirm": "✅",
    "schedule": "\U0001F4C5", "reschedule": "\U0001F4C5\U0001F504",
    "postpone": "⏭️", "delay": "⏳", "urgent": "\U0001F6A8",
    "asap": "⚡", "priority": "❗", "blocker": "\U0001F6A7",
    "issue": "⚠️", "problem": "⚠️", "risk": "⚠️",
    "solution": "\U0001F4A1", "idea": "\U0001F4A1", "plan": "\U0001F5FA️",
    "strategy": "♟️", "decision": "⚖️", "status": "\U0001F4CA",
    "progress": "\U0001F4C8", "done": "✅", "complete": "✅",
    "finish": "✅", "start": "▶️", "pause": "⏸️",
    "hire": "\U0001F91D", "resign": "\U0001F6AA", "promotion": "\U0001F389\U0001F4C8",
    "onboarding": "\U0001F6EC", "training": "\U0001F3CB️", "workshop": "\U0001F6E0️",
    "conference": "\U0001F3A4", "webinar": "\U0001F4BB\U0001F3A4",
    "interview": "\U0001F399️", "resume": "\U0001F4C4", "office": "\U0001F3E2",

    # Engineering
    "bug": "\U0001F41B", "crash": "\U0001F4A5", "error": "❌",
    "fail": "❌", "fix": "\U0001F527", "patch": "\U0001FA79",
    "server": "\U0001F5A5️", "database": "\U0001F5C4️", "backup": "\U0001F4BE",
    "code": "\U0001F4BB", "repo": "\U0001F4C2", "branch": "\U0001F33F",
    "commit": "\U0001F4CC", "merge": "\U0001F500", "test": "\U0001F9EA",
    "build": "\U0001F528", "pipeline": "\U0001F527", "api": "\U0001F50C",
    "app": "\U0001F4F1", "website": "\U0001F310", "login": "\U0001F511",
    "password": "\U0001F511", "account": "\U0001F464", "security": "\U0001F512",
    "hack": "\U0001F3F4‍☠️", "breach": "\U0001F6A8\U0001F513",
    "phishing": "\U0001F3A3", "spam": "\U0001F5D1️", "virus": "\U0001F9A0",
    "update": "\U0001F504", "upgrade": "⬆️", "outage": "\U0001F525",
    "performance": "⚡", "storage": "\U0001F4BE", "cloud": "☁️",

    # Email plumbing
    "email": "\U0001F4E7", "inbox": "\U0001F4E5", "attachment": "\U0001F4CE",
    "file": "\U0001F4C4", "folder": "\U0001F4C1", "link": "\U0001F517",
    "download": "⬇️", "upload": "⬆️", "print": "\U0001F5A8️",

    # Time
    "today": "\U0001F4C6", "tomorrow": "\U0001F305", "yesterday": "\U0001F319",
    "tonight": "\U0001F303", "morning": "☀️", "afternoon": "\U0001F324️",
    "evening": "\U0001F306", "night": "\U0001F319", "week": "\U0001F5D3️",
    "weekend": "\U0001F388", "month": "\U0001F4C5", "year": "\U0001F38A",
    "monday": "1️⃣", "tuesday": "2️⃣", "wednesday": "3️⃣",
    "thursday": "4️⃣", "friday": "5️⃣", "saturday": "6️⃣",
    "sunday": "7️⃣", "now": "⏱️", "soon": "⏳",
    "later": "⏭️", "early": "\U0001F426", "late": "\U0001F40C",
    "hour": "\U0001F550", "minute": "⏱️", "day": "\U0001F4C6",
    "calendar": "\U0001F4C5", "reminder": "\U0001F514", "alarm": "⏰",

    # Travel
    "flight": "✈️", "plane": "✈️", "airport": "\U0001F6EB",
    "hotel": "\U0001F3E8", "booking": "\U0001F5D3️", "reservation": "\U0001F5D3️",
    "train": "\U0001F686", "taxi": "\U0001F695", "car": "\U0001F697",
    "trip": "\U0001F9F3", "travel": "\U0001F9F3", "vacation": "\U0001F3D6️",
    "holiday": "\U0001F3D6️", "passport": "\U0001F6C2", "visa": "\U0001F6C2",
    "luggage": "\U0001F9F3", "ticket": "\U0001F3AB",

    # Money and shopping
    "price": "\U0001F3F7️", "sale": "\U0001F3F7️", "discount": "\U0001F4B8",
    "coupon": "\U0001F39F️", "free": "\U0001F193", "expensive": "\U0001F4B0",
    "order": "\U0001F4E6", "cart": "\U0001F6D2", "shipping": "\U0001F69A",
    "delivery": "\U0001F4E6", "package": "\U0001F4E6", "tracking": "\U0001F4CD",
    "warranty": "\U0001F6E1️", "subscription": "\U0001F501", "renewal": "\U0001F501",
    "trial": "⏳", "bill": "\U0001F9FE", "tax": "\U0001F9FE\U0001F4B8",
    "bank": "\U0001F3E6", "loan": "\U0001F3E6", "mortgage": "\U0001F3E0\U0001F3E6",
    "insurance": "\U0001F6E1️", "cash": "\U0001F4B5", "dollar": "\U0001F4B5",
    "wallet": "\U0001F45B", "invest": "\U0001F4C8", "stock": "\U0001F4C8",
    "profit": "\U0001F4C8", "loss": "\U0001F4C9", "promo": "\U0001F3F7️",
    "newsletter": "\U0001F4F0", "unsubscribe": "\U0001F6AB", "exclusive": "\U0001F48E",
    "winner": "\U0001F3C6", "prize": "\U0001F3C6", "expire": "⌛",
    "hurry": "\U0001F3C3", "guarantee": "\U0001F6E1️",

    # Life
    "birthday": "\U0001F382", "wedding": "\U0001F492", "baby": "\U0001F476",
    "party": "\U0001F389", "dinner": "\U0001F37D️", "lunch": "\U0001F37D️",
    "breakfast": "\U0001F950", "coffee": "☕", "beer": "\U0001F37A",
    "wine": "\U0001F377", "food": "\U0001F355", "restaurant": "\U0001F37D️",
    "movie": "\U0001F3AC", "music": "\U0001F3B5", "game": "\U0001F3AE",
    "book": "\U0001F4DA", "gym": "\U0001F3CB️", "hospital": "\U0001F3E5",
    "sick": "\U0001F912", "health": "\U0001F49A", "dog": "\U0001F436",
    "cat": "\U0001F431", "house": "\U0001F3E0", "home": "\U0001F3E0",
    "apartment": "\U0001F3E2", "rent": "\U0001F3E0", "school": "\U0001F3EB",
    "exam": "\U0001F4DD", "gift": "\U0001F381", "photo": "\U0001F4F7",
    "video": "\U0001F4F9", "weather": "\U0001F324️", "rain": "\U0001F327️",
    "snow": "❄️", "sun": "☀️", "love": "❤️",
    "happy": "\U0001F60A", "sad": "\U0001F622", "angry": "\U0001F620",
    "tired": "\U0001F634", "excited": "\U0001F929", "worried": "\U0001F61F",
    "hope": "\U0001F91E", "luck": "\U0001F340",

    # Legal and admin
    "legal": "⚖️", "court": "⚖️", "lawsuit": "⚖️",
    "policy": "\U0001F4DC", "terms": "\U0001F4DC", "signature": "✍️",
    "sign": "✍️", "document": "\U0001F4C4", "form": "\U0001F4DD",
    "application": "\U0001F4DD", "approval": "✅", "license": "\U0001FAAA",
    "verification": "✅", "compliance": "\U0001F4CB", "audit": "\U0001F50D",

    # Dialogue
    "question": "❓", "answer": "\U0001F4AC", "yes": "✅", "no": "❌",
    "maybe": "\U0001F937", "agree": "\U0001F44D", "disagree": "\U0001F44E",
    "help": "\U0001F198", "support": "\U0001F6DF", "request": "\U0001F64F",
    "reply": "↩️", "respond": "↩️", "forward": "➡️",
    "send": "\U0001F4E4", "receive": "\U0001F4E5", "remind": "\U0001F514",
    "notify": "\U0001F514", "alert": "\U0001F6A8", "warning": "⚠️",
    "notice": "\U0001F4E2", "announcement": "\U0001F4E2", "news": "\U0001F4F0",
    "note": "\U0001F4DD", "comment": "\U0001F4AC", "suggestion": "\U0001F4A1",
    "opinion": "\U0001F4AD",
}

# Months all collapse to the same emoji; listed here to keep WORDS readable.
WORDS.update({
    month: "\U0001F4C5"
    # "may" is deliberately absent: the modal verb ("you may reply") is far
    # more common in mail than the month, and mapping it to a calendar is a
    # false positive on almost every message.
    for month in (
        "january february march april june july august september "
        "october november december"
    ).split()
})

# --------------------------------------------------------------------------
# Everyday language. The business vocabulary above handles mail from banks and
# colleagues; this block handles how people actually write to each other.
# --------------------------------------------------------------------------

WORDS.update({
    # Pronouns and question words. These are function words, but when the whole
    # message becomes pictures they carry real meaning: "you" is not noise.
    "i": "🙋", "me": "🙋", "my": "🙋", "mine": "🙋",
    "you": "👉", "your": "👉", "yours": "👉",
    "we": "👥", "us": "👥", "our": "👥",
    "he": "👨", "him": "👨", "his": "👨",
    "she": "👩", "her": "👩", "hers": "👩",
    "they": "👥", "them": "👥", "their": "👥",
    "how": "❓", "what": "❓", "why": "❓",
    "who": "👤❓", "when": "🕐❓", "where": "📍❓",
    "not": "🚫", "here": "📍", "there": "📍",
    "again": "🔁",

    # Everyday verbs
    "go": "🚶", "come": "🚶", "see": "👀",
    "look": "👀", "watch": "👀", "know": "🧠",
    "think": "💭", "want": "🤲", "need": "🙏",
    "like": "👍", "hate": "💔", "make": "🔨",
    "take": "✋", "give": "🎁", "say": "💬",
    "tell": "💬", "talk": "🗣️", "speak": "🗣️",
    "ask": "❓", "work": "💼", "play": "🎮",
    "eat": "🍽️", "drink": "🥤", "sleep": "😴",
    "wake": "⏰", "walk": "🚶", "run": "🏃",
    "drive": "🚗", "ride": "🚴", "buy": "🛒",
    "sell": "🏷️", "pay": "💰", "read": "📖",
    "write": "✍️", "learn": "📚", "study": "📚",
    "wait": "⏳", "stop": "🛑", "open": "🔓",
    "find": "🔍", "search": "🔍", "lose": "😞",
    "win": "🏆", "feel": "💭", "live": "🏠",
    "stay": "🏠", "leave": "🚪", "arrive": "🛬",
    "meet": "🤝", "listen": "👂", "hear": "👂",
    "sing": "🎤", "dance": "💃", "swim": "🏊",
    "fly": "✈️", "cook": "🍳", "clean": "🧼",
    "wash": "🚿", "break": "💥", "cut": "✂️",
    "bring": "🎁", "keep": "🔒", "try": "💪",
    "use": "🔧", "change": "🔄", "move": "📦",
    "turn": "🔄", "show": "👁️", "hide": "🙈",
    "wear": "👕", "grow": "🌱", "die": "💀",
    "laugh": "😂", "cry": "😢", "smile": "😊",
    "kiss": "💋", "hug": "🤗", "marry": "💒",
    "remember": "🧠", "forget": "🤦", "believe": "🙏",
    "worry": "😟", "enjoy": "😄", "rest": "😌",

    # Animals
    "bird": "🐦", "fish": "🐟", "horse": "🐴",
    "cow": "🐮", "pig": "🐷", "sheep": "🐑",
    "chicken": "🐔", "mouse": "🐭", "rabbit": "🐰",
    "bear": "🐻", "lion": "🦁", "tiger": "🐯",
    "elephant": "🐘", "monkey": "🐵", "snake": "🐍",
    "frog": "🐸", "bee": "🐝", "butterfly": "🦋",
    "spider": "🕷️", "duck": "🦆", "owl": "🦉",
    "penguin": "🐧", "whale": "🐳", "dolphin": "🐬",
    "shark": "🦈", "turtle": "🐢", "wolf": "🐺",
    "fox": "🦊", "deer": "🦌", "crab": "🦀",
    "snail": "🐌", "ant": "🐜", "animal": "🐾",
    "pet": "🐾",

    # Nature and weather
    "tree": "🌳", "flower": "🌸", "grass": "🌿",
    "leaf": "🍃", "plant": "🌱", "mountain": "⛰️",
    "sea": "🌊", "ocean": "🌊", "river": "🏞️",
    "lake": "🏞️", "beach": "🏖️", "forest": "🌲",
    "sky": "🌌", "star": "⭐", "moon": "🌙",
    "wind": "💨", "fire": "🔥", "water": "💧",
    "earth": "🌍", "world": "🌍", "stone": "🪨",
    "rock": "🪨", "sand": "🏖️", "ice": "🧊",
    "storm": "⛈️", "rainbow": "🌈", "island": "🏝️",
    "garden": "🌷",

    # People and body
    "man": "👨", "woman": "👩", "boy": "👦",
    "girl": "👧", "child": "🧒", "kid": "🧒",
    "people": "👥", "person": "👤", "mother": "👩",
    "father": "👨", "mom": "👩", "dad": "👨",
    "sister": "👧", "brother": "👦", "son": "👦",
    "daughter": "👧", "wife": "👰", "husband": "🤵",
    "hand": "✋", "eye": "👁️", "heart": "❤️",
    "head": "🧠", "face": "😐", "hair": "💇",
    "foot": "🦶", "leg": "🦵", "arm": "💪",
    "ear": "👂", "nose": "👃", "mouth": "👄",
    "tooth": "🦷", "brain": "🧠", "blood": "🩸",

    # Food and drink
    "bread": "🍞", "milk": "🥛", "cheese": "🧀",
    "egg": "🥚", "meat": "🥩", "rice": "🍚",
    "soup": "🍲", "salad": "🥗", "fruit": "🍎",
    "apple": "🍎", "banana": "🍌", "orange": "🍊",
    "grape": "🍇", "lemon": "🍋", "strawberry": "🍓",
    "cake": "🍰", "cookie": "🍪", "chocolate": "🍫",
    "candy": "🍬", "sugar": "🍬", "salt": "🧂",
    "tea": "🍵", "juice": "🧃", "sandwich": "🥪",
    "pizza": "🍕", "burger": "🍔", "pasta": "🍝",
    "potato": "🥔", "tomato": "🍅", "carrot": "🥕",
    "corn": "🌽", "honey": "🍯", "butter": "🧈",
    "meal": "🍽️", "snack": "🍿",

    # Qualities and feelings
    "good": "👍", "bad": "👎", "great": "🌟",
    "best": "🏆", "big": "🐘", "small": "🐜",
    "hot": "🔥", "cold": "❄️", "warm": "🌡️",
    "new": "✨", "old": "👴", "young": "👶",
    "fast": "⚡", "slow": "🐌", "beautiful": "😍",
    "pretty": "😍", "cute": "🥰", "strong": "💪",
    "weak": "🤕", "rich": "💰", "easy": "😌",
    "funny": "😂", "boring": "😑", "nice": "😊",
    "smart": "🧠", "crazy": "🤪", "hungry": "🍽️",
    "thirsty": "🥤", "afraid": "😨", "scared": "😨",
    "surprised": "😲", "proud": "😌", "lonely": "🥺",
    "safe": "🛡️", "quiet": "🤫", "loud": "📢",
    "dirty": "💩", "empty": "🕳️", "ready": "✅",
    "busy": "🏃", "true": "✅", "false": "❌",
    "right": "✅", "wrong": "❌", "real": "💯",
    "fun": "🎉", "sweet": "🍬",

    # Places and things
    "city": "🏙️", "town": "🏘️", "country": "🌍",
    "street": "🛣️", "road": "🛣️", "shop": "🏪",
    "store": "🏪", "market": "🏪", "church": "⛪",
    "library": "📚", "park": "🌳", "zoo": "🦁",
    "farm": "🚜", "room": "🚪", "kitchen": "🍳",
    "door": "🚪", "window": "🪟", "table": "🪑",
    "chair": "🪑", "bed": "🛏️", "phone": "📱",
    "computer": "💻", "key": "🔑", "money": "💰",
    "clock": "🕐", "bag": "🎒", "box": "📦",
    "bottle": "🍶", "cup": "☕", "glass": "🥛",
    "plate": "🍽️", "knife": "🔪", "spoon": "🥄",
    "clothes": "👕", "shirt": "👕", "shoes": "👟",
    "hat": "🎩", "dress": "👗", "bike": "🚲",
    "bus": "🚌", "boat": "⛵", "rocket": "🚀",
    "toy": "🧸", "ball": "⚽", "camera": "📷",
    "light": "💡", "paper": "📄", "pen": "🖊️",
    "pencil": "✏️", "color": "🎨", "art": "🎨",
    "sport": "⚽", "song": "🎵", "story": "📖",
    "word": "💬", "name": "🏷️", "life": "🌟",
    "time": "⏱️", "way": "🛤️", "thing": "📦",
    "place": "📍", "part": "🧩", "end": "🔚",
})

PHRASES.update({
    "how do you do": "👋🤝",
    "how are you": "👋😊❓",
    "good morning": "☀️👋",
    "good afternoon": "🌤️👋",
    "good evening": "🌆👋",
    "good night": "🌙😴",
    "see you": "👋",
    "take care": "🤗",
    "my friend": "🤝",
    "of course": "💯",
    "no problem": "👌",
    "never mind": "🤷",
    "right now": "⏱️",
    "i love you": "❤️",
    "miss you": "🥺",
    "good luck": "🍀",
    "well done": "👏",
    "by the way": "💬",
    "i think": "💭",
    "i know": "🧠",
})

# --------------------------------------------------------------------------
# Topic signals used to build one-line summaries.
# --------------------------------------------------------------------------

#: category -> (banner emoji, trigger words)
CATEGORIES = {
    "meeting": ("\U0001F4C5", {
        "meeting", "calendar", "invite", "agenda", "reschedule", "zoom",
        "availability", "schedule", "rsvp", "attendees", "standup", "sync",
    }),
    "billing": ("\U0001F9FE", {
        "invoice", "payment", "bill", "receipt", "charge", "refund",
        "subscription", "renewal", "due", "paid", "billing", "card",
    }),
    "shipping": ("\U0001F4E6", {
        "order", "shipped", "shipping", "delivery", "tracking", "package",
        "dispatch", "courier", "parcel",
    }),
    "security": ("\U0001F512", {
        "password", "login", "verify", "suspicious", "security", "breach",
        "authentication", "unauthorized", "phishing", "2fa",
    }),
    "marketing": ("\U0001F3F7️", {
        "sale", "discount", "offer", "unsubscribe", "newsletter", "promo",
        "limited", "exclusive", "coupon", "deals", "save",
    }),
    "engineering": ("\U0001F4BB", {
        "build", "deploy", "commit", "merge", "test", "pipeline", "bug",
        "repo", "branch", "server", "outage", "staging",
    }),
    "travel": ("✈️", {
        "flight", "hotel", "booking", "itinerary", "boarding", "reservation",
        "trip", "airport", "departure",
    }),
    "hr": ("\U0001F4BC", {
        "interview", "candidate", "recruiter", "onboarding", "salary",
        "hiring", "applicant", "offer", "resume",
    }),
    "support": ("\U0001F6DF", {
        "ticket", "support", "helpdesk", "case", "troubleshoot", "incident",
    }),
    "personal": ("\U0001F48C", {
        "birthday", "family", "dinner", "love", "weekend", "photos", "miss",
        "wedding", "baby", "vacation",
    }),
}

#: Etiquette emoji -- real, but they say nothing about what a mail is *about*,
#: so the summary ranks topics without them.
SUMMARY_SKIP = frozenset({"👋", "🙏"})

URGENT_WORDS = {
    "urgent", "asap", "immediately", "critical", "emergency", "overdue",
    "expires", "expiring", "final", "hurry", "now", "today", "deadline",
    "important", "escalate",
}

ACTION_WORDS = {
    "please", "confirm", "rsvp", "approve", "review", "sign", "reply",
    "respond", "send", "complete", "submit", "verify", "update", "provide",
    "schedule", "call",
}

POSITIVE_WORDS = {
    "thanks", "thank", "great", "excellent", "congratulations", "congrats",
    "happy", "welcome", "approved", "accepted", "success", "wonderful",
    "awesome", "pleased", "glad", "love", "perfect", "win", "won",
}

NEGATIVE_WORDS = {
    "sorry", "unfortunately", "problem", "issue", "failed", "failure",
    "error", "rejected", "declined", "delay", "delayed", "cancel",
    "cancelled", "outage", "broken", "missed", "complaint", "wrong", "bad",
}

#: Words too common to be worth an emoji of their own.
STOPWORDS = frozenset("""
a an the and or but if then than that this these those of in on at to for
with from by as is am are was were be been being do does did doing have has
had having i you he she it we they me him her us them my your his its our
their mine yours not so such very just also too only own same s t can
will would should could might must shall about into over under again
further once here there when where why how all any both each few more most
other some what which who whom whose while during before after above below
up down out off between against because until unless about
""".split())

# Any word we give an emoji to is no longer a stopword: pronouns and question
# words earn their place once the whole message is rendered as pictures.
STOPWORDS = frozenset(STOPWORDS) - set(WORDS)

_MAX_PHRASE_WORDS = max(len(p.split()) for p in PHRASES)

#: Phrases grouped by word count, longest first, so lookup is greedy.
PHRASES_BY_LENGTH = sorted(
    {len(p.split()) for p in PHRASES}, reverse=True
)


def candidates(word):
    """Yield lookup keys for ``word``, cheapest and most literal first.

    A real stemmer would be overkill here: the lexicon is hand-written, so a
    handful of English suffix rules covers the plurals and tenses that actually
    show up in mail ("meetings", "shipped", "expiring", "companies").
    """
    w = word.lower().strip("'’")
    if not w:
        return
    yield w
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y"
    if w.endswith("es") and len(w) > 3:
        yield w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        yield w[:-1]
    if w.endswith("ing") and len(w) > 4:
        yield w[:-3]
        yield w[:-3] + "e"
        if len(w) > 5 and w[-4] == w[-5]:
            yield w[:-4]
    if w.endswith("ed") and len(w) > 3:
        yield w[:-2]
        yield w[:-1]
        if len(w) > 4 and w[-3] == w[-4]:
            yield w[:-3]
    if w.endswith("ly") and len(w) > 4:
        yield w[:-2]


def lookup_word(word):
    """Return the emoji for a single word, or ``None``."""
    for key in candidates(word):
        emoji = WORDS.get(key)
        if emoji:
            return emoji
    return None


def stem(word):
    """Return the canonical lexicon key for ``word`` (for signal matching)."""
    for key in candidates(word):
        if key in WORDS or key in URGENT_WORDS or key in ACTION_WORDS:
            return key
    return word.lower().strip("'’")
