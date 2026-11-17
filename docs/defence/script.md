# Stayline: defence script (first draft)

10-minute pitch, two speakers, five minutes each. The beat sheet is `outline.md`. This file is the play: who speaks, for how long, the exact words. The Slidev deck is built from it.

**Conventions.** `**SPEAKER · about N seconds**` opens a block. `[click]` advances the slide. Lines starting with `>` are stage directions and are not spoken. `If asked:` lines hold facts for the Q&A and are not spoken. `[RESULT: ...]` is a number that will come from the evaluation; it counts as two spoken words in the timing check. Run `python docs/defence/check_timing.py` after every edit.

**Status.** Beats 1 to 4 and 7 are written in full. Beats 5, 6, 8, 9 and 10 have their structure and placeholders until the baseline run (plan task 16).

---

## Beat 1: A judge freezes a contract

**KHADIDJA · about 70 seconds**

We are Khadidja and Ewan, and this is Stayline.

[click] Picture a criminal investigation, a fraud or a money laundering case. A judge seizes a suspect's life-insurance contract until the trial. The money stays inside, but five things must stop.

[click] The holder can no longer withdraw, that is the rachat. [click] They can no longer cancel the contract. [click] They can no longer pledge it. [click] Nobody can newly accept the benefit as beneficiary. [click] And the insurer can no longer grant an advance.

The insurer receives a notice from the court and has to apply it. Stayline is an agent that does it: it finds the right contract, even through a typo or a namesake, checks that the judge may order the seizure, shows a human exactly what it will block, and then writes five lines in a ledger, each one traced to its notice and its rule version. The law is article 706-155 of the code of criminal procedure, in its 2026 version.

If asked: the five restrictions are rachat, renonciation, nantissement, acceptation_benefice, avance. Source: `docs/concept.md` section 2. Confiscation is a later, separate stage and is out of scope. The article is repealed on 1 January 2029 by ordonnance 2025-1091; our rule is pinned to its 2026 version, which is why the rules table is versioned.

## Beat 2: Two dangerous buttons

**KHADIDJA · about 50 seconds**

The agent has two buttons it must never press carelessly.

[click] The first is blocking a contract. Pick the wrong one, and an innocent client is frozen.

[click] The second is paying out a rachat or an advance. If the contract is seized, that money must not leave.

[click] But there is a second way to fail, and it is what makes this project different. In 2012 the Cour de cassation ruled that the seizure can only cause the effects the law lists. So an agent that blocks too much is not careful, it is wrong. Our grader reads the final state of the database and checks both directions. Blocking too little fails. Blocking too much fails.

If asked: Crim. 30 Oct 2012, n° 12-84.961. Arbitrage stays allowed on a seized contract: this is a stated assumption of our mock product, not a legal claim. The notices come from a trusted mock feed, so the agent makes no claim about whether a document is authentic.

## Beat 3: Backend and the two servers

**EWAN · about 45 seconds**

I take the engineering side. The backend is a SQLite database that we reset to a seed before every test: subscribers, contracts, requests and the ledger.

[click] Two MCP servers sit on top of it. `justice_reference` is read only: the notice, who may order a seizure, and the rule in force on a date. `insurer_contracts` reads contracts and has our two dangerous writes, `apply_seizure` and `execute_operation`.

[click] The important point is that the server checks every rule again inside the write, in one transaction, whatever the model asked. A stale version, a duplicate notice, a second seizure: the server refuses and nothing changes.

If asked: tools return a typed result with an error code and a retryable flag. The write tools take an idempotency key that the harness computes and hides from the model. Source: design sections 7 and 8.

## Beat 4: The graph, and why one agent

**EWAN · about 65 seconds**

The agent is a LangGraph graph.

[click] It thinks in a free loop. The model reads, searches and calls tools.

[click] But when it asks for a dangerous write, the loop stops and code takes over, in four steps. Prepare re-reads the contract and builds the approval card from the backend, not from the model's words. Approve pauses the graph with an interrupt, and nothing is written before it. Write uses the exact version the human saw. Verify reads the contract back to confirm.

[click] Why one agent? The job is one linear task with one set of tools. A second agent would add hand-offs and cost, and we measured no gain, so we did not build one. A full seizure takes [RESULT: tool calls per seizure run] tool calls on one agent. The budgets are in code too: a step limit, a model-call limit, and a stop reason read from the state.

If asked: the router is a pure function tested without a model. Approval is one exact versioned action, so a stale version sends the run back to prepare and the human approves the new state. `set_request_status` needs no approval because it cannot execute anything.

## Beat 5: Live demo, a success

**EWAN · about 80 seconds**

> Demo plan: scenario s01 on the base seed, run from the UI. Fallback: the recorded run.

Here is scenario s01, a clean seizure notice, on the base seed.

[click] I type the task and start the run. On the left, every step appears as it happens: the agent reads the notice, checks that the judge may order it, and searches for the contract. Notice that it only reads at this point, it changes nothing yet.

[click] Now it stops. This is the approval card. It shows the notice, the contract and its version, the evidence for why this contract matched, and the exact effect: five restrictions. Nothing has been written yet. A human can say no here, and then nothing is written at all, and the agent is told not to try again.

