<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const a = deck.summary, b = deck.mistral_summary
const better = (x: number, y: number, lower = false) => (lower ? x < y : x > y)
</script>

<template><main class="slide beat-ten">
  <div class="eyebrow">10 / A second model, and the close</div>
  <Kin text="The *right* model" :on="active" />
  <div class="compare reveal" :class="{ on: shown(1) && !shown(2) }">
    <Island><h2>DeepSeek Flash</h2><div class="stats">
      <div><strong>{{ better(a.passed, b.passed) ? '✓ ' : '' }}{{ a.passed }} / {{ a.runs }}</strong><span>passed</span></div>
      <div><strong>{{ better(a.cost_per_success, b.cost_per_success, true) ? '✓ ' : '' }}${{ a.cost_per_success.toFixed(4) }}</strong><span>per success</span></div>
      <div><strong>{{ better(a.latency_s['50'], b.latency_s['50'], true) ? '✓ ' : '' }}{{ a.latency_s['50'].toFixed(1) }} s</strong><span>median</span></div></div></Island>
    <Island><h2>Mistral Small</h2><div class="stats">
      <div><strong>{{ better(b.passed, a.passed) ? '✓ ' : '' }}{{ b.passed }} / {{ b.runs }}</strong><span>passed</span></div>
      <div><strong>{{ better(b.cost_per_success, a.cost_per_success, true) ? '✓ ' : '' }}${{ b.cost_per_success.toFixed(4) }}</strong><span>per success</span></div>
      <div><strong>{{ better(b.latency_s['50'], a.latency_s['50'], true) ? '✓ ' : '' }}{{ b.latency_s['50'].toFixed(1) }} s</strong><span>median</span></div></div></Island>
  </div>
  <div class="bonuses reveal" :class="{ on: shown(1) && !shown(2) }"><span class="chip">Failure injected into a tool</span><span class="chip">The interface you saw</span></div>
  <Island class="limits reveal" :class="{ on: shown(1) && !shown(2) }">Limits: mock feed · one operator at a time · always-yes approver</Island>
  <Island class="closing reveal" :class="{ on: shown(2) }"><p>An AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more.</p><strong>Thank you</strong></Island>
</main></template>
<style scoped>
.compare { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; margin-top: 34px; }
.compare .island { padding: 22px 30px 24px; }
.compare h2 { font-size: 38px; margin-bottom: 10px; }
.stats { display: flex; justify-content: space-between; gap: 18px; }
.stats strong { display: block; font: 650 40px/1.1 'JetBrains Mono Variable'; font-variant-numeric: tabular-nums; }
.stats span { font-size: 28px; color: var(--ink-muted); }
.bonuses { position: absolute; left: 176px; right: 176px; top: 730px; display: flex; gap: 20px; }
.limits { position: absolute; left: 176px; right: 176px; top: 800px; padding: 14px 28px; font-size: 30px; }
.closing { position: absolute; left: 270px; right: 270px; top: 330px; text-align: center; padding: 75px 80px; }
.closing p { font-size: 52px; line-height: 1.2; }
.closing strong { display: block; font-size: 40px; margin-top: 42px; }
</style>
