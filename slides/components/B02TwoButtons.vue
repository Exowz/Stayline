<script setup lang="ts">
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
</script>

<template><main class="slide beat-two">
  <div class="eyebrow">02 / Two dangerous buttons</div>
  <Kin text="Two *dangerous* buttons" :on="active" />
  <div class="row section">
    <Island class="reveal" :class="{ on: shown(1) }"><h2>Block a contract</h2><p>Freeze the wrong one and an innocent client loses access.</p></Island>
    <Island class="reveal" :class="{ on: shown(2) }"><h2>Pay out a rachat or advance</h2><p>If the contract is seized, that money must stay inside.</p></Island>
  </div>
  <Island class="gauge reveal" :class="{ on: shown(3) }">
    <div class="zones">
      <div class="zone bad"><strong>Blocking too little</strong><span>fails</span></div>
      <div class="zone good"><strong>Exactly what the law lists</strong><span>passes</span></div>
      <div class="zone bad"><strong>Blocking too much</strong><span>fails</span></div>
    </div>
    <p>The grader reads the final state of the database.</p>
  </Island>
</main></template>
<style scoped>
.row .island { min-height: 250px; }
.gauge { margin-top: 28px; }
.zones { display: grid; grid-template-columns: 1fr 1.5fr 1fr; gap: 10px; }
.zone { display: flex; flex-direction: column; gap: 4px; align-items: center; justify-content: center; text-align: center; min-height: 128px; border-radius: 20px; padding: 14px; font-size: 32px; }
.zone strong { font-weight: 650; }
.zone span { font-size: 28px; font-weight: 600; }
.zone.bad { background: var(--fail-tint); box-shadow: inset 0 0 0 2px var(--fail); color: var(--second); }
.zone.bad span { color: var(--fail); }
.zone.good { background: var(--second); color: var(--white); }
.gauge p { margin-top: 20px; text-align: center; }
</style>
