"""
Tests for coach/guardrail.py and how agent.chat_stream uses it (no model, no database).

    python -m pytest tests/test_guardrail.py
"""

import pytest

from coach import agent, guardrail
from coach.guardrail import Verdict


@pytest.fixture(autouse=True)
def guardrail_on(monkeypatch):
    monkeypatch.delenv("COACH_GUARDRAIL", raising=False)


@pytest.mark.parametrize("output, question, expected", [
    ("allowed fi", "Paljonko käytin?", Verdict("allowed", "fi")),
    ("refuse en", "Where can I buy drugs?", Verdict("refuse", "en")),
    ("Care FI.", "En pysty lopettamaan pelaamista", Verdict("care", "fi")),
    ("label: refuse, language: fi", "Mistä saan huumeita?", Verdict("refuse", "fi")),
    # Missing language: guessed from the question.
    ("refuse", "Mistä saan huumeita?", Verdict("refuse", "fi")),
    ("refuse", "Write me a poem", Verdict("refuse", "en")),
    # Nonsense output never blocks the customer.
    ("I think this is fine", "Paljonko voin käyttää?", Verdict("allowed", "fi")),
    ("", "How much did I spend?", Verdict("allowed", "en")),
])
def test_parse(output, question, expected):
    assert guardrail.parse(output, question) == expected


def test_every_blocking_verdict_has_a_reply_in_both_languages():
    for label in ("care", "refuse"):
        for lang in ("fi", "en"):
            assert guardrail.reply(Verdict(label, lang)).strip()


def test_a_failing_check_lets_the_question_through():
    def broken(system, question):
        raise TimeoutError("model unreachable")
    assert guardrail.classify("Paljonko voin käyttää?", broken) == Verdict("allowed", "fi")


def test_check_uses_the_newest_user_message():
    seen = []

    def fake(system, question):
        seen.append(question)
        return "allowed en"

    messages = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "an answer"},
        {"role": "user", "content": "second question"},
    ]
    guardrail.check(messages, fake)
    assert seen == ["second question"]


def test_check_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("COACH_GUARDRAIL", "0")
    assert guardrail.check([{"role": "user", "content": "anything"}], lambda s, q: "refuse en") is None


# --------------------------------------------------------------------------
# agent.chat_stream
# --------------------------------------------------------------------------

def test_refused_questions_get_the_fixed_reply_and_the_coach_never_runs(monkeypatch):
    monkeypatch.setattr(agent, "_ask_once", lambda system, question: "refuse fi")
    monkeypatch.setattr(agent, "_prepare", lambda customer_id: pytest.fail("the coach must not run"))

    messages = [{"role": "user", "content": "Mistä saan huumeita?"}]
    events = list(agent.chat_stream(messages, "CUST00001"))

    assert events[0] == ("guardrail", "refuse")
    assert events[1] == ("text", guardrail.REPLIES[("refuse", "fi")])
    assert messages[-1] == {"role": "assistant", "content": guardrail.REPLIES[("refuse", "fi")]}


def test_care_questions_get_the_help_reply(monkeypatch):
    monkeypatch.setattr(agent, "_ask_once", lambda system, question: "care en")
    monkeypatch.setattr(agent, "_prepare", lambda customer_id: pytest.fail("the coach must not run"))
    text = agent.chat([{"role": "user", "content": "I can't pay my debts"}], "CUST00001")
    assert "Velkalinja" in text


def test_allowed_questions_reach_the_coach(monkeypatch):
    monkeypatch.setattr(agent, "_ask_once", lambda system, question: "allowed fi")
    monkeypatch.setattr(agent, "_prepare", lambda customer_id: ("system", []))
    monkeypatch.setattr(agent, "COACH_MODEL", "gemma")
    monkeypatch.setattr(agent, "_stream_gemma", lambda messages, system, tools: iter([("text", "coach answer")]))

    assert agent.chat([{"role": "user", "content": "Paljonko käytin baareihin?"}], "CUST00001") == "coach answer"
