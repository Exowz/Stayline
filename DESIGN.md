# Design

The visual system of the Stayline UI. Approved by Ewan on 2026-11-17 from the reference mockup `docs/design/run-screen.html` (open it in a browser; it is static HTML, not the product). Product context is in `PRODUCT.md`.

## Direction

Clean, modern and calm: floating glass islands on a soft canvas, with room to breathe. Not an AI chat app, not a default admin template, not an industrial or "technical" look, not austere.

## Colour: 60 / 30 / 10

| Share | Role | Colour | Used for |
|---|---|---|---|
| 60% | Main | neutral light grey, `oklch(0.955 0.003 270)` | the canvas and the frosted light panels |
| 30% | Second | graphite, `oklch(0.22 0.01 270)` | the sidebar island, the bottom dock, text, the contract avatar, ticks and small marks |
| 10% | Loud | electric blue, `oklch(0.62 0.24 264)`, white text on it | only what needs the operator: the status pill while waiting, the current plan step, the row on hold, the operations about to be blocked, the primary button |

Rules:

- The loud colour means one thing: this needs you. It is never decoration.
- No separate green or amber. Done and allowed states use the second colour (a tick, an outline).
- **One deliberate exception, the failure colour:** signal red, `oklch(0.6 0.22 25)`, white text on it. It is used only for something that went wrong: a failed scenario on the Evaluation and Models screens, a failed tool call in the plan list, an error or budget stop reason, a failed run's dot in the sidebar. It always comes with a word or an icon, never colour alone. It is not part of the 60/30/10 split and must stay rare: a screen with no failure shows no red. Blue still means "this needs you"; red means "this failed". A blocked operation is not a failure and stays blue.
- Tints are mixed from the three colours (for example the loud colour at 16% on white for chips), never new hues.
- Text on light panels is the second colour at full strength for body, and mixed toward white for secondary text, keeping at least 4.5:1 contrast.

## Surfaces

- **Canvas:** the main colour with two or three large, soft blurred fields of the second and loud colours at low strength, fixed to the viewport, so the glass has something to frost.
- **Islands:** every region floats: the sidebar, the title bar, each content panel, the bottom dock. 16px gaps between islands and to the window edge. Radius 24px. No region touches the window edge.
- **Light islands:** white at about 62% opacity, backdrop blur 26px with saturation 1.5, a one-pixel inner white edge, a soft low shadow tinted with the second colour.
- **Dark islands (sidebar, dock):** the second colour at about 86% opacity, same blur, light text.
- Panels in a row are equal in width and height. Actions sit at the bottom of their panel.
- Glass must stay readable on a projector: never lower the panel opacity below these values, and never put body text directly on the canvas.

## Type

- Sans: Onest (400, 500, 600, 700). Mono: JetBrains Mono, only for identifiers, tool names and figures.
- Sizes: page title 25px semibold; card title 19px semibold; body 14.5px; secondary 13px; labels 12px semibold. No uppercase tracking labels.
- Figures use tabular numerals.

## Components

- **Buttons:** 40px high, radius 12px. Primary: loud colour, white text, a soft glow of the same colour. Secondary: glass with a hairline. One primary per screen.
- **Chips:** pills, 12.5px. Neutral (glass, hairline), confirmed (a tick in the second colour), about to change (loud tint, loud dark text, semibold).
- **Plan list:** a vertical checklist. Each step has a round mark (tick when done, number when pending, loud fill when current), a title, one line of plain explanation, and its tool calls nested as rows (mono tool name, short result, duration right-aligned). Calls made by the harness are tagged "safety check".
- **Approval card:** a kicker in loud dark, a question as the title, then sections split by hairlines: the contract, why this contract (evidence chips), what will change (blocked, still allowed, untouched), the source line, and the Reject and Approve row.
- **Dock:** a dark pill centred at the bottom with the run's steps, tokens, cost, elapsed time and model.
- **Status pill:** top right of the title island; loud while waiting, second colour when done.

## Screens

Run (plan, tool calls, approval), Ledger (three counters and the lineage table), Evaluation (results per kind), Models (the two-model comparison). All four use the same islands and the same three colours.

## Motion

150 to 250 ms, ease-out, only for state changes: a step completing, the approval card resolving, the status pill changing. A slow pulse on the waiting dot. Respect reduced-motion.

## Build notes

React, TypeScript, Tailwind and shadcn/ui. Define the three colours as CSS variables and derive every tint with `color-mix`, as the reference mockup does. Prefer existing components from 21st.dev (agent plan list, timeline) restyled to these tokens over hand-built ones.
