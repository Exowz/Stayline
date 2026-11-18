# Defence outline (beat sheet)

**Format:** 10-minute pitch and 5-minute Q&A, Friday 20 November 2026. Two speakers, five minutes each. The script is written first, as a play: who speaks, for how long, the exact words, and the click cues. The Slidev deck is built from the script, never the other way round.

**What the brief requires, in order:** the domain, the backend and the dangerous action; the architecture (why this graph, why these tools, why one agent, with the number); a live demo of one successful run and one failed run, read from the trace; the per-kind results and the error analysis (what failed, why, what we changed, what remains); everyone speaks.

## Beats

| # | Speaker | Time | Beat | On screen | Source of truth |
|---|---|---|---|---|---|
| 1 | Khadidja | 1:10 | A judge freezes a suspect's life-insurance contract. The insurer must block five things on the right contract, and nothing more. | Cover, then the five restrictions appearing one by one | `docs/concept.md` sections 1 and 2 |
| 2 | Khadidja | 0:50 | The two dangerous buttons, and why blocking too much is also a failure (Crim. 30 Oct 2012). | Two columns: blocks too little, blocks too much | `docs/concept.md` section 2 |
| 3 | Ewan | 0:45 | The backend and the two MCP servers. The server enforces every rule again, whatever the model asks. | Tables and tools, the two dangerous writes marked | Design sections 7 and 8 |
| 4 | Ewan | 1:05 | The graph: a free loop with a coded guard around each dangerous write. Why one agent. | The graph diagram, the guard path lighting up | Design section 9 |
| 5 | Ewan | 1:20 | Live demo, success: a seizure notice, the approval card, the read-back. Read from the trace. | The UI, then the trace | A recorded run as fallback |
| 6 | Ewan | 1:10 | Live demo, failure: one scenario that fails, the first wrong span, what it shows. | The trace of a failed run | `docs/error-analysis.md` |
| 7 | Khadidja | 0:40 | Memory: the Orion alias changes a later run; without it the agent asks. | Two runs side by side | scenarios s14, s18 and s19 in `eval/scenarios.jsonl` |
| 8 | Khadidja | 1:10 | Results per kind with intervals, pass^k, cost per success; under-blocking and over-blocking. | One table, one chart | `eval/summary.md` |
| 9 | Khadidja | 1:10 | Error analysis: what failed, why, what we changed, measured before and after, what remains. | Before and after figures | `docs/error-analysis.md` |
| 10 | Ewan | 0:40 | The bonuses in one breath (two models, recovery from a failure, the UI), limits, and the closing line. | Comparison table, then the tagline | `eval/comparison.md` |

Totals: Khadidja 5:00, Ewan 5:00.

## Script conventions (from the earlier decks)

- One block per beat: `**SPEAKER · about N seconds**`, then the spoken words, with `[click]` where the slide advances.
- Plain spoken English, short sentences, numbers said the way they will be pronounced.
- Each beat ends with an "If asked:" line holding the facts for a likely question.
- Every number in the script is copied from a file in the repo and carries its source in a comment. A timing check counts the words per beat against its time budget (about 140 words per minute).

## Demo plan

- Success: scenario s01 (clean seizure notice) run from the UI on the base seed, approval clicked live.
- Failure: chosen after the baseline run from the real failures, the one whose first wrong span is easiest to read.
- Fallback: both runs recorded beforehand (screen capture and saved trace files), ready to play if the network or the model misbehaves.

## Q&A sheet (to prepare)

Seizure and confiscation are two stages; why arbitrage is allowed (a stated mock-product assumption); the repeal of article 706-155 in 2029; why one agent; why the server also blocks; what the always-yes approver measures; why the approval is not asked for `set_request_status`; how the grader was checked; the team of two.
