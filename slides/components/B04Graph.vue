<script setup lang="ts">
import { useBeat } from './useBeat'
import { useCount } from './useCount'
import Headline from './Headline.vue'
import { LOOP, STAGES } from '../world/formations'

const { shown, print } = useBeat()
const stages = [
  ['prepare', 'Re-reads the contract and builds the approval card from the backend.'],
  ['approve', 'The graph pauses on an interrupt. Nothing is written before it.'],
  ['write', 'Uses the exact version the human saw.'],
  ['verify', 'Reads the contract back to confirm.'],
]
const calls = useCount(() => 10, () => shown(3), () => print.value, 1.4)
</script>

<template><main class="slide">
  <Headline :page="4" eyebrow="The agent" before="A free loop, a " emphasis="gated" after=" write" />

  <div class="loopcap rv rv-s" :class="{ on: shown(1) }" :style="{ left: `${LOOP.x - 200}px`, top: `${LOOP.y - 52}px` }">
    <span class="tag">free loop</span>
    <p>The model reads, searches and calls tools.</p>
  </div>
  <div class="ring-l mono rv" :class="{ on: shown(1) }" :style="{ left: `${LOOP.x - 40}px`, top: `${LOOP.y - LOOP.ry - 58}px` }">model</div>
  <div class="ring-l mono rv" :class="{ on: shown(1) }" :style="{ left: `${LOOP.x - 36}px`, top: `${LOOP.y + LOOP.ry + 30}px` }">tools</div>

  <div v-for="(s, i) in stages" :key="s[0]" class="stage rv" :class="{ on: shown(2), gate: i === 1 }" :style="{ left: `${STAGES[i].x - 112}px`, '--d': `${i * 0.2}s` }">
    <span class="mono n">0{{ i + 1 }}</span>
    <b class="mono">{{ s[0] }}</b>
    <p>{{ s[1] }}</p>
  </div>
  <p class="gatecap rv" :class="{ on: shown(2) }"><span class="tag">a dangerous write: code takes over, in four steps</span></p>

  <div class="one rv" :class="{ on: shown(3) }">
    <span class="tag">Why one agent</span>
    <div class="stats">
      <div><span class="big">1</span><span class="lbl">agent, one linear task</span></div>
      <div><span class="big">≈{{ Math.round(calls) }}</span><span class="lbl">tool calls for a full seizure</span></div>
      <div><span class="big">3</span><span class="lbl">budgets in code: steps, model calls, stop reason</span></div>
    </div>
  </div>
</main></template>

<style scoped>
.loopcap { position: absolute; width: 400px; text-align: center; }
.loopcap p { font-size: 26px; color: var(--muted); margin-top: 8px; }
.loopcap .tag { color: var(--blue); }
.ring-l { position: absolute; font-size: 23px; color: var(--blue); letter-spacing: .08em; }
.stage { position: absolute; top: 760px; width: 226px; }
.stage .n { color: var(--blue); font-size: 20px; } .stage b { display: block; font-size: 30px; font-weight: 500; margin: 2px 0 8px; }
.stage p { font-size: 21px; line-height: 1.3; color: var(--muted); }
.stage.gate b { color: var(--blue); }
.gatecap { position: absolute; left: 1010px; top: 560px; }
.one { position: absolute; left: 1030px; top: 215px; width: 800px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 26px; margin-top: 16px; }
.stats .big { display: block; font-size: 120px; }
.stats .lbl { display: block; margin-top: 10px; font: 400 22px/1.3 var(--sans); }
</style>
