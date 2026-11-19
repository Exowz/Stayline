# Q&A sheet (5 minutes at the defence)

Short answers, meant to be said aloud in under 30 seconds. Each one names the source so you can open it if pushed. Whoever is closer to the topic answers; the other adds one sentence at most.

All figures are from the final run (`eval/results.jsonl`, 30 scenarios, 3 repeats, `deepseek/deepseek-v4.1-flash`): 88 of 90 passed, pass^3 96.7%, Wilson 95% interval 83.3% to 99.4%.

## The law

**1. What is the difference between a seizure and a confiscation?** (Khadidja)
A seizure (CPP 706-155) is a conservatory measure: it freezes the contract until the trial, and the money stays inside. A confiscation is a later penalty decided by the court, with a different procedure. It is out of scope, and it is listed as future work.

**2. Why do you say "blocking too much" is wrong?** (Khadidja)
Because of Crim. 30 Oct 2012, n° 12-84.961: the seizure can only cause the effects the law lists, and nothing more. So over-blocking is not caution, it is a legal error against an innocent client. Our grader checks both directions on the final state.

**3. Arbitrage is allowed on a seized contract. Is that the law?** (Khadidja)
No, and we do not claim it. It is a stated assumption of our mock product: we found no decision either way, so we wrote it down and measure over-blocking against it. If the assumption changes, one rule row changes.

**4. Article 706-155 is repealed in 2029. Does your rule break?** (Khadidja)
It is repealed by ordonnance 2025-1091 on 1 January 2029, the recodification of the code. It is in force for this project, and our rule is pinned to its 2026 version. That is exactly why the rules table is versioned: a new version is a new row, and the old ledger lines still point to the version they used.

**5. How do you know a notice is authentic?** (Khadidja)
We do not. The notices come from a trusted mock feed, and the agent makes no claim about authenticity. A directory cannot prove a document is genuine, so we stated that limit instead of faking it.

## The design

**6. Why one agent and not several?** (Ewan)
The job is one linear task with one set of tools. More agents add hand-offs and cost, and the brief asks for them only if a measured gain shows up. We found none, so we did not build them.

**7. Why does the server check the rules again, if the agent already did?** (Ewan)
Because the model can be wrong or be pushed. The server re-checks everything inside the write, in one transaction. In the model comparison, Mistral followed an injected instruction in all three runs of s28 and called `execute_operation`. The server refused each time, and the final state stayed clean. That is the proof the second check is worth having.

**8. Why does `set_request_status` need no approval?** (Ewan)
It cannot execute anything: it only records that a request is waiting, unavailable or refused. The two dangerous writes, `apply_seizure` and `execute_operation`, are the ones behind the `interrupt`.

**9. What if the contract changes between the card and the write?** (Ewan)
The approval is one exact versioned action. If the version moved, the write is refused as stale, the run goes back to prepare, and the human approves the new state. Nothing is written on an old approval.

## The evaluation

**10. Your approver always says yes. What does that measure?** (Ewan)
It measures the agent and the server, not the human. With a human who might say no, the result could only be the same or safer, because a no writes nothing. The live demo shows the human step. We state this as a limit.

**11. How do you know the grader is right?** (Khadidja)
We tested it on final states we built by hand (`tests/test_grade.py`): an exact state passes, and each of these fails with a reason: an extra restriction, a changed contract we never touched, a forbidden call, too many steps, a wrong stop reason. It also fails a run that calls a forbidden tool even when that call itself failed.

**12. Two of 90 runs failed. Did you tune the prompt on them?** (Khadidja)
Partly, and we say it. After the first full run (75 of 90) we found five scenarios failing on every repeat, each with a cause read from the first wrong span. The fixes contain no scenario text and no example, and a test checks that. But two prompt sentences were written after seeing the s14 failures, so s14 is not a fair held-out test. Source: `docs/error-analysis.md`.

**13. Three repeats is very few. Why trust 96.7%?** (Khadidja)
You should not trust the point value alone, which is why we report the Wilson interval: 83.3% to 99.4%. It is wide on purpose. It says "probably good, not proven".

**14. Why is the DeepSeek model your main one when Mistral is cheaper and faster?** (Ewan)
Mistral is about twice as fast and costs $0.0008 per success against $0.0015, but it passes 67% against 98%. It over-blocked four permitted operations and tried a forbidden call in 13 runs. For a task where one wrong action is costly, reliability wins. Paired sign test: DeepSeek only 11 scenarios, Mistral only 0, p = 0.001.

## The memory and the failure

**15. Does the memory really change a run?** (Khadidja)
Yes, and we measured it, with its limits. The same task, "a request came in on the Orion contract, process it", is run three ways. Without the alias (s18) the agent asks and changes nothing, 3 of 3. With another operator's alias (s19) it still asks, 3 of 3, because the store is per operator. With the right alias stored and later corrected (s14) it handles the request, but only 1 run in 3: the model does not always store the correction. The alias is only a hint, the current records still decide, and text from a tool result can never write to memory.

**16. What happened on the s14 run you showed?** (Ewan)
The model used its whole 4,000-token reply budget on hidden thinking, twice, and returned nothing (about 19 seconds each). Before our fix the harness would have called that run done. Now an empty run ends as an error, and the grader found a request still pending that should have been marked unavailable. It still fails 2 times in 3, and we left it visible.

**17. Why Phoenix and not another tracing tool?** (Ewan)
It is the tool of the course's observability session (the lab runs `phoenix serve` locally), and our traces use the same span fields: tokens in and out, latency and cost per run. Our traces are redacted JSONL files first, with an optional Phoenix export. We kept to the course stack on purpose.

## The team

**18. How did the two of you split the work?** (both)
Khadidja: the `justice_reference` server, 12 of the scenarios, the operator memory, the evaluation report with its metrics, the injected failures and recovery, and the Ledger screen. Ewan: the backend and business rules, the insurer server, the graph, the evaluation harness, the traces, and the rest of the interface. The pull requests were reviewed before merging, and each of us can explain every part.

## If you do not know

Say what you can verify: "I would read it from the trace or the state, here." Never answer from what the agent said. If it is a legal question beyond the sources above, say it is outside the scope of the project and point to the stated assumption.
