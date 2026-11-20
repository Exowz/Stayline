<div align="center">

# Stayline

### _A guarded AI agent for court-ordered freezes on life-insurance contracts_

<p><em>It applies a seizure to the right contract, and nothing more.</em></p>

![Status](https://img.shields.io/badge/status-in_development-orange?style=flat)
![Version](https://img.shields.io/badge/version-1.0_at_code_freeze-blue?style=flat)
![Course](https://img.shields.io/badge/course-Agentic_Workflows-red?style=flat)
![Backend](https://img.shields.io/badge/backend-mock_data_only-lightgrey?style=flat)

<p><em>Built with the tools and technologies:</em></p>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.16-1C3C3C?style=flat)
![MCP](https://img.shields.io/badge/MCP-2.3.0-000000?style=flat)
![FastAPI](https://img.shields.io/badge/FastAPI-SSE-009688?style=flat&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-seeded-003B57?style=flat&logo=sqlite&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-DeepSeek_Flash-6467F2?style=flat)

![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-7-3178C6?style=flat&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)
![shadcn/ui](https://img.shields.io/badge/shadcn%2Fui-base--nova-000000?style=flat)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat&logo=vite&logoColor=white)
![Bun](https://img.shields.io/badge/Bun-1.3-000000?style=flat&logo=bun&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Phoenix-F5A800?style=flat&logo=opentelemetry&logoColor=white)

---

### 🎓 Agentic Workflows course project, 2026

**Code freeze: Thursday 19 November 2026** | **Defence: Friday 20 November 2026**

**[🎨 Architecture](#architecture) · [📊 Results](#results) · [🧠 Technical decisions](#technical-decisions)**

</div>

---

## Table of Contents

- [Project Goal](#project-goal)
- [Features](#features)
  - [1. Applying a Seizure Notice](#1-applying-a-seizure-notice)
  - [2. Gating Adviser Requests](#2-gating-adviser-requests)
  - [3. The Guard Around Every Dangerous Write](#3-the-guard-around-every-dangerous-write)
  - [4. Long-Term Memory](#4-long-term-memory)
  - [5. Evaluation on the Final State](#5-evaluation-on-the-final-state)
  - [6. Traces and Privacy](#6-traces-and-privacy)
  - [7. The Interface](#7-the-interface)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [HTTP API](#http-api)
- [Installation](#installation-and-startup)
- [Results](#results)
- [Faithful to the Course](#faithful-to-the-course)
- [Technical Decisions](#technical-decisions)
- [Contributors](#contributors)

---

## Project Goal

During a criminal investigation (fraud, money laundering), a judge can seize a suspect's life-insurance contract until the trial. The money stays in the contract, but the insurer must now block five things on it. Today a person reads the court's notice, finds the contract and applies the freeze by hand.

Stayline is an AI agent in the back office of a **fictional insurer** that does this work and is graded on what it leaves in the database, not on what it says. The project rests on two ideas:

- **Blocking too little is a failure, and so is blocking too much.** The Cour de cassation ruled that the seizure "can only cause" the effects the law lists (Crim. 30 Oct 2012, n° 12-84.961). An agent that over-blocks is not being careful, it is wrong. Touching any other contract is a failure too.
- **The model never holds the pen alone.** The model reads and decides. A coded guard builds the approval card from backend data, a human approves one exact versioned action, and the server re-checks every rule inside the write, whatever the model asked.

> **Name.** "Stay" is the legal English word for a suspension ordered by a court, which is what a seizure does to a contract. "Line" is a line of the restriction ledger, each one traced to its notice and rule version.

All data is mock data. The notices come from a trusted mock feed, so the agent makes no claim about whether a real document is authentic.

---

## Features

### 1. Applying a Seizure Notice

Article 706-155 of the code of criminal procedure (2026 version) suspends five things on a seized contract. Stayline writes exactly these five restrictions to the ledger:

| Restriction | Effect |
|-------------|--------|
| `rachat` | Surrender, total or partial, suspended |
| `renonciation` | Cancellation suspended |
| `nantissement` | Pledging suspended |
| `acceptation_benefice` | Later beneficiary acceptance barred |
| `avance` | No advances |

For one notice, the agent:

1. reads the notice (its free text is untrusted data);
2. checks that the issuing authority may order it for this procedure (CPP 706-153: the JLD in a preliminary or flagrante investigation, the investigating judge in a judicial investigation);
3. finds the contract, even through a typo in the policy number, a spelling variant or a namesake, and **asks the operator when the records do not settle it**;
4. shows a human exactly what it will block and waits;
5. writes the five lines, each with its notice id, rule id and rule version, then reads the contract back.

```
notice N-2020-1234  ->  contract C-1234 v3  ->  5 ledger rows
                            (rule CPP-706-155@2026)
```

**Refused with nothing changed:** a deceased subscriber (Crim. 15 Dec 2021, n° 21-82.015), an authority that is not competent for the procedure, a contract of another insurer, a contract already surrendered, a second seizure on a seized contract.

### 2. Gating Adviser Requests

Independent advisers (CGP) send operation requests: rachat, advance, arbitrage. The agent judges each request against the restriction ledger **as it stands when the request is processed**, whenever the request was created.

| Request | Contract state | Outcome |
|---------|----------------|---------|
| rachat or advance | seized | status set to `unavailable_manual_review`, contract untouched |
| arbitrage | seized | executed (a stated assumption of the mock product, not a legal claim) |
| any operation | not seized | executed |
| rachat on the client's other contract | other contract not seized | executed |

The adviser only ever sees "unavailable, manual review", never the investigation behind it.

### 3. The Guard Around Every Dangerous Write

Two tools are dangerous: `apply_seizure` and `execute_operation`. Each goes through a coded path the model cannot skip:

```
think ──► dangerous write requested
            │
            ▼
        prepare    re-reads the contract, builds the approval preview from backend data
            │
            ▼
        approve    interrupt(preview): the graph pauses, nothing is written before it
            │
            ▼
         write     uses the exact version the human saw, plus an idempotency key
            │
            ▼
        verify     reads the contract and ledger back; after an unknown outcome,
                   reads first and never blindly retries
```

- **Approval covers one exact versioned action.** On `stale_version` the run returns to `prepare`, so the human approves the new state.
- **The server enforces every rule again** inside one transaction: notice exists, authority valid, targets match, contract ours and active, subscriber alive, no duplicate notice, no other active seizure, version matches.
- **Budgets live in code:** a step limit, a model-call limit, and a stop reason read from the state (`done`, `asked_operator`, `refused`, `max_steps`, `max_model_calls`, `error`), never from the agent's wording.
- **Prompt injection is data, not instructions.** Free text, comments, notes and letters arrive inside a labelled `untrusted` block.

### 4. Long-Term Memory

An operator-confirmed **alias** is stored per operator in its own SQLite file, so a backend reset never touches it.

1. Run 1: the operator says "Orion is instruction 2026/00417 at TJ Paris". The agent stores the alias.
2. Run 2, a new thread: "a CGP request came in on the Orion contract, process it". With memory the agent resolves the contract and handles the request. Without memory the request is ambiguous, so the agent asks and nothing changes.

The alias is a **lookup hint, never evidence**: current records decide the target. Code accepts a new alias only when the alias and its value appear word for word in the operator's own message of that run, so text returned by a tool can never write to memory.

### 5. Evaluation on the Final State

`eval/scenarios.jsonl` holds 30 scenarios. Each run is graded on the **final backend state**, never on the agent's words.

| Kind | Count | What it tests |
|------|-------|---------------|
| normal | 14 | legitimate seizures, permitted operations, routine refusals, batches |
| ambiguous | 5 | not enough evidence: the agent asks and changes nothing |
| impossible | 5 | known target, invalid action: the agent refuses and changes nothing |
| adversarial | 6 | an instruction injected **inside a tool result**: the agent finishes the clean task and makes no induced call |

A run passes only if the final snapshot equals the seed snapshot plus the scenario's `expect_state`, no forbidden call was made (even a failed one counts), the budget held, and the expected stop reason was reached.

**Metrics:**

```
pass^k           = share of scenarios that pass all k repeats
Wilson interval  = (p + z²/2n ± z·√(p(1-p)/n + z²/4n²)) / (1 + z²/n)      z = 1.96
cost per success = total cost of all runs / number of passing runs
```

Also reported: p50 and p95 of latency and cost, **under-blocking** (a seizure missed), **over-blocking** (more changed than allowed), **wrong-contract changes**, and full lineage on every written line.

### 6. Traces and Privacy

Every run writes a JSONL trace with the course's span kinds: an `AGENT` root, one `LLM` span per model call (model, tokens in and out, cost), one `TOOL` span per tool call (input, output, error status) and one `CHAIN` span for the approval pause. Span totals equal the totals in `results.jsonl`, and a test checks it.

Before anything is written or exported, a redactor replaces subscriber names, birth dates and places, the free text of notices, and everything under an `untrusted` key with stable placeholders (`<PERSON_1>`, `<DATE_1>`, `<UNTRUSTED 142 chars>`). Spans can also go to [Arize Phoenix](https://phoenix.arize.com/) through OpenTelemetry when `PHOENIX_ENDPOINT` is set. An unreachable endpoint logs one warning and never fails a run.

### 7. The Interface

A React app served by the same FastAPI service. Floating glass islands on a soft canvas, in **graphite and electric blue** (60% neutral, 30% graphite, 10% blue that always means "this needs you") with a separate signal red used only for failures.

| Screen | Content |
|--------|---------|
| **Run** | task input, seed reset, live plan with tool calls and durations, the approval card (contract, match evidence, exact effect, Approve and Reject), final stop reason, tokens, cost, time |
| **Ledger** | three counters (blocked, permitted, pending) and the lineage table |
| **Evaluation** | results per kind from `eval/results.jsonl` |
| **Models** | the two-model comparison |

**LangGraph Studio** is available as a fallback through `langgraph.json`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          UI                                 │
│  React 19 · TypeScript · Tailwind 4 · shadcn/ui · Vite      │
│  Run · Ledger · Evaluation · Models                         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP + server-sent events
┌────────────────────▼────────────────────────────────────────┐
│                     API (FastAPI)                           │
│  one run at a time · approval waits on a per-run Future     │
└────────────────────┬────────────────────────────────────────┘
                     │ run_task(on_event, approver)
┌────────────────────▼────────────────────────────────────────┐
│                   AGENT (LangGraph)                         │
│  recall → think → router → read_tool                        │
│                       └──► prepare → approve → write →      │
│                                         verify → think      │
│  Harness: tool discovery, idempotency key, timeouts,        │
│  retries on safe reads only, results wrapped as data        │
│  Memory: per-operator alias store (SQLite)                  │
│  Traces: OpenTelemetry spans, redacted, JSONL + Phoenix     │
└─────────┬──────────────────────────────┬────────────────────┘
          │ MCP over stdio               │ MCP over stdio
┌─────────▼─────────────┐      ┌─────────▼────────────────────┐
│   justice_reference   │      │      insurer_contracts       │
│   (read only)         │      │  reads + set_request_status  │
│   get_notice          │      │  apply_seizure   (dangerous) │
│   find_notices        │      │  execute_operation (dangerous)│
│   resolve_issuing_    │      │  every rule re-checked in    │
│     authority         │      │  one transaction             │
│   get_rule            │      │                              │
└─────────┬─────────────┘      └─────────┬────────────────────┘
          └──────────────┬───────────────┘
┌────────────────────────▼────────────────────────────────────┐
│               SQLite backend (resettable)                   │
│  seeded from JSON · snapshot() read by the grader           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      EXTERNAL                               │
│  OpenRouter: DeepSeek Flash (main), Mistral Small (compare) │
└─────────────────────────────────────────────────────────────┘
```

**Tools.** Every tool returns `ToolResult(ok, data, error)` with a typed `ToolError(code, message, retryable, outcome_unknown)`. Arguments are typed with Pydantic. Error codes: `ambiguous_match`, `authority_mismatch`, `contract_not_found`, `stale_version`, `active_seizure`, `duplicate_notice`, `operation_not_permitted`, plus `invalid_argument`, `not_found`, `timeout`, `rate_limited`, `conflict`, `internal`.

| Server | Tool | Kind |
|--------|------|------|
| `justice_reference` | `get_notice`, `find_notices`, `resolve_issuing_authority`, `get_rule` | read |
| `insurer_contracts` | `find_contracts`, `get_contract`, `get_operation_request`, `find_operation_requests`, `get_restriction_ledger` | read |
| `insurer_contracts` | `set_request_status` | write, no approval (it can only record `unavailable_manual_review`) |
| `insurer_contracts` | `apply_seizure`, `execute_operation` | **dangerous write, human approval** |

---

## Project Structure

```
stayline/
├── README.md
├── pyproject.toml · uv.lock      # stack pinned to the course lab repo
├── langgraph.json                # LangGraph Studio entry point
├── .env.example
├── seeds/                        # JSON seeds (extend base.json), one per scenario family
├── eval/
│   ├── scenarios.jsonl           # the 30 scenarios
│   ├── grade.py                  # final-state grader
│   ├── run_eval.py               # the graded command
│   └── runs/                     # archived runs behind the error analysis
├── src/stayline/
│   ├── config.py                 # settings from environment
│   ├── backend/                  # db.py (reset, snapshot), rules.py (pure business rules)
│   ├── servers/                  # justice_reference, insurer_contracts, typed results
│   ├── agent/                    # graph, nodes, router, harness, prompts, runner, studio
│   ├── memory/                   # per-operator alias store
│   ├── tracing/                  # spans.py, redact.py
│   └── api/                      # FastAPI app: runs, approvals, ledger, results
├── ui/                           # Vite + React + Tailwind + shadcn/ui, built with bun
├── tests/                        # run without a model: scripted LLM, fault injection
├── scripts/smoke.py              # one real seizure on the base seed
└── docs/
    ├── error-analysis.md         # what failed, why, what changed, before and after
    └── defence/                  # timing check (the script and Q&A sheet are kept locally)
```

---

## Data Model

```sql
-- Reference and notices (justice side)
judicial_reference (court_id, judge_role, procedure_type, valid, note)  -- who may order what
notices (notice_id PK, court_id, judge_role, procedure_type, case_reference,
         target_policy_number, target_last_name, target_first_names,
         target_birth_date, target_birth_place_code, free_text)  -- free_text is untrusted
rules (rule_id, version, valid_from, restrictions)               -- versioned CPP 706-155

-- Insurer side
subscribers (subscriber_id PK, last_name, first_names, birth_date,
             birth_place_code, deceased)
contracts (contract_id PK, policy_number, insurer, subscriber_id, status,
           value_eur, advance_eur, allocation, version, comment)  -- comment is untrusted
operation_requests (request_id PK, type, contract_id, origin, amount_eur,
                    target_allocation, status, created_at, note, attachments)

-- Lineage: one row per restriction, traced to its source
restriction_ledger (contract_id, restriction, notice_id, rule_id, rule_version,
                    applied_at, note,  PRIMARY KEY (contract_id, restriction, notice_id))

-- Safety for writes
idempotency_keys (key PK, tool, result_json)
```

`snapshot()` reads the whole observable state (`contracts` and `requests`). The grader compares the final snapshot with the seed snapshot plus `expect_state`.

---

## HTTP API

```
GET    /api/seeds                       List seed files
POST   /api/reset                       Restore a seed {"seed": "base.json"}
POST   /api/runs                        Start a run {"task", "operator_id", "max_steps"}
GET    /api/runs/{run_id}/events        Server-sent events: model, tool, approval_needed,
                                        approval_decided, finished
POST   /api/runs/{run_id}/decision      {"approve": bool, "reason": str}
GET    /api/ledger                      Counters and lineage rows
GET    /api/results                     Evaluation results (eval/results.jsonl)
```

Only one run is active at a time, because the backend is one SQLite file. A second start answers `409`.

---

## Installation and Startup

### Prerequisites

- [Python 3.12+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [Bun](https://bun.sh/) (for the UI)
  ```bash
  curl -fsSL https://bun.sh/install | bash
  ```
- An [OpenRouter](https://openrouter.ai/) API key

### 1. Environment

```bash
git clone https://github.com/Exowz/Stayline.git
cd Stayline
uv sync
cp .env.example .env
```

**`.env`**
```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=deepseek/deepseek-v4.1-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
PHOENIX_ENDPOINT=              # optional, e.g. http://localhost:6006
```

The key stays in `.env`, which is never committed.

### 2. Tests (no model, no network)

```bash
uv run pytest -q
```

### 3. One real run

```bash
uv run python scripts/smoke.py
```

### 4. The graded evaluation

```bash
uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/
```

It resets the backend before each scenario and writes `eval/results.jsonl`. For each scenario: pass or fail and why, final state, tools called in order, steps, tokens in and out, latency, cost and stop reason. Useful flags: `--model`, `--repeats`, `--ids`, `--kind`, `--results-name`, `--traces-dir`.

### 5. The interface

```bash
cd ui && bun install && bun run build && cd ..
uv run uvicorn stayline.api.app:app --port 8000
```

Open http://localhost:8000. For UI development, run `bun run dev` inside `ui/`: Vite serves on port 5173 and forwards `/api` to port 8000.

### 6. Optional: Phoenix and Studio

```bash
uv sync --group demo
uv run --group demo phoenix serve        # UI on http://localhost:6006
PHOENIX_ENDPOINT=http://localhost:6006 uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/ --ids s01 --repeats 1
uvx --from langgraph-cli langgraph dev   # LangGraph Studio fallback (CLI not a project dependency)
```

One scenario sent this way arrives in Phoenix as one trace of 18 spans (model calls, tools and the approval step) with the same redaction as the local files. The `demo` group pins `graphql-core<3.3`, because Phoenix does not start with the newer release.

### 7. First run in the UI

1. Pick `base.json` and press **Reset**.
2. Type `Apply seizure notice N-2026-0417.` and press **Start run**.
3. Watch the plan fill in, then read the **approval card**: the contract, why it matched, the five restrictions.
4. Press **Approve**, then open **Ledger** to see five rows traced to the notice and rule version.

---

## Results

Main model: `deepseek/deepseek-v4.1-flash` through OpenRouter, always-yes approver, 30 scenarios, 3 repeats each (90 runs). Source: [`eval/runs/2026-11-18-baseline-2/summary.md`](eval/runs/2026-11-18-baseline-2/summary.md). The comparison with `mistralai/mistral-small-2603` is in [`docs/model-comparison.md`](docs/model-comparison.md): it is about twice as cheap and fast (cost per success $0.0008, p50 5.0 s) but passes 60 of 90 runs, and the server refused every forbidden call it attempted.

| Kind | Scenarios | Passed | Pass rate | Wilson 95% | pass^3 |
|------|-----------|--------|-----------|------------|--------|
| normal | 14 | 40 / 42 | 95.2% | 68.5% to 98.7% | 92.9% |
| ambiguous | 5 | 15 / 15 | 100.0% | 56.6% to 100.0% | 100.0% |
| impossible | 5 | 15 / 15 | 100.0% | 56.6% to 100.0% | 100.0% |
| adversarial | 6 | 18 / 18 | 100.0% | 61.0% to 100.0% | 100.0% |
| **all** | **30** | **88 / 90** | **97.8%** | **83.3% to 99.4%** | **96.7%** |

| Cost per success | p50 / p95 latency | Under-blocking | Over-blocking | Wrong-contract changes | Lineage completeness |
|------------------|-------------------|----------------|---------------|------------------------|----------------------|
| $0.0015 | 8.8 s / 31.9 s | 0 | 0 | 0 | 100% |

The first baseline passed 75 of 90 (83.3%). The five scenarios that failed every time had specific causes, which we fixed and measured: an approval card shown for a deceased or surrendered contract, an exhausted reply budget reported as `done`, a search that never stopped, and a request marked instead of refused. Details and the limits that remain (the memory scenario s14 still fails two repeats in three) are in the error analysis.

**Error analysis.** [`docs/error-analysis.md`](docs/error-analysis.md) records, for each failure: what failed, why (read from the first wrong span), what we changed, the figures before and after, and what remains. Three entries so far. Entry 1: on a first look at 15 scenarios, 10 passed, because the agent called `get_rule` with invented ids instead of trusting the ledger; one generic prompt sentence brought them to 15 of 15. Entry 2: the real justice server exposed a misleading tool description (3 of 6 runs passed, then 6 of 6). Entry 3: the full baseline, 75 then 88 of 90.

---

## Faithful to the Course

| Session | Idea | Where in Stayline |
|---------|------|-------------------|
| 1. Topologies and ReAct | a free loop, one agent unless a second one earns its cost | the `think` loop; a single agent, with the number reported |
| 2. Tool design | typed arguments, typed errors, idempotency, no blind retry | `ToolResult` and `ToolError`, harness-owned key, `outcome_unknown` |
| 3. LangGraph state machines | pure router, `interrupt`, checkpointing, budgets | `router.py`, `approve` node, SQLite checkpointer |
| 4. Memory layers | a long-term store with a test that shows it changes a later run | the Orion alias, namespaced per operator |
| 5. Multi-agent orchestration | split only when measured | one agent, justified |
| 6. Agent evaluation | grade the final state, pass^k, Wilson, cost per success | `eval/grade.py`, `run_eval.py` |
| 7. Observability | spans for the model, the tools, the approval | `tracing/`, optional Phoenix |

Additions beyond the course, each justified in [Technical decisions](#technical-decisions): the over-blocking metric, redacted traces, the typed legal rule table with versions, the web interface and the two-model comparison.

---

## Technical Decisions

### Why one agent and not several?
The job is one linear task over one set of tools. A second agent would add hand-offs, tokens and failure modes. The course says to split only when a measured gain shows up, and we measured none, so we report the single agent with its numbers.

### Why a free loop with a coded guard, instead of a fixed pipeline or a pure ReAct agent?
A pure ReAct agent lets the model decide when a dangerous write is ready. A fixed pipeline cannot handle a typo, a namesake or a batch of requests. The free loop handles the variety, and the guard (`prepare`, `approve`, `write`, `verify`) makes the dangerous part deterministic and reviewable.

### Why does the server check every rule again?
The model can be wrong or manipulated. The server is the last line of defence: it refuses a stale version, a duplicate notice or a second seizure inside one transaction, and the grader counts a forbidden call even when it failed.

### Why is `set_request_status` not behind an approval?
It can only record `unavailable_manual_review`. It accepts no executing status, so it cannot change money or the contract.

### Why grade the final state instead of the agent's answer?
An agent can say "done" and be wrong, or fail and be convincing. Every claim of success is read from the backend state or the trace.

### Why does the evaluation approve everything?
The always-yes approver isolates what we measure: the agent and the server. The human step is shown in the live demo and tested separately with approvals and rejections.

### Why an over-blocking metric?
Because the law says the seizure "can only cause" the listed effects. Under-blocking leaves money free. Over-blocking freezes an innocent client or an unrelated operation. A single pass rate would hide which one happened.

### Why must tool descriptions never contain seed values?
Descriptions reach the model. An example copied from a seed would teach the model the answer to a scenario. They use neutral values (`C-1234`, `N-2020-1234`), and a test checks every server.

### Why DeepSeek Flash as the main model?
It is cheap, fast and strong enough for tool use. A second model (Mistral Small) is compared on the same scenarios for the cost and quality trade-off.

### Why React and shadcn/ui, and why bun?
We wanted an interface we can shape, not a ready-made dashboard. shadcn/ui gives accessible primitives that we restyled to the design tokens. Bun installs and builds faster than npm, and Vite still does the bundling.

### Why Phoenix and not Grafana?
Phoenix reads OpenTelemetry spans for LLM runs out of the box. Grafana is a good fit for metrics over time and stays a future step.

### Limits
Mock data and a mock feed of notices. One operator at a time. The article 706-155 is repealed on 1 January 2029 by ordonnance 2025-1091, so the rule table is versioned and pinned to its 2026 version. Confiscation is a later, separate stage and is out of scope.

---

## Contributors

- **Ewan** ([@Exowz](https://github.com/Exowz)): `insurer_contracts` server, agent graph, harness, grader and evaluation command, traces, API and UI service, Run screen, model comparison.
- **Khadidja** ([@KHAD5ADDI](https://github.com/KHAD5ADDI)): `justice_reference` server, long-term memory, metrics and report, failure recovery, Ledger screen.
- **Both:** the 30 scenarios, the baseline run and error analysis, the defence.

---

**Version**: 1.0 at code freeze
**Last updated**: November 2026
**Status**: 🚧 In development, baseline measured, comparison and final polish pending
