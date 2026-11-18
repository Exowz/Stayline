<script setup lang="ts">
import { computed } from 'vue'
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, click, shown } = useBeat()
const moments = ['Run starts and only reads', 'Approval card asks a human', 'Approve, write, read back', 'Proof from trace and database']
const shot = computed(() => Math.max(1, Math.min(4, click.value)))
const trace = deck.traces.s01
</script>

<template><main class="slide beat-five">
  <div class="eyebrow">05 / Live demo: success</div>
  <Kin text="A freeze with *proof*" :on="active" />
  <div class="demo-grid section">
    <Island class="screenshot">
      <img v-for="n in 4" :key="n" v-show="shot === n" :src="`/media/demo-${n}.png`" :alt="`Live demo, moment ${n}`" />
    </Island>
    <div class="side">
      <Island class="scenario"><strong class="mono">s01</strong><span>A clean seizure notice, on the base seed</span></Island>
      <Island v-for="(moment, index) in moments" :key="moment" class="moment" :class="{ done: shown(index + 1) }"><span class="mark">{{ shown(index + 1) ? '✓' : index + 1 }}</span>{{ moment }}</Island>
      <Island class="proof reveal" :class="{ on: shown(4) }">
        <div><strong>{{ trace.model_calls }}</strong><span>model calls</span></div>
        <div><strong>{{ trace.tool_calls }}</strong><span>tool calls</span></div>
        <div><strong>{{ (trace.total_tokens_in + trace.total_tokens_out).toLocaleString() }}</strong><span>tokens</span></div>
        <div><strong>${{ trace.total_cost_usd.toFixed(4) }}</strong><span>cost</span></div>
      </Island>
    </div>
  </div>
</main></template>
<style scoped>
.demo-grid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 26px; align-items: start; }
.screenshot { padding: 12px; aspect-ratio: 1024 / 640; display: grid; }
.screenshot img { grid-area: 1 / 1; width: 100%; height: 100%; object-fit: cover; border-radius: 18px; }
.side { display: grid; gap: 14px; }
.scenario { padding: 14px 24px; display: flex; gap: 18px; align-items: baseline; font-size: 30px; }
.moment { padding: 12px 22px; display: flex; align-items: center; gap: 18px; font-size: 31px; opacity: .5; transition: opacity .4s; }
.moment.done { opacity: 1; }
.mark { width: 42px; height: 42px; border-radius: 50%; display: grid; place-content: center; background: var(--second); color: var(--white); flex: none; font-size: 26px; }
.proof { padding: 14px 18px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }
.proof strong { display: block; font: 650 34px/1.1 'JetBrains Mono Variable'; font-variant-numeric: tabular-nums; }
.proof span { font-size: 26px; color: var(--ink-muted); }
</style>
