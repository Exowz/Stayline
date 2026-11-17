# Stayline

An AI agent that applies a court-ordered freeze (a criminal seizure under CPP 706-155) to the right life-insurance contract, and nothing more. It also gates adviser requests (rachat, advance, arbitrage) against that freeze. This is a school project for the Agentic Workflows course, built by Ewan and Khadidja, and also Ewan's portfolio repo.

## Read first, in this order

1. `docs/concept.md`: the **approved concept**: what we build, the legal grounding, the servers, the graph, the memory test, the 30 scenarios, the metrics, the open design decisions.
2. `.handoff/HANDOFF.md`: **private context**: team, deadline, how the concept was chosen, Ewan's working style, open questions, schedule. It is gitignored. Never commit it, and never copy personal details from it into committed files.
3. `.handoff/course/project-brief.txt`: the graded brief (the bar).
4. `.handoff/course/course-digest.md`: the teacher's conventions from the 7 sessions. The jury grades faithfulness to the course, so follow them.

Go deeper when needed:
- `.handoff/course/slides-text/` for the slides;
- `.handoff/course/slides-and-labs/sessions/` for the labs;
- `.handoff/course/lab-repo/` for the course stack (`pyproject.toml`, `uv.lock`);
- `.handoff/debate/` for why this concept.

## Status (2026-11-17)

- Concept and design approved. Design: `docs/superpowers/specs/2026-11-17-stayline-design.md` (where it differs from the concept, the design wins).
- Plan: `docs/superpowers/plans/2026-11-17-stayline.md` (21 tasks, two even lanes: Khadidja and Ewan).
- GitHub: `Exowz/Stayline`, private until the defence; Khadidja (`KHAD5ADDI`) is a collaborator.
- Done on `main`: plan tasks 1 to 3 (scaffold, typed results, settings, SQLite backend and seeds, business rules) and the shared server test fixtures (`tests/helpers.py`, `tests/conftest.py`).
- Next: the two lanes of the plan, in parallel.
- Code freeze **Thursday 19 Nov 2026, 23:59** (tag `v1.0`); defence Friday 20 Nov.

## What to do next

Follow the plan task by task. For each task: Claude writes `.techlead/stepN_spec.md` from the plan task, a coding agent implements it (Codex or Opus), Claude reviews, re-runs the tests and commits. The design is settled: do not reopen it without Ewan.

## Non-negotiable requirements (from the brief)

- **Backend:** resettable to a seed, with read and write operations and at least one dangerous write. Ours are `apply_seizure` and `execute_operation`.
- **MCP:** at least two servers with typed arguments and errors (`justice_reference`, `insurer_contracts`).
- **LangGraph:** a step budget, and a human approval (`interrupt`) before each dangerous write.
- **Memory:** one long-term memory, with a test showing it changes a later run (the Orion alias).
- **Agents:** one agent, unless more agents show a measured gain.
- **Scenarios:** `eval/scenarios.jsonl` holds about 30, scored on the final backend state: 14 normal, 5 ambiguous, 5 impossible, 6 adversarial (injection inside a tool result).
  - Each line has `id`, `kind`, `task`, `seed`, `expect_state`, `forbid_calls`, `max_steps`.
- **Evaluation command:** `uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/` must work as written. It resets the backend before each scenario and writes `eval/results.jsonl`. For each scenario:
  - pass or fail, and why;
  - final state;
  - tools called in order;
  - steps;
  - tokens in and out;
  - latency;
  - cost;
  - stop reason.
- **Traces:** tokens, cost and latency for every run.
- **Bonuses** (planned):
  - a UI showing the plan, the tool calls and the approval step;
  - a two-model comparison;
  - recovery from an injected tool failure.

## Working rules

**Communication:**
- Explain things to Ewan in plain words, in English.
- Recommend; don't list every option.
- Don't re-ask settled facts.
- No artifacts or published pages unless asked.

**Codex does the heavy coding:**
- Write a spec in `.techlead/stepN_spec.md` (gitignored) and dispatch the `codex:codex-rescue` agent.
- In the Codex sandbox, use `.venv/bin/python` (not `uv run`), and never ask Codex to delete files.

**Git:**
- Plain commit messages, **no `Co-Authored-By:` or any AI attribution**, in commits or PR descriptions.
- Never force-push.
- Commit after each reviewed phase.
- Branches: one short branch per task, named by owner (`ewan/<task>`, `khadidja/<task>`), merged into `main` through a small pull request once its tests pass. No long-lived personal branches.
- Ask before creating the GitHub repo and before the first push.

**Repo content:**
- Never use the long dash character.
- Mock data only, never real employer data.
- API keys only in `.env` (OpenRouter, as in the course labs); never print or commit them.
- Pin the stack to the course lab repo: Python >= 3.12, langgraph 1.2.16, langgraph-checkpoint-sqlite 3.1.2, mcp 2.3.0, openai 3.31.0.

**Language:**
- README, deck and Q&A prep in English.
- Code, comments and prompts in English. French only for legal terms and the text of mock notices.

**Engineering:**
- Every claim of success is read from the backend state or the trace, never from the agent's own words.
- Course conventions win over personal taste: `ToolResult` / `ToolError`, an idempotency key computed in the harness, no blind retry after `outcome_unknown`, `interrupt` with no side effect before it, a pure router tested without a model, store namespaces per operator, pass^k, Wilson intervals, cost per success, p50/p95.
