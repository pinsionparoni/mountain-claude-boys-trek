"""Finance-coach chat agent.

COACH_MODEL picks the model: "claude" (default, Anthropic API) or "gemma"
(Gemma 4 on Verda via its OpenAI-compatible endpoint, VERDA_BASE_URL + VERDA_API_KEY).
"""

import json
import os

from dotenv import load_dotenv

from coach import db, web_search
from coach.tools import to_anthropic, to_openai

load_dotenv()

COACH_MODEL = os.getenv("COACH_MODEL", "claude")
CLAUDE_MODEL = "claude-opus-5-5"
GEMMA_MODEL = "gemma-coach"  # --served-model-name of the Verda deployment
MAX_TURNS = 10

SYSTEM_PROMPT = """You are a friendly personal finance coach inside a Finnish bank's mobile app. \
You help everyday customers understand where their money goes and make better decisions.

You are talking with customer {customer_id} (age {age}). Their transaction data runs from {data_from} \
to {data_to}. Treat {data_to} as today: "this month", "last month" and "this week" are relative to that date. \
Their current account balance is {balance_eur} €.

Teach with three spending baskets:
1. Mandatory and regular (housing, utilities, groceries, transport)
2. Mandatory and irregular (health, home & tech: a broken washing machine, a dentist bill)
3. Everyday spending that slips through your fingers (restaurants, entertainment, lifestyle, travel)

Use your tools for every number about the customer's money. Never estimate or invent amounts; if the tools \
can't answer, say so. Show the key numbers you used, rounded to whole euros. Explain financial ideas in plain \
language, and end with one concrete, encouraging suggestion when it fits.

Keep answers short and mobile-friendly. Answer in the language the user writes in."""

_clients = {}


def _client():
    if COACH_MODEL not in _clients:
        if COACH_MODEL == "gemma":
            from openai import OpenAI
            _clients[COACH_MODEL] = OpenAI(base_url=os.environ["VERDA_BASE_URL"],
                                           api_key=os.environ["VERDA_API_KEY"])
        else:
            import anthropic
            _clients[COACH_MODEL] = anthropic.Anthropic()
    return _clients[COACH_MODEL]


def _run_tool(tools, name, args):
    tool = tools.get(name)
    if tool is None:
        return f'Error: unknown tool "{name}"', True
    try:
        return tool.run(args), False
    except Exception as e:  # surface tool failures to the model instead of crashing the turn
        return f"Error: {e}", True


def _chat_claude(messages, system, tools):
    by_name = {t.name: t for t in tools}
    params = {"tools": [to_anthropic(t) for t in tools]} if tools else {}
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


def _chat_gemma(messages, system, tools):
    by_name = {t.name: t for t in tools}
    params = {"tools": [to_openai(t) for t in tools]} if tools else {}
    for _ in range(MAX_TURNS):
        response = _client().chat.completions.create(
            model=GEMMA_MODEL,
            max_tokens=4096,
            messages=[{"role": "system", "content": system}, *messages],
            **params,
        )
        choice = response.choices[0]
        msg = choice.message
        turn = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            turn["tool_calls"] = [{"id": c.id, "type": "function",
                                   "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                  for c in msg.tool_calls]
        messages.append(turn)

        if not msg.tool_calls:
            text = msg.content or ""
            if choice.finish_reason == "length":
                text += "\n\n(Answer was cut off.)"
            return text

        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                output = "Error: tool arguments were not valid JSON"
            else:
                output, _ = _run_tool(by_name, call.function.name, args)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return "Sorry, that took too many steps. Could you narrow the question down?"


def chat(messages, customer_id):
    """Run one user turn for one customer.

    `messages` is the conversation so far in the chosen model's format, ending with a
    {"role": "user", "content": "..."} message. Appends the assistant's turn(s) in place
    and returns the final reply text.
    """
    system = SYSTEM_PROMPT.format(**db.customer_profile(customer_id))
    tools = db.load_tools(customer_id) + web_search.load_tools()
    if web_search.enabled():
        system += web_search.PROMPT
    if COACH_MODEL == "gemma":
        return _chat_gemma(messages, system, tools)
    return _chat_claude(messages, system, tools)
