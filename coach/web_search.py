"""Optional Exa web search for the coach.

Off by default. Enable with COACH_WEB_SEARCH=1 and an EXA_API_KEY.
"""

import os

from coach.tools import Tool

PROMPT = """

Web search (optional helper, use sparingly):
- You can call `web_search` and `get_contents` when outside information would genuinely help the customer, \
for example Finnish benchmarks (Statistics Finland), current prices, interest rates, Kela benefits or tax rules. \
Most questions are about the customer's own data and need no search.
- On every search, write an `objective` that says which documents should rank first, which to exclude, \
and which figures to pull. Prefer official Finnish sources and cite the URLs you used.
- Never put the customer's personal or financial details (names, amounts, merchants, account data) into a search."""


def enabled():
    return os.getenv("COACH_WEB_SEARCH") == "1" and bool(os.getenv("EXA_API_KEY"))


def load_tools():
    """Return Exa tools, or [] when web search is disabled."""
    if not enabled():
        return []
    from exa_py import Exa  # imported lazily so exa-py stays an optional dependency

    exa = Exa()  # reads EXA_API_KEY from the environment
    # Provider-neutral specs, so the same tools work with Claude and Gemma.
    specs = [exa.tools.web_search(), exa.tools.get_contents()]
    return [Tool(s.name, s.description, s.json_schema, s.run) for s in specs]
