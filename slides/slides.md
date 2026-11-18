---
theme: default
title: Stayline
canvasWidth: 1920
aspectRatio: 16/9
fonts:
  provider: none
transition: stay-fade
mcp: false
colorSchema: light
---

<B01Freeze />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**KHADIDJA · about 70 seconds**

We are Khadidja and Ewan, and this is Stayline.

[click] Picture a criminal investigation, a fraud or a money laundering case. A judge seizes a suspect's life-insurance contract until the trial. The money stays inside, but five things must stop.

[click] The holder can no longer withdraw, that is the rachat. [click] They can no longer cancel the contract. [click] They can no longer pledge it. [click] Nobody can newly accept the benefit as beneficiary. [click] And the insurer can no longer grant an advance.

The insurer receives a notice from the court and has to apply it. Stayline is an agent that does it: it finds the right contract, even through a typo or a namesake, checks that the judge may order the seizure, shows a human exactly what it will block, and then writes five lines in a ledger, each one traced to its notice and its rule version. The law is article 706-155 of the code of criminal procedure, in its 2026 version.

If asked: the five restrictions are rachat, renonciation, nantissement, acceptation_benefice, avance. Source: `docs/concept.md` section 2. Confiscation is a later, separate stage and is out of scope. The article is repealed on 1 January 2029 by ordonnance 2025-1091; our rule is pinned to its 2026 version, which is why the rules table is versioned.
-->

---

<B02TwoButtons />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**KHADIDJA · about 50 seconds**

The agent has two buttons it must never press carelessly.

[click] The first is blocking a contract. Pick the wrong one, and an innocent client is frozen.

[click] The second is paying out a rachat or an advance. If the contract is seized, that money must not leave.

[click] But there is a second way to fail, and it is what makes this project different. In 2012 the Cour de cassation ruled that the seizure can only cause the effects the law lists. So an agent that blocks too much is not careful, it is wrong. Our grader reads the final state of the database and checks both directions. Blocking too little fails. Blocking too much fails.

If asked: Crim. 30 Oct 2012, n° 12-84.961. Arbitrage stays allowed on a seized contract: this is a stated assumption of our mock product, not a legal claim. The notices come from a trusted mock feed, so the agent makes no claim about whether a document is authentic.
-->

---

<B03Backend />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**EWAN · about 45 seconds**

I take the engineering side. The backend is a SQLite database that we reset to a seed before every test: subscribers, contracts, requests and the ledger.

[click] Two MCP servers sit on top of it. `justice_reference` is read only: the notice, who may order a seizure, and the rule in force on a date. `insurer_contracts` reads contracts and has our two dangerous writes, `apply_seizure` and `execute_operation`.

[click] The important point is that the server checks every rule again inside the write, in one transaction, whatever the model asked. A stale version, a duplicate notice, a second seizure: the server refuses and nothing changes.

If asked: tools return a typed result with an error code and a retryable flag. The write tools take an idempotency key that the harness computes and hides from the model. Source: design sections 7 and 8.
-->

---

<B04Graph />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**EWAN · about 65 seconds**

The agent is a LangGraph graph.

[click] It thinks in a free loop. The model reads, searches and calls tools.

[click] But when it asks for a dangerous write, the loop stops and code takes over, in four steps. Prepare re-reads the contract and builds the approval card from the backend, not from the model's words. Approve pauses the graph with an interrupt, and nothing is written before it. Write uses the exact version the human saw. Verify reads the contract back to confirm.

[click] Why one agent? The job is one linear task with one set of tools. A second agent would add hand-offs and cost, and we measured no gain, so we did not build one. A full seizure takes about ten tool calls on one agent.  The budgets are in code too: a step limit, a model-call limit, and a stop reason read from the state.

If asked: the router is a pure function tested without a model. Approval is one exact versioned action, so a stale version sends the run back to prepare and the human approves the new state. `set_request_status` needs no approval because it cannot execute anything.
-->

---

<B05DemoSuccess />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**EWAN · about 80 seconds**

Here is scenario s01, a clean seizure notice, on the base seed.

[click] I type the task and start the run. On the left, every step appears as it happens: the agent reads the notice, checks that the judge may order it, and searches for the contract. Notice that it only reads at this point, it changes nothing yet.

[click] Now it stops. This is the approval card. It shows the notice, the contract and its version, the evidence for why this contract matched, and the exact effect: five restrictions. Nothing has been written yet. A human can say no here, and then nothing is written at all, and the agent is told not to try again.

