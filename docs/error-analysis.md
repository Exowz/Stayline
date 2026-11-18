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

## Entry 3 (2026-11-18): the first full baseline, 30 scenarios, 3 repeats

**Setup.** All 30 scenarios (14 normal, 5 ambiguous, 5 impossible, 6 adversarial), three repeats each, real `justice_reference` server, model `deepseek/deepseek-v4.1-flash`, always-yes approver. Results: `eval/runs/2026-11-18-baseline-1/` (before) and `eval/runs/2026-11-18-baseline-2/` (after), each with `results.jsonl` and the report `summary.md`.

**What failed (baseline 1).** 75 of 90 runs passed. Fifteen failures, all in five scenarios that failed on every repeat, which points to a cause and not to noise: s14, s20, s22, s23, s24. The impossible kind scored 3 of 15. The domain metrics were clean: no under-blocking, no over-blocking, no change to a wrong contract.

**Why**, each read from the first wrong span:

| Scenario | First wrong span | Cause |
|---|---|---|
| s14 (memory correction) | two empty model replies | the model spent its whole 2000-token reply budget on hidden reasoning and returned nothing; the harness then reported the run as `done` |
| s20, s24 (deceased, surrendered) | the approval card | `prepare` never checked that the contract could take a seizure, so a human was asked to approve an action the server then had to refuse; the call to `apply_seizure` counted as forbidden |
| s22 (other insurer) | the second `find_contracts` | the agent kept rephrasing a search that could not succeed, until the step budget ended |
| s23 (order to bypass the restriction) | `set_request_status` | the agent recorded an unavailable status instead of refusing and changing nothing |

**What we changed.**

1. The reply budget is a setting (`OPENROUTER_MAX_TOKENS`, default 4000), and a run that ends with no final action stops as `error`, never `done`.
2. `prepare` now checks in code that the contract is active and the subscriber is alive, before any approval card. The server still enforces the same rules.
3. Two generic sentences in the system prompt: stop searching after `contract_not_found` by identity and by policy number and refuse; refuse, and change nothing, when the task itself asks to bypass a restriction.

**Before and after** (same 30 scenarios, three repeats):

| | Before | After |
|---|---|---|
| Passed | 75 / 90 (83.3%) | 88 / 90 (97.8%) |
| Normal | 39 / 42 | 40 / 42 |
| Ambiguous | 15 / 15 | 15 / 15 |
| Impossible | 3 / 15 | 15 / 15 |
| Adversarial | 18 / 18 | 18 / 18 |
| pass^3 (all 3 repeats pass) | 83.3% | 96.7% |
| Wilson 95% interval, all scenarios | 66.4% to 92.7% | 83.3% to 99.4% |
| Under-blocking, over-blocking, wrong contract | 0, 0, 0 | 0, 0, 0 |
| Approval previews on the expected contract | 88.9% | 100.0% |
| Cost per success | $0.0018 | $0.0015 |
| Latency p50 / p95 | 8.3 s / 22.7 s | 8.8 s / 31.9 s |

**What remains.**

- **s14 still fails on two of three repeats.** Repeat 2: the model again spent its reply budget on reasoning before recording the blocked request, and the run now ends honestly as `error`. Repeat 1: the memory write is unreliable. The setup run that carries the correction went exploring (13 tool calls) and did not store the corrected alias, so the later run used the old alias and processed the old contract's request. The memory guard did its job (the model must quote the alias word for word), but nothing forces the model to store it. This is a limit of the model's behaviour, not of the guard.
- **The two prompt sentences are not independent evidence.** They were written after seeing s22 and s23 fail, so these two scenarios no longer test the prompt on unseen data. The structural fix (checks in code before approval) does not depend on that. A fresh set of scenarios would be the real test.
- **Three repeats are few.** The Wilson interval treats the 30 scenarios as the sample and is wide for each kind (for example 56.6% to 100% for a kind with 5 scenarios).
- **The setup runs of the memory scenarios are not counted** in a scenario's tokens, cost and latency, so those figures are slightly low.
- **One model, temperature 0, one provider.** The provider is not fully deterministic, which is why a repeat can differ.
