# Developer Setup

For the Mountain Claude Boys team. The [README](README.md) is the public, grader-facing overview; this file is how we build and run the project.

Related docs: [CHALLENGE.md](CHALLENGE.md) (the brief) · [TECH_STACK.md](TECH_STACK.md) (plan, build order, submission checklist) · [BASKETS.md](BASKETS.md) (proposed spending-basket rules) · [DATA.md](DATA.md) (what's in the data: categories, merchant types, amounts, timing; regenerate with `.venv/bin/python scripts/profile_data.py`)

## 1. Python environment

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Re-run the `pip install` line whenever `requirements.txt` changes after a pull.

## 2. Settings and keys

```bash
cp .env.example .env
```

Fill in `.env`:

| Setting | Required | Where to get it |
|---|---|---|
| `COACH_MODEL` | No | `gemma` (default in `.env.example`, the product) or `claude` (development / comparison). Code default if unset: `claude` |
| `VERDA_BASE_URL` | With `gemma` | `https://containers.datacrunch.io/gemma-coach/v1` (see step 5) |
| `VERDA_API_KEY` | With `gemma` | Verda console → **Credentials** → **Inference API Keys** → **Create** (ask the teammate who owns Verda) |
| `ANTHROPIC_API_KEY` | With `claude` | [console.anthropic.com](https://console.anthropic.com) (Junction gives $20 of credits per person) |
| `DATABASE_URL` | Yes | Service URI of the shared Aiven database from the Aiven console, or a local PostgreSQL (see step 4) |
| `COACH_WEB_SEARCH` | No | `1` turns on optional Exa web search; default `0` |
| `EXA_API_KEY` | Only with web search | [dashboard.exa.ai](https://dashboard.exa.ai) |

> **Never commit `.env` or paste keys or the Aiven URI in chat.** `.env`, `.venv/` and `data/` are in `.gitignore`. If a key leaks, revoke it in that service's console.

## 3. Get the data (only for a local database)

Skip this if you only use the shared Aiven database: the data is already loaded there.

The S-Pankki CSVs live in [hackjunction/Junction-2026-S-pankki](https://github.com/hackjunction/Junction-2026-S-pankki). Download them into `data/` (ignored by git):

```bash
mkdir -p data
# Transactions: stored in Git LFS, so it needs the media URL
curl -fL -o data/tx_junction_transactions.csv \
  https://media.githubusercontent.com/media/hackjunction/Junction-2026-S-pankki/main/tx_junction_transactions.csv
# The other three are regular files
for f in tx_customers_junction.csv mtg_negotiation_history.csv mtg_tx_customer_link_and_final_mtg_infio.csv; do
  curl -fL -o data/$f https://raw.githubusercontent.com/hackjunction/Junction-2026-S-pankki/main/$f
done
```

Check it worked:

```bash
ls -l data/                                   # transactions file should be ~363 MB
head -c 100 data/tx_junction_transactions.csv # CSV columns, not "version https://git-lfs..."
```

## 4. Database

### Shared Aiven database (what the team uses)

**Already set up and loaded** with all the data:

| | |
|---|---|
| Service | `pg-2a3bcedc` in the `mountain-claude-boys` Aiven organization |
| Version / plan | PostgreSQL 18.7, Developer-1 (1 CPU, 1 GB RAM, 8 GB storage, max 15 connections) |
| Region | DigitalOcean Frankfurt, Germany (EU) |
| Data | All four tables loaded, 628 MB |

To connect:

1. Accept the Aiven invite email. If you haven't got one, ask a teammate with admin access to invite you (Admin → Users → Invite users, then project → Permissions → Grant permissions, role **Developer**).
2. In the Aiven console, open `pg-2a3bcedc` and copy the **Service URI** (`postgres://avnadmin:…@….aivencloud.com:…/defaultdb?sslmode=require`).
3. Put it in your `.env` as `DATABASE_URL`. Don't paste it in chat or commit it.
4. **Don't run the loader** against this database. It refuses if the tables exist, and `--replace` would wipe and reload the shared data (about 7 minutes of downtime for everyone), so only do that if the team agrees.

Queries take roughly 50–100 ms from a laptop, almost all of it network time to Frankfurt.

If the database ever has to be recreated: create a PostgreSQL service in an EU region with at least 2 GB of disk, download the data (step 3), set `DATABASE_URL`, and run `.venv/bin/python scripts/load_data.py`. Loading into Aiven takes about 7 minutes, mostly uploading the 363 MB file.

### Local database (optional)

Useful for working offline or experimenting without touching the shared data. Install PostgreSQL (e.g. `sudo apt install postgresql` on Ubuntu/WSL, or run it in Docker), create a database, point `DATABASE_URL` at it, and run the loader. A local load takes about 30 seconds.

### Tables

| Table | Rows | Contents |
|---|---|---|
| `customers` | 5,100 | `customer_id`, `postal_code`, `age` |
| `transactions` | 3,626,755 | Oct 2024 – Sep 2026; `customer_id, bank_account_id, tx_date, tx_timestamp, category, tx_amount_eur, balance_after_eur, transaction_type, merchant_id, mcc_code` |
| `mortgage_outcomes` | 200 | Final outcome per mortgage application, linked to `customer_id` |
| `mortgage_events` | 3,452 | Mortgage application event history (Jan – Sep 2026) |

Negative `tx_amount_eur` is money out. "Salary Sweep" and "Invest Withdraw" look like transfers between accounts rather than spending (to confirm with the S-Bank mentors).

## 5. Gemma on Verda

The coach's model, Google's Gemma 4 31B, runs in our own vLLM container on Verda:

| | |
|---|---|
| Deployment | `gemma-coach`, Verda Serverless Containers, On-Demand, Continuous |
| URL | `https://containers.datacrunch.io/gemma-coach/v1` (OpenAI-compatible `/v1/chat/completions`) |
| Model name in requests | `gemma-coach` |
| Hardware | 1× H100 SXM5 80 GB |
| Cost | **€5.15 per hour while a replica is running**, starting from the moment it boots |
| Image | `docker.io/vllm/vllm-openai:v0.29.0` |

**Cost rule:** set **Min replicas to 0** in the deployment's scaling settings when nobody is using it (nights, long breaks), and back to **1** at least 20–30 minutes before anyone needs it (demo, judging). A cold start takes several minutes; the first request after scaling to zero waits for it. Tell the team in chat when you change it.

Quick check that it's up (replace the key):

```bash
curl -X POST https://containers.datacrunch.io/gemma-coach/v1/chat/completions \
  --header 'Authorization: Bearer <VERDA_API_KEY>' \
  --header 'Content-Type: application/json' \
  --data '{"model": "gemma-coach", "messages": [{"role": "user", "content": "Selitä lyhyesti, mikä on hätävara."}]}'
```

<details>
<summary>Redeploying from scratch</summary>

Prerequisite: a Hugging Face **Read** token (huggingface.co → profile picture → Access Tokens → Create new token → type **Read**, not fine-grained). If the model page asks you to accept a license, accept it first.

Verda console → Containers → New deployment:

| Field | Value |
|---|---|
| Deployment name | `gemma-coach` (becomes the URL; can't be changed later) |
| Deployment type / compute type | Continuous / On-Demand |
| Compute | 1x H100 SXM5 (`1H100.80S.21V`) |
| Image / tag | `docker.io/vllm/vllm-openai` / `v0.29.0` (the plain linux/amd64 one), public, image caching ON |
| Exposed HTTP port | `8000` (vLLM's port, **not** the default 80) |
| Healthcheck | ON, port `8000`, path `/health` |
| Entrypoint | empty |
| Environment variables | `HF_HOME` = `/data/.huggingface`, `HF_TOKEN` = your Hugging Face token |
| Scaling | Min 1 / Max 1, concurrent requests per replica 8, queue load Balanced |
| Storage | container disk `/data` (100 GiB is enough), SHM `/dev/shm` 8 GiB |

**CMD:** each row of the argument list is passed to vLLM as **one** argument, so a flag and its value must be on **separate rows** (or paste this into the command-line view `>_` and check the list view shows 13 rows):

```
--model google/gemma-4-31B-it --quantization fp8 --served-model-name gemma-coach --max-model-len 32768 --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4
```

Don't add `--gpu-memory-utilization 0.9`: it's vLLM's default anyway, and the form mangled the `0.9` value. `--quantization fp8` makes vLLM compress Google's weights to FP8 at load time so the 31B model fits on one H100.

First start takes 15–30 minutes (image pull, ~62 GB model download, FP8 compression). Ready when the logs show the server on port 8000 and the status is healthy.

| Log message | Fix |
|---|---|
| `unrecognized arguments` | A flag and its value share one CMD row; split them |
| `401` / `403` downloading | Wrong `HF_TOKEN`, or license not accepted on Hugging Face |
| `CUDA out of memory` | Lower `--max-model-len` to `16384` |
| Healthcheck failing | Exposed and healthcheck ports must both be `8000` |

</details>

## 6. Modal

Used for the what-if calculation Sandboxes (in progress). Connect your machine once:

```bash
.venv/bin/modal setup        # opens the browser to log in
.venv/bin/modal profile current
```

The token is stored in your home directory, not in the project. Ask to be invited to the team's Modal workspace so you use the shared credits.

## 7. Run the coach

```bash
.venv/bin/python -m coach                 # customer CUST00001
.venv/bin/python -m coach CUST02500       # any customer from CUST00001 to CUST05100
COACH_MODEL=claude .venv/bin/python -m coach   # override the model for one run
```

A terminal chat for testing. Ctrl+D quits. Questions to try: "How much did I spend on taxis last month?", "Mihin rahani menevät? Jaa kulutukseni kolmeen koriin viime kuukaudelta.", "How much could I save per year if I cut restaurant spending by 20%?"

The data ends on 30 September 2026, so the coach treats each customer's last transaction date as "today".

## Project layout

| Path | Purpose |
|---|---|
| `coach/agent.py` | The coach: system prompt (three spending baskets, customer context) and the chat loops for Gemma and Claude |
| `coach/db.py` | Read-only database tools bound to one customer, plus the category → basket mapping |
| `coach/tools.py` | Provider-neutral tool definition, converted for Claude or OpenAI-compatible models |
| `coach/web_search.py` | Optional Exa tools, only loaded when `COACH_WEB_SEARCH=1` |
| `coach/__main__.py` | Terminal chat: `python -m coach [CUSTOMER_ID]` |
| `scripts/load_data.py` | Loads `data/*.csv` into PostgreSQL (`DATABASE_URL`) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for `.env` |

### Coach tools

Each tool only sees the customer the app chose; the model can't pick a different customer. Connections run in read-only mode.

| Tool | Answers questions like |
|---|---|
| `spending_summary` | "Where did my money go last month?" Spending in a date range split into the three baskets with per-category totals, plus income, savings and transfers. With a category, a breakdown by merchant type (taxi, fuel, parking, public transport, …). |
| `monthly_overview` | "How have my finances changed?", "What's safe to spend?" Month-by-month income, spending per basket, savings and end-of-month balance. |
| `list_transactions` | "What were my biggest purchases?" The largest or latest transactions in a date range, optionally for one category. |

**Basket mapping** (draft, in `BASKETS` at the top of `coach/db.py`; change it there):

| Basket | Categories |
|---|---|
| Mandatory and regular | Housing, Utilities, Groceries, Transportation |
| Mandatory and irregular | Health, Home & Tech |
| Everyday | Restaurants, Entertainment, Lifestyle, Travel |
| Not spending | Salary, Other Income, Invest Withdraw (income); Invest Deposit (savings); Salary Sweep (transfer) |

### How a chat turn works

`chat(messages, customer_id)` builds the system prompt from the customer's profile, sends the conversation to the model with the tools, runs any tool calls, sends the results back, and repeats until there's a final answer (at most 10 rounds).

```mermaid
sequenceDiagram
    participant U as You
    participant A as agent.chat()
    participant G as Gemma (or Claude)
    participant D as Aiven PostgreSQL

    U->>A: "How much did I spend on taxis last month?"
    A->>G: system prompt + conversation + tools
    G-->>A: tool call: spending_summary(Transportation, 2026-09-01..30)
    A->>D: read-only query for this customer
    D-->>A: totals by merchant type
    A->>G: tool result
    G-->>A: "No taxis last month; transport was 267 €: ..."
    A-->>U: reply
```

## Next steps

- FastAPI web API around `chat()` for the mobile front end.
- What-if and safe-to-spend calculations in Modal Sandboxes.
- Decide where the backend runs for the demo (Modal, Aiven or Verda).
