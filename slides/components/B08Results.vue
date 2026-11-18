<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const summary = deck.summary
const pct = (value: number) => `${(value * 100).toFixed(1)}%`
const repeats = Math.max(...deck.runs.map(run => run.repeat)) + 1
</script>

<template><main class="slide beat-eight">
  <div class="eyebrow">08 / Results</div>
  <Kin text="*Measured* outcomes" :on="active" />
  <Island class="grid-caption">Each dot is one run: {{ summary.by_kind.reduce((total, kind) => total + kind.scenarios, 0) }} scenarios across, {{ repeats }} repeats down</Island>
  <div class="result-islands">
    <Island class="kinds reveal" :class="{ on: shown(1) }"><strong class="big">{{ summary.passed }} of {{ summary.runs }}</strong><div class="kind-grid"><span v-for="kind in summary.by_kind" :key="kind.kind"><b>{{ kind.kind }}</b><strong class="mono">{{ kind.passed }}/{{ kind.runs }}</strong></span></div></Island>
    <Island class="interval reveal" :class="{ on: shown(2) }"><h2>pass^k: {{ pct(summary.overall.pass_hat_k) }}</h2><div class="range-track"><i class="range-span" :style="{ left: pct(summary.overall.ci_low), width: pct(summary.overall.ci_high - summary.overall.ci_low) }" /><i class="range-mark" :style="{ left: pct(summary.overall.pass_hat_k) }" /></div><p class="small">Wilson 95%: {{ pct(summary.overall.ci_low) }} to {{ pct(summary.overall.ci_high) }}</p></Island>
    <Island class="operating reveal" :class="{ on: shown(3) }"><div><span>Cost per success</span><strong class="mono">${{ summary.cost_per_success.toFixed(4) }}</strong></div><div><span>Latency p50 / p95</span><strong class="mono">{{ summary.latency_s['50'].toFixed(1) }} / {{ summary.latency_s['95'].toFixed(1) }} s</strong></div><div><span>Under-blocking / over-blocking</span><strong class="mono">✓ {{ summary.domain.under_blocking }} / ✓ {{ summary.domain.over_blocking }}</strong></div></Island>
  </div>
</main></template>
<style scoped>
.grid-caption { position: absolute; top: 285px; left: 176px; padding: 11px 22px; font-size: 28px; font-weight: 600; }
.result-islands { position: absolute; top: 610px; left: 176px; right: 176px; display: grid; grid-template-columns: 1.3fr 1fr 1.1fr; gap: 20px; }
.result-islands .island { padding: 24px 26px; min-height: 230px; }
.kind-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 20px; margin-top: 9px; font-size: 26px; }
.kind-grid span, .operating > div { display: flex; justify-content: space-between; gap: 12px; }
.kind-grid b { font-weight: 550; }
.interval h2 { font-size: 32px; }
.interval .small { margin-top: 21px; }
.operating { display: grid; gap: 13px; font-size: 26px; }
.operating strong { white-space: nowrap; }
</style>
