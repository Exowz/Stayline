<script setup lang="ts">
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
</script>

<template><main class="slide beat-seven">
  <div class="eyebrow">07 / Memory</div>
  <Kin text="An alias is a *hint*" :on="active" />
  <div class="row section">
    <Island class="run-one"><h2>Run 1</h2><p class="quote">"Orion is instruction 2026/00417 at the Paris court"</p><div class="arrow">↓</div><div class="memory-block">Memory, per operator</div></Island>
    <Island class="run-two reveal" :class="{ on: shown(1) }"><h2>Run 2, a new session</h2><p class="quote">"A request came in on the Orion contract, process it."</p>
      <div class="outcomes">
        <div class="with"><strong>✓ With memory</strong><p>Finds the seized contract and handles the request</p></div>
        <div class="without"><strong>Without memory</strong><p>Ambiguous: asks, and changes nothing</p></div>
      </div></Island>
  </div>
  <Island class="footer-line"><p>The alias is a hint. Current records decide. Tool text cannot write memory.</p></Island>
</main></template>
<style scoped>
.row .island { min-height: 420px; display: flex; flex-direction: column; }
.quote { font-size: 34px; color: var(--ink-muted); }
.arrow { text-align: center; font-size: 56px; line-height: 1; margin: auto 0 14px; }
.memory-block { background: var(--second); color: var(--white); border-radius: 18px; padding: 20px; text-align: center; font-size: 34px; font-weight: 600; }
.outcomes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: auto; }
.outcomes > div { border-radius: 20px; padding: 18px 22px; min-height: 190px; }
.outcomes strong { font-size: 34px; font-weight: 650; }
.outcomes p { font-size: 31px; margin-top: 8px; }
.with { background: var(--second); color: var(--white); }
.without { background: color-mix(in oklab, var(--second) 7%, var(--white)); box-shadow: inset 0 0 0 1.5px var(--line); }
.footer-line { margin-top: 24px; padding: 20px 32px; }
.footer-line p { font-size: 34px; }
</style>
