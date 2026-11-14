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

from coach import budget, charts, explore, guardrail, web_search
from coach.database import queries
from coach.tools import spending

load_dotenv()

COACH_MODEL = os.getenv("COACH_MODEL", "claude")
CLAUDE_MODEL = "claude-opus-5-5"
GEMMA_MODEL = "gemma-coach"  # --served-model-name of the Verda deployment
MAX_TURNS = 10

SYSTEM_PROMPT = """You are a friendly personal finance coach inside S-Pankki's S-mobiili app. \
You help everyday customers understand where their money goes and make better decisions.

Teach with three spending baskets: regular essentials, unexpected necessities, and everyday spending \
that slips through your fingers.

Explain financial ideas in plain language, and end with one concrete, encouraging suggestion when it fits.

Stay on the customer's own money (see POLICY.md and S_PANKKI_REFERENCE.md):
- Spending in any category is just data: answer neutrally, without moralising, also for bars, alcohol \
or entertainment.
- Investments: explain concepts, diversification and risks in general terms only; never recommend buying, \
selling or holding a specific stock or fund (even with a disclaimer), and refer to S-Pankki's investment \
advice / experts (asiantuntijat).
- Loans: never suggest taking credit to cover a budget shortfall or stress; treat any loan calculation as an \
estimate, not a loan offer (arvio, ei lainatarjous), and refer to S-Pankki's credit assessment / experts.
- Taxes: give general tax information only, not a binding ruling (yleistä verotietoa, ei Verohallinnon sitova \
ratkaisu), and refer personal cases to Verohallinto (vero.fi) or S-Bank's experts.
- Security & scope: never ask for or accept card PINs or banking credentials (pankkitunnukset). Don't help \
with anything harmful, illegal or unrelated to money; decline briefly and offer money help.

Voice and Finnish style:
- In Finnish, use standard friendly sinuttelu ("sinä", never slang "sä") and S-Pankki terms naturally: \
käyttötili / S-Tili, säästötili, puskuri (or taloudellinen puskuri; also explain hätävara if asked), \
kiinteät menot, palkkapäivä, e-lasku, katevaraus, Säästäjä, Bonus. Keep brand names (S-mobiili, S-Tili, \
Säästäjä, Bonus) unchanged in English.
- Format Finnish numbers as "68,23 €", "2 541,89 €" and "20 %", dates without leading zeros ("15.9.2026"), \
and continue in lowercase after a plain colon and when inflecting basket names mid-sentence ("arjen kulutukseen").

Never show internal names or values from the tools (such as field names, "cash", "budget" as a status, \
or tool names); say what they mean in plain words.

Keep answers short and mobile-friendly: answer the question first, add only the details that help, and leave \
out long breakdowns unless the customer asks. Don't use dashes between clauses, quote marks or parentheses (except around a date range); \
write two sentences instead. Don't list purchase counts unless asked. In Finnish answers, every word and heading is Finnish ("Ehdotus:", "Vinkki:"). \
Answer in the language the user writes in."""

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


