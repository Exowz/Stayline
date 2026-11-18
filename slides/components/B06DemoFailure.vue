<script setup lang="ts">
import { computed } from 'vue'
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Headline from './Headline.vue'

const { shown } = useBeat()
const trace = deck.traces.s14
const graderLine = deck.s14.reason.replace(/^state: /, '').split('; ')[0]
const rows = computed(() => trace.spans.map((span, index) => ({
  ...span, index, bad: span.kind === 'LLM' && span.tokens_out === 4000,
  left: (span.t0_ms / trace.total_ms) * 100, width: Math.max((span.ms / trace.total_ms) * 100, 0.7),
})))
</script>

<template><main class="slide">
  <Headline :page="6" eyebrow="Live demo · failure" before="The first " emphasis="wrong" after=" span" fail />

  <div class="scn mono rv rv-r" :class="{ on: shown(1) }"><b>s14</b> · memory scenario · "a request came in on the Orion contract, process it" · final run, repeat 2</div>

  <div class="wf rv" :class="{ on: shown(2) }">
    <div class="head"><span class="tag">Trace waterfall</span><span class="mono">{{ (trace.total_ms / 1000).toFixed(1) }} s · {{ trace.model_calls }} model calls · {{ trace.tool_calls }} tool calls</span></div>
    <div v-for="r in rows" :key="r.index" class="r" :class="{ bad: r.bad }">
      <span class="nm mono">{{ r.name === 'complete' ? 'model call' : r.name }}</span>
      <div class="tk"><i :class="[r.kind.toLowerCase(), { on: shown(2) }]" :style="{ left: `${r.left}%`, width: `${r.width}%`, '--d': `${0.25 + r.index * 0.11}s` }" /></div>
      <span class="dt mono">{{ r.bad ? `${r.tokens_out.toLocaleString('en-US')} tokens · ${Math.round(r.ms / 1000)} s · empty reply` : `${r.kind === 'LLM' ? r.tokens_out + ' tokens' : Math.round(r.ms) + ' ms'}` }}</span>
    </div>
  </div>

  <div class="panel fail grader rv" :class="{ on: shown(3) }">
    <span class="tag">The grader, reading the database</span>
    <p>{{ graderLine }}</p>
    <p class="mono sr">stop_reason: {{ deck.s14.stop_reason }} <span>· a reasoning model spent its whole reply budget thinking. Before our fix this run would have been called done.</span></p>
  </div>
</main></template>

<style scoped>
.scn { position: absolute; left: 100px; top: 228px; font-size: 23px; color: var(--muted); }
.scn b { color: var(--fail); font-weight: 500; }
.wf { position: absolute; left: 100px; right: 100px; top: 284px; }
.head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; font-size: 21px; color: var(--muted); }
.head .tag { font-size: 18px; color: var(--muted); }
.r { display: grid; grid-template-columns: 250px 1fr 410px; gap: 20px; align-items: center; height: 31px; font-size: 20px; }
.nm { color: var(--muted); } .dt { color: var(--muted); text-align: right; white-space: nowrap; font-size: 19px; }
.tk { position: relative; height: 14px; border-radius: 7px; background: rgba(238, 240, 246, .05); }
.tk i { position: absolute; top: 0; height: 14px; min-width: 5px; border-radius: 7px; background: var(--ivory); transform: scaleX(0); transform-origin: left; transition: transform .6s cubic-bezier(.3, .6, .2, 1); transition-delay: var(--d); }
.tk i.llm { background: var(--blue); } .tk i.on { transform: none; }
.r.bad .nm, .r.bad .dt { color: var(--fail); font-weight: 600; }
.r.bad .tk i { background: var(--fail); box-shadow: 0 0 22px rgba(255, 92, 98, .9); animation: throb 1.4s ease-in-out infinite; }
@keyframes throb { 50% { box-shadow: 0 0 40px rgba(255, 92, 98, 1); filter: brightness(1.25); } }
.grader { left: 100px; right: 100px; top: 790px; padding: 18px 28px; }
.grader .tag { margin-bottom: 6px; font-size: 17px; }
.grader p { font-size: 26px; font-weight: 500; line-height: 1.25; }
.sr { font-size: 21px !important; font-weight: 400 !important; color: var(--muted); margin-top: 4px !important; } .sr span { font-family: var(--sans); }
</style>
