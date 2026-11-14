"""
Rule-based checks for the coach's Finnish answers.

No AI and no network: the same text always gives the same issues, so runs
before and after fine-tuning can be compared. Each issue has a ``code``, a
``severity`` ("error": wrong Finnish; "warning": usually wrong, a native
speaker should look), the ``excerpt`` that triggered it and a ``hint``.

What the rules can't see: typos that form no known pattern ("viihkkeeseen"),
real words used wrongly ("ulkoilma-ateria") and general clunkiness. Add those
to bad_phrases.py once seen, and use the review sheet for the rest.

    from evals.finnish.checks import check_answer
    for issue in check_answer(text): print(issue)
"""

import re
from dataclasses import asdict, dataclass

from coach.spending_baskets import (
    BASKET_LABELS,
    BASKET_LABELS_FI,
    CATEGORY_BASKETS,
    CATEGORY_MEDIAN_EUR,
    MERCHANT_TYPES,
    OTHER_BASKETS,
)
from evals.finnish.bad_phrases import BAD_PHRASES

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    excerpt: str
    hint: str
    position: int = 0  # character offset in the answer, for ordering

    def as_dict(self):
        return asdict(self)


def _issue(code, severity, text, start, end, hint):
    return Issue(code, severity, _excerpt(text, start, end), hint, start)


# --------------------------------------------------------------------------
# Capital letters
# --------------------------------------------------------------------------

# Words allowed a capital anywhere: names and brands, matched by the start of
# the word so inflected forms pass too (S-Pankin, Helsingissä, Suomessa).
ALLOWED_CAPITAL_PREFIXES = (
    "S-Pank", "S-mobiil", "S-Etukort", "Etukort", "S-Tili", "Visa", "Mastercard",
    "Helsin", "Hel", "Espoo", "Vanta", "Suom", "Euroop", "Tilastokesk", "Kela",
    "Verda", "Gemma", "Claude", "Google", "MyData", "PSD2",
    # Help services named in POLICY.md and organisations the coach may refer to.
    "Peluur", "Kriisipuhel", "Takuusäät", "Velkalinj", "Verohallin", "Finanssivalvon",
)

# The first words of S-Bank's Finnish basket names. Written exactly as the
# name ("☕ Arjen kulutus", "(🏠 Välttämättömät menot)", "Arjen kulutus
# -koriin") they pass; inflected mid-sentence with a capital ("kuuluvat
# ☕ Arjen kulutukseen") they get their own warning.
BASKET_WORD_PREFIXES = ("välttämättöm", "yllättäv", "arjen")
_BASKET_NAMES = tuple(label.split(" ", 1)[1] for label in BASKET_LABELS_FI.values())
_BASKET_NAME = re.compile("(?:" + "|".join(map(re.escape, _BASKET_NAMES)) + r")(?![^\W\d_])")

_WORD = re.compile(r"[^\W\d_][\w-]*", re.UNICODE)
# Line starts: list bullets, numbered items, headings, quotes.
_LINE_PREFIX = re.compile(r"^\s*(?:[-*•+]\s+|\d+[.)]\s+|#+\s+|>\s*)*")
# End of a sentence: . ! ? … not after a digit (dates, ordinals: 15. syyskuuta),
# except after a four-digit year ("…elokuussa 2026. Nämä menot…").
_SENTENCE_END = re.compile(r"(?:(?<!\d)|(?<=(?<!\d)\d{4}))[.!?…]+[\"'”»)*_]*\s+")


def _is_allowed_capital(word):
    if len(word) == 1 or word.isupper():  # S, EU, ALV
        return True
    return word.startswith(ALLOWED_CAPITAL_PREFIXES)


def _excerpt(text, start, end, width=30):
    left = max(0, start - width)
    right = min(len(text), end + width)
    snippet = text[left:right].replace("\n", " ").strip()
    return ("…" if left else "") + snippet + ("…" if right < len(text) else "")


def _capital_issues(text):
    issues = []
    # Words inside an English phrase ("Home & Tech") are the English check's.
    english = [m.span() for m in _ENGLISH.finditer(text)]
    for line_match in re.finditer(r"[^\n]+", text):
        line = line_match.group()
        offset = line_match.start()
        body_start = _LINE_PREFIX.match(line).end()

        # Segment boundaries: line start, sentence ends and colons. Each word
        # is judged by what comes between the last boundary and it.
        boundaries = [(body_start, "start")]
        boundaries += [(m.end(), "start") for m in _SENTENCE_END.finditer(line)]
        # A colon closing a bold label ("**Vinkki:** Koska…", "**Viihde**: Käytät…")
        # acts as a small heading: a capital may follow. Plain colons inside a
        # sentence ("Pieni vinkki: Koska…") are checked.
        for m in re.finditer(r"(\*\*)?:(\*\*)?\s+", line):
            boundaries.append((m.end(), "start" if (m.group(1) or m.group(2)) else "colon"))
        boundaries.sort()

        for word_match in _WORD.finditer(line, body_start):
            word = word_match.group()
            pos = word_match.start()
            if not word[0].isupper() or _is_allowed_capital(word):
                continue
            if any(start <= offset + pos < end for start, end in english):
                continue  # reported by the English check
            last_pos, kind = max((b for b in boundaries if b[0] <= pos), default=(body_start, "start"))
            # Only punctuation, emoji, markdown or numbers since the boundary:
            # the word opens its sentence or list item ("**746,21 €** – Asuminen").
            if not _WORD.search(line, last_pos, pos):
                if kind == "start":
                    continue
                issues.append(_issue(
                    "capital_after_colon", WARNING, text, offset + pos, offset + word_match.end(),
                    f"Kaksoispisteen jälkeen jatketaan yleensä pienellä: '{word[0].lower() + word[1:]}'.",
                ))
                continue
            if word.lower().startswith(BASKET_WORD_PREFIXES):
                if _BASKET_NAME.match(line, pos):
                    continue  # the basket's name, written as a name
                code, severity = "basket_name_capital", WARNING
                hint = f"Korin nimi kesken lauseen pienellä: '{word.lower()}' (esim. 'arjen kulutukseen')."
            else:
                code, severity = "capital_mid_sentence", ERROR
                hint = f"Iso kirjain kesken lauseen: '{word[0].lower() + word[1:]}', ellei kyse ole erisnimestä."
            issues.append(_issue(code, severity, text, offset + pos, offset + word_match.end(), hint))
    return issues