[click] I approve. The agent writes, then reads the contract back, and the ledger shows five lines, each with its notice and rule version.

[click] And now the proof. A success is not the agent saying it is done. We read the trace and the database. This run made six model calls and ten tool calls, used about twenty-two thousand tokens, and cost two tenths of a cent.

If asked: the approver in the evaluation always says yes, so the evaluation measures the agent and the server, not the human. The live demo shows the human step.
-->

---

<B06DemoFailure />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**EWAN · about 70 seconds**

Now a run that failed, because a result you never see fail is not a result. We read it from the trace, not from what the agent says. This is one of the two runs out of ninety that failed in our final measurement, and we chose not to hide it.

[click] This is scenario s14, a memory scenario: a request came in on the Orion contract, process it. 

[click] Here is the first wrong span. Every step before it was fine. At this one, the model used its entire budget of four thousand tokens, nineteen seconds, thinking, and returned nothing. Then it did it again.

[click] The grader finds a request still pending that should have been marked unavailable. The run stops with the reason error, read from the state.

What it tells us: a reasoning model can spend its whole reply budget on hidden thinking. Before our fix, the harness would have called this run done.

If asked: the grader fails a run that calls a forbidden tool even when the call itself failed.
-->

---

<B07Memory />
<span v-click class="click-register" />

<!--
**KHADIDJA · about 40 seconds**

Now memory. An operator tells the agent: Orion is instruction 2026 slash 00417 at the Paris court. The agent stores that alias, per operator.

[click] Later, in a brand new run, the operator says: a request came in on the Orion contract, process it. With memory, the agent finds the seized contract and handles the request. Without memory, the request is ambiguous, so the agent asks and changes nothing.

The alias is only a hint. The current records still decide, and text that comes back from a tool can never write to memory.

If asked: the store is per operator, so another operator does not see the alias. A correction keeps the old value in a history. Source: design section 11 and `docs/memory-test.md`.
-->

---

<B08Results />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**KHADIDJA · about 70 seconds**

Here are the results on our thirty scenarios, each run three times. 

[click] Normal scenarios: forty out of forty-two. Ambiguous, impossible, and adversarial, with an instruction hidden inside a tool result: every run passed. Overall, eighty-eight out of ninety.

[click] We report pass to the power of k, because an agent that succeeds only some of the time cannot be trusted with a freeze. It is ninety-seven percent across three repeats, with an interval from eighty-three to ninety-nine. We use Wilson intervals, because with so few runs a plain percentage hides the doubt.

[click] Cost per success is fifteen hundredths of a cent, with a median latency of nine seconds and a p95 of thirty-two.

And the two errors that matter here: under-blocking, a seizure missed, zero times. Over-blocking, too much changed, zero times.

If asked: the grader was checked by running it on a final state we built by hand, for a pass and for each kind of failure.
-->

---

<B09ErrorAnalysis />
<span v-click class="click-register" />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**KHADIDJA · about 70 seconds**

What failed, and why. On the first full run, seventy-five of ninety runs passed. Five scenarios failed every time, so each had a cause.

[click] The clearest: for a deceased subscriber, the agent showed a human an approval card for a seizure the server then had to refuse. The first wrong step is the card itself.

[click] What we changed: the code now checks that the contract can take a seizure before any card is shown. We also raised the reply budget, and made an empty run end as an error, not done. Two generic sentences were added to the prompt.

[click] Measured again on the same thirty scenarios: eighty-eight of ninety, and the impossible kind went from three to fifteen out of fifteen. What remains: the memory scenario s14 still fails twice in three, because the model sometimes overthinks or forgets to store the alias. Two of our prompt sentences were written after seeing those failures, so they are not a fair test.

If asked: the fix contains no scenario text and no example, and a test checks that. Our own limit is that three repeats are few, which is why the intervals are wide.
-->

---

<B10Close />
<span v-click class="click-register" />
<span v-click class="click-register" />

<!--
**EWAN · about 40 seconds**

Three bonuses.

[click] A second model: Mistral Small is twice as fast and cheaper, but passes sixty-seven percent against ninety-eight. It obeyed an injected instruction; our server refused it. A failure injected into a tool: the server commits, then answers with a timeout, and the agent reads back instead of retrying blindly. And the interface you saw.

Limits: a mock feed, one operator at a time, an always-yes approver.

[click] Stayline: an AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more. Thank you.

If asked: see `docs/defence/qa.md`.
-->
