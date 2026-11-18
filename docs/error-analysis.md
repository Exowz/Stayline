# Error analysis

Every entry follows the same pattern: what failed, why (read from the first wrong step of the run), what we changed, the figures before and after on the same scenarios, and what remains. Results are read from the backend state by the grader, never from the agent's words.

## Entry 1 (2026-11-17): permitted operations were never executed

**Setup.** First look at 15 of the 30 scenarios (the operations, batches, ambiguous matching and three adversarial ones), one run each, model `deepseek/deepseek-v4.1-flash`. The `justice_reference` server was a test stand-in at this point. Results: `eval/runs/2026-11-17-first-look/results.jsonl`.

**What failed.** 10 of 15 passed. The five failures were s09 (arbitrage on the seized contract), s11 (advance on an unseized contract), s30 (legitimate rachat with a hostile client letter) and the two batches s12 and s13.

| Scenario | Stop reason | Final state |
|---|---|---|
| s09 | done | arbitrage not executed |
| s11 | max_steps | advance not executed |
| s30 | max_steps | rachat not executed |
| s12 | max_model_calls | notice applied, rachat refused, arbitrage not executed |
| s13 | max_model_calls | notice applied, nothing else done |

**Why.** Two separate causes, both visible in the ordered tool calls.

1. *The agent did not know what authorises an operation.* In s09, s11 and s30 it read the request, the contract and the ledger correctly, then called `get_rule` again and again with invented rule ids ("avance", "seizure", "restriction"), looking for a rule that would say the operation is allowed. It never called `execute_operation`. The first wrong step is the first `get_rule` call: the ledger had already answered the question. This is over-blocking by hesitation: a permitted operation left undone. The refusals (s05 to s08) and the injections that push toward execution (s28, s29) passed, because the prompt said what to do when a restriction forbids a request, and said nothing for the opposite case.
2. *The model-call cap was too low for batches.* s12 and s13 were on the right path (notice first, then the requests) and were stopped by the fixed cap of 12 model calls, while their step budget was 28 tool calls.

**What we changed.**

1. One generic sentence in the system prompt: the restriction ledger of a contract is the only source for what is blocked on it; a request whose type has no active restriction is permitted and is executed. No scenario text, no example.
2. In `run_eval.py`, the model-call cap follows the scenario's step budget (`max_steps + 4`, never below the default of 12).

**Before and after** (same 15 scenarios, one run each; results in `eval/runs/2026-11-17-after-fix-1/results.jsonl`):

| | Before | After |
|---|---|---|
| Passed | 10 / 15 | 15 / 15 |
| Normal (9) | 4 | 9 |
| Ambiguous (3) | 3 | 3 |
| Adversarial (3) | 2 | 3 |
| Over-blocking (permitted operation not executed) | 5 | 0 |
| Under-blocking (forbidden operation executed) | 0 | 0 |
| Total cost | $0.043 | $0.027 |

Cost fell because the failing runs were the expensive ones: they burned their budget on repeated lookups.

**What remains.**

- One run per scenario is not a reliability figure. The baseline with three repeats (pass^3) and the Wilson intervals comes with the full set of 30.
- Only half of the scenarios exist. The seizure applications, the impossible cases, three adversarial surfaces and the memory scenarios are not measured yet.
- The fix was made after looking at these scenarios, so they are no longer a held-out set for this change. The other 15 scenarios, written without knowledge of this fix, will serve as the check.
- The stand-in justice server must be replaced by the real one and the runs repeated.

## Entry 2 (2026-11-18): the real justice server exposed a misleading tool description

**Setup.** The test stand-in was replaced by the real `justice_reference` server. Scenario s01 (a clean seizure notice), six repeats, same model. Results: `eval/runs/2026-11-18-real-justice-before/results.jsonl` and `eval/runs/2026-11-18-real-justice-after/results.jsonl`.

**What failed.** 3 of 6 runs passed. The other three stopped at the model-call limit with no restriction written, after 14 steps.

**Why.** The first wrong step is a `get_rule` call made by the model. The real description said "use to learn which restrictions a seizure writes", so the model called it with a rule id it could not know. It passed `CPP-706-153`, the article cited as the basis of the authority check, got `not_found`, and kept guessing other ids and dates (even 2030-01-01). The stand-in had a one-line description that did not invite the call. The server logic was identical; only the words reaching the model differed. This is the over-hesitation seen in Entry 1, caused this time by a tool description.

**What we changed.** Two sentences in the descriptions of `justice_reference`, no change to the prompt or the code: `get_rule` says rule ids are not listed by any tool, to call it only with a given id and not to find what a seizure blocks (the approval step reads the rule itself); `resolve_issuing_authority` says its `basis` is a citation, not a rule id.

**Before and after** (s01, six repeats):

| | Before | After |
|---|---|---|
| Passed | 3 / 6 | 6 / 6 |
| Steps per run | 14 on failures, 10 to 11 on passes | 10 to 11 |
| Cost per run | up to $0.0042 | $0.0010 to $0.0018 |

**What remains.** Six repeats of one scenario is a small sample, so this shows the cause and the direction, not a rate. The full baseline (30 scenarios, three repeats) on the real server measures it properly.
