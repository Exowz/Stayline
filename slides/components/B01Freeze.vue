<script setup lang="ts">
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const restrictions = [
  ['Rachat', 'withdrawal'], ['Renonciation', 'cancellation'], ['Nantissement', 'pledge'],
  ['Acceptation of beneficiary', 'acceptance'], ['Avance', 'advance'],
]
</script>

<template><main class="slide beat-one">
  <div class="eyebrow">01 / The freeze</div>
  <Kin text="*Stayline*" :on="active" />
  <p class="subtitle">An agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more.</p>
  <Island class="names">Khadidja and Ewan</Island>
  <Island class="notice reveal" :class="{ on: shown(1) }"><strong>Notice N-2026-0417</strong><span class="mono">CPP 706-155 · Tribunal judiciaire de Paris</span></Island>
  <div class="restriction-row">
    <span v-for="(item, index) in restrictions" :key="item[0]" class="chip reveal" :class="{ on: shown(index + 2) }"><b class="tick">✓</b>{{ item[0] }} <small>({{ item[1] }})</small></span>
  </div>
</main></template>

<style scoped>
.beat-one .kin { font-size: 134px; }
.names { display: inline-block; margin-top: 26px; padding: 12px 24px; font-size: 30px; font-weight: 600; }
.notice { position: absolute; left: 176px; right: 176px; top: 475px; display: flex; justify-content: space-between; gap: 25px; font-size: 31px; }
.restriction-row { position: absolute; left: 176px; right: 176px; top: 630px; display: flex; flex-wrap: wrap; gap: 16px; }
.restriction-row .chip { font-size: 27px; }
.restriction-row small { font-size: 26px; }
</style>
