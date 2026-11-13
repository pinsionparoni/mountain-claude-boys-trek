"""Finance-coach chat agent."""

from datetime import date

import anthropic
from dotenv import load_dotenv

from coach import web_search

load_dotenv()

MODEL = "claude-opus-5-5"
MAX_TURNS = 10

SYSTEM_PROMPT = """You are a friendly personal finance coach inside a Finnish bank's mobile app. \
You help everyday customers understand where their money goes and make better decisions.

Today's date is {today}.

Teach with three spending baskets:
1. Mandatory and regular (rent, insurance, subscriptions)
2. Mandatory and irregular (a broken washing machine, a dentist bill)
3. Everyday spending that slips through your fingers (coffees, takeaway, impulse buys)

Keep answers short and mobile-friendly. Answer in the language the user writes in."""

client = anthropic.Anthropic()
TOOLS = web_search.load_tools()
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def _echoable(content):
    """Drop declined-model blocks that precede a server-side fallback boundary."""
    boundary = max((i for i, b in enumerate(content) if b.type == "fallback"), default=-1)
    return [b for i, b in enumerate(content) if i > boundary or b.type == "text"]


def _run_tool(block):
    tool = TOOLS_BY_NAME.get(block.name)
    if tool is None:
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f'Error: unknown tool "{block.name}"', "is_error": True}
    try:
        content = tool.run(block.input)
    except Exception as e:  # surface tool failures to the model instead of crashing the turn
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"Error: {e}", "is_error": True}
    return {"type": "tool_result", "tool_use_id": block.id, "content": content}


def chat(messages):
    """Run one user turn. `messages` is the conversation so far, ending with a user message.

    Appends the assistant's turn(s) to `messages` in place and returns the final reply text.
    """
    system = SYSTEM_PROMPT.format(today=date.today().isoformat())
    if web_search.enabled():
        system += web_search.PROMPT
    for _ in range(MAX_TURNS):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one. Try asking about your spending in another way."

        content = _echoable(response.content)
        messages.append({"role": "assistant", "content": content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in content if b.type == "text")
            if response.stop_reason == "max_tokens":
                text += "\n\n(Answer was cut off.)"
            return text

        tool_results = [_run_tool(b) for b in content if b.type == "tool_use"]
        messages.append({"role": "user", "content": tool_results})

    return "Sorry, that took too many steps. Could you narrow the question down?"
