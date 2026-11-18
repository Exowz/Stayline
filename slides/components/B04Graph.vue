<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
</script>

<template><main class="slide beat-four">
  <div class="eyebrow">04 / The graph</div>
  <Kin text="One agent, *guarded* writes" :on="active" />
  <Island class="graph-card section"><svg class="graph" viewBox="0 0 1480 340" aria-label="Agent graph: a free loop, then a guarded write path">
    <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="currentColor" /></marker></defs>
    <g class="loop" :class="{ lit: shown(1) }">
      <text class="cap" x="0" y="34">The model, free to read and search</text>
      <path class="edge" d="M170 112H210 M380 112H420" marker-end="url(#arr)" />
      <path class="edge" d="M505 154V270H470" marker-end="url(#arr)" /><path class="edge" d="M300 270H250V154" marker-end="url(#arr)" />
      <rect x="0" y="70" width="170" height="84" rx="24"/><text x="85" y="122">recall</text>
      <rect x="210" y="70" width="170" height="84" rx="24"/><text x="295" y="122">think</text>
      <rect x="420" y="70" width="170" height="84" rx="24"/><text x="505" y="122">router</text>
      <rect x="300" y="228" width="170" height="84" rx="24"/><text x="385" y="280">read_tool</text>
    </g>
    <g class="guarded" :class="{ lit: shown(2) }">
      <text class="cap" x="720" y="34">Code takes over, in four steps</text>
      <path class="edge" d="M590 112H720" marker-end="url(#arr)" />
      <path class="edge" d="M890 112H930 M1100 112H1140 M1310 112H1350" marker-end="url(#arr)" />
      <rect x="720" y="70" width="170" height="84" rx="24"/><text x="805" y="122">prepare</text>
      <rect class="approve" x="930" y="70" width="170" height="84" rx="24"/><text class="onblue" x="1015" y="122">approve</text>
      <rect x="1140" y="70" width="170" height="84" rx="24"/><text x="1225" y="122">write</text>
      <rect x="1350" y="70" width="130" height="84" rx="24"/><text x="1415" y="122">verify</text>
      <text class="note" x="1015" y="196">human decides</text>
      <text class="note" x="805" y="196">re-reads facts</text>
    </g>
  </svg></Island>
  <Island class="fact reveal" :class="{ on: shown(3) }"><strong>One agent: about {{ deck.traces.s01.tool_calls }} tool calls per seizure</strong><span>Budgets in code: step limit · model-call limit</span></Island>
</main></template>
<style scoped>
.graph-card { padding: 26px 28px 20px; }
.graph { display: block; width: 100%; height: 360px; overflow: visible; color: var(--second); }
.graph rect { fill: color-mix(in oklab, var(--white) 80%, transparent); stroke: var(--line); stroke-width: 2; }
.graph text { fill: var(--second); text-anchor: middle; font: 600 30px 'JetBrains Mono Variable'; }
.graph text.cap { text-anchor: start; font: 650 30px 'Onest Variable'; fill: var(--ink-muted); }
.graph text.note { font: 500 27px 'Onest Variable'; fill: var(--ink-muted); }
.graph .edge { fill: none; stroke: currentColor; stroke-width: 3.5; opacity: .6; }
.graph g { opacity: .22; transition: opacity .6s; }
.graph g.lit { opacity: 1; }
.graph .approve { fill: var(--loud); stroke: var(--loud); }
.graph text.onblue { fill: var(--white); }
.fact { margin-top: 22px; display: flex; justify-content: space-between; gap: 24px; font-size: 34px; }
</style>