def _ask_once(system, question):
    """A short, single model call without tools: used by the guardrail."""
    if COACH_MODEL == "gemma":
        # Streamed like every Gemma call: the client always asks Verda for a stream
        # (see _client), so a plain request would come back as raw stream text.
        stream = _client().chat.completions.create(
            model=GEMMA_MODEL, max_tokens=8, temperature=0, stream=True,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": question}],
        )
        return "".join(chunk.choices[0].delta.content or "" for chunk in stream if chunk.choices)
    response = _client().messages.create(
        model=CLAUDE_MODEL, max_tokens=1024, system=system, output_config={"effort": "low"},
        messages=[{"role": "user", "content": question}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


def _too_many_steps(messages):
    """Fallback when the model keeps calling tools past MAX_TURNS, in the customer's language."""
    question = next((m["content"] for m in reversed(messages)
                     if m.get("role") == "user" and isinstance(m.get("content"), str)), "")
    if guardrail.guess_lang(question) == "fi":
        return "Pahoittelut, tähän meni liian monta vaihetta. Voisitko rajata kysymystä hieman?"
    return "Sorry, that took too many steps. Could you narrow the question down?"


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


def _chart(name, output, is_error):
    """The chart spec from a successful show_chart call (coach/charts.py), else None."""
    if name != "show_chart" or is_error:
        return None
    try:
        return json.loads(output)["chart"]
    except (ValueError, KeyError, TypeError):
        return None


def _offered_chart(by_name, calls):
    """A chart matching the turn's lookups, when the model didn't pick one (coach/charts.py)."""
    args = charts.offer_args(calls)
    tool = by_name.get("show_chart")
    if args is None or tool is None:
        return None
    output, is_error = _run_tool(by_name, "show_chart", args)
    return _chart("show_chart", output, is_error)


def _stream_claude(messages, system, tools):
    """Yield ("tool", name) as Claude calls tools and ("text", answer) at the end."""
    by_name = {t.name: t for t in tools}
    params = {"tools": [dict(t) for t in tools]} if tools else {}
    calls, charted = [], False   # this turn's successful lookups; did the model pick a chart
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
            yield "text", "Sorry, I can't help with that one. Try asking about your spending in another way."
            return

        # Drop declined-model blocks that precede a server-side fallback boundary.
        boundary = max((i for i, b in enumerate(response.content) if b.type == "fallback"), default=-1)
        content = [b for i, b in enumerate(response.content) if i > boundary or b.type == "text"]
        messages.append({"role": "assistant", "content": content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in content if b.type == "text")
            if response.stop_reason == "max_tokens":
                text += "\n\n(Answer was cut off.)"
            yield "text", text
            if not charted and (chart := _offered_chart(by_name, calls)) is not None:
                yield "chart", chart
            return

        results = []
        for block in content:
            if block.type == "tool_use":
                yield "tool", block.name
                output, is_error = _run_tool(by_name, block.name, block.input)
                if not is_error:
                    calls.append((block.name, block.input))
                if (chart := _chart(block.name, output, is_error)) is not None:
                    charted = True
                    yield "chart", chart
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    yield "text", _too_many_steps(messages)


def _stream_gemma(messages, system, tools):
    """Yield ("text", chunk) as Gemma writes and ("tool", name) as tools run."""
    by_name = {t.name: t for t in tools}
    params = {"tools": [_to_openai(t) for t in tools]} if tools else {}
    done, charted = [], False   # this turn's successful lookups; did the model pick a chart
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
            if not charted and (chart := _offered_chart(by_name, done)) is not None:
                yield "chart", chart
            return

        for call in calls.values():
            yield "tool", call["name"]
            try:
                args = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError:
                output = "Error: tool arguments were not valid JSON"
            else:
                output, is_error = _run_tool(by_name, call["name"], args)
                if not is_error:
                    done.append((call["name"], args))
                if (chart := _chart(call["name"], output, is_error)) is not None:
                    charted = True
                    yield "chart", chart
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})

    yield "text", _too_many_steps(messages)


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
        if explore.enabled():
            system += explore.PROMPT
            tools += explore.load_tools(customer_id, today)
    if web_search.enabled():
        system += web_search.PROMPT
    return system, tools


def chat_stream(messages, customer_id=None):
    """Run one user turn, yielding ("text", chunk), ("tool", name) and ("chart", spec) events as they happen.

    Same arguments as ``chat``. Gemma streams word by word; Claude yields its answer in
    one piece (after its tool calls). The guardrail checks the question first: for "care" and "refuse" it yields
    ("guardrail", label) and a fixed reply, and the coach doesn't run.
    """
    verdict = guardrail.check(messages, _ask_once)
    if verdict and verdict.label != "allowed":
        answer = guardrail.reply(verdict)
        messages.append({"role": "assistant", "content": answer})
        yield "guardrail", verdict.label
        yield "text", answer
        return

    system, tools = _prepare(customer_id)
    if COACH_MODEL == "gemma":
        yield from _stream_gemma(messages, system, tools)
    else:
        yield from _stream_claude(messages, system, tools)


def chat(messages, customer_id=None):
    """Run one user turn.

    `messages` is the conversation so far in the chosen model's format, ending with a
    {"role": "user", "content": "..."} message. Appends the assistant's turn(s) in place
    and returns the final reply text.

    With a `customer_id` the coach can read that one customer's transactions through the
    spending tools. Without one it has no access to any customer data.
    """
    return "".join(chunk for kind, chunk in chat_stream(messages, customer_id) if kind == "text")
