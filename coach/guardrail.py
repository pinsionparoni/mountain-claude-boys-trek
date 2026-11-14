"""
The check before the coach answers (see POLICY.md).

Each new question is sorted into one of three groups by a short, narrow model
call that only answers with a label and the question's language:

- "allowed": the coach answers normally.
- "care": the person seems to be in trouble; a fixed, kind reply points to help.
- "refuse": harmful, illegal or off-topic; a fixed, polite decline.

For "care" and "refuse" the coach itself never runs, so its reply can't contain
anything unexpected. If the check fails (network, odd output), the question is
treated as allowed: the coach's own prompt rules still apply, and a broken check
never blocks a customer.

Set COACH_GUARDRAIL=0 to turn it off, e.g. to measure its effect with the test set.
"""

import os
import re
from dataclasses import dataclass

LABELS = ("allowed", "care", "refuse")

CLASSIFY_PROMPT = """You sort messages sent to the personal finance coach in a Finnish bank's mobile app. \
The coach only talks about the customer's own money: spending, income, balance, budget, saving, \
comparisons, and general money words.

Reply with exactly two words: the label, then the message's language (fi or en). Example: "allowed fi".

Labels:
- allowed: anything about the customer's own money, even awkward categories (how much they spent at \
bars, on alcohol, entertainment or gambling sites), saving tips, what-ifs, investment or loan questions \
(the coach answers those in general terms), greetings, thanks, and "what can you do?".
- care: the person seems to be in real trouble: gambling or addiction they can't control, debts they \
can't pay, despair or crisis.
- refuse: help buying or using drugs, anything illegal, hiding money or purchases, fraud, gambling \
strategies, weapons, or anything not about money (health, politics, coding, homework, poems, jokes).

When in doubt between allowed and refuse, choose allowed."""

REPLIES = {
    ("refuse", "fi"): (
        "En voi auttaa tässä. Voin kuitenkin auttaa omien raha-asioidesi kanssa, esimerkiksi "
        "katsomaan, mihin rahasi menevät tai paljonko voit käyttää tällä viikolla."
    ),
    ("refuse", "en"): (
        "I can't help with that. I'm happy to help with your own money, for example where it goes "
        "or what you can safely spend this week."
    ),
    # Help services to confirm with S-Bank before the demo (POLICY.md).
    ("care", "fi"): (
        "Kiitos, että kerroit. Et ole tilanteessasi yksin, ja apua on saatavilla maksutta ja "
        "luottamuksellisesti: rahapelaamisen ongelmiin Peluurista, velka-asioihin Takuusäätiön "
        "Velkalinjalta tai kunnan talous- ja velkaneuvonnasta, ja jos olo on raskas, MIELI ry:n "
        "Kriisipuhelimesta. Kun haluat, voin katsoa kanssasi, miten rahasi riittävät palkkapäivään."
    ),
    ("care", "en"): (
        "Thank you for telling me. You're not alone with this, and free, confidential help is "
        "available: Peluuri for gambling problems, Takuusäätiö's Velkalinja or your municipality's "
        "debt counselling for debts, and MIELI ry's crisis line if things feel heavy. Whenever you "
        "like, I can look with you at how your money will last until payday."
    ),
}

_FINNISH_HINT = re.compile(r"[äöå]|\b(mi(ten|kä|ksi|hin|stä)|paljonko|olen|minun|voin|kuinka)\b", re.I)


@dataclass(frozen=True)
class Verdict:
    label: str
    lang: str


def enabled():
    return os.getenv("COACH_GUARDRAIL", "1") != "0"


def guess_lang(text):
    return "fi" if _FINNISH_HINT.search(text or "") else "en"


def parse(output, question):
    """Turn the model's "label lang" reply into a Verdict; unknown output means allowed."""
    words = re.findall(r"[a-z]+", (output or "").lower())
    label = next((w for w in words if w in LABELS), "allowed")
    lang = next((w for w in words if w in ("fi", "en")), guess_lang(question))
    return Verdict(label, lang)


def reply(verdict):
    """The fixed reply for a care or refuse verdict."""
    return REPLIES[(verdict.label, verdict.lang)]


def _latest_user_text(messages):
    for m in reversed(messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            return m["content"]
    return ""


def classify(question, ask_model):
    """Classify one question. ``ask_model(system, question) -> str`` is the narrow model call."""
    try:
        return parse(ask_model(CLASSIFY_PROMPT, question), question)
    except Exception:  # a broken check never blocks the customer (see module docstring)
        return Verdict("allowed", guess_lang(question))


def check(messages, ask_model):
    """Verdict for the newest user message, or None when the guardrail is off."""
    if not enabled():
        return None
    question = _latest_user_text(messages)
    if not question.strip():
        return Verdict("allowed", "en")
    return classify(question, ask_model)
