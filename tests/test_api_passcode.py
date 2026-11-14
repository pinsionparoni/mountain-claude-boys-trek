"""
The demo passcode on the web API (coach/api.py): no database, no model.

The passcode is checked before any endpoint runs, so a wrong or missing one
never reaches customer data or Gemma. Without DEMO_PASSCODE nothing changes.
"""

import pytest
from fastapi.testclient import TestClient

from coach import api, budget

CLIENT = TestClient(api.app)  # not "with": the startup preload doesn't run
PROTECTED_GETS = ["/passcode", "/customers/CUST00226/budget", "/customers/CUST00226/summary"]


@pytest.fixture
def fake_budget(monkeypatch):
    """The budget endpoint without the database."""
    monkeypatch.setattr(api, "_today", lambda customer_id: None)
    monkeypatch.setattr(budget, "safe_to_spend", lambda customer_id, today: {"safe_to_spend_this_week": 68.23})


def test_without_a_passcode_nothing_is_checked(monkeypatch, fake_budget):
    monkeypatch.delenv("DEMO_PASSCODE", raising=False)
    assert CLIENT.get("/health").json()["passcode_required"] is False
    assert CLIENT.get("/passcode").status_code == 200
    assert CLIENT.get("/customers/CUST00226/budget").json() == {"safe_to_spend_this_week": 68.23}


@pytest.mark.parametrize("path", PROTECTED_GETS)
@pytest.mark.parametrize("headers", [{}, {"X-Demo-Passcode": "wrong"}, {"X-Demo-Passcode": ""}])
def test_missing_or_wrong_passcode_is_refused(monkeypatch, fake_budget, path, headers):
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")
    response = CLIENT.get(path, headers=headers)
    assert response.status_code == 401
    assert "68.23" not in response.text


def test_chat_is_refused_before_it_reaches_the_model(monkeypatch):
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")
    called = []
    monkeypatch.setattr(api.agent, "chat_stream", lambda *a, **k: called.append(1) or iter(()))
    response = CLIENT.post("/chat", json={"customer_id": "CUST00226", "message": "Hei"})
    assert response.status_code == 401
    assert called == []


def test_right_passcode_lets_requests_through(monkeypatch, fake_budget):
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")
    headers = {"X-Demo-Passcode": "junction-2026"}
    assert CLIENT.get("/health").json()["passcode_required"] is True
    assert CLIENT.get("/passcode", headers=headers).json() == {"ok": True}
    assert CLIENT.get("/customers/CUST00226/budget", headers=headers).json() == {"safe_to_spend_this_week": 68.23}


def test_health_stays_open(monkeypatch):
    # The app needs it to know whether to ask for a passcode.
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")
    assert CLIENT.get("/health").status_code == 200


def test_receipts_are_protected_and_stop_at_today(monkeypatch):
    from datetime import date
    asked = []
    monkeypatch.setattr(api, "_today", lambda customer_id: date(2026, 9, 10))
    monkeypatch.setattr(api.queries, "recent_purchases",
                        lambda customer_id, until, limit: asked.append((customer_id, until, limit)) or [])
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")

    assert CLIENT.get("/customers/CUST00226/receipts").status_code == 401
    response = CLIENT.get("/customers/CUST00226/receipts?limit=5", headers={"X-Demo-Passcode": "junction-2026"})
    assert response.json() == {"today": "2026-09-10", "receipts": []}
    assert asked == [("CUST00226", date(2026, 9, 10), 5)]
    bad = CLIENT.get("/customers/CUST00226/receipts?limit=500", headers={"X-Demo-Passcode": "junction-2026"})
    assert bad.status_code == 400


def test_tip_is_protected(monkeypatch):
    from datetime import date
    monkeypatch.setattr(api, "_today", lambda customer_id: date(2026, 9, 10))
    monkeypatch.setattr(api.tips, "pick", lambda c, t: {"kind": "on_track", "facts": {}, "chart": {}})
    monkeypatch.setenv("DEMO_PASSCODE", "junction-2026")
    assert CLIENT.get("/customers/CUST00226/tip").status_code == 401
    ok = CLIENT.get("/customers/CUST00226/tip", headers={"X-Demo-Passcode": "junction-2026"})
    assert ok.json() == {"today": "2026-09-10", "kind": "on_track", "facts": {}, "chart": {}}
