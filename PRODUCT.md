# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A back-office operator at a fictional life-insurance company. The operator watches an AI agent handle court seizure notices and adviser operation requests, and approves or rejects each dangerous write before it runs. The work is evaluated by a course jury (live demo, seen on a projector) and by recruiters (a screenshot in the repository README).

## Product Purpose

Stayline applies a court-ordered freeze (a criminal seizure under CPP 706-155) to the right life-insurance contract, and nothing more, and gates adviser requests (rachat, avance, arbitrage) against that freeze. Success means the right contract gets exactly the five restrictions, forbidden operations are refused, permitted ones go through, and every claim is read from the backend state.

## Positioning

The agent fails if it blocks too little and also if it blocks too much. Every restriction is one ledger line traced to its source: which notice, which rule version.

## Operating Context

Two kinds of work arrive: seizure notices from a court, and operation requests from independent advisers. The agent reads records through tools, proposes a dangerous write, and pauses. The operator sees the notice or request, the matched contract with the evidence for the match, the current version, and the exact proposed effect, then approves or rejects. A second view shows the restriction ledger: restricted contracts, operations blocked and permitted, and each restriction's lineage.

## Capabilities and Constraints

- Two screens: Run (the task, the live step log, the approval card, the final stop reason with tokens, cost and latency) and Ledger (three counters and the lineage table).
- Dangerous writes: `apply_seizure` and `execute_operation`. `set_request_status` records a refusal and needs no approval.
- Five restrictions: `rachat`, `renonciation`, `nantissement`, `acceptation_benefice`, `avance`.
- Stop reasons: done, asked the operator, refused, step budget, model-call budget, error.
- English interface; French only for legal terms and mock notice text.
- Mock data only. Adviser-facing wording never reveals a seizure.
- Stack: React, TypeScript, Tailwind, shadcn/ui, served by a FastAPI service. Built last; it must never endanger the evaluation.

## Brand Commitments

- Name: Stayline. "Stay" is the legal word for a court-ordered suspension; "line" is a line in the restriction ledger.
- Tagline: an AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more.
- It must not look like an AI chat app, a generic admin dashboard template, or a playful startup product, and it must not be so austere that it looks unfinished.
- Never use the long dash character.

## Evidence on Hand

- Mock seeds under `seeds/` (contracts, notices, requests), the approved concept in `docs/concept.md` and the design in `docs/design.md`.
- No logo, no photography, no real customers. Do not invent any.

## Product Principles

- The human decides on facts read from the backend, never on the agent's summary.
- Danger is rare and unmistakable: approval is asked only for what cannot be undone.
- Every restriction shows its source.
- Doing nothing more than asked is a feature to make visible.

## Accessibility & Inclusion

Readable from the back of a classroom on a projector and as a still screenshot. State is never carried by colour alone.
