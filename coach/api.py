"""Web API for the mobile front end.

Run it with:

    .venv/bin/uvicorn coach.api:app --reload

Endpoints:

- ``POST /chat``: send a message, get the coach's answer streamed back as
  server-sent events (``text/event-stream``):

  - ``conversation``: ``{"conversation_id": "..."}``, first; send it back with the
    next message to continue the same conversation.
  - ``tool``: ``{"name": "get_safe_to_spend"}`` while the coach looks something up,
    so the app can show "checking your spending…".
  - ``text``: ``{"text": "..."}``, a piece of the answer; append them in order.
  - ``chart``: a chart spec (coach/charts.py) to draw with the answer: the model
    chose it, every number in it was computed from the customer's data.
  - ``guardrail``: ``{"label": "care" | "refuse"}`` when the question got a fixed reply
    instead of the coach (see POLICY.md).
  - ``error``: ``{"message": "..."}`` if something went wrong.
  - ``done``: ``{}`` at the end.

- ``GET /customers/{id}/summary``: spending in the three baskets for a period
  (default: this month so far), for basket cards. No AI involved.
- ``GET /customers/{id}/budget``: the monthly budget and safe to spend this week.
- ``GET /customers/{id}/receipts``: the latest card purchases up to "today",
  newest first, each with its merchant type and basket. No AI involved.
- ``GET /customers/{id}/tip``: the home screen's money-coaching tip, picked by
  rules from the customer's data (coach/tips.py), with a chart. No AI involved.
- ``GET /health``: is the API up, and does it need a demo passcode.
- ``GET /passcode``: 200 if the ``X-Demo-Passcode`` header is right (for the login screen).

Conversations live in this process's memory, so a restart forgets them. There
is no real login: anyone who can reach the API can pick any customer. Fine for
the demo, not for real customers. A hosted demo sets ``DEMO_PASSCODE``: then
the coach and customer endpoints answer 401 unless the request carries it in
the ``X-Demo-Passcode`` header, so strangers can't read data or keep Gemma busy.
Without ``DEMO_PASSCODE`` (local development) nothing is checked.
"""

import hmac
import json
import logging
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from coach import agent, budget, peers, tips
from coach.database import queries
from coach.spending_baskets import BASKET_LABELS_FI
from coach.tools.spending import DATA_END

log = logging.getLogger(__name__)


def _warm_peer_cache():
    # Every customer's data ends in late September 2026, so one period serves them all.
    try:
        peers.warm_up(budget.coach_today(DATA_END))
        log.info("Peer comparison data loaded")
    except Exception:  # the first compare_with_peers call will load it instead
        log.exception("Could not preload peer comparison data")


@asynccontextmanager
async def lifespan(app):
    # The peer population takes several seconds to load; do it in the
    # background so the API answers immediately.
    threading.Thread(target=_warm_peer_cache, daemon=True).start()
    yield


app = FastAPI(title="Mountain Claude Boys finance coach", lifespan=lifespan)

# The front end may be served from another address while developing.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CUSTOMER_ID = re.compile(r"^CUST\d{5}$")
_conversations = {}  # conversation_id -> {"customer_id": ..., "messages": [...]}


class ChatRequest(BaseModel):
    customer_id: str = Field(examples=["CUST00001"])
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


def _today(customer_id):
    """The coach's "today" for this customer, or 404 if the customer doesn't exist."""
    if not CUSTOMER_ID.match(customer_id):
        raise HTTPException(404, "Unknown customer")
    try:
        profile = queries.customer_profile(customer_id)
    except ValueError:
        raise HTTPException(404, "Unknown customer") from None
    return budget.coach_today(date.fromisoformat(profile["data_to"]))


def _passcode():
    return os.getenv("DEMO_PASSCODE") or None


def require_passcode(x_demo_passcode: str | None = Header(default=None)):
    """401 unless the request carries the demo passcode (only when DEMO_PASSCODE is set)."""
    expected = _passcode()
    if expected and not hmac.compare_digest((x_demo_passcode or "").encode(), expected.encode()):
        raise HTTPException(401, "Wrong or missing demo passcode")


PROTECTED = [Depends(require_passcode)]


def _event(name, data):
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/health")
def health():
    return {"ok": True, "model": agent.COACH_MODEL, "passcode_required": _passcode() is not None}


@app.get("/passcode", dependencies=PROTECTED)
def check_passcode():
    return {"ok": True}


@app.post("/chat", dependencies=PROTECTED)
def chat(request: ChatRequest):
    _today(request.customer_id)  # 404 for unknown customers before streaming starts

    conversation = _conversations.get(request.conversation_id)
    if conversation is None or conversation["customer_id"] != request.customer_id:
        conversation_id = uuid.uuid4().hex
        conversation = {"customer_id": request.customer_id, "messages": []}
        _conversations[conversation_id] = conversation
    else:
        conversation_id = request.conversation_id

    messages = conversation["messages"]
    messages.append({"role": "user", "content": request.message})

    def events():
        yield _event("conversation", {"conversation_id": conversation_id})
        try:
            for kind, value in agent.chat_stream(messages, customer_id=request.customer_id):
                if kind == "text":
                    yield _event("text", {"text": value})
                elif kind == "tool":
                    yield _event("tool", {"name": value})
                elif kind == "chart":
                    yield _event("chart", value)
                elif kind == "guardrail":
                    yield _event("guardrail", {"label": value})
        except Exception as e:  # the stream has started, so report errors in it
            yield _event("error", {"message": f"The coach couldn't answer: {e}"})
        yield _event("done", {})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.get("/customers/{customer_id}/summary", dependencies=PROTECTED)
def summary(customer_id: str, start_date: date | None = None, end_date: date | None = None):
    today = _today(customer_id)
    end = min(end_date or today, today)
    start = start_date or end.replace(day=1)
    if start > end:
        raise HTTPException(400, "start_date must be on or before end_date (and not after today)")
    result = queries.basket_summary(customer_id, start, end)
    result["today"] = today.isoformat()
    result["labels_fi"] = BASKET_LABELS_FI
    return result


@app.get("/customers/{customer_id}/budget", dependencies=PROTECTED)
def monthly_budget(customer_id: str):
    return budget.safe_to_spend(customer_id, _today(customer_id))


@app.get("/customers/{customer_id}/receipts", dependencies=PROTECTED)
def receipts(customer_id: str, limit: int = 30):
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit must be between 1 and 100")
    today = _today(customer_id)
    return {"today": today.isoformat(), "receipts": queries.recent_purchases(customer_id, today, limit)}


@app.get("/customers/{customer_id}/tip", dependencies=PROTECTED)
def tip(customer_id: str):
    today = _today(customer_id)
    return {"today": today.isoformat(), **tips.pick(customer_id, today)}