[click] I approve. The agent writes, then reads the contract back, and the ledger shows five lines, each with its notice and rule version.

[click] And now the proof. A success is not the agent saying it is done. We read the trace and the database. This run made [RESULT: s01 model calls] model calls and [RESULT: s01 tool calls] tool calls, used [RESULT: s01 tokens] tokens and cost [RESULT: s01 cost] dollars.

If asked: the approver in the evaluation always says yes, so the evaluation measures the agent and the server, not the human. The live demo shows the human step.

## Beat 6: Live demo, a failure

**EWAN · about 70 seconds**

> Pick the failed run after the baseline. Choose the one whose first wrong span is easiest to read.

Now a run that failed, because a result you never see fail is not a result. We read it the same way, from the trace and not from what the agent says.

[click] This is scenario [RESULT: failed scenario id], of the kind [RESULT: its kind]. The task was [RESULT: the task in one sentence].

[click] Here is the first wrong span. Every earlier step was fine. At this one, [RESULT: what the agent did at that span, in one sentence]. A trace lets us point at one exact step, not at a whole run, and that is what makes a failure fixable.

[click] The final state of the database shows the consequence. The grader compared it with the state we expected, and found [RESULT: what the grader found wrong]. The run stopped with the reason [RESULT: stop reason], which the grader reads from the state.

What it tells us: [RESULT: the cause in one sentence]. That is exactly the kind of entry we come back to in the error analysis, with the figures before and after the change.

If asked: the grader fails a run that calls a forbidden tool even when the call itself failed.

## Beat 7: Memory

**KHADIDJA · about 40 seconds**

Now memory. An operator tells the agent: Orion is instruction 2026 slash 00417 at the Paris court. The agent stores that alias, per operator.

[click] Later, in a brand new run, the operator says: a request came in on the Orion contract, process it. With memory, the agent finds the seized contract and handles the request. Without memory, the request is ambiguous, so the agent asks and changes nothing.

The alias is only a hint. The current records still decide, and text that comes back from a tool can never write to memory.

If asked: the store is per operator, so another operator does not see the alias. A correction keeps the old value in a history. Source: design section 11 and `docs/memory-test.md`.

## Beat 8: Results

**KHADIDJA · about 70 seconds**

> One table, one chart. Source: `eval/summary.md`.

Here are the results on our thirty scenarios: fourteen normal, five ambiguous, five impossible and six adversarial, each run [RESULT: repeats] times.

[click] Normal scenarios: [RESULT: normal pass rate with interval]. Ambiguous: [RESULT: ambiguous pass rate]. Impossible: [RESULT: impossible pass rate]. Adversarial, with an instruction hidden inside a tool result: [RESULT: adversarial pass rate].

[click] We report pass to the power of k, because an agent that succeeds only some of the time cannot be trusted with a freeze. It is [RESULT: pass^k] across [RESULT: k] repeats. The intervals are Wilson intervals, because with so few runs, a plain percentage hides the doubt, and we prefer to show it.

[click] Cost per success is [RESULT: cost per success] dollars, with a median latency of [RESULT: p50] seconds and a p95 of [RESULT: p95].

And the two errors that matter for this domain, which a single pass rate would hide. Under-blocking, a seizure missed, happened [RESULT: under-blocking count] times. Over-blocking, too much changed, happened [RESULT: over-blocking count] times.

If asked: the grader was checked by running it on a final state we built by hand, for a pass and for each kind of failure.

## Beat 9: Error analysis

**KHADIDJA · about 70 seconds**

> Source: `docs/error-analysis.md`. Entry 1 is real; update the figures after the baseline.

What failed, and why. On our first look at fifteen scenarios, ten passed. Five failed, and they were the same mistake: permitted operations were never executed.

[click] The first wrong step is easy to find in the trace. The agent had already read the ledger, which said nothing blocked the operation. Then it called the rule tool again and again with invented rule names, looking for permission. It was over-blocking by hesitation.

[click] What we changed was one generic sentence in the prompt: the ledger is the only source of what is blocked, and a request with no active restriction is permitted. We also let the model-call limit follow the step budget, because two batches were stopped by a cap that was too low.

[click] Measured on the same fifteen scenarios, fifteen out of fifteen passed after the change. On the full baseline, the figures are [RESULT: before and after on the full set]. What remains, and what we did not fix: [RESULT: remaining failures and limits].

If asked: the fix contains no scenario text and no example, and a test checks that. Our own limit is that the fifteen scenarios were the ones we looked at when fixing, so the full thirty are the fair test.

## Beat 10: Bonuses, limits, and the close

**EWAN · about 40 seconds**

Three bonuses.

[click] A second model: we compared the main model with [RESULT: second model] on the same scenarios, and the table shows [RESULT: comparison]. A failure injected into a tool: the server commits, then answers with a timeout, and the agent reads back instead of retrying blindly: [RESULT: recovery result]. And the interface you saw.

Our limits: a mock feed, one operator at a time, and an always-yes approver in the evaluation.

[click] Stayline: an AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more. Thank you.

If asked: see `docs/defence/qa.md`.
