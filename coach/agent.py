"""Finance-coach chat agent.

COACH_MODEL picks the model: "claude" (default, Anthropic API) or "gemma"
(Gemma 4 on Verda via its OpenAI-compatible endpoint, VERDA_BASE_URL + VERDA_API_KEY).

Every tool is an Anthropic tool definition (a dict with name, description and
input_schema) that also has ``name`` and ``run(input) -> str``: the coach's
spending tools (coach/tools/spending.py) and Exa's helpers both work this way.
For Gemma the definitions are converted to the OpenAI function format.
"""

import json
import os
from datetime import date

from dotenv import load_dotenv

from coach import budget, web_search
from coach.database import queries
from coach.tools import spending

load_dotenv()

COACH_MODEL = os.getenv("COACH_MODEL", "claude")
CLAUDE_MODEL = "claude-opus-5-5"
GEMMA_MODEL = "gemma-coach"  # --served-model-name of the Verda deployment
MAX_TURNS = 10

SYSTEM_PROMPT = """You are a friendly personal finance coach inside a Finnish bank's mobile app. \
You help everyday customers understand where their money goes and make better decisions.

Teach with three spending baskets: regular essentials, unexpected necessities, and everyday spending \
that slips through your fingers.

Explain financial ideas in plain language, and end with one concrete, encouraging suggestion when it fits.

Keep answers short and mobile-friendly. Answer in the language the user writes in."""

CUSTOMER_PROMPT = """

You are talking with customer {customer_id} (age {age}). Today is {today} ({weekday}); their transaction data \
runs from {data_from} up to today. Their account balance today is {balance_eur} €."""

_clients = {}


def _client():
    if COACH_MODEL not in _clients:
        if COACH_MODEL == "gemma":
            from openai import OpenAI
            # Verda's container gateway holds back the whole streamed answer unless
            # the request carries the standard SSE headers.
            _clients[COACH_MODEL] = OpenAI(
                base_url=os.environ["VERDA_BASE_URL"],
                api_key=os.environ["VERDA_API_KEY"],
                default_headers={"Accept": "text/event-stream", "Cache-Control": "no-cache",
                                 "Connection": "keep-alive"},
            )
        else:
            import anthropic
            _clients[COACH_MODEL] = anthropic.Anthropic()
    return _clients[COACH_MODEL]


def _to_openai(tool):
    return {"type": "function", "function": {
        "name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]}}


def _run_tool(tools, name, args):
    """Run a tool and return (output, is_error)."""
    tool = tools.get(name)
    if tool is None:
        return f'Error: unknown tool "{name}"', True
    try:
        return tool.run(args), False
    except Exception as e:  # surface tool failures to the model instead of crashing the turn
        return f"Error: {e}", True


def _chat_claude(messages, system, tools):
    by_name = {t.name: t for t in tools}
    params = {"tools": [dict(t) for t in tools]} if tools else {}
    for _ in range(MAX_TURNS):
        response = _client().beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            system=system,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **params,
        )

        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one. Try asking about your spending in another way."

        # Drop declined-model blocks that precede a server-side fallback boundary.
        boundary = max((i for i, b in enumerate(response.content) if b.type == "fallback"), default=-1)
        content = [b for i, b in enumerate(response.content) if i > boundary or b.type == "text"]
        messages.append({"role": "assistant", "content": content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in content if b.type == "text")
            if response.stop_reason == "max_tokens":
                text += "\n\n(Answer was cut off.)"
            return text

        results = []
        for block in content:
            if block.type == "tool_use":
                output, is_error = _run_tool(by_name, block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    return "Sorry, that took too many steps. Could you narrow the question down?"


def _stream_gemma(messages, system, tools):
    """Yield ("text", chunk) as Gemma writes and ("tool", name) as tools run."""
    by_name = {t.name: t for t in tools}
    params = {"tools": [_to_openai(t) for t in tools]} if tools else {}
    for _ in range(MAX_TURNS):
        stream = _client().chat.completions.create(
            model=GEMMA_MODEL,
            max_tokens=4096,
            messages=[{"role": "system", "content": system}, *messages],
            stream=True,
            **params,
        )
        text, calls, finish = [], {}, None
        for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                text.append(delta.content)
                yield "text", delta.content
            # Tool calls arrive in pieces; join them by index.
            for piece in delta.tool_calls or []:
                call = calls.setdefault(piece.index, {"id": None, "name": "", "arguments": ""})
                call["id"] = piece.id or call["id"]
                if piece.function:
                    call["name"] += piece.function.name or ""
                    call["arguments"] += piece.function.arguments or ""
            finish = choice.finish_reason or finish

        turn = {"role": "assistant", "content": "".join(text)}
        if calls:
            turn["tool_calls"] = [{"id": c["id"], "type": "function",
                                   "function": {"name": c["name"], "arguments": c["arguments"]}}
                                  for c in calls.values()]
        messages.append(turn)

        if not calls:
            if finish == "length":
                yield "text", "\n\n(Answer was cut off.)"
            return

        for call in calls.values():
            yield "tool", call["name"]
            try:
                args = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError:
                output = "Error: tool arguments were not valid JSON"
            else:
                output, _ = _run_tool(by_name, call["name"], args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})

    yield "text", "Sorry, that took too many steps. Could you narrow the question down?"


def _prepare(customer_id):
    """System prompt and tools for one customer (or for no customer data at all)."""
    system = SYSTEM_PROMPT
    tools = web_search.load_tools()
    if customer_id:
        profile = queries.customer_profile(customer_id)
        today = budget.coach_today(date.fromisoformat(profile["data_to"]))
        system += CUSTOMER_PROMPT.format(
            customer_id=customer_id, age=profile["age"], data_from=profile["data_from"],
            today=today.isoformat(), weekday=today.strftime("%A"),
            balance_eur=queries.balance_as_of(customer_id, today),
        )
        system += spending.PROMPT
        tools += spending.load_tools(customer_id, today)
    if web_search.enabled():
        system += web_search.PROMPT
    return system, tools


def chat_stream(messages, customer_id=None):
    """Run one user turn, yielding ("text", chunk) and ("tool", name) events as they happen.

    Same arguments as ``chat``. Gemma streams word by word; Claude yields its answer in
    one piece.
    """
    system, tools = _prepare(customer_id)
    if COACH_MODEL == "gemma":
        yield from _stream_gemma(messages, system, tools)
    else:
        yield "text", _chat_claude(messages, system, tools)


def chat(messages, customer_id=None):
    """Run one user turn.

    `messages` is the conversation so far in the chosen model's format, ending with a
    {"role": "user", "content": "..."} message. Appends the assistant's turn(s) in place
    and returns the final reply text.

    With a `customer_id` the coach can read that one customer's transactions through the
    spending tools. Without one it has no access to any customer data.
    """
    return "".join(chunk for kind, chunk in chat_stream(messages, customer_id) if kind == "text")
