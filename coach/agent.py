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

from dotenv import load_dotenv

from coach import web_search
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

You are talking with customer {customer_id} (age {age}). Their transaction data runs from {data_from} \
to {data_to}; treat {data_to} as today. Their current account balance is {balance_eur} €."""

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


def _chat_gemma(messages, system, tools):
    by_name = {t.name: t for t in tools}
    params = {"tools": [_to_openai(t) for t in tools]} if tools else {}
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


def chat(messages, customer_id=None):
    """Run one user turn.

    `messages` is the conversation so far in the chosen model's format, ending with a
    {"role": "user", "content": "..."} message. Appends the assistant's turn(s) in place
    and returns the final reply text.

    With a `customer_id` the coach can read that one customer's transactions through the
    spending tools. Without one it has no access to any customer data.
    """
    system = SYSTEM_PROMPT
    tools = web_search.load_tools()
    if customer_id:
        system += CUSTOMER_PROMPT.format(**queries.customer_profile(customer_id))
        system += spending.PROMPT
        tools += spending.load_tools(customer_id)
    if web_search.enabled():
        system += web_search.PROMPT
    if COACH_MODEL == "gemma":
        return _chat_gemma(messages, system, tools)
    return _chat_claude(messages, system, tools)
