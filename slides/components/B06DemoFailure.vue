<script setup lang="ts">
import { computed } from 'vue'
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const trace = deck.traces.s14
const graderLine = deck.s14.reason.replace(/^state: /, '').split('; ')[0]
const rows = computed(() => trace.spans.map((span, index) => ({ ...span, last: span.kind === 'LLM' && span.tokens_out === 4000,
  left: `${span.t0_ms / trace.total_ms * 100}%`, width: `${Math.max(span.ms / trace.total_ms * 100, 0.8)}%`, index })))
</script>

<template><main class="slide beat-six">
  <div class="eyebrow">06 / Live demo: failure</div>
  <Kin text="The first *wrong* span" :on="active" />
  <Island class="scenario reveal" :class="{ on: shown(1) }"><strong class="mono">s14 · memory scenario</strong><span>Orion request, final run, repeat 2</span></Island>
  <Island class="waterfall reveal" :class="{ on: shown(2) }">
    <div class="trace-head"><strong>Trace waterfall</strong><span class="mono">{{ (trace.total_ms / 1000).toFixed(1) }} s total</span></div>
    <div v-for="row in rows" :key="row.index" class="trace-row" :class="{ failed: row.last }">
      <span class="mono">{{ row.name === 'complete' ? 'model call' : row.name }}</span>
      <div class="track"><i :class="row.kind.toLowerCase()" :style="{ left: row.left, width: row.width }" /></div>
      <span class="trace-detail mono">{{ row.last ? `${row.tokens_out.toLocaleString()} tokens, ${Math.round(row.ms / 1000)} s, empty reply` : `${Math.round(row.ms)} ms` }}</span>
    </div>
  </Island>
  <Island tone="fail" class="grader reveal" :class="{ on: shown(3) }"><strong>Grader: {{ graderLine }}</strong><span class="mono">stop_reason: {{ deck.s14.stop_reason }}</span></Island>
  <Island class="lesson reveal" :class="{ on: shown(4) }">A reasoning model spent its reply budget thinking. The run ends as an error.</Island>
</main></template>
<style scoped>
.scenario { position: absolute; top: 270px; left: 176px; right: 176px; display: flex; justify-content: space-between; gap: 20px; padding: 12px 26px; font-size: 28px; }
.waterfall { position: absolute; top: 345px; left: 176px; right: 176px; padding: 12px 22px; }
.trace-head { display: flex; justify-content: space-between; font-size: 27px; margin-bottom: 5px; }
.trace-row { display: grid; grid-template-columns: 320px 1fr 520px; gap: 16px; align-items: center; height: 29px; font-size: 27px; line-height: 1; }
.trace-row .mono { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.track { position: relative; height: 17px; border-radius: 8px; background: color-mix(in oklab, var(--second) 6%, transparent); }
.track i { position: absolute; top: 1px; height: 15px; min-width: 5px; border-radius: 8px; background: var(--second); }
.track i.llm { background: var(--ink-muted); }
.failed { color: var(--fail); font-weight: 650; }
.failed .track i.llm { background: var(--fail); }
.grader { position: absolute; top: 810px; left: 176px; right: 176px; display: flex; justify-content: space-between; gap: 24px; align-items: center; padding: 12px 25px; font-size: 26px; }
.grader strong { max-width: 1100px; }
.lesson { position: absolute; top: 915px; left: 176px; right: 176px; padding: 7px 20px; font-size: 26px; line-height: 1.1; }
</style>