# --------------------------------------------------------------------------
# English leaking into Finnish
# --------------------------------------------------------------------------

def _english_terms():
    """Category, merchant and basket names from the data, plus common words."""
    terms = set(CATEGORY_MEDIAN_EUR) | set(CATEGORY_BASKETS) | set(OTHER_BASKETS)
    terms |= {"Salary", "Other Income", "Invest Deposit", "Invest Withdraw", "Salary Sweep"}
    terms |= {label for label, _basket in MERCHANT_TYPES.values()}
    terms |= {label.split(" ", 1)[1] for label in BASKET_LABELS.values()}  # drop the emoji
    terms |= {
        "the", "and", "you", "your", "with", "spending", "savings", "income",
        "budget", "peers", "median", "typical", "other", "bill", "tip", "per month",
    }
    # Merchant labels that are also fine Finnish words or loans.
    return sorted(terms - {"taxi"}, key=len, reverse=True)


_ENGLISH = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(t).replace(r"\ ", r"\s+") for t in _english_terms()) + r")(?![\w])",
    re.IGNORECASE,
)


def _english_issues(text):
    return [
        _issue(
            "english_word", ERROR, text, m.start(), m.end(),
            f"Englantia suomenkielisessä vastauksessa: '{m.group()}'. Käytä suomenkielistä nimeä.",
        )
        for m in _ENGLISH.finditer(text)
    ]


# --------------------------------------------------------------------------
# Numbers, money and dates (Kielitoimisto's recommendations)
# --------------------------------------------------------------------------

_DECIMAL_HINT = "Desimaalierottimena pilkku: 84,7 % ja 68,23 €."

_NUMBER_RULES = [
    # 84.7 % / 68.23 € / 1,086.14 €: a decimal point before a percent or euro
    # sign (times like klo 14.30 and dates have no unit, so they pass).
    (re.compile(r"(?<![\d.,])\d+(?:,\d{3})*\.\d{1,2}(?!\.?\d)(?=\s?(?:%|€|e\b|euroa))"),
     "decimal_point", ERROR, _DECIMAL_HINT),
    # €68.23
    (re.compile(r"(?<=€)\s?\d+(?:,\d{3})*\.\d{1,2}(?!\.?\d)"),
     "decimal_point", ERROR, _DECIMAL_HINT),
    (re.compile(r"€\s?\d"), "euro_before_number", ERROR, "Euromerkki luvun perään välilyönnin kanssa: 68,23 €."),
    (re.compile(r"\d(?:%|€)"), "no_space_before_unit", WARNING, "Välilyönti ennen merkkiä: 84,7 % ja 68 €."),
    # 12345 € (but not the "086" of a correctly written "1 086 €").
    (re.compile(r"(?<![\d.,])(?<!\d\s)\d{5,}(?:,\d+)?(?=\s?(?:€|euroa))"),
     "no_thousands_space", WARNING, "Isoissa luvuissa välilyönti tuhansien välissä: 12 345 €."),
    (re.compile(r"(?<![\d.])(?:0\d\.\d{1,2}\.|\d{1,2}\.0\d\.)(?:\d{4})?"),
     "date_leading_zero", WARNING, "Päivämäärä ilman etunollia: 1.9.2025."),
]


def _number_issues(text):
    issues = []
    for pattern, code, severity, hint in _NUMBER_RULES:
        for m in pattern.finditer(text):
            issues.append(_issue(code, severity, text, m.start(), m.end(), hint))
    return issues


# --------------------------------------------------------------------------
# Known bad phrases (bad_phrases.py)
# --------------------------------------------------------------------------

_BAD = [(re.compile(pattern, re.IGNORECASE), code, severity, hint)
        for pattern, code, severity, hint in BAD_PHRASES]


def _bad_phrase_issues(text):
    return [
        _issue(code, severity, text, m.start(), m.end(), hint)
        for pattern, code, severity, hint in _BAD
        for m in pattern.finditer(text)
    ]


# --------------------------------------------------------------------------

def check_answer(text):
    """All issues in one Finnish answer, in the order they appear."""
    issues = (_capital_issues(text) + _english_issues(text)
              + _number_issues(text) + _bad_phrase_issues(text))
    return sorted(issues, key=lambda i: i.position)
