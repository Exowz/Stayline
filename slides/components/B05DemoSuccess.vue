<script setup lang="ts">
import { computed, ref } from 'vue'
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, click, shown } = useBeat()
const moments = ['Run starts and only reads', 'Approval card asks a human', 'Approve, write, read back', 'Proof from trace and database']
const screenshot = computed(() => `/media/demo-${Math.max(1, Math.min(4, click.value))}.png`)
const missing = ref(true)
const hideBroken = () => { missing.value = true }
const showLoaded = () => { missing.value = false }
const trace = deck.traces.s01
</script>

<template><main class="slide beat-five">
  <div class="eyebrow">05 / Live demo: success</div>
  <Kin text="A freeze with *proof*" :on="active" />
  <div class="demo-grid section">
    <div>
      <Island><h2 class="mono">s01 · clean seizure notice</h2><p>Base seed. The notice names the contract.</p></Island>
      <Island class="screenshot"><img v-show="!missing" :key="screenshot" :src="screenshot" alt="Live demo moment screenshot" @error="hideBroken" @load="showLoaded" /><Island v-if="click === 2 && missing" tone="loud" class="approval-preview"><strong>Approval needed</strong><p>Confirm the contract and five restrictions before writing.</p></Island><span>Live browser demo</span></Island>
    </div>
    <div class="moments">
      <Island v-for="(moment, index) in moments" :key="moment" class="moment" :class="{ done: shown(index + 1) }"><span class="mark">{{ shown(index + 1) ? '✓' : index + 1 }}</span>{{ moment }}</Island>
    </div>
  </div>
  <Island class="proof reveal" :class="{ on: shown(4) }"><strong>Trace proof</strong><span>{{ trace.model_calls }} model calls</span><span>{{ trace.tool_calls }} tool calls</span><span>{{ (trace.total_tokens_in + trace.total_tokens_out).toLocaleString() }} tokens</span><span>${{ trace.total_cost_usd.toFixed(4) }}</span><span>{{ (trace.total_ms / 1000).toFixed(1) }} s</span></Island>
</main></template>
<style scoped>
.demo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; }
.demo-grid > div { min-width: 0; }
.demo-grid h2 { font-size: 30px; }
.screenshot { height: 315px; margin-top: 20px; display: grid; place-items: center; position: relative; overflow: hidden; }
.screenshot img { max-width: 100%; max-height: 100%; object-fit: contain; }
.screenshot span { position: absolute; bottom: 18px; left: 30px; font-size: 26px; }
.approval-preview { padding: 24px; width: 100%; font-size: 28px; }
.approval-preview p { font-size: 26px; margin-top: 15px; }
.moments { display: grid; gap: 15px; }
.moment { padding: 16px 25px; display: flex; align-items: center; gap: 20px; font-size: 29px; opacity: .5; transition: opacity .4s; }
.moment.done { opacity: 1; }
.mark { width: 44px; height: 44px; border-radius: 50%; display: grid; place-content: center; background: var(--second); color: var(--white); flex: none; }
.proof { margin-top: 20px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font: 600 27px 'JetBrains Mono Variable'; }
.proof strong { font-family: 'Onest Variable'; }
</style>
